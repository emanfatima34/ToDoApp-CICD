from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

driver.get("http://localhost:5000")

print(driver.title)

# Test 1: Check login button exists
assert "TaskMaster" in driver.title

# Test 2: Click register link
register = driver.find_element(By.LINK_TEXT, "Welcome! Get Started")
register.click()

time.sleep(2)

driver.quit()