# tasks.py

import requests
from django.db import transaction
from .models import DisposableDomains  # replace 'your_app' with your actual app name

DISPOSABLE_EMAIL_URL = "https://raw.githubusercontent.com/martenson/disposable-email-domains/master/disposable_email_blocklist.conf"

from celery import shared_task

@shared_task
def update_disposable_email_domains():
    print(f"📌 Fetching disposable email domains from: {DISPOSABLE_EMAIL_URL}")

    try:
        response = requests.get(DISPOSABLE_EMAIL_URL, timeout=10)

        if response.status_code == 200:
            domains = [line.strip() for line in response.text.splitlines() if line.strip()]
            
            # Use transaction.atomic to ensure database integrity
            with transaction.atomic():
                # First, clear the old entries (if needed)
                DisposableDomains.objects.all().delete()

                # Bulk create new domain entries
                DisposableDomains.objects.bulk_create([
                    DisposableDomains(domain_name=domain) for domain in domains
                ])

            print(f"✅ {len(domains)} domains saved successfully into the database.")
        else:
            print(f"⚠️ Failed to fetch data. HTTP Status: {response.status_code}")

    except Exception as e:
        print(f"❌ Error updating disposable email list: {e}")
