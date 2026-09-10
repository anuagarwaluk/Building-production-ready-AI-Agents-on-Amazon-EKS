"""Pytest path setup: allow 'import src...' when running tests from this directory."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
