
import time
import random
import os
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import config

def random_sleep(min_seconds=config.MIN_DELAY, max_seconds=config.MAX_DELAY):
    time.sleep(random.uniform(min_seconds, max_seconds))

def init_driver():
    options = webdriver.ChromeOptions()
    if config.HEADLESS:
        options.add_argument("--headless")
    
    # Anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36")
    options.add_argument("--start-maximized")
    
    # Persist profile to save login state
    # Using a local 'profile' directory in the current folder
    current_dir = os.getcwd()
    profile_dir = os.path.join(current_dir, "chrome_profile")
    options.add_argument(f"user-data-dir={profile_dir}")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_login(driver):
    driver.get("https://www.linkedin.com/feed/")
    random_sleep()
    
    if "feed" not in driver.current_url:
        print("Not logged in. Please log in manually in the browser window.")
        input("Press Enter here after you have successfully logged in...")
        driver.get("https://www.linkedin.com/feed/")
    else:
        print("Already logged in!")

def generate_job_search_url(keywords, location):
    base_url = "https://www.linkedin.com/jobs/search/?"
    params = {
        "keywords": keywords,
        "location": location,
        "f_AL": "true"  # Easy Apply filter
    }
    return base_url + urllib.parse.urlencode(params)

def handle_easy_apply(driver):
    print("Attempting to apply...")
    try:
        # Click the Apply button
        apply_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "jobs-apply-button"))
        )
        apply_btn.click()
        random_sleep(1, 3)
        
        # Simple loop to click Next/Review/Submit
        # This is a basic implementation; LinkedIn forms vary wildly.
        submitted = False
        while True:
            try:
                # Check for Submit Application button
                submit_btn = driver.find_elements(By.XPATH, "//button[@aria-label='Submit application']")
                if submit_btn:
                    print("Found Submit button!")
                    # Uncomment logic below to actually submit
                    # submit_btn[0].click()
                    # submitted = True
                    print("-- Dry Run: Not actually clicking Submit --")
                    break

                # Check for Review button
                review_btn = driver.find_elements(By.XPATH, "//button[@aria-label='Review your application']")
                if review_btn:
                    review_btn[0].click()
                    random_sleep(1, 3)
                    continue

                # Check for Next button
                next_btn = driver.find_elements(By.XPATH, "//button[@aria-label='Continue to next step']")
                if next_btn:
                    next_btn[0].click()
                    random_sleep(1, 3)
                    continue
                
                # Check for upload resume input if visible (and if not already present)
                # LinkedIn often pre-fills, but sometimes asks again.
                # Simplification: assuming resume is present if pre-uploaded to LinkedIn
                
                # If we get stuck or no buttons found, break
                print("No obvious buttons found, or form is complex.")
                break
                
            except Exception as e:
                print(f"Error in form interaction: {e}")
                break
        
        # Close modal if not submitted (to move to next job)
        if not submitted:
            try:
                close_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'artdeco-modal__dismiss')]")
                close_btn.click()
                random_sleep(0.5, 1)
                discard_btn = driver.find_element(By.XPATH, "//button[@data-control-name='discard_application_confirm_btn']")
                discard_btn.click()
            except:
                pass
            
    except Exception as e:
        print(f"Could not click initial apply button: {e}")

def run_bot():
    driver = init_driver()
    
    try:
        check_login(driver)
        
        for loc in config.LOCATIONS:
            print(f"Searching in {loc}...")
            search_url = generate_job_search_url(config.KEYWORDS[0], loc)
            driver.get(search_url)
            random_sleep(3, 5)
            
            # Find job cards (left rail)
            job_cards = driver.find_elements(By.CLASS_NAME, "job-card-container")
            print(f"Found {len(job_cards)} jobs on this page.")
            
            for index, card in enumerate(job_cards[:5]): # Limit to 5 per location for safety/testing
                try:
                    # Re-find elements to avoid stale reference
                    current_cards = driver.find_elements(By.CLASS_NAME, "job-card-container")
                    if index >= len(current_cards): break
                    
                    card = current_cards[index]
                    card.click()
                    random_sleep(2, 4)
                    
                    # Handle application
                    handle_easy_apply(driver)
                    
                except Exception as e:
                    print(f"Error processing job card: {e}")
                    continue
                    
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    finally:
        print("Closing driver...")
        driver.quit()

if __name__ == "__main__":
    run_bot()
