# LinkedIn Job & Networking Bot 🤖

A Python automation tool that scrapes "Product Manager" jobs from LinkedIn, filters them for uniqueness, and emails you a **Daily Digest**.

The digest includes:
1.  **Top 20 Jobs** (filtered by Company/Location).
2.  **Networking Links**: One-click searches to find **Alumni** or **Locals** at those companies.

## 🚀 Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# OR
pip install selenium webdriver_manager
```

### 2. Configure
1.  Copy `config.example.py` to `config.py`.
2.  Edit `config.py` with your preferences (Keywords, Locations, University).
3.  Add your Gmail info (requires an **App Password**).

### 3. Run Manually
```bash
# Export password if using env var, or hardcode in config (carefully)
export GMAIL_PASSWORD='your_app_password'
python3 daily_digest.py
```

## ⏰ Schedule (Cron)

Use the provided `setup_cron.sh` (or `setup_cron_example.sh` if you make one) to run this daily at 7 AM.

## ⚠️ Safety Note
This bot runs in **read-only** mode (no auto-applying), which drastically reduces the risk of LinkedIn account flagging compared to auto-appliers.
