import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import time
import os
import re

def get_race_results(date):
    """Fetch race results for a specific date"""
    url = f"https://www.punters.com.au/racing-results/{date.strftime('%Y/%m/%d')}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        meetings = soup.find_all('div', class_='race-meetings-desktop')
        
        if not meetings:
            return []
        
        all_races = []
        
        for meeting in meetings:
            # Get venue name
            venue_elem = meeting.find('a', class_='race-meetings-desktop__meeting-name')
            if not venue_elem:
                venue_elem = meeting.find('h3', class_='race-meetings-desktop__meeting-name')
            venue = venue_elem.text.strip() if venue_elem else 'Unknown'
            
            # Get track condition
            track_elem = meeting.find('div', class_='track-condition')
            track_condition = track_elem.text.strip() if track_elem else 'Unknown'
            
            # Get going code
            going_code = ''
            if 'good' in track_condition.lower():
                going_code = 'G'
            elif 'soft' in track_condition.lower():
                going_code = 'S'
            elif 'heavy' in track_condition.lower():
                going_code = 'H'
            
            # Get country
            country = 'Australia'
            if 'uk' in url.lower() or 'carlisle' in venue.lower():
                country = 'United Kingdom'
            elif 'ire' in url.lower() or 'roscommon' in venue.lower():
                country = 'Ireland'
            elif 'france' in url.lower() or 'chantilly' in venue.lower():
                country = 'France'
            elif 'south africa' in url.lower() or 'kenilworth' in venue.lower():
                country = 'South Africa'
            elif 'usa' in url.lower() or 'finger lakes' in venue.lower():
                country = 'United States'
            elif 'japan' in url.lower() or 'kanazawa' in venue.lower():
                country = 'Japan'
            
            # Get all races at this meeting
            events = meeting.find_all('td', class_='race-meetings-desktop__event')
            
            for event in events:
                # Get race name
                race_name_elem = event.find('span', class_='race-name')
                race_name = race_name_elem.text.strip() if race_name_elem else ''
                
                # Get off time
                off_time_elem = event.find('abbr', class_='event-status__time')
                off_time = off_time_elem.text.strip() if off_time_elem else ''
                
                # Get top 3 cloth numbers
                results_span = event.find('span', class_='event-status__results')
                cloth_numbers = []
                if results_span:
                    cloth_text = results_span.text.strip()
                    cloth_numbers = cloth_text.split(',')
                
                # Get race link
                link = event.find('a')
                race_url = ''
                if link:
                    href = link.get('href', '')
                    if href:
                        race_url = f"https://www.punters.com.au{href}"
                
                # Create race record
                race_record = {
                    'Date': date.strftime('%Y-%m-%d'),
                    'Course': venue,
                    'Country': country,
                    'Surface': 'Turf',
                    'Race Time': '',
                    'Off Time': off_time,
                    'Race Name': race_name,
                    'Class': '',
                    'Age Restrict': '',
                    'Handicap?': 'Yes' if 'handicap' in race_name.lower() else 'No',
                    'Dist Raw': '',
                    'Dist (m)': '',
                    'Going': track_condition,
                    'Going Code': going_code,
                    'Runners': '',
                    'Win Time': '',
                    'Winner': '',
                    'Winner SP': '',
                    'Winner SP Dec': '',
                    'Winner Jockey': '',
                    'Winner Trainer': '',
                    'Winner Cloth': cloth_numbers[0] if len(cloth_numbers) > 0 else '',
                    'Winner Weight': '',
                    'Runner-Up': '',
                    'Runner-Up Cloth': cloth_numbers[1] if len(cloth_numbers) > 1 else '',
                    'Runner-Up Weight': '',
                    'Third': '',
                    'Third Cloth': cloth_numbers[2] if len(cloth_numbers) > 2 else '',
                    'Third Weight': '',
                    'Fourth': '',
                    'Fourth Cloth': '',
                    'Fourth Weight': '',
                    'Fifth': '',
                    'Fifth Cloth': '',
                    'Fifth Weight': '',
                    'Favourite': '',
                    'Fav SP': '',
                    'Fav SP Dec': '',
                    'Fav Position': '',
                    'Fav Jockey': '',
                    'Fav Trainer': ''
                }
                
                all_races.append(race_record)
        
        return all_races
        
    except Exception as e:
        print(f"Error fetching {date}: {e}")
        return []

def main():
    # Get today's date
    today = datetime.now()
    
    print(f"Fetching race results for {today.strftime('%Y-%m-%d')}...")
    
    results = get_race_results(today)
    
    if results:
        # Save to CSV
        filename = f"racing_results_{today.strftime('%Y%m%d')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = results[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Success! Saved {len(results)} races to {filename}")
    else:
        print("❌ No races found for today")

if __name__ == "__main__":
    main()