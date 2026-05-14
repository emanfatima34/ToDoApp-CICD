# Headless browser + Selenium for CI (Jenkins runs this image with --network host).
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir selenium

COPY selenium_tests/ ./selenium_tests/

ENV SELENIUM_HEADLESS=1

CMD ["python3", "selenium_tests/test_ui.py"]
