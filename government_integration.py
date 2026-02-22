#!/usr/bin/env python3
"""
Government Data Integration for CFR Train Tracker
Integrates official CFR data from data.gov.ro into the train tracker application
"""

from government_data_parser import GovernmentDataParser
import json
from datetime import datetime, date
import re

import os

class GovernmentDataIntegration:
    def __init__(self, xml_file_path=None):
        if xml_file_path is None:
            # Default to the file in the same directory as this script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            xml_file_path = os.path.join(current_dir, 'trenuri-2025-2026_sntfc.xml')
            
        self.parser = GovernmentDataParser(xml_file_path)
        self.stations_list = []
        self.trains_list = []
        self.stations_dict = {}
        self.initialized = False
        # Data validity information
        self.valid_from = None
        self.valid_until = None
        self.export_date = None
        
    def initialize(self):
        """Load and parse government data"""
        if not self.parser.load_xml():
            return False
        
        # Extract data validity period
        self.extract_data_validity()
            
        self.stations_list = self.parser.extract_stations()
        self.trains_list = self.parser.extract_trains()
        self.parser.trains = self.trains_list  # Set for get_train_route
        
        # Create stations dictionary for quick lookup
        self.stations_dict = {station['code']: station for station in self.stations_list}
        
        self.initialized = True
        print(f"Government data initialized: {len(self.stations_list)} stations, {len(self.trains_list)} trains")
        print(f"Data valid from {self.valid_from} to {self.valid_until}")
        return True
    
    def get_stations_for_app(self):
        """Get stations in the format expected by the train tracker app"""
        if not self.initialized:
            return []
            
        # Convert to app format
        app_stations = []
        for station in self.stations_list:
            app_station = {
                'id': station['code'],
                'name': station['name'],
                'region': self._get_station_region(station['name']),
                'importance': self._get_station_importance(station['name'])
            }
            app_stations.append(app_station)
        
        # Sort by importance and name
        app_stations.sort(key=lambda x: (x['importance'], x['name']))
        return app_stations
    
    def convert_seconds_to_time(self, seconds_str):
        """Convert seconds from midnight to HH:MM format"""
        if not seconds_str:
            return None
        
        try:
            seconds = int(seconds_str)
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            
            # Handle times that go past midnight (next day)
            if hours >= 24:
                hours = hours % 24
            
            return f"{hours:02d}:{minutes:02d}"
        except (ValueError, TypeError):
            return seconds_str  # Return original if conversion fails

    def extract_data_validity(self):
        """Extract the data validity period from XML metadata"""
        try:
            # Find the Mt element with validity information
            mt_element = self.parser.root.find('.//Mt')
            if mt_element is not None:
                # Extract validity dates
                valid_from_str = mt_element.get('MtValabilDeLa')  # Format: YYYYMMDD
                valid_until_str = mt_element.get('MtValabilPinaLa')  # Format: YYYYMMDD
                export_date_str = mt_element.get('DataExport')  # Format: YYYYMMDD
                
                if valid_from_str and valid_until_str:
                    # Parse dates from YYYYMMDD format
                    self.valid_from = datetime.strptime(valid_from_str, '%Y%m%d').date()
                    self.valid_until = datetime.strptime(valid_until_str, '%Y%m%d').date()
                    
                if export_date_str:
                    self.export_date = datetime.strptime(export_date_str, '%Y%m%d').date()
                else:
                    self.export_date = date.today()
            else:
                # Fallback dates if XML doesn't contain validity info
                self.valid_from = date(2024, 12, 15)
                self.valid_until = date(2025, 12, 13)
                self.export_date = date.today()
                
        except Exception as e:
            print(f"⚠️ Could not extract data validity: {e}")
            # Set fallback dates
            self.valid_from = date(2024, 12, 15)
            self.valid_until = date(2025, 12, 13)
            self.export_date = date.today()
    
    def is_date_valid(self, search_date):
        """Check if a given date is within the data validity period"""
        if isinstance(search_date, str):
            try:
                search_date = datetime.strptime(search_date, '%Y-%m-%d').date()
            except ValueError:
                return False
        elif isinstance(search_date, datetime):
            search_date = search_date.date()
            
        return self.valid_from <= search_date <= self.valid_until
    
    def get_data_validity_info(self):
        """Get information about data validity period"""
        return {
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "export_date": self.export_date.isoformat(),
            "is_current": self.valid_from <= date.today() <= self.valid_until,
            "days_remaining": (self.valid_until - date.today()).days if self.valid_until > date.today() else 0
        }

    def get_train_data(self, train_number, search_date=None, filter_stops=True):
        """Get train data in the format expected by the train tracker app
        
        Args:
            train_number: The train number to search for
            search_date: Optional date to validate against data validity
            filter_stops: If True, only include actual passenger stops (stop_type='N')
        """
        if not self.initialized:
            return None
        
        # Validate date if provided
        if search_date:
            if not self.is_date_valid(search_date):
                return {
                    "error": "Date out of range",
                    "message": f"Date {search_date} is outside data validity period",
                    "valid_from": self.valid_from.isoformat(),
                    "valid_until": self.valid_until.isoformat()
                }
            
        # Clean train number (remove any prefixes)
        clean_number = self._clean_train_number(train_number)
        
        # Get route from government data
        route = self.parser.get_train_route(clean_number)
        if not route:
            return None
            
        # Find train info
        train_info = None
        for train in self.trains_list:
            if train['train_number'] == clean_number:
                train_info = train
                break
                
        if not train_info:
            return None
            
        # Filter stations to show only actual passenger stops if requested
        # First add 'is_stop' attribute to all stations for the frontend
        for station in route:
            # A station is a stop if it's the first station, last station, or has stop_type 'C'
            # (Note: government XML uses 'C' for commercial stops, 'N' for passing points)
            station['is_stop'] = station.get('stop_type') == 'C' or station == route[0] or station == route[-1]

        if filter_stops:
            # Only include stations where passengers can actually board/alight
            filtered_route = [station for station in route if station['is_stop']]
            route = filtered_route if filtered_route else route  # Fallback to all stations if no 'C' stops found
        app_data = {
            "train_number": f"{train_info['category']} {clean_number}",
            "last_updated": datetime.now().isoformat(),
            "stations": route,
            "summary": {
                "total_stations": len(route),
                "origin": route[0]["station_name"] if route else None,
                "destination": route[-1]["station_name"] if route else None,
                "category": train_info['category'],
                "operator": train_info['operator']
            },
            "data_source": {
                "type": "government_official_data",
                "source": "data.gov.ro CFR Călători",
                "timestamp": datetime.now().isoformat(),
                "search_date": search_date if search_date else "current_schedule",
                "data_validity": {
                    "valid_from": self.valid_from.isoformat(),
                    "valid_until": self.valid_until.isoformat()
                },
                "reliability": "official"
            },
            "fallback_mode": False
        }
        
        return app_data
    
    def get_station_timetable(self, station_code):
        """Build station timetable from government data
        
        Args:
            station_code: Station code to get timetable for
            
        Returns:
            List of trains passing through this station with times
        """
        if not self.initialized:
            return []
        
        timetable = []
        
        # Convert station_code to string for comparison
        station_code_str = str(station_code)
        
        # Search through all trains to find ones that stop at this station
        for train in self.trains_list:
            train_number = train['train_number']
            route = self.parser.get_train_route(train_number)
            
            if not route:
                continue
            
            # Find ALL occurrences of this station in the route
            # (some stations appear multiple times, use the most relevant one)
            matches = []
            for i, stop in enumerate(route):
                if stop.get('station_code') == station_code_str:
                    matches.append((i, stop))
            
            if not matches:
                continue
            
            # Use the most relevant occurrence:
            # - If last match has no departure time, it's the destination (use that)
            # - Otherwise use the first match
            if len(matches) > 1 and not matches[-1][1].get('departure_time'):
                i, stop = matches[-1]  # Final destination
            else:
                i, stop = matches[0]  # First occurrence
            
            # This train stops at our station
            arrival_time = stop.get('arrival_time', '')
            departure_time = stop.get('departure_time', '')
            
            # Determine if this is origin, destination, or intermediate stop
            is_origin = i == 0
            is_destination = i == len(route) - 1 or not departure_time
            is_stop = not is_origin and not is_destination
            
            timetable_entry = {
                "rank": train['category'],
                "train_id": f"{train['category']} {train_number}",
                "train_number": train_number,
                "operator": train['operator'],
                "origin": route[0]['station_name'] if route else '',
                "destination": route[-1]['station_name'] if route else '',
                "arrival_time": arrival_time if arrival_time else "",
                "departure_time": departure_time if departure_time else "",
                "delay": 0,  # Government data doesn't have real-time delays
                "platform": "",  # Government data doesn't have platform info
                "is_origin": is_origin,
                "is_destination": is_destination,
                "is_stop": is_stop,
                "mentions": "",
                "data_source": "government_xml"  # Indicate this is scheduled data
            }
            
            timetable.append(timetable_entry)
        
        # Sort by time (departures take priority, then arrivals)
        def sort_key(entry):
            time_str = entry['departure_time'] or entry['arrival_time'] or "99:99"
            return time_str
        
        timetable.sort(key=sort_key)
        return timetable
    
    def search_trains(self, query, search_date=None):
        """Search for trains matching a query, optionally filtered by date"""
        if not self.initialized:
            return []
        
        # Validate date if provided
        if search_date:
            if not self.is_date_valid(search_date):
                print(f"⚠️ Date {search_date} is outside data validity period ({self.valid_from} to {self.valid_until})")
                return []
            
        matches = []
        query_lower = query.lower()
        
        for train in self.trains_list:
            # Match by number
            if query_lower in train['train_number'].lower():
                matches.append({
                    'train_number': f"{train['category']} {train['train_number']}",
                    'category': train['category'],
                    'relevance': 'exact' if query_lower == train['train_number'].lower() else 'partial',
                    'search_date': search_date if search_date else 'current_schedule'
                })
            # Match by category - improved logic
            elif self._category_matches(query_lower, train['category'].lower()):
                matches.append({
                    'train_number': f"{train['category']} {train['train_number']}",
                    'category': train['category'],
                    'relevance': 'category',
                    'search_date': search_date if search_date else 'current_schedule'
                })
        
        # Sort by relevance
        matches.sort(key=lambda x: (x['relevance'] == 'exact', x['relevance'] == 'partial', x['train_number']))
        return matches[:20]  # Limit to 20 results
    
    def _category_matches(self, query, category):
        """Improved category matching logic"""
        # Exact match
        if query == category:
            return True
            
        # Handle common variations
        if query == 'r' and category == 'r':
            return True
        elif query == 'ir-n' and category == 'ir-n':
            return True
        elif query == 'irn' and category == 'ir-n':  # IRN -> IR-N
            return True
        elif query == 'ir_n' and category == 'ir-n':  # IR_N -> IR-N
            return True
        elif query == 'r-e' and category == 'r-e':
            return True
        elif query == 're' and category == 'r-e':  # RE -> R-E
            return True
        elif query == 'r-m' and category == 'r-m':
            return True
        elif query == 'rm' and category == 'r-m':  # RM -> R-M
            return True
            
        # Partial match for longer categories (avoid R matching IR)
        if len(query) > 1 and query in category:
            return True
            
        return False
    
    def _clean_train_number(self, train_id):
        """Extract just the number from train ID
        Handles formats like: 'IC 536', 'IC536', 'R-M 7948', 'R-M7948', '536', etc.
        """
        import re
        
        # First, try to extract just the numeric part using regex
        # This handles all cases: "IC 536", "IC536", "R-M 7948", "R-M7948", "536"
        match = re.search(r'(\d+)', train_id)
        if match:
            return match.group(1)
        
        # Fallback: return cleaned string
        return train_id.strip()
    
    def _get_station_region(self, station_name):
        """Determine station region based on name"""
        name_lower = station_name.lower()
        
        if 'bucureşti' in name_lower or 'bucurești' in name_lower:
            return 'Bucharest'
        elif any(city in name_lower for city in ['cluj', 'timişoara', 'timisoara', 'iaşi', 'iasi']):
            return 'Major Cities'
        elif any(city in name_lower for city in ['constanţa', 'constanta', 'craiova', 'braşov', 'brasov']):
            return 'Major Cities'
        elif any(term in name_lower for term in ['jud', 'târgu', 'targu']):
            return 'Regional Centers'
        else:
            return 'Local'
    
    def _get_station_importance(self, station_name):
        """Get station importance for sorting (lower number = higher importance)"""
        name_lower = station_name.lower()
        
        if 'bucureşti nord' in name_lower:
            return 1  # Highest priority
        elif 'bucureşti' in name_lower or 'bucurești' in name_lower:
            return 2
        elif any(city in name_lower for city in ['cluj napoca', 'timişoara nord', 'timisoara nord']):
            return 3
        elif any(city in name_lower for city in ['constanţa', 'constanta', 'craiova', 'braşov', 'brasov']):
            return 4
        elif 'nord' in name_lower or 'est' in name_lower or 'vest' in name_lower:
            return 5  # Directional stations
        else:
            return 6  # Regular stations

# Global instance
government_data = GovernmentDataIntegration()

def init_government_data():
    """Initialize government data (call this at app startup)"""
    return government_data.initialize()

def get_government_stations():
    """Get stations from government data"""
    return government_data.get_stations_for_app()

def get_government_train_data(train_number, search_date=None, filter_stops=True):
    """Get train data from government data
    
    Args:
        train_number: The train number to search for
        search_date: Optional date to validate
        filter_stops: If True, only show actual passenger stops (default: True)
    """
    return government_data.get_train_data(train_number, search_date, filter_stops)

def get_government_station_timetable(station_code):
    """Get station timetable from government data
    
    Args:
        station_code: Station code to get timetable for
        
    Returns:
        List of trains passing through this station
    """
    return government_data.get_station_timetable(station_code)

def search_government_trains(query, search_date=None):
    """Search trains in government data"""
    return government_data.search_trains(query, search_date)

def get_data_validity_info():
    """Get data validity information"""
    return government_data.get_data_validity_info()

def is_date_valid(search_date):
    """Check if a date is within the data validity period"""
    return government_data.is_date_valid(search_date)

def get_government_station_name(station_id):
    """Get station name by ID"""
    station_code = str(station_id)
    if not government_data.initialized:
        return None
        
    if station_code in government_data.stations_dict:
        return government_data.stations_dict[station_code]['name']
    return None

if __name__ == "__main__":
    # Test the integration
    print("=== TESTING GOVERNMENT DATA INTEGRATION ===")
    
    if init_government_data():
        print("Government data initialized successfully")
        
        # Test stations
        stations = get_government_stations()
        print(f"✅ Got {len(stations)} stations")
        print("Top 10 stations:")
        for station in stations[:10]:
            print(f"  {station['name']} ({station['region']}) - Priority: {station['importance']}")
        
        # Test train lookup
        print(f"\n=== TESTING TRAIN LOOKUP ===")
        test_trains = ['IC 536', '536', 'IR 1655', '1655', 'R 2872', '2872']
        for train_num in test_trains:
            data = get_government_train_data(train_num)
            if data:
                print(f"✅ {train_num} -> {data['summary']['origin']} to {data['summary']['destination']} ({data['summary']['total_stations']} stops)")
            else:
                print(f"❌ {train_num} not found")
        
        # Test search
        print(f"\n=== TESTING TRAIN SEARCH ===")
        for query in ['IC', '536', 'IR']:
            results = search_government_trains(query)
            print(f"Search '{query}': {len(results)} results")
            for result in results[:3]:
                print(f"  {result['train_number']} ({result['relevance']})")
    
    else:
        print("❌ Failed to initialize government data")
