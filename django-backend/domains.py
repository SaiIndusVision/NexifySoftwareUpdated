import os
import re
import requests

# Define the file path where disposable email domains will be stored
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the script's directory
DISPOSABLE_EMAIL_FILE = os.path.join(BASE_DIR, "disposable_emails.txt")
DISPOSABLE_EMAIL_URL = "https://raw.githubusercontent.com/martenson/disposable-email-domains/master/disposable_email_blocklist.conf"

# Regex for common disposable email services
DISPOSABLE_EMAIL_REGEX = re.compile(
    r"@(yopmail\.com|mailinator\.com|tempmail\.net|dispostable\.com|guerrillamail\.com|10minutemail\.com)$",
    re.IGNORECASE,
)

# Function to update the disposable email list and store it locally
def update_disposable_email_domains():
    print(f"📌 Fetching disposable email domains from: {DISPOSABLE_EMAIL_URL}")

    try:
        response = requests.get(DISPOSABLE_EMAIL_URL, timeout=10)

        if response.status_code == 200:
            with open(DISPOSABLE_EMAIL_FILE, "w") as f:
                f.write(response.text)
            print(f"✅ File saved successfully at: {DISPOSABLE_EMAIL_FILE}")
        else:
            print(f"⚠️ Failed to fetch data. HTTP Status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error updating disposable email list: {e}")

# Function to load disposable email domains from file
def load_disposable_email_domains():
    if not os.path.exists(DISPOSABLE_EMAIL_FILE):
        print(f"⚠️ Disposable email file not found: {DISPOSABLE_EMAIL_FILE}")
        return set()  # Return empty set if the file doesn't exist

    with open(DISPOSABLE_EMAIL_FILE, "r") as f:
        return set(line.strip() for line in f.readlines() if line.strip())

# Function to check if an email is disposable
def is_disposable_email(email):
    domain = email.split("@")[-1]
    disposable_domains = load_disposable_email_domains()
    return domain in disposable_domains or bool(DISPOSABLE_EMAIL_REGEX.search(email))

# Run the update function (Only update when needed)
if __name__ == "__main__":
    update_disposable_email_domains()
