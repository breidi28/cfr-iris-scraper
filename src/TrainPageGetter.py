from viewstate import ViewState
from src import config
import requests_html
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import requests

# Updated to use the working mersultrenurilor site
base_url = "https://mersultrenurilor.infofer.ro/ro-RO/Tren/{}"


def get_station_id_by_name(name):
    if name in config.global_station_list:
        return config.global_station_list[name]
    return None


def clean_train_number(train_id):
    """Clean train number for URL format: extract only the numeric part"""
    match = re.search(r'\d+', train_id)
    if match:
        return match.group(0)
    return train_id.strip().replace(' ', '')


def get_train(train_id):
    """
    Get real train information from mersultrenurilor.infofer.ro
    """
    return get_real_train_data(train_id)


def get_real_train_data(train_id):
    """
    Get real train data from mersultrenurilor.infofer.ro with live delays
    Uses AJAX to get actual train data with delay information
    """
    
    try:
        # Use numeric train ID 
        numeric_train_id = clean_train_number(train_id)
        url = base_url.format(numeric_train_id)
        
        print(f"Fetching train data from mersultrenurilor: {url}")
        
        # Step 1: Get the initial page to extract form data
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract form data for AJAX request
        form_data = {}
        for field in ['Date', 'TrainRunningNumber', 'SelectedBranchCode', 'ReCaptcha', 
                      'ConfirmationKey', '__RequestVerificationToken']:
            input_field = soup.find('input', {'name': field}) or soup.find('input', {'id': field})
            if input_field:
                form_data[field] = input_field.get('value', '')
        
        # Add hidden fields
        form_data['IsSearchWanted'] = soup.find('input', {'id': 'input-is-search-wanted'}).get('value', 'False')
        form_data['IsReCaptchaFailed'] = soup.find('input', {'id': 'input-recaptcha-failed'}).get('value', 'False')
        
        # Step 2: POST to get actual train data via AJAX
        result_url = "https://mersultrenurilor.infofer.ro/ro-RO/Trains/TrainsResult"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': url
        }
        
        result_response = requests.post(result_url, data=form_data, headers=headers, timeout=15)
        result_response.raise_for_status()
        
        result_soup = BeautifulSoup(result_response.content, 'html.parser')
        
        # Step 3: Parse all branches. The page has one button + div pair per branch.
        # Buttons have id="button-group-XXXXX", divs have id="div-stations-branch-XXXXX".
        # We parse every branch and return them all so the frontend can offer a selector.

        def parse_stations_from_div(branch_div):
            stops = []
            for item in branch_div.find_all('li', class_='list-group-item'):
                station_link = item.find('a', href=lambda x: x and '/ro-RO/Statie/' in x)
                if not station_link:
                    continue
                station_name = station_link.get_text(strip=True)
                time_divs = item.find_all('div', class_='text-1-3rem')
                arrival_time = time_divs[0].get_text(strip=True) if len(time_divs) > 0 else None
                departure_time = time_divs[1].get_text(strip=True) if len(time_divs) > 1 else arrival_time
                delay_divs = item.find_all('div', class_=['color-firebrick', 'color-darkgreen'])
                delay_minutes = 0
                if delay_divs:
                    for delay_div in delay_divs:
                        delay_text = delay_div.get_text(strip=True)
                        if 'la timp' in delay_text.lower():
                            delay_minutes = 0
                            break
                        delay_match = re.search(r'([+\-]\d+)\s*min', delay_text)
                        if delay_match:
                            delay_minutes = int(delay_match.group(1))
                            break

                # Extract platform ("Linia X" or "Perón X" label in small text)
                platform = None
                for small in item.find_all(['small', 'div', 'span']):
                    txt = small.get_text(strip=True)
                    linia_match = re.search(r'(?:Linia|linia|Linie|Per[oó]n|perón)\s*(\d)', txt)
                    if linia_match:
                        platform = linia_match.group(1)
                        break

                # Compute dwell time from arrival/departure difference
                dwell_minutes = 0
                if arrival_time and departure_time and arrival_time != departure_time:
                    try:
                        def t2m(t):
                            h, m = t.strip().split(':')
                            return int(h) * 60 + int(m)
                        dwell_minutes = t2m(departure_time) - t2m(arrival_time)
                        if dwell_minutes < 0:
                            dwell_minutes += 24 * 60  # midnight crossing
                    except Exception:
                        dwell_minutes = 0

                stops.append({
                    'station_name': station_name,
                    'arrival_time': arrival_time,
                    'departure_time': departure_time,
                    'delay': delay_minutes,
                    'platform': platform,
                    'dwell_minutes': dwell_minutes,
                })
            return stops

        branch_divs = result_soup.find_all('div', id=lambda x: x and x.startswith('div-stations-branch-'))
        branches = []

        for branch_div in branch_divs:
            branch_id = branch_div['id'].replace('div-stations-branch-', '')
            # Find the matching button for the label
            button = result_soup.find('button', id=f'button-group-{branch_id}')
            label = 'Rută'
            if button:
                # Label is the full text of the button, e.g. "Tren principal\nBucurești Nord → Cluj Napoca"
                # Sometimes the arrow is a separate element, giving 3 parts instead of 2.
                parts = [p.strip() for p in button.get_text(separator='\n').split('\n') if p.strip()]
                # Filter out bare arrow characters that may appear as their own part
                parts = [p for p in parts if p not in ('→', '->', '–', '►')]
                if len(parts) >= 2:
                    label = f"{parts[0]} · {' → '.join(parts[1:])}"
                elif parts:
                    label = parts[0]
                else:
                    label = 'Rută'

            stops = parse_stations_from_div(branch_div)
            if stops:
                branches.append({'label': label, 'stations_data': stops})

        # Fallback: if no branch divs found, parse everything
        if not branches:
            all_items = result_soup.find_all('li', class_='list-group-item')
            stops = []
            for item in all_items:
                station_link = item.find('a', href=lambda x: x and '/ro-RO/Statie/' in x)
                if not station_link:
                    continue
                station_name = station_link.get_text(strip=True)
                time_divs = item.find_all('div', class_='text-1-3rem')
                arrival_time = time_divs[0].get_text(strip=True) if len(time_divs) > 0 else None
                departure_time = time_divs[1].get_text(strip=True) if len(time_divs) > 1 else arrival_time
                platform = None
                for small in item.find_all(['small', 'div', 'span']):
                    txt = small.get_text(strip=True)
                    linia_match = re.search(r'(?:Linia|linia|Linie|Per[oó]n)\s*(\d+[a-zA-Z]?)', txt)
                    if linia_match:
                        platform = linia_match.group(1)
                        break
                dwell_minutes = 0
                if arrival_time and departure_time and arrival_time != departure_time:
                    try:
                        def t2m(t): h, m = t.strip().split(':'); return int(h)*60+int(m)
                        dwell_minutes = t2m(departure_time) - t2m(arrival_time)
                        if dwell_minutes < 0: dwell_minutes += 24*60
                    except Exception:
                        dwell_minutes = 0
                stops.append({'station_name': station_name, 'arrival_time': arrival_time,
                              'departure_time': departure_time, 'delay': 0,
                              'platform': platform, 'dwell_minutes': dwell_minutes})
            if stops:
                branches.append({'label': 'Rută', 'stations_data': stops})

        if not branches:
            raise Exception("No station data found in AJAX result")

        # For backward-compat: expose the longest branch as the default `stations_data`
        stations_data = max(branches, key=lambda b: len(b['stations_data']))['stations_data']

        print(f"Found {len(branches)} branch(es), {len(stations_data)} stations in main branch")
        
        return {
            'train_number': numeric_train_id,
            'stations_data': stations_data,
            'branches': branches,
            'category': train_id.replace(numeric_train_id, '').strip(),
            'data_source': 'mersultrenurilor_live'
        }
    
    except Exception as e:
        print(f"Error fetching real train data from mersultrenurilor: {e}")
        raise
