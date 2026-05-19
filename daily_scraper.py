#!/usr/bin/env python3
"""
Daily Incremental Scraper - Only fetches TODAY's races
Runs in under 2 minutes every day
"""

import os
import sys
from datetime import datetime
import pandas as pd

# Import from main scraper
from racing_scraper_complete import setup_scraper, fetch_date_races

def main():
    today = datetime.now().date()
    print(f"🕐 Running daily scrape for: {today}")
    
    scraper = setup_scraper()
    if not scraper:
        print("❌ Failed to initialize scraper")
        return
    
    results = fetch_date_races(scraper, today)
    
    if not results:
        print(f"⚠️ No races found for {today}")
        return
    
    # Save daily file
    daily_file = f"daily_results_{today}.csv"
    df = pd.DataFrame(results)
    df.to_csv(daily_file, index=False, encoding='utf-8-sig')
    print(f"✅ Saved {len(results)} races to {daily_file}")
    
    # Append to master file
    master_file = "racing_data_complete/racing_results_complete.csv"
    os.makedirs("racing_data_complete", exist_ok=True)
    
    if os.path.exists(master_file):
        existing = pd.read_csv(master_file)
        combined = pd.concat([existing, df], ignore_index=True)
        combined = combined.drop_duplicates(subset=['Date', 'Course', 'Race Name'])
        combined.to_csv(master_file, index=False, encoding='utf-8-sig')
        print(f"✅ Appended to master file. Total rows: {len(combined)}")
    else:
        df.to_csv(master_file, index=False, encoding='utf-8-sig')
        print(f"✅ Created master file with {len(df)} rows")

if __name__ == "__main__":
    main()