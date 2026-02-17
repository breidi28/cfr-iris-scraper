"""
Live Station Timetable Getter - IRIS Integration
Fetches real-time station timetables with delays from appiris.infofer.ro
"""

from viewstate import ViewState
import requests_html
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup

# IRIS station timetable URL
base_url = "https://appiris.infofer.ro/SosPlcRO.aspx?gara={}"


def get_live_station_timetable(station_code):
    """
    Get live station timetable with real-time delays from IRIS
    
    Args:
        station_code: CFR station code (e.g., 10003, 10017)
        
    Returns:
        List of trains with live delay information
    """
    session = requests_html.HTMLSession()
    
    try:
        url = base_url.format(station_code)
        print(f"Fetching live timetable from IRIS: {url}")
        
        response = session.get(url, timeout=20)
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code} from IRIS")
        
        # Parse ViewState-based page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract timetable data from IRIS page
        trains = parse_iris_station_page(soup, station_code)
        
        if trains and len(trains) > 0:
            # Log delay statistics
            delayed_count = sum(1 for t in trains if t.get('delay', 0) > 0)
            print(f"Successfully scraped {len(trains)} trains with live data for station {station_code}")
            print(f"  - Trains with delays: {delayed_count}")
            if delayed_count > 0:
                avg_delay = sum(t.get('delay', 0) for t in trains if t.get('delay', 0) > 0) / delayed_count
                print(f"  - Average delay: {avg_delay:.1f} minutes")
            return trains
        else:
            print(f"No live trains found for station {station_code}")
            return []
            
    except Exception as e:
        print(f"Error fetching live station timetable: {e}")
        raise


def parse_iris_station_page(soup, station_code):
    """
    Parse IRIS station timetable page
    The page structure includes tables with train information
    """
    trains = []
    
    try:
        # Look for the main data table
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            # Skip header rows (usually first 1-2 rows)
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 4:  # Need at least train number, times, destination
                    train_data = parse_iris_train_row(cells, station_code)
                    if train_data:
                        trains.append(train_data)
        
        # Alternative: Look for div-based layouts (newer IRIS versions)
        if not trains:
            train_containers = soup.find_all('div', class_=re.compile(r'train|tren|arrival|departure|sosire|plecare', re.I))
            for container in train_containers:
                train_data = parse_iris_train_div(container, station_code)
                if train_data:
                    trains.append(train_data)
        
    except Exception as e:
        print(f"Error parsing IRIS station page: {e}")
    
    return trains


def parse_iris_train_row(cells, station_code):
    """
    Parse a table row from IRIS station timetable
    
    Expected columns (vary by IRIS version):
    - Train number (e.g., "IR 1621")
    - Arrival time
    - Departure time  
    - Origin/Destination
    - Platform
    - Delay/Status
    """
    try:
        # Extract text from cells
        cell_texts = [cell.get_text(strip=True) for cell in cells]
        
        # Train number is usually first column
        train_number_raw = cell_texts[0] if len(cell_texts) > 0 else ""
        
        # Clean train number (remove category prefix if combined)
        train_match = re.search(r'([A-Z\-]+\s*)?(\d+[a-z]*)', train_number_raw)
        if not train_match:
            return None
        
        category = train_match.group(1).strip() if train_match.group(1) else "R"
        train_number = train_match.group(2)
        
        # Times are usually in columns 1-2 (arrival, departure)
        arrival_time = parse_time(cell_texts[1]) if len(cell_texts) > 1 else None
        departure_time = parse_time(cell_texts[2]) if len(cell_texts) > 2 else None
        
        # Destination/Origin
        route_info = cell_texts[3] if len(cell_texts) > 3 else ""
        
        # Platform
        platform = cell_texts[4] if len(cell_texts) > 4 else None
        
        # Delay/Status - Check both cell text and HTML attributes for delay info
        delay_minutes = 0
        status = "La timp"
        
        # Method 1: Look for delay text in cells
        for cell_text in cell_texts:
            # Match patterns like: "+15 min", "întârziere 20 min", "delay 10", "15min", etc.
            delay_match = re.search(r'(?:\+|întârziere|intarziere|delay)\s*(\d+)\s*(?:min|minute)?', cell_text, re.I)
            if delay_match:
                delay_minutes = int(delay_match.group(1))
                status = f"+{delay_minutes} min"
                break
            
            # Also check for standalone numbers that might be delays (be conservative)
            if not delay_match and re.search(r'^\+?\d{1,3}$', cell_text):
                try:
                    potential_delay = int(cell_text.replace('+', ''))
                    if 1 <= potential_delay <= 300:  # Reasonable delay range
                        delay_minutes = potential_delay
                        status = f"+{delay_minutes} min"
                        break
                except:
                    pass
        
        # Method 2: Check HTML attributes for delay indicators
        for cell in cells:
            # Check for CSS classes like 'delay', 'late', 'intarziere'
            cell_class = cell.get('class', [])
            if isinstance(cell_class, list):
                cell_class = ' '.join(cell_class).lower()
            else:
                cell_class = str(cell_class).lower()
            
            if any(keyword in cell_class for keyword in ['delay', 'late', 'intarziere', 'tarziu']):
                # This cell likely contains delay info
                delay_text = cell.get_text(strip=True)
                delay_match = re.search(r'(\d+)', delay_text)
                if delay_match and not delay_minutes:  # Only set if not already found
                    delay_minutes = int(delay_match.group(1))
                    status = f"+{delay_minutes} min"
                    break
            
            # Check for style attributes (red/orange text often indicates delays)
            style = cell.get('style', '')
            if 'color' in style and any(color in style.lower() for color in ['red', 'orange', '#ff', '#f00', '#e74c3c']):
                delay_text = cell.get_text(strip=True)
                delay_match = re.search(r'(\d+)', delay_text)
                if delay_match and not delay_minutes:
                    delay_minutes = int(delay_match.group(1))
                    status = f"+{delay_minutes} min"
                    break
        
        # Check for cancelled/suppressed status
        for cell_text in cell_texts:
            if re.search(r'anulat|cancelled|supprim|suspendat', cell_text, re.I):
                status = "Anulat"
                delay_minutes = -999  # Special value for cancelled trains
                break
        
        # Determine if train is departing or arriving at this station
        is_origin = departure_time and not arrival_time
        is_destination = arrival_time and not departure_time
        is_stop = arrival_time and departure_time
        
        # Format train_id consistently with government data
        train_id = f"{category}{train_number}" if category else train_number
        
        return {
            'rank': category,  # Category for badge display
            'train_id': train_id,  # Full train identifier
            'train_number': train_number,
            'category': category,
            'arrival_time': arrival_time,
            'departure_time': departure_time,
            'origin': route_info if is_destination or is_stop else "",
            'destination': route_info if is_origin or is_stop else "",
            'platform': platform,
            'delay': delay_minutes,
            'status': status,
            'is_origin': is_origin,
            'is_destination': is_destination,
            'is_stop': is_stop,
            'operator': 'CFR Călători',
            'station_code': station_code,
            'data_source': 'iris_live',
            'mentions': ""
        }
        
    except Exception as e:
        print(f"Error parsing train row: {e}")
        return None


def parse_iris_train_div(container, station_code):
    """Parse train data from a div container (alternative layout)"""
    try:
        text = container.get_text(separator=' ', strip=True)
        
        # Look for train number
        train_match = re.search(r'([A-Z\-]+)?\s*(\d+[a-z]*)', text)
        if not train_match:
            return None
        
        category = train_match.group(1).strip() if train_match.group(1) else "R"
        train_number = train_match.group(2)
        
        # Look for times (HH:MM format)
        times = re.findall(r'(\d{1,2}:\d{2})', text)
        arrival_time = times[0] if len(times) > 0 else None
        departure_time = times[1] if len(times) > 1 else times[0] if len(times) == 1 else None
        
        # Look for delay - multiple patterns
        delay_minutes = 0
        status = "La timp"
        
        # Pattern 1: "+15 min" or "întârziere 20 min"
        delay_match = re.search(r'(?:\+|întârziere|intarziere|delay)\s*(\d+)\s*(?:min|minute)?', text, re.I)
        if delay_match:
            delay_minutes = int(delay_match.group(1))
            status = f"+{delay_minutes} min"
        
        # Pattern 2: Check HTML classes for delay indicators
        container_class = container.get('class', [])
        if isinstance(container_class, list):
            container_class = ' '.join(container_class).lower()
        else:
            container_class = str(container_class).lower()
        
        if 'delay' in container_class or 'late' in container_class or 'intarziere' in container_class:
            # Extract number from text if we haven't found delay yet
            if not delay_minutes:
                num_match = re.search(r'(\d+)\s*(?:min)?', text)
                if num_match:
                    delay_minutes = int(num_match.group(1))
                    status = f"+{delay_minutes} min"
        
        # Check for cancelled
        if re.search(r'anulat|cancelled|supprim|suspendat', text, re.I):
            status = "Anulat"
            delay_minutes = -999
        
        # Format train_id consistently
        train_id = f"{category}{train_number}" if category else train_number
        
        return {
            'rank': category,
            'train_id': train_id,
            'train_number': train_number,
            'category': category,
            'arrival_time': arrival_time,
            'departure_time': departure_time,
            'origin': "",
            'destination': "",
            'platform': None,
            'delay': delay_minutes,
            'status': status,
            'is_origin': departure_time and not arrival_time,
            'is_destination': arrival_time and not departure_time,
            'is_stop': arrival_time and departure_time,
            'operator': 'CFR Călători',
            'station_code': station_code,
            'data_source': 'iris_live',
            'mentions': ""
        }
        
    except Exception as e:
        print(f"Error parsing train div: {e}")
        return None


def parse_time(time_str):
    """Parse time from various formats"""
    if not time_str:
        return None
    
    # Clean the string
    time_str = time_str.strip()
    
    # Match HH:MM format
    time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        return f"{hours:02d}:{minutes:02d}"
    
    return None


def format_live_timetable(trains):
    """
    Format live timetable data for API response
    Sorts by time and adds metadata
    """
    # Sort by departure or arrival time
    def get_sort_time(train):
        time_str = train.get('departure_time') or train.get('arrival_time') or "00:00"
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    sorted_trains = sorted(trains, key=get_sort_time)
    
    return sorted_trains


if __name__ == "__main__":
    # Test with București Nord (station code 10003)
    import sys
    
    station_code = sys.argv[1] if len(sys.argv) > 1 else "10003"
    
    print(f"Testing live timetable for station {station_code}...")
    trains = get_live_station_timetable(station_code)
    
    print(f"\nFound {len(trains)} trains:")
    for train in trains[:10]:  # Show first 10
        print(f"{train['category']}{train['train_number']}: "
              f"Arr={train['arrival_time']} Dep={train['departure_time']} "
              f"Delay={train['delay']}min Status={train['status']}")
