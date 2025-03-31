"""One-time setup script to authenticate with the college website"""
from selenium import webdriver
import os
import time

# Create profile directory if it doesn't exist
profile_dir = "E:\\data science tool\\chrome_profile"
os.makedirs(profile_dir, exist_ok=True)

# Launch Chrome with this profile
driver = webdriver.Chrome(
    options=webdriver.ChromeOptions().add_argument(f"user-data-dir={profile_dir}")
)

# Open the site
driver.get("https://exam.sanand.workers.dev/tds-2025-01-ga1#hq-use-devtools")

print("Please log in to your account manually in the browser window.")
print("After logging in, wait 10 seconds and this script will save your session.")
print("This saved session will be used for automated checks in the future.")

# Wait for manual login
time.sleep(120)  # 2 minutes to log in

# Save the cookies and close
driver.quit()
print(f"Authentication saved to {profile_dir}")
print("You can now run the automated tests without visible browser windows.")