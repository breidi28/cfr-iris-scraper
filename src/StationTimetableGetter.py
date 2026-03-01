import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from cachetools import cached, TTLCache

# Infofer URLs
INFOFER_BASE_URL = "https://mersultrenurilor.infofer.ro/ro-RO/Statie/{}"
INFOFER_AJAX_URL = "https://mersultrenurilor.infofer.ro/ro-RO/Stations/StationsResult"

def slugify(text):
    """Convert station name to Infofer URL slug"""
    text = text.lower()
    replacements = {
        'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ț': 't',
        'ş': 's', 'ţ': 't'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def get_station_name_by_id(station_id):
    """Map internal app numeric IDs to readable station names."""
    mapping = {
        "10001": "București Nord",
        "10101": "București Basarab",
        "10102": "București Obor",
        "10002": "Cluj-Napoca",
        "10003": "Constanța",
        "10004": "Brașov",
        "10005": "Timișoara Nord",
        "10006": "Iași",
        "10007": "Craiova",
        "10008": "Galați",
        "10009": "Ploiești Sud",
        "10109": "Ploiești Vest",
        "10010": "Oradea",
        "10011": "Arad",
        "10071": "Sinaia",
        "10072": "Predeal",
    }
    if isinstance(station_id, str) and not station_id.isdigit():
        return station_id.replace('-', ' ').title()
    return mapping.get(str(station_id), f"Station-{station_id}")

@cached(cache=TTLCache(maxsize=100, ttl=45))
def get_timetable(station_id, station_name=None, date_str=None):
    """Main entry point for fetching station timetable"""
    return get_infofer_timetable(station_id, station_name, date_str)

def get_infofer_timetable(station_id, station_name=None, date_str=None):
    """
    Scrape real-time timetable from mersultrenurilor.infofer.ro
    """
    if not station_name:
        station_name = get_station_name_by_id(station_id)
    
    slug = slugify(station_name)
    
    slugs_to_try = [slug]
    parts = slug.split('-')
    proper_slug = '-'.join(p.capitalize() for p in parts)
    if proper_slug != slug:
        slugs_to_try.insert(0, proper_slug)
    if 'bucuresti-nord' in slug:
        slugs_to_try.insert(0, 'Bucuresti-Nord')
    
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    last_error = None
    for s in slugs_to_try:
        try:
            url = INFOFER_BASE_URL.format(s)
            print(f"Trying Infofer station page: {url}")
            
            resp = session.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"Slug {s} failed with status {resp.status_code}")
                continue
                
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            form_data = {}
            for field in ['Date', 'StationName', 'ReCaptcha', 'ConfirmationKey', '__RequestVerificationToken']:
                input_field = soup.find('input', {'name': field}) or soup.find('input', {'id': field})
                if input_field:
                    form_data[field] = input_field.get('value', '')
            
            # FIX: Always hardcode these — reading from form gives 'False' and causes JS redirect
            form_data['IsSearchWanted'] = 'True'
            form_data['IsReCaptchaFailed'] = 'False'
            
            # Use provided date or default to today
            if date_str:
                form_data['Date'] = date_str
            elif not form_data.get('Date'):
                form_data['Date'] = datetime.now().strftime("%d.%m.%Y")
            
            # Parse requested date to pass to parser
            try:
                requested_date = datetime.strptime(form_data['Date'], "%d.%m.%Y")
                # Maintain the time part to handle filtering relative to CURRENT time if it's today
                now = datetime.now()
                if requested_date.date() == now.date():
                    requested_date = now
                else:
                    # For future days, assume we want to see from start of day (midnight)
                    requested_date = requested_date.replace(hour=0, minute=0, second=0)
            except:
                requested_date = datetime.now()

            ajax_headers = headers.copy()
            ajax_headers.update({
                'Referer': url,
                'X-Requested-With': 'XMLHttpRequest'
            })
            
            print(f"Fetching timetable results via AJAX for {station_name}...")
            res = session.post(INFOFER_AJAX_URL, data=form_data, headers=ajax_headers, timeout=15)

            if res.status_code != 200:
                print(f"AJAX POST failed with status {res.status_code}")
                continue

            # Guard: detect JS redirect response
            if 'window.location' in res.text[:500]:
                print(f"Infofer returned JS redirect for slug {s}, trying next variant...")
                continue

            result = parse_infofer_html(res.text, station_name, requested_date)
            if result:
                return result
            # If empty result, try next slug variant
            print(f"Empty result for slug {s}, trying next...")
            
        except Exception as e:
            print(f"Error fetching from Infofer (slug {s}): {e}")
            last_error = e
            
    if last_error:
        raise last_error
    return []

def parse_infofer_html(html, station_name, target_date=None):
    """Parse the Infofer AJAX response HTML"""
    if target_date is None:
        target_date = datetime.now()
        
    soup = BeautifulSoup(html, 'html.parser')
    trains = []
    
    items = soup.find_all('li', class_='list-group-item')
    print(f"Found {len(items)} raw items in Infofer response")
    
    for item in items:
        try:
            # 1. Train number
            train_link = item.find('a', href=lambda x: x and ('/ro-RO/Itinerarii/Tren/' in x or '/ro-RO/Tren/' in x))
            if not train_link:
                continue
                
            train_num = train_link.get_text(strip=True).replace('Tren ', '', 1)
            
            # 2. Rank - Infofer often puts the rank (IR, R, etc) in a separate div or before the number
            all_text = item.get_text(separator=' ', strip=True)
            
            # Default to R (Regio) if we can't find anything
            rank = "R"
            
            # Look for ranks in the text. Station board usually has them as standalone labels.
            if "IC" in all_text.split(): rank = "IC"
            elif "IRN" in all_text.split(): rank = "IRN"
            elif "IR" in all_text.split(): rank = "IR"
            elif "R-E" in all_text.split(): rank = "R-E"
            elif "R" in all_text.split(): rank = "R"
            
            # Reconstruct the full name if it's just a number
            if rank and not any(r in train_num for r in ["IR", "IC", "R-E", "R"]):
                train_full_name = f"{rank} {train_num}"
            else:
                train_full_name = train_num
            
            # 2. Times — extract from dedicated time divs, not raw text regex.
            # This avoids accidentally picking up times from delay labels.
            # Infofer structure uses divs with label siblings like "Pleacă la" / "Sosește la"
            raw_arrival = ""
            raw_departure = ""

            all_text = item.get_text(separator=' ', strip=True)

            # Find all label+time pairs in structured divs
            for wrapper in item.find_all('div'):
                label_div = wrapper.find('div', class_=re.compile(r'text-0'))
                time_div = wrapper.find('div', class_=re.compile(r'text-1-3'))
                if label_div and time_div:
                    label = label_div.get_text(strip=True)
                    time_val = time_div.get_text(strip=True)
                    if re.match(r'^\d{1,2}:\d{2}$', time_val):
                        if 'Pleacă' in label:
                            raw_departure = time_val
                        elif 'Sosește' in label:
                            raw_arrival = time_val

            # Fallback: if structured extraction failed, use positional regex
            # but only on a narrowed scope (exclude delay text regions)
            if not raw_arrival and not raw_departure:
                # Remove delay spans first to avoid false matches
                item_copy = BeautifulSoup(str(item), 'html.parser')
                for delay_el in item_copy.find_all(class_=re.compile(r'color-|delay')):
                    delay_el.decompose()
                clean_text = item_copy.get_text(separator=' ', strip=True)
                times_found = re.findall(r'\b(\d{1,2}:\d{2})\b', clean_text)
                if 'Pleacă la' in all_text and 'Sosește la' in all_text:
                    if len(times_found) >= 2:
                        raw_arrival = times_found[0]
                        raw_departure = times_found[1]
                elif 'Pleacă la' in all_text:
                    raw_departure = times_found[0] if times_found else ""
                elif 'Sosește la' in all_text:
                    raw_arrival = times_found[0] if times_found else ""

            # 3. Route — the other station (not ours)
            other_station_link = item.find('a', href=lambda x: x and '/ro-RO/Statie/' in x and slugify(station_name) not in x.lower())
            route_name = other_station_link.get_text(strip=True) if other_station_link else "Unknown"
            
            # 4. Operator
            operator = "CFR Călători"
            operator_img = item.find('img', title=True)
            if operator_img:
                operator = operator_img['title']
            else:
                common_operators = ["Softrans", "Astra Trans Carpatic", "Transferoviar", "Regio Călători", "Interregional"]
                for op in common_operators:
                    if op.lower() in all_text.lower():
                        operator = op
                        break

            # 5. Delay
            delay = 0
            delay_match = re.search(r'\+(\d+)\s*min', all_text)
            if delay_match:
                delay = int(delay_match.group(1))
            
            # 6. Platform — Improved to avoid capturing adjacent data (like train numbers or times)
            platform = ""
            platform_match = re.search(r'Linia\s*:?\s*(\d{1,2}[A-Za-z]?)\b', all_text)
            if platform_match:
                platform = platform_match.group(1)
            
            # Timestamps
            arr_ts = convert_time_to_timestamp(raw_arrival, target_date) if raw_arrival else None
            dep_ts = convert_time_to_timestamp(raw_departure, target_date) if raw_departure else None
            
            is_origin = bool(raw_departure and not raw_arrival)
            is_destination = bool(raw_arrival and not raw_departure)
            is_stop = bool(raw_arrival and raw_departure)

            # Skip items where we couldn't extract any time at all
            if not raw_arrival and not raw_departure:
                print(f"Skipping item for {train_full_name} — no times extracted")
                continue
            
            # Filter: Only keep trains for the requested window
            # This prevents trains from far in the future/past showing up due to site structure
            target_ts = target_date
            # If it's early morning (0-4 AM), we are likely looking at the end of the "previous" day's schedule
            # but Infofer usually resets at midnight.
            if dep_ts or arr_ts:
                ts = dep_ts or arr_ts
                if ts > target_ts + timedelta(hours=20):
                    # Likely a next-day train we don't want yet
                    continue
                if ts < target_ts - timedelta(hours=20):
                    # Likely a yesterday train
                    continue

            trains.append({
                "rank": rank,
                "train_id": train_full_name.replace(' ', ''),
                "train_number": train_full_name,
                "operator": operator,
                "origin": route_name if is_destination else station_name,
                "destination": route_name if (is_origin or is_stop) else station_name,
                "is_origin": is_origin,
                "is_stop": is_stop,
                "is_destination": is_destination,
                "delay": delay,
                "arrival_time": raw_arrival,
                "departure_time": raw_departure,
                "arrival_timestamp": arr_ts.isoformat() if arr_ts else None,
                "departure_timestamp": dep_ts.isoformat() if dep_ts else None,
                "platform": platform,
                "real_data": True
            })
            
        except Exception as e:
            print(f"Error parsing train item: {e}")
            continue
            
    trains.sort(key=lambda x: x.get('departure_timestamp') or x.get('arrival_timestamp') or '')
    return trains

def convert_time_to_timestamp(time_str, base_date):
    """Convert '14:30' to datetime object with 4 AM cutoff for schedule continuity"""
    try:
        h, m = map(int, time_str.split(':'))
        dt = base_date.replace(hour=h, minute=m, second=0, microsecond=0)
        
        # Roll-over adjustments only make sense in real-time mode (where base_date has a time)
        # For future-day lookups (where we set time to 00:00), we don't want to roll back to 'yesterday'
        if base_date.hour != 0 or base_date.minute != 0:
            # If the train time is very early (00:00 - 04:00) but we are late in the day (20:00 - 23:59),
            # it's clearly for tomorrow morning.
            if base_date.hour >= 20 and h < 4:
                dt += timedelta(days=1)
            # If train time is late (20:00 - 23:59) but we are early morning (00:00 - 04:00),
            # it's likely from the "previous day" schedule still showing.
            elif base_date.hour < 4 and h >= 20:
                dt -= timedelta(days=1)
            
        return dt
    except Exception:
        return None

def generate_demo_timetable(station_id):
    """Fallback — returns empty, better than fake data"""
    return []