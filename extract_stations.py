import json
import re
import os

def extract_stations_text():
    xml_path = 'trenuri-2025-2026_sntfc.xml'
    if not os.path.exists(xml_path):
        print(f"XML not found at {xml_path}")
        return
    
    print(f"Scanning {xml_path} as text...")
    stations_set = set() # (code, name)
    
    # Regex to find CodStaOrigine and DenStaOrigine
    # Example: CodStaOrigine="55043" DenStaOrigine="StrÃ¢mba h."
    pattern_orig = re.compile(r'CodStaOrigine="(\d+)" DenStaOrigine="([^"]+)"')
    pattern_dest = re.compile(r'CodStaDest="(\d+)" DenStaDestinatie="([^"]+)"')
    
    try:
        with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                matches_orig = pattern_orig.findall(line)
                for code, name in matches_orig:
                    stations_set.add((code, name))
                
                matches_dest = pattern_dest.findall(line)
                for code, name in matches_dest:
                    stations_set.add((code, name))
        
        print(f"Found {len(stations_set)} raw pairs")
        
        # Format and cleanup names
        stations_list = []
        for code, name in stations_set:
            # Fix common encoding issues if any (but errors='ignore' should handle basics)
            # Actually, the file seems to have some mangled characters like Äƒ
            # We'll just take it as is for now as it matches what the XML parser would see
            stations_list.append({
                "name": name.strip(),
                "station_id": code,
                "region": "Unknown",
                "importance": 6
            })
            
        stations_list.sort(key=lambda x: x['name'])
        
        with open('src/station_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(stations_list, f, ensure_ascii=False, indent=2)
            
        print(f"Saved {len(stations_list)} stations to src/station_mapping.json")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_stations_text()
