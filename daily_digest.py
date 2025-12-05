
import time
import random
import os
import urllib.parse
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import config

def random_sleep(min_seconds=config.MIN_DELAY, max_seconds=config.MAX_DELAY):
    time.sleep(random.uniform(min_seconds, max_seconds))

def init_driver():
    options = webdriver.ChromeOptions()
    if config.HEADLESS:
        options.add_argument("--headless")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36")
    options.add_argument("--start-maximized")
    
    # Use the same profile directory to keep login state
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
    else:
        print("Already logged in!")

def get_job_search_url(keywords, location):
    base = "https://www.linkedin.com/jobs/search/?"
    params = {
        "keywords": keywords,
        "location": location,
        "sortBy": "R" # Most relevant (Removed Past 24h to ensure results for test)
    }
    return base + urllib.parse.urlencode(params)

def get_people_search_url(company, location=None, school=None):
    # Generates a search link for people at this company
    # location and school are extra keywords to narrow it down
    query = f"{company}"
    if location:
        query += f" {location}"
    if school:
        query += f" {school}"
        
    base = "https://www.linkedin.com/search/results/people/?"
    params = {
        "keywords": query,
        "origin": "GLOBAL_SEARCH_HEADER"
    }
    return base + urllib.parse.urlencode(params)

def scrape_jobs(driver):
    all_jobs = []
    seen_combinations = set() # (company, location) tuples
    
    for loc in config.LOCATIONS:
        print(f"Scraping {loc}...")
        url = get_job_search_url(config.KEYWORDS[0], loc)
        driver.get(url)
        random_sleep(3, 5)
        
        # Scroll a bit to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        random_sleep(2, 3)
        
        # Try multiple common container classes
        job_cards = driver.find_elements(By.CLASS_NAME, "base-search-card")
        if not job_cards:
            job_cards = driver.find_elements(By.CLASS_NAME, "job-search-card")
        
        print(f"Found {len(job_cards)} jobs in {loc}.")
        
        if len(job_cards) == 0:
            print("No jobs found. Taking screenshot to debug...")
            driver.save_screenshot(f"debug_{loc.replace(' ', '_')}.png")
            # Save HTML source
            with open(f"debug_source_{loc.replace(' ', '_')}.html", "w") as f:
                f.write(driver.page_source)
            print("Saved debug source HTML.")
            # break # Keep loop going to try other locations
        
        for card in job_cards[:7]: # Top 7 per location to get ~20 total
            try:
                # Use generalized selectors
                title = card.find_element(By.CLASS_NAME, "base-search-card__title").text.strip()
                company = card.find_element(By.CLASS_NAME, "base-search-card__subtitle").text.strip()
                location = card.find_element(By.CLASS_NAME, "job-search-card__location").text.strip()
                link = card.find_element(By.CLASS_NAME, "base-card__full-link").get_attribute("href")
                
                # Deduplication Logic: Max 1 job per company per location
                # We use the scraped location, which might be slightly different from the search location
                # but "Austin, Texas, United States" vs "Austin, TX" handling is good enough by exact match or simple inclusion.
                combo = (company, location)
                
                if combo in seen_combinations:
                     continue
                
                # Check if already added (link check acts as secondary safety)
                if any(j['link'] == link for j in all_jobs):
                    continue

                seen_combinations.add(combo)
                all_jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link
                })
            except Exception as e:
                # print(f"Skipping card: {e}")
                pass
            except Exception as e:
                # print(f"Skipping card: {e}")
                pass
                
    return all_jobs

def generate_html(jobs):
    html_content = f"""
    <html>
    <head>
        <title>Daily Job Digest - {datetime.date.today()}</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; }}
            h1 {{ border-bottom: 2px solid #0a66c2; padding-bottom: 10px; }}
            .job-card {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; background: #fafafa; }}
            .job-title {{ font-size: 1.2rem; font-weight: bold; color: #004182; text-decoration: none; }}
            .company {{ font-weight: bold; margin-top: 5px; }}
            .meta {{ color: #666; font-size: 0.9rem; margin-top: 5px; }}
            .actions {{ margin-top: 15px; }}
            .btn {{ display: inline-block; padding: 6px 12px; background: #0a66c2; color: white; text-decoration: none; border-radius: 4px; font-size: 0.9rem; margin-right: 10px; }}
            .btn-secondary {{ background: white; color: #0a66c2; border: 1px solid #0a66c2; }}
            .btn:hover {{ opacity: 0.9; }}
        </style>
    </head>
    <body>
        <h1>Job Digest for {datetime.date.today()}</h1>
        <p>Found {len(jobs)} jobs based on your preferences.</p>
    """
    
    for job in jobs:
        # Networking links
        alumni_url = get_people_search_url(job['company'], school=config.UNIVERSITY)
        local_network_url = get_people_search_url(job['company'], location=job['location'])
        
        html_content += f"""
        <div class="job-card">
            <a href="{job['link']}" target="_blank" class="job-title">{job['title']}</a>
            <div class="company">{job['company']}</div>
            <div class="meta">{job['location']}</div>
            
            <div class="actions">
                <a href="{job['link']}" target="_blank" class="btn">View Job</a>
                <a href="{alumni_url}" target="_blank" class="btn btn-secondary">Find Alumni at {job['company']}</a>
                <a href="{local_network_url}" target="_blank" class="btn btn-secondary">Find Locals at {job['company']}</a>
            </div>
        </div>
        """
        
    html_content += "</body></html>"
    
    # Return absolute path for email attachment/reading
    abs_path = os.path.abspath(config.OUTPUT_FILE)
    print(f"Digest generated: {abs_path}")
    return abs_path

def send_email(html_file_path):
    if not config.EMAIL_PASSWORD:
        print("Skipping email: GMAIL_PASSWORD not set.")
        return

    try:
        with open(html_file_path, "r") as f:
            html_content = f.read()

        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = config.RECEIVER_EMAIL
        msg['Subject'] = f"Daily Job Digest: {datetime.date.today()}"

        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config.SENDER_EMAIL, config.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(config.SENDER_EMAIL, config.RECEIVER_EMAIL, text)
        server.quit()
        print(f"Email sent successfully to {config.RECEIVER_EMAIL}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def run():
    print("Starting Daily Digest...")
    driver = init_driver()
    try:
        check_login(driver)
        jobs = scrape_jobs(driver)
        html_path = generate_html(jobs)
        send_email(html_path)
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
