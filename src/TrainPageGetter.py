from src import config
import requests
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from cachetools import cached, TTLCache

# Updated to use the working mersultrenurilor site
base_url = "https://mersultrenurilor.infofer.ro/ro-RO/Tren/{}"
# CFR Călători site (bilete.cfrcalatori.ro) has richer composition/service data.
cfr_base_url = "https://bilete.cfrcalatori.ro/ro-RO/Tren/{}"


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
    Get real train information.  By default we attempt to fetch from the
    CFR Călători ticketing site first, falling back to the legacy
    mersultrenurilor.infofer.ro (Infofer) if anything goes wrong.  The
    newer source provides train composition and service icons which the
    old site does not expose.
    """
    try:
        return get_cfr_train_data(train_id)
    except Exception as e:
        # forward compatibility: if CFR site is down or the format changes
        print(f"CFR Calatori fetch failed ({e}), falling back to Infofer")
        return get_real_train_data(train_id)

@cached(cache=TTLCache(maxsize=200, ttl=30))
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
        
        # Step 1: Get the initial page to extract form tokens
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
        
        # FIX: Always hardcode IsSearchWanted=True and IsReCaptchaFailed=False.
        # Reading these from the form returns 'False' by default, which causes
        # Infofer to return a JS redirect instead of the actual results HTML.
        form_data['IsSearchWanted'] = 'True'
        form_data['IsReCaptchaFailed'] = 'False'
        
        # Ensure date is set (Infofer requires this)
        if not form_data.get('Date'):
            form_data['Date'] = datetime.now().strftime("%d.%m.%Y")
        
        # Step 2: POST to get actual train data via AJAX
        result_url = "https://mersultrenurilor.infofer.ro/ro-RO/Trains/TrainsResult"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        result_response = requests.post(result_url, data=form_data, headers=headers, timeout=15)
        result_response.raise_for_status()

        # Guard: if Infofer still returned a JS redirect, raise clearly
        if 'window.location' in result_response.text[:500]:
            raise Exception(
                f"Infofer returned a JS redirect instead of train data for train {numeric_train_id}. "
                f"The form tokens may be missing or the train number is invalid."
            )
        
        result_soup = BeautifulSoup(result_response.content, 'html.parser')
        

        # Step 3: Parse all branches. The page has one button + div pair per branch.
        # Buttons have id="button-group-XXXXX", divs have id="div-stations-branch-XXXXX".

        def parse_stations_from_div(branch_div):
            stops = []
            last_known_delay = 0
            
            for item in branch_div.find_all('li', class_='list-group-item'):
                station_link = item.find('a', href=lambda x: x and '/ro-RO/Statie/' in x)
                if not station_link:
                    continue
                station_name = station_link.get_text(strip=True)
                time_divs = item.find_all('div', class_='text-1-3rem')
                arrival_time = time_divs[0].get_text(strip=True) if len(time_divs) > 0 else None
                departure_time = time_divs[1].get_text(strip=True) if len(time_divs) > 1 else arrival_time
                
                delay_divs = item.find_all('div', class_=lambda c: c and ('color-' in c or 'delay' in c))
                parsed_delay = None
                
                if delay_divs:
                    for delay_div in delay_divs:
                        delay_text = delay_div.get_text(strip=True).lower()
                        if 'la timp' in delay_text:
                            parsed_delay = 0
                            break
                        delay_match = re.search(r'([+\-]?\d+)\s*min', delay_text)
                        if delay_match:
                            parsed_delay = int(delay_match.group(1).replace('+', ''))
                            break
                
                if parsed_delay is None:
                    full_text = item.get_text(separator=' ', strip=True).lower()
                    if 'la timp' in full_text:
                        parsed_delay = 0
                    else:
                        delay_match = re.search(r'(?:întârzier\w*|intarzier\w*|estimat\w*)\s*(?:estimată)?\s*:?\s*([+\-]?\d+)\s*min', full_text)
                        if delay_match:
                            parsed_delay = int(delay_match.group(1).replace('+', ''))

                # Intelligent delay propagation
                if parsed_delay is not None:
                    if parsed_delay > 0:
                        last_known_delay = parsed_delay
                    else:
                        if last_known_delay > 15:
                            parsed_delay = last_known_delay
                        else:
                            last_known_delay = 0
                else:
                    parsed_delay = last_known_delay

                delay_minutes = parsed_delay if parsed_delay is not None else 0

                platform = None
                for small in item.find_all(['small', 'div', 'span']):
                    txt = small.get_text(strip=True)
                    # Limit to 1-2 digits plus optional letter, stop at word boundary
                    linia_match = re.search(r'(?:Linia|linia|Linie|Per[oó]n|perón)\s*:?\s*(\d{1,2}[A-Za-z]?)\b', txt)
                    if linia_match:
                        platform = linia_match.group(1)
                        break

                dwell_minutes = 0
                if arrival_time and departure_time and arrival_time != departure_time:
                    try:
                        def t2m(t):
                            h, m = t.strip().split(':')
                            return int(h) * 60 + int(m)
                        dwell_minutes = t2m(departure_time) - t2m(arrival_time)
                        if dwell_minutes < 0:
                            dwell_minutes += 24 * 60
                    except Exception:
                        dwell_minutes = 0

                is_stop = 'not-displayed' not in item.get('class', [])
                full_text = item.get_text(separator=' ', strip=True)
                if 'oprire' in full_text.lower() or 'Pleacă la' in full_text or 'Sosește la' in full_text:
                    is_stop = True

                stops.append({
                    'station_name': station_name,
                    'arrival_time': arrival_time,
                    'departure_time': departure_time,
                    'delay': delay_minutes,
                    'platform': platform,
                    'dwell_minutes': dwell_minutes,
                    'is_stop': is_stop
                })
            return stops

        branch_divs = result_soup.find_all('div', id=lambda x: x and x.startswith('div-stations-branch-'))
        branches = []

        for branch_div in branch_divs:
            branch_id = branch_div['id'].replace('div-stations-branch-', '')
            button = result_soup.find('button', id=f'button-group-{branch_id}')
            label = 'Rută'
            if button:
                parts = [p.strip() for p in button.get_text(separator='\n').split('\n') if p.strip()]
                parts = [p for p in parts if p not in ('→', '->', '–', '►')]
                if len(parts) >= 2:
                    label = f"{parts[0]} · {' → '.join(parts[1:])}"
                elif parts:
                    label = parts[0]

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
                        def t2m_fb(t):
                            h, m = t.strip().split(':')
                            return int(h) * 60 + int(m)
                        dwell_minutes = t2m_fb(departure_time) - t2m_fb(arrival_time)
                        if dwell_minutes < 0:
                            dwell_minutes += 24 * 60
                    except Exception:
                        dwell_minutes = 0
                stops.append({'station_name': station_name, 'arrival_time': arrival_time,
                              'departure_time': departure_time, 'delay': 0,
                              'platform': platform, 'dwell_minutes': dwell_minutes})
            if stops:
                branches.append({'label': 'Rută', 'stations_data': stops})

        if not branches:
            raise Exception("No station data found in AJAX result")

        stations_data = max(branches, key=lambda b: len(b['stations_data']))['stations_data']

        # Step 4: Extract warnings/alerts
        alerts_set = set()
        for s in [soup, result_soup]:
            for alert_box in s.find_all('div', class_=lambda c: c and 'alert' in c.lower()):
                text = alert_box.get_text(separator=' ', strip=True)
                if text and len(text) > 10 and 'Fără internet' not in text:
                    cleaned_text = re.sub(r'\s+', ' ', text).strip()
                    alerts_set.add(cleaned_text)
        
        alerts = list(alerts_set)

        # Step 5: Identify the operator (CFR, Softrans, Astra, etc.)
        # FIX: Search result_soup (the POST response), not soup (the initial GET page).
        # The operator label only appears in the rendered results HTML.
        operator = "CFR Călători"
        for p in result_soup.find_all('p', class_='text-1-1rem'):
            p_text = p.get_text(strip=True)
            if 'Operat de' in p_text:
                operator = p_text.replace('Operat de', '').strip()
                # operator may contain diacritics; log safely
                print(f"Detected official operator: {operator.encode('ascii','ignore').decode('ascii')}")
                break
        
        # Step 6: Extract category (IR, R, etc.)
        category = train_id.replace(numeric_train_id, '').strip()
        if not category:
            # Try to find it in the HTML
            category_span = result_soup.find('span', class_=re.compile(r'span-train-category-'))
            if category_span:
                category = category_span.get_text(strip=True)
            else:
                # Fallback: check h2/h4 contents
                header_text = result_soup.get_text(separator=' ', strip=True)
                for r in ["IC", "IRN", "IR", "R-E", "R"]:
                    if f" {r} " in f" {header_text} ":
                        category = r
                        break

        # avoid accented characters in logging by stripping to ascii
        safe_operator = operator.encode('ascii','ignore').decode('ascii')
        print(f"Found {len(branches)} branch(es), {len(stations_data)} stations in main branch, {len(alerts)} alerts. Operator: {safe_operator}, Category: {category}")
        
        return {
            'train_number': numeric_train_id,
            'stations_data': stations_data,
            'branches': branches,
            'alerts': alerts,
            'operator': operator,
            'category': category,
            'data_source': 'mersultrenurilor_live'
        }
    
    except Exception as e:
        print(f"Error fetching real train data from mersultrenurilor: {e}")
        raise


@cached(cache=TTLCache(maxsize=200, ttl=30))
def get_cfr_train_data(train_id):
    """Fetch train details from the CFR Călători ticketing site.

    This implementation mirrors :func:`get_real_train_data` but adapts to
    the slightly different form fields and HTML structure on
    bilete.cfrcalatori.ro. It also extracts additional information such as
    train services and the raw coach-composition HTML.
    """
    try:
        numeric_train_id = clean_train_number(train_id)
        url = cfr_base_url.format(numeric_train_id)
        # use ascii in log to avoid encoding issues
        print(f"Fetching train data from CFR Calatori: {url}")

        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # collect form tokens
        form_data = {}
        for field in ['Date', 'TrainRunningNumber', 'JourneyDepartureStationId',
                      'JourneyArrivalStationId', 'SelectedBranchCode',
                      'ConfirmationKey', '__RequestVerificationToken']:
            input_field = soup.find('input', {'name': field}) or soup.find('input', {'id': field})
            if input_field:
                form_data[field] = input_field.get('value', '')

        # always include these flags to avoid JS redirect behavior
        form_data.setdefault('IsSearchWanted', 'True')
        form_data.setdefault('IsReCaptchaFailed', 'False')
        if not form_data.get('Date'):
            form_data['Date'] = datetime.now().strftime("%d.%m.%Y")

        result_url = "https://bilete.cfrcalatori.ro/ro-RO/Trains/TrainsResult"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': url,
            'X-Requested-With': 'XMLHttpRequest'
        }

        result_response = requests.post(result_url, data=form_data, headers=headers, timeout=15)
        result_response.raise_for_status()

        if 'window.location' in result_response.text[:500]:
            raise Exception("CFR Calatori returned a JS redirect instead of train data")

        result_soup = BeautifulSoup(result_response.content, 'html.parser')

        # parse station list similar to Infofer
        stations = []
        last_known_delay = 0
        for item in result_soup.find_all('li', class_='list-group-item'):
            station_link = item.find('a', href=lambda x: x and '/ro-RO/Statie/' in x)
            if not station_link:
                continue
            station_name = station_link.get_text(strip=True)
            time_divs = item.find_all('div', class_='text-1-3rem')
            arrival_time = time_divs[0].get_text(strip=True) if len(time_divs) > 0 else None
            departure_time = time_divs[1].get_text(strip=True) if len(time_divs) > 1 else arrival_time
            parsed_delay = None
            for delay_div in item.find_all('div', class_=lambda c: c and ('color-' in c or 'delay' in c)):
                delay_text = delay_div.get_text(strip=True).lower()
                if 'la timp' in delay_text:
                    parsed_delay = 0
                    break
                delay_match = re.search(r'([+\-]?\d+)\s*min', delay_text)
                if delay_match:
                    parsed_delay = int(delay_match.group(1).replace('+', ''))
                    break
            if parsed_delay is None:
                full_text = item.get_text(separator=' ', strip=True).lower()
                if 'la timp' in full_text:
                    parsed_delay = 0
                else:
                    delay_match = re.search(r'(?:întârzier\w*|intarzier\w*|estimat\w*)\s*(?:estimată)?\s*:?\s*([+\-]?\d+)\s*min', full_text)
                    if delay_match:
                        parsed_delay = int(delay_match.group(1).replace('+', ''))
            if parsed_delay is not None:
                if parsed_delay > 0:
                    last_known_delay = parsed_delay
                else:
                    if last_known_delay > 15:
                        parsed_delay = last_known_delay
                    else:
                        last_known_delay = 0
            else:
                parsed_delay = last_known_delay
            delay_minutes = parsed_delay if parsed_delay is not None else 0
            platform = None
            for small in item.find_all(['small', 'div', 'span']):
                txt = small.get_text(strip=True)
                # platform/line number may appear as "Linia 3" or "peron 2" etc.
                linia_match = re.search(r'(?:Linia|linia|Linie|Per[oó]n|perón)\s*:?\s*(\d{1,2}[A-Za-z]?)\b', txt)
                if linia_match:
                    platform = linia_match.group(1)
                    break
            dwell_minutes = 0
            if arrival_time and departure_time and arrival_time != departure_time:
                try:
                    def t2m(t):
                        h, m = t.strip().split(':')
                        return int(h) * 60 + int(m)
                    dwell_minutes = t2m(departure_time) - t2m(arrival_time)
                    if dwell_minutes < 0:
                        dwell_minutes += 24 * 60
                except Exception:
                    dwell_minutes = 0
            is_stop = 'not-displayed' not in item.get('class', [])
            full_text = item.get_text(separator=' ', strip=True)
            if 'oprire' in full_text.lower() or 'Pleacă la' in full_text or 'Sosește la' in full_text:
                is_stop = True
            stations.append({
                'station_name': station_name,
                'arrival_time': arrival_time,
                'departure_time': departure_time,
                'delay': delay_minutes,
                'platform': platform,
                'dwell_minutes': dwell_minutes,
                'is_stop': is_stop
            })
        branches = [{'label': 'Rută', 'stations_data': stations}]

        # determine coach order per station based on embedded JS
        coaches_by_station = {}
        for script in result_soup.find_all('script'):
            txt = script.string or ''
            if 'button-coach-scheme' in txt:
                for m in re.finditer(r"data-stationId='(\d+)'\]\[data-coachName='([^']+)'", txt, re.IGNORECASE):
                    sid = m.group(1)
                    coaches_by_station.setdefault(sid, []).append(m.group(2))

        # resolve station names and build coach_order map
        station_names = {}
        station_options = []
        # Collect from <option> elements
        for opt in result_soup.find_all('option'):
            sid = opt.get('data-stationid') or opt.get('data-stationId')
            if sid:
                name = opt.get_text(strip=True)
                station_names[sid] = name
                station_options.append({'id': sid, 'name': name})
        # Ensure all stations from parsed list are included
        for s in stations:
            name = s['station_name']
            # Try to find sid by name (reverse lookup)
            sid = None
            for k, v in station_names.items():
                if v == name:
                    sid = k
                    break
            if not any(opt['name'] == name for opt in station_options):
                station_options.append({'id': sid or name, 'name': name})
        coach_order = {}
        # Ensure all stations in station_options are present in coach_order
        for opt in station_options:
            name = opt['name']
            sid = opt['id']
            coaches = coaches_by_station.get(sid, [])
            coach_order[name] = coaches

        # compute full list of coaches seen anywhere (preserves order encountered)
        all_coaches = []
        for coaches in coaches_by_station.values():
            for c in coaches:
                if c not in all_coaches:
                    all_coaches.append(c)

        # also look for coach class info in the same scripts
        coach_classes = {}
        for script in result_soup.find_all('script'):
            txt = script.string or ''
            for m in re.finditer(r"data-coachName='([^']+)'.*?title=\"\s*(Clasa[^\"]+)\"", txt, re.DOTALL):
                coach = m.group(1)
                cls = m.group(2).strip()
                if coach not in coach_classes:
                    coach_classes[coach] = cls

        # collect alerts from both initial soup and the AJAX result
        alerts_set = set()
        for s in [soup, result_soup]:
            for alert_box in s.find_all('div', class_=lambda c: c and 'alert' in c.lower()):
                text = alert_box.get_text(separator=' ', strip=True)
                if text and len(text) > 10 and 'Fără internet' not in text:
                    cleaned = re.sub(r'\s+', ' ', text).strip()
                    alerts_set.add(cleaned)
        alerts = list(alerts_set)

        # operator detection
        operator = "CFR Călători"
        for p in result_soup.find_all('p', class_='text-1-1rem'):
            p_text = p.get_text(strip=True)
            if 'Operat de' in p_text:
                operator = p_text.replace('Operat de', '').strip()
                # operator may contain diacritics; log safely
                print(f"Detected official operator: {operator.encode('ascii','ignore').decode('ascii')}")
                break

        # category detection
        category = train_id.replace(numeric_train_id, '').strip()
        if not category:
            span = result_soup.find('span', class_=re.compile(r'span-train-category-'))
            if span:
                category = span.get_text(strip=True)
            else:
                header_text = result_soup.get_text(separator=' ', strip=True)
                for r in ["IC", "IRN", "IR", "R-E", "R"]:
                    if f" {r} " in f" {header_text} ":
                        category = r
                        break

        # services list
        services = []
        serv_hdr = result_soup.find(lambda tag: tag.name in ['h4', 'h3'] and 'Servicii tren' in tag.get_text())
        if serv_hdr:
            for span in serv_hdr.parent.find_all('span', class_='color-blue'):
                services.append(span.get_text(strip=True))

        # composition html extraction
        composition_html = None
        for script in result_soup.find_all('script'):
            txt = script.string or ''
            if 'mapToShow' in txt:
                m = re.search(r"mapToShow\s*=\s*'((?:\\'|[^'])*)'", txt, re.DOTALL)
                if m:
                    composition_html = m.group(1).replace("\\'", "'")
                    break

        # build result
        result = {
            'train_number': numeric_train_id,
            'stations_data': stations,
            'branches': branches,
            'alerts': alerts,
            'operator': operator,
            'category': category,
            'services': services,
            'composition_html': composition_html,
            'coach_order': coach_order,
            'data_source': 'cfrcalatori',
            'all_coaches': all_coaches,
        }
        if coach_classes:
            result['coach_classes'] = coach_classes
        if station_options:
            result['station_options'] = station_options
        return result
    except Exception as e:
        print(f"Error fetching real train data from cfrcalatori: {e}")
        raise