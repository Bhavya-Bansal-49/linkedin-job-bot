
# config.py

import os

# Job preferences
KEYWORDS = ["Product Manager"]
LOCATIONS = ["Austin, TX", "San Francisco, CA", "United States"]

# Networking / Referral settings
UNIVERSITY = "University of Texas at Austin" 

# Email Settings
SENDER_EMAIL = "bhavya4995bansal@gmail.com"
RECEIVER_EMAIL = "bhavyabansalai@gmail.com"
EMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD") # Must be set in environment

# LinkedIn Credentials (Required for Cloud/Headless)
LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Bot settings
# Minimum seconds to wait between actions
MIN_DELAY = 3
MAX_DELAY = 7

# Set to True to run in headless mode (no visible browser window)
HEADLESS = True

# Output path for the HTML digest
OUTPUT_FILE = "daily_digest.html"
