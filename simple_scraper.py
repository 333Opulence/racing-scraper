#!/usr/bin/env python3
"""
Simple working scraper for punters.com.au using requests and BeautifulSoup
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import csv
import os

def fetch_page(url):
    """Fetch URL with headers to avoid blocking"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def scrape_today():
    """Scrape today's race results"""
    today = datetime.now().strftime('%Y/%m/%d')
    url = f"https://www.punters.com.au/racing-results/{today}/"
    
    print(f"Fetching: {url}")
    html = fetch_page(url)
    
    if not html:
        print("Failed to fetch page")
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    # Find all race meetings
    meetings = soup.find_all('div', class_='race-meetings-desktop')
    
    if not meetings:
        meetings = soup.find_all('div', attrs={'id': lambda x: x and x.startswith('country-')})
    
    print(f"Found {len(meetings)} meetings")
    
    for meeting in meetings:
        # Get venue name
        venue_elem = meeting.find('a', class_='race-meetings-desktop__meeting-name')
        if not venue_elem:
            venue_elem = meeting.find('h3', class_='race-meetings-desktop__meeting-name')
        venue = venue_elem.text.strip() if venue_elem else 'Unknown'
        
        # Get track condition
        track_elem = meeting.find('div', class_='track-condition')
        track_condition = track_elem.text.strip() if track_elem else 'Unknown'
        
        # Get all races
        events = meeting.find_all('td', class_='race-meetings-desktop__event')
        
        for event in events:
            # Get race name
            race_name_elem = event.find('span', class_='race-name')
            race_name = race_name_elem.text.strip() if race_name_elem else ''
            
            # Get link to race details
            link = event.find('a')
            race_url = ''
            if link:
                href = link.get('href', '')
                if href:
                    race_url = f"https://www.punters.com.au{href}"
            
            # Get top 3 cloth numbers from results span
            results_span = event.find('span', class_='event-status__results')
            cloth_numbers = []
            if results_span:
                results_text = results_span.text.strip()
                cloth_numbers = results_text.split(',')
            
            results.append({
                'date': datetime.now().strftime('%Y-%m-%d'),
                'venue': venue,
                'race_name': race_name,
                'track_condition': track_condition,
                'winner_cloth': cloth_numbers[0] if len(cloth_numbers) > 0 else '',
                'runnerup_cloth': cloth_numbers[1] if len(cloth_numbers) > 1 else '',
                'third_cloth': cloth_numbers[2] if len(cloth_numbers) > 2 else '',
                'race_url': race_url
            })
    
    return results

def main():
    print("Starting scraper...")
    results = scrape_today()
    
    if results:
        # Save to CSV
        filename = f"racing_results_{datetime.now().strftime('%Y%m%d')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Saved {len(results)} races to {filename}")
        
        # Print summary
        for r in results:
            print(f"  {r['venue']}: {r['race_name']} - Winner cloth: {r['winner_cloth']}")
    else:
        print("No results found")

if __name__ == "__main__":
    main()