"""
Government Railway Data Parser
Parses the official Romanian railway XML data from data.gov.ro
"""
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class GovDataParser:
    def __init__(self, xml_file_path: str):
        """Initialize with path to the XML file"""
        self.xml_file_path = xml_file_path
        self.tree = None
        self.root = None
        self.trains_data = {}
        self.stations_data = {}
        
    def load_xml(self):
        """Load and parse the XML file"""
        try:
            self.tree = ET.parse(self.xml_file_path)
            self.root = self.tree.getroot()
            return True
        except Exception as e:
            print(f"Error loading XML: {e}")
            return False
    
    def parse_trains(self):
        """Parse all trains from the XML data"""
        if not self.root:
            if not self.load_xml():
                return {}
        
        trains = {}
        
        # Find all train elements
        for train_elem in self.root.findall(".//Tren"):
            train_data = self._parse_single_train(train_elem)
            if train_data:
                train_number = train_data['number']
                trains[train_number] = train_data
                
        self.trains_data = trains
        return trains
    
    def _parse_single_train(self, train_elem) -> Optional[Dict[str, Any]]:
        """Parse a single train element"""
        try:
            # Basic train info
            train_number = train_elem.get('Numar')
            category = train_elem.get('CategorieTren')
            
            if not train_number or not category:
                return None
            
            train_data = {
                'number': train_number,
                'category': category,
                'operator': 'CFR Călători',
                'length': train_elem.get('Lungime'),
                'tonnage': train_elem.get('Tonaj'),
                'rank': train_elem.get('Rang'),
                'services': train_elem.get('Servicii'),
                'routes': []
            }
            
            # Parse routes
            for route_elem in train_elem.findall(".//Trasa"):
                route_data = self._parse_route(route_elem)
                if route_data:
                    train_data['routes'].append(route_data)
            
            return train_data
            
        except Exception as e:
            print(f"Error parsing train: {e}")
            return None
    
    def _parse_route(self, route_elem) -> Optional[Dict[str, Any]]:
        """Parse a single route element"""
        try:
            route_data = {
                'id': route_elem.get('Id'),
                'type': route_elem.get('Tip'),
                'origin_station_code': route_elem.get('CodStatieInitiala'),
                'destination_station_code': route_elem.get('CodStatieFinala'),
                'stops': []
            }
            
            # Parse route elements (stops)
            for elem_trasa in route_elem.findall("ElementTrasa"):
                stop_data = self._parse_stop(elem_trasa)
                if stop_data:
                    route_data['stops'].append(stop_data)
                    
                    # Collect station data
                    origin_code = stop_data['origin_station_code']
                    dest_code = stop_data['destination_station_code']
                    
                    if origin_code not in self.stations_data:
                        self.stations_data[origin_code] = {
                            'code': origin_code,
                            'name': stop_data['origin_station_name']
                        }
                    
                    if dest_code not in self.stations_data:
                        self.stations_data[dest_code] = {
                            'code': dest_code,
                            'name': stop_data['destination_station_name']
                        }
            
            return route_data
            
        except Exception as e:
            print(f"Error parsing route: {e}")
            return None
    
    def _parse_stop(self, elem_trasa) -> Optional[Dict[str, Any]]:
        """Parse a single stop element"""
        try:
            # Convert time from seconds to HH:MM format
            def seconds_to_time(seconds_str):
                if not seconds_str:
                    return None
                try:
                    total_seconds = int(seconds_str)
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    return f"{hours:02d}:{minutes:02d}"
                except:
                    return None
            
            stop_data = {
                'sequence': int(elem_trasa.get('Secventa', 0)),
                'origin_station_code': elem_trasa.get('CodStaOrigine'),
                'destination_station_code': elem_trasa.get('CodStaDest'),
                'origin_station_name': elem_trasa.get('DenStaOrigine'),
                'destination_station_name': elem_trasa.get('DenStaDestinatie'),
                'departure_time': seconds_to_time(elem_trasa.get('OraP')),
                'arrival_time': seconds_to_time(elem_trasa.get('OraS')),
                'distance_km': elem_trasa.get('Km'),
                'stop_type': elem_trasa.get('TipOprire'),
                'stop_duration_seconds': int(elem_trasa.get('StationareSecunde', 0)),
                'speed_limit': elem_trasa.get('VitezaLivret')
            }
            
            return stop_data
            
        except Exception as e:
            print(f"Error parsing stop: {e}")
            return None
    
    def get_train_by_number(self, train_number: str) -> Optional[Dict[str, Any]]:
        """Get train data by train number"""
        if not self.trains_data:
            self.parse_trains()
        
        return self.trains_data.get(train_number)
    
    def search_trains_by_route(self, origin_station: str, destination_station: str) -> List[Dict[str, Any]]:
        """Search for trains that go from origin to destination"""
        if not self.trains_data:
            self.parse_trains()
        
        matching_trains = []
        
        for train_number, train_data in self.trains_data.items():
            for route in train_data['routes']:
                # Check if this route contains both stations in the correct order
                origin_found = False
                origin_sequence = None
                
                for stop in route['stops']:
                    # Check if origin station matches
                    if (origin_station.lower() in stop['origin_station_name'].lower() or
                        origin_station.lower() in stop['destination_station_name'].lower()):
                        if not origin_found:
                            origin_found = True
                            origin_sequence = stop['sequence']
                    
                    # Check if destination station matches (after origin)
                    if (origin_found and origin_sequence and 
                        stop['sequence'] > origin_sequence and
                        (destination_station.lower() in stop['origin_station_name'].lower() or
                         destination_station.lower() in stop['destination_station_name'].lower())):
                        
                        matching_trains.append({
                            'train': train_data,
                            'route': route,
                            'origin_sequence': origin_sequence,
                            'destination_sequence': stop['sequence']
                        })
                        break
        
        return matching_trains
    
    def get_all_stations(self) -> Dict[str, Dict[str, str]]:
        """Get all stations found in the data"""
        if not self.stations_data:
            self.parse_trains()
        
        return self.stations_data
    
    def search_stations(self, query: str) -> List[Dict[str, str]]:
        """Search for stations by name"""
        if not self.stations_data:
            self.parse_trains()
        
        query_lower = query.lower()
        matching_stations = []
        
        for station_code, station_data in self.stations_data.items():
            if query_lower in station_data['name'].lower():
                matching_stations.append(station_data)
        
        return matching_stations
    
    def get_train_categories(self) -> List[str]:
        """Get all unique train categories"""
        if not self.trains_data:
            self.parse_trains()
        
        categories = set()
        for train_data in self.trains_data.values():
            categories.add(train_data['category'])
        
        return sorted(list(categories))

# Example usage and testing
if __name__ == "__main__":
    parser = GovDataParser("railway_data_2025.xml")
    
    # Test parsing
    print("Loading and parsing XML data...")
    trains = parser.parse_trains()
    print(f"Parsed {len(trains)} trains")
    
    # Test getting a specific train
    test_train = parser.get_train_by_number("536")  # IC 536 from our example
    if test_train:
        print(f"\nTrain IC 536 details:")
        print(f"Category: {test_train['category']}")
        print(f"Routes: {len(test_train['routes'])}")
        if test_train['routes']:
            first_route = test_train['routes'][0]
            print(f"First route stops: {len(first_route['stops'])}")
            if first_route['stops']:
                print(f"First stop: {first_route['stops'][0]['origin_station_name']} -> {first_route['stops'][0]['destination_station_name']}")
    
    # Test station search
    stations = parser.search_stations("București")
    print(f"\nFound {len(stations)} stations matching 'București':")
    for station in stations[:5]:  # Show first 5
        print(f"- {station['name']} (Code: {station['code']})")
    
    # Show categories
    categories = parser.get_train_categories()
    print(f"\nTrain categories: {', '.join(categories)}")
