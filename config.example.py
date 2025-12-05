
# config.py template
# Rename this file to 'config.py' and fill in your details.

import os

# Job preferences
KEYWORDS = ["Product Manager"]
LOCATIONS = ["Austin, TX", "San Francisco, CA", "United States"]

# Networking / Referral settings
UNIVERSITY = "University of Texas at Austin" 

# Email Settings
# You need a Gmail App Password for this to work.
SENDER_EMAIL = "your_email@gmail.com"
RECEIVER_EMAIL = "recipient_email@gmail.com"

# Set this environment variable or hardcode (not recommended for public repos)
EMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD") 

# Bot settings
MIN_DELAY = 3
MAX_DELAY = 7
HEADLESS = False
OUTPUT_FILE = "daily_digest.html"
