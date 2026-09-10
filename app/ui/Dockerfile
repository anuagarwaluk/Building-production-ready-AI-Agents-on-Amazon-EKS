FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md app.py ./
RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8080", "--headless"]
