#!/usr/bin/env python3
"""
AUSTRALIAN HORSE RACING RESULTS SCRAPER - COMPLETE 40-COLUMN FETCH
Uses punters-client library to fetch ALL race data including winner, SP, jockey, trainer
"""

import os
import sys
import io
import time
import json
import re
import logging
from datetime import datetime, timedelta
import pandas as pd

# Fix Windows Unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Install required packages if not present
try:
    import punters_client
    import cache_requests
    from lxml import html
except ImportError:
    print("Installing required packages...")
    os.system(f"{sys.executable} -m pip install punters-client cache-requests lxml pandas")
    import punters_client
    import cache_requests
    from lxml import html

import warnings
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_complete.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============ CONFIGURATION ============
START_DATE = datetime(2023, 5, 18)
END_DATE = datetime(2026, 5, 18)
DELAY_BETWEEN_DAYS = 2
DELAY_BETWEEN_RACES = 0.5
OUTPUT_DIR = "racing_data_complete"
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint_complete.json")
RESULTS_CSV = os.path.join(OUTPUT_DIR, "racing_results_complete.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# State to Country mapping
STATE_COUNTRY = {
    'NSW': 'Australia', 'VIC': 'Australia', 'QLD': 'Australia',
    'SA': 'Australia', 'WA': 'Australia', 'TAS': 'Australia',
    'NT': 'Australia', 'ACT': 'Australia', 'UK': 'United Kingdom',
    'IRE': 'Ireland', 'FR': 'France', 'ZA': 'South Africa',
    'US': 'United States', 'JP': 'Japan', 'TR': 'Turkey', 'AE': 'UAE'
}

# ============ HELPER FUNCTIONS ============
def extract_state(venue):
    venue_lower = venue.lower()
    
    nsw = ['sydney', 'randwick', 'rosehill', 'warwick', 'newcastle', 'gosford', 'wyong', 'kembla', 'hawkesbury']
    vic = ['melbourne', 'flemington', 'caulfield', 'sandown', 'moonee valley', 'cranbourne', 'geelong', 'ballarat']
    qld = ['brisbane', 'eagle farm', 'doomben', 'gold coast', 'sunshine coast', 'ipswich', 'toowoomba']
    sa = ['adelaide', 'morphettville', 'gawler', 'strathalbyn', 'balaklava']
    wa = ['perth', 'ascot', 'belmont', 'pinjarra', 'bunbury', 'albany']
    tas = ['hobart', 'launceston', 'devonport', 'burnie']
    nt = ['darwin', 'alice springs']
    act = ['canberra', 'queanbeyan']
    uk = ['carlisle', 'lingfield', 'redcar', 'windsor', 'wolverhampton', 'newmarket', 'ascot', 'york']
    ireland = ['roscommon', 'curragh', 'leopardstown']
    france = ['chantilly', 'dax', 'marseille', 'longchamp']
    south_africa = ['kenilworth', 'greyville', 'turffontein']
    usa = ['finger lakes', 'horseshoe indianapolis', 'mountaineer', 'presque isle downs', 'thistledown']
    japan = ['kanazawa', 'morioka', 'nagoya', 'ohi', 'tokyo', 'kyoto']
    turkey = ['ankara', 'bursa', 'sanliurfa']
    uae = ['meydan', 'jebel ali']
    
    if any(v in venue_lower for v in nsw): return 'NSW'
    if any(v in venue_lower for v in vic): return 'VIC'
    if any(v in venue_lower for v in qld): return 'QLD'
    if any(v in venue_lower for v in sa): return 'SA'
    if any(v in venue_lower for v in wa): return 'WA'
    if any(v in venue_lower for v in tas): return 'TAS'
    if any(v in venue_lower for v in nt): return 'NT'
    if any(v in venue_lower for v in act): return 'ACT'
    if any(v in venue_lower for v in uk): return 'UK'
    if any(v in venue_lower for v in ireland): return 'IRE'
    if any(v in venue_lower for v in france): return 'FR'
    if any(v in venue_lower for v in south_africa): return 'ZA'
    if any(v in venue_lower for v in usa): return 'US'
    if any(v in venue_lower for v in japan): return 'JP'
    if any(v in venue_lower for v in turkey): return 'TR'
    if any(v in venue_lower for v in uae): return 'AE'
    
    return 'Unknown'

def get_surface(track_condition):
    if not track_condition:
        return 'Turf'
    tc_lower = track_condition.lower()
    if 'synthetic' in tc_lower or 'polytrack' in tc_lower:
        return 'Synthetic'
    if 'dirt' in tc_lower:
        return 'Dirt'
    if 'fiber' in tc_lower:
        return 'Synthetic'
    return 'Turf'

def get_going_code(going):
    if not going:
        return ''
    going_lower = going.lower()
    if 'good' in going_lower: return 'G'
    if 'soft' in going_lower: return 'S'
    if 'heavy' in going_lower: return 'H'
    if 'dead' in going_lower: return 'D'
    if 'slow' in going_lower: return 'SL'
    if 'fast' in going_lower: return 'F'
    if 'firm' in going_lower: return 'FM'
    if 'polytrack' in going_lower: return 'PO'
    if 'dirt' in going_lower: return 'DI'
    if 'fiber' in going_lower: return 'FI'
    return going[:2].upper() if going else ''

def extract_sp_decimal(sp_str):
    if not sp_str:
        return ''
    match = re.search(r'[\d\.]+', str(sp_str).replace('$', ''))
    return match.group(0) if match else ''

def extract_age_restriction(race_name):
    if not race_name:
        return ''
    race_lower = race_name.lower()
    if '2yo' in race_lower or '2-year-old' in race_lower:
        return '2YO'
    if '3yo' in race_lower or '3-year-old' in race_lower:
        return '3YO'
    if '4yo+' in race_lower:
        return '4YO+'
    return ''

def is_handicap(race_name, race_class):
    if not race_name and not race_class:
        return 'Unknown'
    race_lower = (str(race_name) + ' ' + str(race_class)).lower()
    if 'handicap' in race_lower or 'hcp' in race_lower:
        return 'Yes'
    return 'No'

def extract_class(race_name):
    if not race_name:
        return ''
    race_lower = race_name.lower()
    class_patterns = {
        'Group 1': ['group 1', 'gr1', 'g1'],
        'Group 2': ['group 2', 'gr2', 'g2'],
        'Group 3': ['group 3', 'gr3', 'g3'],
        'Listed': ['listed', 'lr'],
        'Stakes': ['stakes', 'stk'],
        'Maiden': ['maiden', 'mdn'],
        'Handicap': ['handicap', 'hcp'],
        'Open': ['open', 'opn']
    }
    
    for class_name, patterns in class_patterns.items():
        for pattern in patterns:
            if pattern in race_lower:
                return class_name
    return ''

def convert_distance(distance_str):
    if not distance_str:
        return '', ''
    match = re.search(r'(\d+)', str(distance_str))
    if match:
        return distance_str, int(match.group(1))
    return distance_str, ''

# ============ SETUP PUNTERS CLIENT ============
def setup_scraper():
    try:
        import cache_requests
        from lxml import html
        import punters_client
        
        http_client = cache_requests.Session()
        html_parser = html.fromstring
        scraper = punters_client.Scraper(http_client, html_parser)
        logger.info("✅ Punters client scraper initialized successfully")
        return scraper
    except Exception as e:
        logger.error(f"Failed to initialize punters client: {e}")
        return None

# ============ FETCH ALL RACE DATA ============
def fetch_date_races(scraper, date):
    try:
        meets = scraper.scrape_meets(date)
        
        if not meets:
            return []
        
        all_races = []
        
        for meet in meets:
            venue = meet.get('track', 'Unknown') if isinstance(meet, dict) else getattr(meet, 'track', 'Unknown')
            state = extract_state(venue)
            country = STATE_COUNTRY.get(state, 'Australia')
            track_condition = meet.get('track_condition', 'Unknown') if isinstance(meet, dict) else getattr(meet, 'track_condition', 'Unknown')
            going_code = get_going_code(track_condition)
            surface = get_surface(track_condition)
            
            races = scraper.scrape_races(meet)
            
            for race in races:
                race_name = race.get('name', '') if isinstance(race, dict) else getattr(race, 'name', '')
                race_number = race.get('number', '') if isinstance(race, dict) else getattr(race, 'number', '')
                distance_raw = race.get('distance', '') if isinstance(race, dict) else getattr(race, 'distance', '')
                distance_raw, distance_meters = convert_distance(distance_raw)
                race_time = race.get('time', '') if isinstance(race, dict) else getattr(race, 'time', '')
                
                runners = scraper.scrape_runners(race)
                
                if runners:
                    race_row = build_race_row_from_runners(
                        runners, date, venue, country, surface, track_condition, 
                        going_code, race_name, race_number, distance_raw, 
                        distance_meters, race_time
                    )
                    all_races.append(race_row)
                
                time.sleep(DELAY_BETWEEN_RACES)
        
        return all_races
        
    except Exception as e:
        logger.error(f"Error fetching data for {date}: {e}")
        return []

def build_race_row_from_runners(runners, date, venue, country, surface, track_condition, 
                                 going_code, race_name, race_number, distance_raw, 
                                 distance_meters, race_time):
    
    winner = None
    runner_up = None
    third = None
    fourth = None
    fifth = None
    favourite = None
    lowest_sp = float('inf')
    
    for runner in runners:
        result = runner.get('result', '') if isinstance(runner, dict) else getattr(runner, 'result', '')
        sp = runner.get('starting_price', '') if isinstance(runner, dict) else getattr(runner, 'starting_price', '')
        
        if sp:
            try:
                sp_value = float(str(sp).replace('$', ''))
                if sp_value < lowest_sp:
                    lowest_sp = sp_value
                    favourite = runner
            except:
                pass
        
        if result == '1' or result == 1:
            winner = runner
        elif result == '2' or result == 2:
            runner_up = runner
        elif result == '3' or result == 3:
            third = runner
        elif result == '4' or result == 4:
            fourth = runner
        elif result == '5' or result == 5:
            fifth = runner
    
    def get_runner_field(runner, field):
        if not runner:
            return ''
        if isinstance(runner, dict):
            return runner.get(field, '')
        return getattr(runner, field, '')
    
    return {
        'Date': date.strftime('%Y-%m-%d'),
        'Course': venue,
        'Country': country,
        'Surface': surface,
        'Race Time': race_time,
        'Off Time': '',
        'Race Name': race_name,
        'Class': extract_class(race_name),
        'Age Restrict': extract_age_restriction(race_name),
        'Handicap?': is_handicap(race_name, ''),
        'Dist Raw': distance_raw,
        'Dist (m)': distance_meters,
        'Going': track_condition,
        'Going Code': going_code,
        'Runners': len(runners),
        'Win Time': get_runner_field(winner, 'time') or get_runner_field(winner, 'finish_time'),
        'Winner': get_runner_field(winner, 'horse') or get_runner_field(winner, 'name'),
        'Winner SP': get_runner_field(winner, 'starting_price') or get_runner_field(winner, 'sp'),
        'Winner SP Dec': extract_sp_decimal(get_runner_field(winner, 'starting_price') or get_runner_field(winner, 'sp')),
        'Winner Jockey': get_runner_field(winner, 'jockey'),
        'Winner Trainer': get_runner_field(winner, 'trainer'),
        'Winner Cloth': get_runner_field(winner, 'number') or get_runner_field(winner, 'cloth'),
        'Winner Weight': get_runner_field(winner, 'carrying') or get_runner_field(winner, 'weight'),
        'Runner-Up': get_runner_field(runner_up, 'horse') or get_runner_field(runner_up, 'name'),
        'Runner-Up Cloth': get_runner_field(runner_up, 'number') or get_runner_field(runner_up, 'cloth'),
        'Runner-Up Weight': get_runner_field(runner_up, 'carrying') or get_runner_field(runner_up, 'weight'),
        'Third': get_runner_field(third, 'horse') or get_runner_field(third, 'name'),
        'Third Cloth': get_runner_field(third, 'number') or get_runner_field(third, 'cloth'),
        'Third Weight': get_runner_field(third, 'carrying') or get_runner_field(third, 'weight'),
        'Fourth': get_runner_field(fourth, 'horse') or get_runner_field(fourth, 'name'),
        'Fourth Cloth': get_runner_field(fourth, 'number') or get_runner_field(fourth, 'cloth'),
        'Fourth Weight': get_runner_field(fourth, 'carrying') or get_runner_field(fourth, 'weight'),
        'Fifth': get_runner_field(fifth, 'horse') or get_runner_field(fifth, 'name'),
        'Fifth Cloth': get_runner_field(fifth, 'number') or get_runner_field(fifth, 'cloth'),
        'Fifth Weight': get_runner_field(fifth, 'carrying') or get_runner_field(fifth, 'weight'),
        'Favourite': get_runner_field(favourite, 'horse') or get_runner_field(favourite, 'name'),
        'Fav SP': get_runner_field(favourite, 'starting_price') or get_runner_field(favourite, 'sp'),
        'Fav SP Dec': extract_sp_decimal(get_runner_field(favourite, 'starting_price') or get_runner_field(favourite, 'sp')),
        'Fav Position': get_runner_field(favourite, 'result'),
        'Fav Jockey': get_runner_field(favourite, 'jockey'),
        'Fav Trainer': get_runner_field(favourite, 'trainer'),
    }

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                cp = json.load(f)
                return cp
        except:
            pass
    return {'last_date': None, 'total_records': 0, 'day_count': 0}

def save_checkpoint(current_date, total_records, day_count):
    checkpoint = {
        'last_date': current_date.strftime('%Y-%m-%d'),
        'total_records': total_records,
        'day_count': day_count,
        'timestamp': datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

def save_to_csv(results):
    if not results:
        return
    
    df = pd.DataFrame(results)
    
    columns = [
        'Date', 'Course', 'Country', 'Surface', 'Race Time', 'Off Time', 'Race Name',
        'Class', 'Age Restrict', 'Handicap?', 'Dist Raw', 'Dist (m)', 'Going', 'Going Code',
        'Runners', 'Win Time', 'Winner', 'Winner SP', 'Winner SP Dec', 'Winner Jockey',
        'Winner Trainer', 'Winner Cloth', 'Winner Weight', 'Runner-Up', 'Runner-Up Cloth',
        'Runner-Up Weight', 'Third', 'Third Cloth', 'Third Weight', 'Fourth', 'Fourth Cloth',
        'Fourth Weight', 'Fifth', 'Fifth Cloth', 'Fifth Weight', 'Favourite', 'Fav SP',
        'Fav SP Dec', 'Fav Position', 'Fav Jockey', 'Fav Trainer'
    ]
    
    for col in columns:
        if col not in df.columns:
            df[col] = ''
    
    df = df[columns]
    df.to_csv(RESULTS_CSV, index=False, encoding='utf-8-sig')
    logger.info(f"Saved {len(results)} races to {RESULTS_CSV}")

def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║     COMPLETE RACING SCRAPER - ALL 40 COLUMNS                    ║
    ║     Using punters-client library                                ║
    ║     Fetches: Winner, SP, Jockey, Trainer, Weights, ALL data    ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    scraper = setup_scraper()
    if not scraper:
        logger.error("Failed to initialize scraper. Exiting.")
        return
    
    checkpoint = load_checkpoint()
    
    if checkpoint['last_date']:
        start_date = datetime.strptime(checkpoint['last_date'], '%Y-%m-%d') + timedelta(days=1)
        total_records = checkpoint['total_records']
        day_count = checkpoint['day_count']
        logger.info(f"▶ Resuming from {start_date.date()}")
    else:
        start_date = START_DATE
        total_records = 0
        day_count = 0
        logger.info(f"▶ Starting fresh from {start_date.date()}")
    
    all_results = []
    current_date = start_date
    
    try:
        while current_date <= END_DATE:
            day_count += 1
            logger.info(f"[{day_count}] {current_date.strftime('%Y-%m-%d')}")
            
            day_results = fetch_date_races(scraper, current_date)
            
            if day_results:
                all_results.extend(day_results)
                logger.info(f"   🏆 Found {len(day_results)} races (Total: {len(all_results)})")
            
            if day_count % 7 == 0 and all_results:
                save_checkpoint(current_date, total_records + len(all_results), day_count)
                save_to_csv(all_results)
                logger.info(f"   💾 Progress saved")
            
            current_date += timedelta(days=1)
            time.sleep(DELAY_BETWEEN_DAYS)
        
        if all_results:
            save_to_csv(all_results)
            logger.info(f"\n✅✅✅ SCRAPE COMPLETE! ✅✅✅")
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user!")
        if all_results:
            save_checkpoint(current_date, total_records + len(all_results), day_count)
            save_to_csv(all_results)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)

if __name__ == "__main__":
    main()