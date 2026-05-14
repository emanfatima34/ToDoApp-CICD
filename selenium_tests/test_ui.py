"""
UI tests for TaskMaster (home + register flow).
Run on the Jenkins host via Docker (--network host) so http://127.0.0.1:5000 reaches the app.
"""
import os
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _build_driver():
    opts = Options()
    if os.environ.get("SELENIUM_HEADLESS", "1").lower() in ("1", "true", "yes"):
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,900")

    # Linux / Docker image (chromium + chromium-driver packages)
    if os.path.isfile("/usr/bin/chromium"):
        opts.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        # Local dev: Chrome/Chromium from PATH (Selenium resolves driver when possible)
        service = Service()

    return webdriver.Chrome(service=service, options=opts)


def main():
    base = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5000")
    driver = _build_driver()
    wait = WebDriverWait(driver, 20)
    try:
        # Test 1: Home page loads and title matches TaskMaster branding
        driver.get(f"{base}/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        title = driver.title
        assert "TaskMaster" in title, f"Expected TaskMaster in title, got: {title!r}"

        # Test 2: Navigate to registration via primary CTA
        register = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Welcome! Get Started"))
        )
        register.click()
        wait.until(EC.title_contains("Create"))
        assert "Create Account" in driver.title

        # Test 3: Registration form is present (extra coverage for assignment minimum)
        wait.until(EC.presence_of_element_located((By.NAME, "username")))
    finally:
        driver.quit()

    print("Selenium tests passed.", file=sys.stderr)


if __name__ == "__main__":
    main()
