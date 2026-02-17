#!/usr/bin/env python3
"""
Romanian Railway Government Data Parser
Parses official CFR data from data.gov.ro XML files
"""

import xml.etree.ElementTree as ET
import json
from datetime import datetime
import re

class GovernmentDataParser:
    def __init__(self, xml_file_path):
        self.xml_file_path = xml_file_path
        self.tree = None
        self.root = None
        self.trains = []
        self.stations = {}
        
    def load_xml(self):
        """Load and parse the XML file"""
        try:
            self.tree = ET.parse(self.xml_file_path)
            self.root = self.tree.getroot()
            print(f"Successfully loaded XML file: {self.xml_file_path}")
            return True
        except Exception as e:
            print(f"Error loading XML file: {e}")
            return False
    
    def extract_stations(self):
        """Extract all unique stations from the XML data"""
        stations_set = set()
        
        # Find all train routes under Trenuri/Tren
        for tren in self.root.findall('.//Trenuri/Tren'):
            # Get route elements under Trase/Trasa/ElementTrasa
            for element in tren.findall('.//Trase/Trasa/ElementTrasa'):
                # Origin station
                cod_sta_orig = element.get('CodStaOrigine')
                den_sta_orig = element.get('DenStaOrigine')
                if cod_sta_orig and den_sta_orig:
                    stations_set.add((cod_sta_orig, den_sta_orig))
                
                # Destination station
                cod_sta_dest = element.get('CodStaDest')
                den_sta_dest = element.get('DenStaDestinatie')
                if cod_sta_dest and den_sta_dest:
                    stations_set.add((cod_sta_dest, den_sta_dest))
        
        # Convert to list of dictionaries
        stations_list = []
        for code, name in stations_set:
            if code and name:  # Ensure both code and name exist
                stations_list.append({
                    'code': code,
                    'name': name.strip(),
                    'id': code  # Use code as ID for compatibility
                })
        
        # Sort by name for better organization
        stations_list.sort(key=lambda x: x['name'])
        
        print(f"Extracted {len(stations_list)} unique stations")
        return stations_list
    
    def extract_trains(self):
        """Extract all trains from the XML data"""
        trains_list = []
        
        for tren in self.root.findall('.//Trenuri/Tren'):
            # Get basic train info from attributes
            train_number = tren.get('Numar')
            category = tren.get('CategorieTren')
            operator = tren.get('Operator')
            
            if train_number:
                # Get route info
                route_elements = []
                
                for trasa in tren.findall('.//Trase/Trasa'):
                    for element in trasa.findall('ElementTrasa'):
                        # Extract station and timing info from attributes
                        element_data = {
                            'cod_sta_origine': element.get('CodStaOrigine'),
                            'den_sta_origine': element.get('DenStaOrigine'),
                            'cod_sta_dest': element.get('CodStaDest'),
                            'den_sta_dest': element.get('DenStaDestinatie'),
                            'ora_plecare': element.get('OraP'),
                            'ora_sosire': element.get('OraS'),
                            'km': element.get('Km'),
                            'tip_oprire': element.get('TipOprire'),
                            'secventa': element.get('Secventa')
                        }
                        route_elements.append(element_data)
                
                train_data = {
                    'train_number': train_number,
                    'category': category if category else 'Unknown',
                    'operator': 'CFR Călători',
                    'route_elements': route_elements
                }
                
                trains_list.append(train_data)
        
        print(f"Extracted {len(trains_list)} trains")
        return trains_list
    
    def get_train_route(self, train_number):
        """Get specific train route by train number"""
        for train in self.trains:
            if train['train_number'] == train_number:
                return self.convert_to_stops_format(train)
        return None
    
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

    def convert_to_stops_format(self, train_data):
        """Convert government data format to our app's expected format"""
        stops = []
        
        for i, element in enumerate(train_data['route_elements']):
            # For the first element, use origin station
            if i == 0 and element['den_sta_origine']:
                stop = {
                    'station_name': element['den_sta_origine'],
                    'station_code': element['cod_sta_origine'],
                    'arrival_time': None,  # First station has no arrival
                    'departure_time': self.convert_seconds_to_time(element['ora_plecare']),
                    'platform': None,
                    'delay': 0,
                    'status': 'scheduled',
                    'distance_km': float(element['km']) if element['km'] else 0,
                    'stop_type': element['tip_oprire']
                }
                stops.append(stop)
            
            # Add destination station
            if element['den_sta_dest']:
                stop = {
                    'station_name': element['den_sta_dest'],
                    'station_code': element['cod_sta_dest'],
                    'arrival_time': self.convert_seconds_to_time(element['ora_sosire']),
                    'departure_time': self.convert_seconds_to_time(element['ora_plecare']) if i < len(train_data['route_elements']) - 1 else None,
                    'platform': None,
                    'delay': 0,
                    'status': 'scheduled',
                    'distance_km': float(element['km']) if element['km'] else 0,
                    'stop_type': element['tip_oprire']
                }
                stops.append(stop)
        
        # Remove duplicates while preserving order
        # Strategy: Keep stations by code, preferring final destination (no departure) over intermediate stops
        seen_codes = {}
        for i, stop in enumerate(stops):
            code = stop['station_code']
            if code not in seen_codes:
                seen_codes[code] = i
            else:
                # Station appears multiple times
                # If current stop has no departure time (final destination), replace previous
                if not stop['departure_time']:
                    seen_codes[code] = i
        
        # Build unique stops list based on selected indices
        unique_stops = [stops[i] for i in sorted(seen_codes.values())]
        
        return unique_stops

def categorize_stations(stations):
    """Categorize stations by importance and location with proper city identification"""
    categories = {
        'major_cities': [],
        'regional_centers': [],
        'smaller_stations': [],
        'bucharest_area': []
    }
    
    # Major cities in Romania (by population and railway importance)
    major_cities = {
        'cluj': 'Cluj-Napoca',
        'timişoara': 'Timișoara', 
        'timisoara': 'Timișoara',
        'iaşi': 'Iași',
        'iasi': 'Iași',
        'constanţa': 'Constanța',
        'constanta': 'Constanța',
        'craiova': 'Craiova',
        'braşov': 'Brașov',
        'brasov': 'Brașov',
        'galaţi': 'Galați',
        'galati': 'Galați',
        'ploieşti': 'Ploiești',
        'ploiesti': 'Ploiești',
        'oradea': 'Oradea',
        'arad': 'Arad',
        'bacău': 'Bacău',
        'bacau': 'Bacău',
        'sibiu': 'Sibiu',
        'târgu mureş': 'Târgu Mureș',
        'targu mures': 'Târgu Mureș',
        'baia mare': 'Baia Mare',
        'buzău': 'Buzău',
        'buzau': 'Buzău',
        'satu mare': 'Satu Mare',
        'botoşani': 'Botoșani',
        'botosani': 'Botoșani',
        'râmnicu vâlcea': 'Râmnicu Vâlcea',
        'ramnicu valcea': 'Râmnicu Vâlcea',
        'piatra neamţ': 'Piatra Neamț',
        'piatra neamt': 'Piatra Neamț',
        'deva': 'Deva',
        'alba iulia': 'Alba Iulia',
        'hunedoara': 'Hunedoara',
        'reşiţa': 'Reșița',
        'resita': 'Reșița',
        'târgovişte': 'Târgoviște',
        'targoviste': 'Târgoviște'
    }
    
    # Regional indicators
    regional_indicators = ['jud', 'județ', 'judet', 'târgu', 'targu', 'târg', 'targ']
    
    for station in stations:
        name_lower = station['name'].lower()
        
        # Check if it's in Bucharest area
        if 'bucureşti' in name_lower or 'bucurești' in name_lower or 'băneasa' in name_lower:
            categories['bucharest_area'].append(station)
        # Check if it's a major city station
        elif any(city in name_lower for city in major_cities.keys()):
            categories['major_cities'].append(station)
        # Check if it's a regional center
        elif any(indicator in name_lower for indicator in regional_indicators):
            categories['regional_centers'].append(station)
        else:
            categories['smaller_stations'].append(station)
    
    return categories

def main():
    # Initialize parser
    parser = GovernmentDataParser('sntfc-cfr-calatori-s.a_1303-tr_2025.xml')
    
    if not parser.load_xml():
        return
    
    # Extract data
    print("Extracting stations...")
    stations = parser.extract_stations()
    
    print("Extracting trains...")
    trains = parser.extract_trains()
    parser.trains = trains
    
    # Categorize stations
    print("Categorizing stations...")
    categorized = categorize_stations(stations)
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total stations: {len(stations)}")
    print(f"Bucharest area: {len(categorized['bucharest_area'])}")
    print(f"Major cities: {len(categorized['major_cities'])}")
    print(f"Regional centers: {len(categorized['regional_centers'])}")
    print(f"Smaller stations: {len(categorized['smaller_stations'])}")
    print(f"Total trains: {len(trains)}")
    
    # Sample some major city stations
    print(f"\n=== MAJOR CITY STATIONS (sample) ===")
    for station in categorized['major_cities'][:10]:
        print(f"  {station['name']} (Code: {station['code']})")
    
    # Sample some Bucharest stations
    print(f"\n=== BUCHAREST AREA STATIONS ===")
    for station in categorized['bucharest_area']:
        print(f"  {station['name']} (Code: {station['code']})")
    
    # Test train lookup
    print(f"\n=== TESTING TRAIN LOOKUP ===")
    test_trains = ['IC 581', 'IR 1731', 'R 2345']
    for train_num in test_trains:
        route = parser.get_train_route(train_num)
        if route:
            print(f"\nTrain {train_num} found! Route:")
            for stop in route[:3]:  # Show first 3 stops
                print(f"  {stop['station_name']} - Arr: {stop['arrival_time']}, Dep: {stop['departure_time']}")
            if len(route) > 3:
                print(f"  ... and {len(route) - 3} more stops")
        else:
            print(f"Train {train_num} not found")
    
    return parser, stations, trains, categorized

if __name__ == "__main__":
    main()
