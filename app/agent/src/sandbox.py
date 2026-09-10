"""Sandboxed tools from Amazon Bedrock AgentCore (integrated track).

The self-managed track keeps every tool inside the cluster. The two tools
here move risky work OUT of the cluster into managed, isolated sandboxes:

  execute_python  ->  AgentCore Code Interpreter (isolated session)
  browse_url      ->  AgentCore Browser (managed cloud browser)

The agent pod needs no extra containers, no Chrome install, and no code
execution rights of its own. Credentials come from EKS Pod Identity.

Requires the bedrock-agentcore SDK (see pyproject, extra "agentcore").
"""

import json
import logging
import os

from strands import tool

logger = logging.getLogger(__name__)

REGION = os.getenv("AWS_REGION", "us-west-2")


@tool
def execute_python(code: str) -> str:
    """Run Python code in an isolated managed sandbox and return the output.

    Use for precise arithmetic (order totals, refunds, comparisons) or any
    computation the customer asks for. The sandbox has no access to the
    cluster or customer systems.

    Args:
        code: Python code to execute. Print what should be returned.
    """
    try:
        from bedrock_agentcore.tools.code_interpreter_client import code_session
    except ImportError:
        return "Code Interpreter SDK not installed (pip install bedrock-agentcore)."

    try:
        with code_session(REGION) as client:
            response = client.invoke(
                "executeCode",
                {"code": code, "language": "python", "clearContext": False},
            )
            for event in response["stream"]:
                return json.dumps(event["result"], default=str)
        return "No result returned from the sandbox."
    except Exception as e:
        logger.error("Code Interpreter failed: %s", e)
        return f"Code execution failed: {e}"


@tool
def browse_url(url: str, instruction: str) -> str:
    """Visit a public web page in a managed cloud browser sandbox and
    extract information from it.

    Use for live information that is not in the catalogue, such as a
    carrier's public tracking page. Never send credentials or customer
    personal data to a page.

    Args:
        url: The public URL to open
        instruction: What to look for on the page
    """
    try:
        from bedrock_agentcore.tools.browser_client import browser_session
    except ImportError:
        return "Browser SDK not installed (pip install bedrock-agentcore)."

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Playwright not installed; the browser tool needs it to drive the sandbox."

    try:
        with browser_session(REGION) as client:
            ws_url, headers = client.generate_ws_headers()
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(ws_url, headers=headers)
                page = browser.contexts[0].pages[0] if browser.contexts and browser.contexts[0].pages else browser.new_page()
                page.goto(url, timeout=30000)
                text = page.inner_text("body")[:4000]
                browser.close()
        return f"Page content from {url} (task: {instruction}):\n{text}"
    except Exception as e:
        logger.error("Browser sandbox failed: %s", e)
        return f"Browsing failed: {e}"
