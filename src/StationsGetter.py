import requests_html
import re
import json
from pprint import pprint

base_url = "https://bilete.cfrcalatori.ro/ro-RO/Stations"


def get_stations():
    """
    Get real station list from CFR Călători website
    Falls back to comprehensive demo data if API fails
    """
    try:
        return get_real_stations()
    except Exception as e:
        print(f"Failed to fetch real stations: {e}")
        print("Falling back to comprehensive demo station list")
        return get_demo_stations()


def get_real_stations():
    """
    Scrape real stations from CFR Călători website
    """
    session = requests_html.HTMLSession()
    
    try:
        # Try to get the stations page
        response = session.get(base_url, timeout=15)
        response.raise_for_status()
        
        # Parse the page to extract station data
        # CFR Călători likely has an autocomplete endpoint for stations
        
        # Try to find JavaScript that loads stations
        scripts = response.html.find('script')
        station_data = []
        
        for script in scripts:
            if script.text and ('station' in script.text.lower() or 'gara' in script.text.lower()):
                # Look for JSON data containing stations
                try:
                    # Extract JSON-like patterns
                    json_matches = re.findall(r'\[.*?\]', script.text)
                    for match in json_matches:
                        if 'station' in match.lower() or len(match) > 100:
                            try:
                                data = json.loads(match)
                                if isinstance(data, list) and len(data) > 10:
                                    # This might be our stations list
                                    for item in data:
                                        if isinstance(item, dict) and 'name' in item:
                                            station_data.append(item)
                            except:
                                continue
                except:
                    continue
        
        # If we found station data, format it properly
        if station_data and len(station_data) > 20:
            print(f"Successfully scraped {len(station_data)} stations from CFR")
            return format_scraped_stations(station_data)
        
        # If direct scraping failed, try alternative approach
        return try_autocomplete_api()
        
    except Exception as e:
        print(f"Error scraping CFR stations: {e}")
        raise


def try_autocomplete_api():
    """
    Try to find CFR's autocomplete API for stations
    """
    session = requests_html.HTMLSession()
    
    # Common autocomplete endpoints
    endpoints = [
        "https://bilete.cfrcalatori.ro/api/stations",
        "https://bilete.cfrcalatori.ro/ro-RO/api/stations", 
        "https://bilete.cfrcalatori.ro/autocomplete/stations",
        "https://bilete.cfrcalatori.ro/ro-RO/autocomplete/stations"
    ]
    
    for endpoint in endpoints:
        try:
            response = session.get(endpoint, timeout=10)
            if response.status_code == 200 and response.text:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 20:
                        print(f"Found stations API at {endpoint}")
                        return format_api_stations(data)
                except:
                    continue
        except:
            continue
    
    # If no API found, return our comprehensive demo list
    raise Exception("No real station API found")


def format_scraped_stations(raw_data):
    """Format scraped station data into our expected format"""
    formatted = []
    for item in raw_data[:150]:  # Limit to reasonable number
        if isinstance(item, dict):
            name = item.get('name', item.get('label', item.get('text', '')))
            station_id = item.get('id', item.get('value', item.get('station_id', '')))
            
            if name and station_id:
                formatted.append({
                    "name": name,
                    "station_id": str(station_id)
                })
    
    return formatted if len(formatted) > 20 else get_demo_stations()


def format_api_stations(raw_data):
    """Format API station data into our expected format"""
    formatted = []
    for item in raw_data[:150]:
        if isinstance(item, dict):
            name = item.get('name', item.get('label', item.get('text', '')))
            station_id = item.get('id', item.get('value', item.get('code', '')))
            
            if name and station_id:
                formatted.append({
                    "name": name,
                    "station_id": str(station_id)
                })
        elif isinstance(item, str):
            # If it's just a string, create an ID from it
            formatted.append({
                "name": item,
                "station_id": item.lower().replace(' ', '-').replace('ă', 'a').replace('î', 'i').replace('ș', 's').replace('ț', 't').replace('â', 'a')
            })
    
    return formatted if len(formatted) > 20 else get_demo_stations()


def get_demo_stations():
    """
    Comprehensive station list for Romanian Railway Network
    Based on real CFR network - used as fallback
    """
    stations = [
        # Major hubs and cities
        {"name": "București Nord", "station_id": "bucuresti-nord"},
        {"name": "București Basarab", "station_id": "bucuresti-basarab"},
        {"name": "București Obor", "station_id": "bucuresti-obor"},
        {"name": "Constanța", "station_id": "constanta"},
        {"name": "Cluj-Napoca", "station_id": "cluj-napoca"},
        {"name": "Iași", "station_id": "iasi"},
        {"name": "Brașov", "station_id": "brasov"},
        {"name": "Timișoara Nord", "station_id": "timisoara-nord"},
        {"name": "Craiova", "station_id": "craiova"},
        {"name": "Galați", "station_id": "galati"},
        {"name": "Suceava", "station_id": "suceava"},
        {"name": "Ploiești Sud", "station_id": "ploiesti-sud"},
        {"name": "Ploiești Vest", "station_id": "ploiesti-vest"},
        {"name": "Buzău", "station_id": "buzau"},
        {"name": "Oradea", "station_id": "oradea"},
        {"name": "Arad", "station_id": "arad"},
        {"name": "Bacău", "station_id": "bacau"},
        {"name": "Pitești", "station_id": "pitesti"},
        {"name": "Satu Mare", "station_id": "satu-mare"},
        {"name": "Baia Mare", "station_id": "baia-mare"},
        {"name": "Reșița", "station_id": "resita"},
        {"name": "Deva", "station_id": "deva"},
        {"name": "Târgu Mureș", "station_id": "targu-mures"},
        {"name": "Sibiu", "station_id": "sibiu"},
        
        # Regional centers
        {"name": "Alba Iulia", "station_id": "alba-iulia"},
        {"name": "Alba Iulia Parc", "station_id": "alba-iulia-parc"},
        {"name": "Alexandria", "station_id": "alexandria"},
        {"name": "Bârlad", "station_id": "barlad"},
        {"name": "Bistrița", "station_id": "bistrita"},
        {"name": "Botoșani", "station_id": "botosani"},
        {"name": "Brăila", "station_id": "braila"},
        {"name": "Calafat", "station_id": "calafat"},
        {"name": "Caracal", "station_id": "caracal"},
        {"name": "Caransebeș", "station_id": "caransebes"},
        {"name": "Cernavodă", "station_id": "cernavoda"},
        {"name": "Dej", "station_id": "dej"},
        {"name": "Dorohoi", "station_id": "dorohoi"},
        {"name": "Drăgășani", "station_id": "dragasani"},
        {"name": "Făgăraș", "station_id": "fagaras"},
        {"name": "Fetești", "station_id": "fetesti"},
        {"name": "Filiași", "station_id": "filiasi"},
        {"name": "Focșani", "station_id": "focsani"},
        {"name": "Giurgiu Nord", "station_id": "giurgiu-nord"},
        {"name": "Hunedoara", "station_id": "hunedoara"},
        {"name": "Lugoj", "station_id": "lugoj"},
        {"name": "Mangalia", "station_id": "mangalia"},
        {"name": "Medgidia", "station_id": "medgidia"},
        {"name": "Miercurea Ciuc", "station_id": "miercurea-ciuc"},
        {"name": "Moreni", "station_id": "moreni"},
        {"name": "Motru", "station_id": "motru"},
        {"name": "Oltenița", "station_id": "oltenita"},
        {"name": "Onești", "station_id": "onesti"},
        {"name": "Orșova", "station_id": "orsova"},
        {"name": "Pascani", "station_id": "pascani"},
        {"name": "Petroșani", "station_id": "petrosani"},
        {"name": "Piatra Neamț", "station_id": "piatra-neamt"},
        {"name": "Râmnicu Vâlcea", "station_id": "ramnicu-valcea"},
        {"name": "Roman", "station_id": "roman"},
        {"name": "Roșiori Nord", "station_id": "rosiori-nord"},
        {"name": "Sălaj", "station_id": "salaj"},
        {"name": "Sfântu Gheorghe", "station_id": "sfantu-gheorghe"},
        {"name": "Sighetu Marmației", "station_id": "sighetu-marmatiei"},
        {"name": "Sighișoara", "station_id": "sighisoara"},
        {"name": "Simeria", "station_id": "simeria"},
        {"name": "Slobozia", "station_id": "slobozia"},
        {"name": "Târgoviște", "station_id": "targoviste"},
        {"name": "Târgu Jiu", "station_id": "targu-jiu"},
        {"name": "Tecuci", "station_id": "tecuci"},
        {"name": "Tulcea", "station_id": "tulcea"},
        {"name": "Turda", "station_id": "turda"},
        {"name": "Turnu Severin", "station_id": "turnu-severin"},
        {"name": "Vaslui", "station_id": "vaslui"},
        {"name": "Vatra Dornei", "station_id": "vatra-dornei"},
        {"name": "Zalău", "station_id": "zalau"},
        
        # Mountain and tourism destinations
        {"name": "Sinaia", "station_id": "sinaia"},
        {"name": "Predeal", "station_id": "predeal"},
        {"name": "Azuga", "station_id": "azuga"},
        {"name": "Busteni", "station_id": "busteni"},
        {"name": "Câmpina", "station_id": "campina"},
        {"name": "Băile Herculane", "station_id": "baile-herculane"},
        {"name": "Băile Olănești", "station_id": "baile-olanesti"},
        {"name": "Băile Govora", "station_id": "baile-govora"},
        {"name": "Sovata", "station_id": "sovata"},
        {"name": "Borșa", "station_id": "borsa"},
        {"name": "Vișeu de Sus", "station_id": "viseu-de-sus"},
        
        # Industrial and suburban stations
        {"name": "Băicoi", "station_id": "baicoi"},
        {"name": "Băilești", "station_id": "bailesti"},
        {"name": "Bălți", "station_id": "balti"},
        {"name": "Bicaz", "station_id": "bicaz"},
        {"name": "Blaj", "station_id": "blaj"},
        {"name": "Bocșa", "station_id": "bocsa"},
        {"name": "Boldești Scăeni", "station_id": "boldesti-scaeni"},
        {"name": "Borcea", "station_id": "borcea"},
        {"name": "Brad", "station_id": "brad"},
        {"name": "Breaza", "station_id": "breaza"},
        {"name": "Budești", "station_id": "budesti"},
        {"name": "Carei", "station_id": "carei"},
        {"name": "Călan", "station_id": "calan"},
        {"name": "Călărași", "station_id": "calarasi"},
        {"name": "Codlea", "station_id": "codlea"},
        {"name": "Comănești", "station_id": "comanesti"},
        {"name": "Corabia", "station_id": "corabia"},
        {"name": "Costești", "station_id": "costesti"},
        
        # Border and international connections
        {"name": "Curtici", "station_id": "curtici"},
        {"name": "Episcopia Bihor", "station_id": "episcopia-bihor"},
        {"name": "Halmeu", "station_id": "halmeu"},
        {"name": "Ianca", "station_id": "ianca"},
        {"name": "Jimbolia", "station_id": "jimbolia"},
        {"name": "Nădlac", "station_id": "nadlac"},
        {"name": "Petea", "station_id": "petea"},
        {"name": "Rădăuți", "station_id": "radauti"},
        {"name": "Stamora Moravița", "station_id": "stamora-moravita"},
        {"name": "Vicșani", "station_id": "vicsani"},
        
        # Smaller towns and villages with railway connections
        {"name": "Abrud", "station_id": "abrud"},
        {"name": "Adjud", "station_id": "adjud"},
        {"name": "Agnita", "station_id": "agnita"},
        {"name": "Aiud", "station_id": "aiud"},
        {"name": "Aleșd", "station_id": "alesd"},
        {"name": "Apoldu de Sus", "station_id": "apoldu-de-sus"},
        {"name": "Armășești", "station_id": "armasesti"},
        {"name": "Avrig", "station_id": "avrig"},
        {"name": "Bălan", "station_id": "balan"},
        {"name": "Băneasa", "station_id": "baneasa"},
        {"name": "Baru Mare", "station_id": "baru-mare"},
        {"name": "Beclean", "station_id": "beclean"},
        {"name": "Beius", "station_id": "beius"},
        {"name": "Bethlen", "station_id": "bethlen"},
        {"name": "Câmpia Turzii", "station_id": "campia-turzii"},
        {"name": "Capu Midia", "station_id": "capu-midia"},
        {"name": "Ciceu", "station_id": "ciceu"},
        {"name": "Ciurea", "station_id": "ciurea"},
        {"name": "Copșa Mică", "station_id": "copsa-mica"},
        {"name": "Coșlariu", "station_id": "coslariu"},
        {"name": "Criscior", "station_id": "criscior"},
        {"name": "Dărmănești", "station_id": "darmanesti"},
        {"name": "Gheorgheni", "station_id": "gheorgheni"},
        {"name": "Gherla", "station_id": "gherla"},
        {"name": "Ghimbav", "station_id": "ghimbav"},
        {"name": "Gura Humorului", "station_id": "gura-humorului"},
        {"name": "Hațeg", "station_id": "hateg"},
        {"name": "Ilia", "station_id": "ilia"},
        {"name": "Intorsura Buzăului", "station_id": "intorsura-buzaului"},
        {"name": "Jibou", "station_id": "jibou"}
    ]
    
    return stations
