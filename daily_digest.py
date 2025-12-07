
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
import json

SEEN_JOBS_FILE = "seen_jobs.json"

def clean_url(url):
    return url.split('?')[0]

def load_seen_jobs():
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()
    try:
        with open(SEEN_JOBS_FILE, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, IOError):
        return set()

def save_seen_jobs(new_links):
    seen = load_seen_jobs()
    seen.update(new_links)
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)

    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)


def calculate_score(job):
    score = 0
    
    # 1. Location Scoring
    loc = job['location'].lower()
    if "austin" in loc:
        score += 30
    elif "san francisco" in loc or "bay area" in loc:
        score += 20
    elif "united states" in loc: # Remote/General
        score += 10
        
    # 2. Title/Seniority Scoring
    title = job['title'].lower()
    
    # Penalties for junior roles
    if any(x in title for x in ["intern", "internship", "junior", "jr.", "apprentice"]):
        score -= 20
        
    # Boosts for senior/match roles
    if "product manager" in title: # Exact phrase match (vs just 'manager')
        score += 5
        
    if any(x in title for x in ["senior", "sr.", "principal", "staff", "lead", "head", "director"]):
        score += 10
        
    return score

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
    all_candidates = []
    seen_combinations = set() # (company, location) tuples
    seen_links = load_seen_jobs()

    
    for loc in config.LOCATIONS:
        print(f"Scraping {loc}...")
        url = get_job_search_url(config.KEYWORDS[0], loc)
        driver.get(url)
        random_sleep(3, 5)
        
        # Deep Scroll: Scroll multiple times to load more jobs
        # We want to find enough potential candidates to satisfy the top 20
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5): # Scroll 5 times
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            random_sleep(2, 3)
            
            # Click "See more jobs" if present? (Often infinite scroll is enough for first 100)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        # Try multiple common container classes
        job_cards = driver.find_elements(By.CLASS_NAME, "base-search-card")
        if not job_cards:
            job_cards = driver.find_elements(By.CLASS_NAME, "job-search-card")
        
        print(f"Found {len(job_cards)} total cards in {loc}.")
        
        # Process ALL cards found
        for card in job_cards:
            try:
                # Use generalized selectors
                title = card.find_element(By.CLASS_NAME, "base-search-card__title").get_attribute("innerText").strip()
                company = card.find_element(By.CLASS_NAME, "base-search-card__subtitle").get_attribute("innerText").strip()
                location = card.find_element(By.CLASS_NAME, "job-search-card__location").get_attribute("innerText").strip()
                link = card.find_element(By.CLASS_NAME, "base-card__full-link").get_attribute("href")
                link = clean_url(link)
                
                # Check against historical memory FIRST
                if link in seen_links:
                    continue

                # Deduplication Logic within current run
                combo = (company, location)
                if combo in seen_combinations:
                     continue
                
                # Check link dict uniqueness
                if any(j['link'] == link for j in all_candidates):
                    continue

                seen_combinations.add(combo)
                
                job_data = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "link": link
                }
                
                # Pre-calculate score
                job_data['score'] = calculate_score(job_data)
                
                all_candidates.append(job_data)
                
            except Exception as e:
                # print(f"Skipping card: {e}")
                pass
                
    return all_candidates

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
    
    with open(config.OUTPUT_FILE, "w") as f:
        f.write(html_content)
    
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
        candidates = scrape_jobs(driver)
        
        print(f"Total unique new candidates found: {len(candidates)}")
        
        if not candidates:
            print("No new jobs found today.")
            return

        # Prioritize: Sort by score descending
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Select Top 20
        final_jobs = candidates[:20]
        print(f"Selected top {len(final_jobs)} jobs to send.")

        # Save the new jobs to memory
        new_links = [j['link'] for j in final_jobs]
        save_seen_jobs(new_links)

        html_path = generate_html(final_jobs)
        send_email(html_path)

    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
