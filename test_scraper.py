#!/usr/bin/env python3
"""Simple test scraper to verify punters-client works"""

import sys
from datetime import datetime

print("Python version:", sys.version)
print("Testing punters-client library...")

try:
    import punters_client
    print("✅ punters-client imported successfully")
except ImportError as e:
    print(f"❌ Failed to import punters-client: {e}")
    sys.exit(1)

try:
    import cache_requests
    print("✅ cache-requests imported successfully")
except ImportError as e:
    print(f"❌ Failed to import cache-requests: {e}")

try:
    from lxml import html
    print("✅ lxml imported successfully")
except ImportError as e:
    print(f"❌ Failed to import lxml: {e}")

try:
    import pandas as pd
    print("✅ pandas imported successfully")
except ImportError as e:
    print(f"❌ Failed to import pandas: {e}")

print("\n" + "="*50)
print("All imports successful!")
print("="*50)

# Try to initialize scraper
try:
    import cache_requests
    from lxml import html
    http_client = cache_requests.Session()
    html_parser = html.fromstring
    scraper = punters_client.Scraper(http_client, html_parser)
    print("✅ Scraper initialized successfully")
    
    # Try to fetch today's meets
    today = datetime.now().date()
    print(f"\nAttempting to fetch meets for {today}...")
    meets = scraper.scrape_meets(today)
    print(f"Found {len(meets) if meets else 0} meetings")
    
except Exception as e:
    print(f"❌ Error initializing scraper: {e}")

print("\nTest complete!")