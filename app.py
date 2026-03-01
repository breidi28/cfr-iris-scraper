from src import StationsGetter, StationTimetableGetter, config
from src.TrainPageGetter import get_train, get_real_train_data
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_compress import Compress
from datetime import datetime, timedelta
from dateutil import tz, parser
import logging
import json
import sqlite3
import os
import random
import threading
import re

app = Flask(__name__)
CORS(app)
Compress(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize passenger reports database
def init_passenger_db():
    """Initialize SQLite database for passenger reports and interactions"""
    # Always attempt table creation (IF NOT EXISTS is safe to run repeatedly)
    conn = sqlite3.connect('passenger_data.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS passenger_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        train_number TEXT NOT NULL,
        report_type TEXT NOT NULL,
        message TEXT,
        platform TEXT,
        delay_minutes INTEGER,
        crowding_level TEXT,
        station_name TEXT,
        reported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        verified_count INTEGER DEFAULT 0,
        helpful_count INTEGER DEFAULT 0,
        user_ip TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seat_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        train_number TEXT NOT NULL,
        car_number TEXT,
        available_seats INTEGER,
        total_seats INTEGER,
        station_name TEXT,
        reported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_ip TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS passenger_tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_name TEXT,
        tip_type TEXT NOT NULL,
        message TEXT NOT NULL,
        helpful_count INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_ip TEXT
    )
    ''')

    conn.commit()
    conn.close()
    logger.info("Passenger database initialized")

# Initialize the database
init_passenger_db()

# Generate the station lookup table with error handling
config.global_station_list = {}
stations: list[dict] = []

def get_demo_stations():
    """Comprehensive station list for Romanian Railway Network"""
    return [
        # Major cities and hubs
        {"name": "București Nord", "station_id": "bucuresti-nord"},
        {"name": "București Basarab", "station_id": "bucuresti-basarab"},
        {"name": "București Obor", "station_id": "bucuresti-obor"},
        {"name": "Cluj-Napoca", "station_id": "cluj-napoca"},
        {"name": "Constanța", "station_id": "constanta"},
        {"name": "Brașov", "station_id": "brasov"},
        {"name": "Timișoara Nord", "station_id": "timisoara-nord"},
        {"name": "Iași", "station_id": "iasi"},
        {"name": "Craiova", "station_id": "craiova"},
        {"name": "Galați", "station_id": "galati"},
        {"name": "Ploiești Sud", "station_id": "ploiesti-sud"},
        {"name": "Ploiești Vest", "station_id": "ploiesti-vest"},
        {"name": "Oradea", "station_id": "oradea"},
        {"name": "Arad", "station_id": "arad"},
        {"name": "Deva", "station_id": "deva"},
        {"name": "Târgu Mureș", "station_id": "targu-mures"},
        {"name": "Sibiu", "station_id": "sibiu"},
        {"name": "Bacău", "station_id": "bacau"},
        {"name": "Pitești", "station_id": "pitesti"},
        {"name": "Suceava", "station_id": "suceava"},
        {"name": "Satu Mare", "station_id": "satu-mare"},
        {"name": "Baia Mare", "station_id": "baia-mare"},
        {"name": "Reșița", "station_id": "resita"},
        
        # Regional centers and important towns
        {"name": "Alba Iulia", "station_id": "10021"},
        {"name": "Alba Iulia Parc", "station_id": "10121"},
        {"name": "Alexandria", "station_id": "10022"},
        {"name": "Bârlad", "station_id": "10023"},
        {"name": "Bistrița", "station_id": "10024"},
        {"name": "Botoșani", "station_id": "10025"},
        {"name": "Brăila", "station_id": "10026"},
        {"name": "Buzău", "station_id": "10027"},
        {"name": "Calafat", "station_id": "10028"},
        {"name": "Caracal", "station_id": "10029"},
        {"name": "Caransebeș", "station_id": "10030"},
        {"name": "Cernavodă", "station_id": "10031"},
        {"name": "Dej", "station_id": "10032"},
        {"name": "Dorohoi", "station_id": "10033"},
        {"name": "Drăgășani", "station_id": "10034"},
        {"name": "Făgăraș", "station_id": "10035"},
        {"name": "Fetești", "station_id": "10036"},
        {"name": "Filiași", "station_id": "10037"},
        {"name": "Focșani", "station_id": "10038"},
        {"name": "Giurgiu Nord", "station_id": "10039"},
        {"name": "Hunedoara", "station_id": "10040"},
        {"name": "Lugoj", "station_id": "10041"},
        {"name": "Mangalia", "station_id": "10042"},
        {"name": "Medgidia", "station_id": "10043"},
        {"name": "Miercurea Ciuc", "station_id": "10044"},
        {"name": "Moreni", "station_id": "10045"},
        {"name": "Motru", "station_id": "10046"},
        {"name": "Oltenița", "station_id": "10047"},
        {"name": "Onești", "station_id": "10048"},
        {"name": "Orșova", "station_id": "10049"},
        {"name": "Pascani", "station_id": "10050"},
        {"name": "Petroșani", "station_id": "10051"},
        {"name": "Piatra Neamț", "station_id": "10052"},
        {"name": "Râmnicu Vâlcea", "station_id": "10053"},
        {"name": "Roman", "station_id": "10054"},
        {"name": "Roșiori Nord", "station_id": "10055"},
        {"name": "Sălaj", "station_id": "10056"},
        {"name": "Sfântu Gheorghe", "station_id": "10057"},
        {"name": "Sighetu Marmației", "station_id": "10058"},
        {"name": "Sighișoara", "station_id": "10059"},
        {"name": "Simeria", "station_id": "10060"},
        {"name": "Slobozia", "station_id": "10061"},
        {"name": "Târgoviște", "station_id": "10062"},
        {"name": "Târgu Jiu", "station_id": "10063"},
        {"name": "Tecuci", "station_id": "10064"},
        {"name": "Tulcea", "station_id": "10065"},
        {"name": "Turda", "station_id": "10066"},
        {"name": "Turnu Severin", "station_id": "10067"},
        {"name": "Vaslui", "station_id": "10068"},
        {"name": "Vatra Dornei", "station_id": "10069"},
        {"name": "Zalău", "station_id": "10070"},
        
        # Mountain and tourism destinations
        {"name": "Sinaia", "station_id": "10071"},
        {"name": "Predeal", "station_id": "10072"},
        {"name": "Azuga", "station_id": "10073"},
        {"name": "Busteni", "station_id": "10074"},
        {"name": "Câmpina", "station_id": "10075"},
        {"name": "Băile Herculane", "station_id": "10076"},
        {"name": "Băile Olănești", "station_id": "10077"},
        {"name": "Băile Govora", "station_id": "10078"},
        {"name": "Sovata", "station_id": "10079"},
        {"name": "Borșa", "station_id": "10080"},
        {"name": "Vișeu de Sus", "station_id": "10081"},
        
        # Industrial and suburban stations
        {"name": "Băicoi", "station_id": "10082"},
        {"name": "Băilești", "station_id": "10083"},
        {"name": "Bălți", "station_id": "10084"},
        {"name": "Bicaz", "station_id": "10085"},
        {"name": "Blaj", "station_id": "10086"},
        {"name": "Bocșa", "station_id": "10087"},
        {"name": "Boldești Scăeni", "station_id": "10088"},
        {"name": "Borcea", "station_id": "10089"},
        {"name": "Brad", "station_id": "10090"},
        {"name": "Breaza", "station_id": "10091"},
        {"name": "Budești", "station_id": "10092"},
        {"name": "Carei", "station_id": "10093"},
        {"name": "Călan", "station_id": "10094"},
        {"name": "Călărași", "station_id": "10095"},
        {"name": "Cărei", "station_id": "10096"},
        {"name": "Codlea", "station_id": "10097"},
        {"name": "Comănești", "station_id": "10098"},
        {"name": "Corabia", "station_id": "10099"},
        {"name": "Costești", "station_id": "10100"},
        
        # Border and international connections
        {"name": "Curtici", "station_id": "10110"},
        {"name": "Episcopia Bihor", "station_id": "10111"},
        {"name": "Halmeu", "station_id": "10112"},
        {"name": "Ianca", "station_id": "10113"},
        {"name": "Jimbolia", "station_id": "10114"},
        {"name": "Nădlac", "station_id": "10115"},
        {"name": "Petea", "station_id": "10116"},
        {"name": "Rădăuți", "station_id": "10117"},
        {"name": "Stamora Moravița", "station_id": "10118"},
        {"name": "Vicșani", "station_id": "10119"},
        
        # Smaller towns and villages with railway connections
        {"name": "Abrud", "station_id": "10120"},
        {"name": "Adjud", "station_id": "10122"},
        {"name": "Agnita", "station_id": "10123"},
        {"name": "Aiud", "station_id": "10124"},
        {"name": "Aleșd", "station_id": "10125"},
        {"name": "Apoldu de Sus", "station_id": "10126"},
        {"name": "Armășești", "station_id": "10127"},
        {"name": "Avrig", "station_id": "10128"},
        {"name": "Bălan", "station_id": "10129"},
        {"name": "Băneasa", "station_id": "10130"},
        {"name": "Baru Mare", "station_id": "10131"},
        {"name": "Beclean", "station_id": "10132"},
        {"name": "Beius", "station_id": "10133"},
        {"name": "Bethlen", "station_id": "10134"},
        {"name": "Câmpia Turzii", "station_id": "10135"},
        {"name": "Capu Midia", "station_id": "10136"},
        {"name": "Ciceu", "station_id": "10137"},
        {"name": "Ciurea", "station_id": "10138"},
        {"name": "Copșa Mică", "station_id": "10139"},
        {"name": "Coșlariu", "station_id": "10140"},
        {"name": "Criscior", "station_id": "10141"},
        {"name": "Dărmănești", "station_id": "10142"},
        {"name": "Gheorgheni", "station_id": "10143"},
        {"name": "Gherla", "station_id": "10144"},
        {"name": "Ghimbav", "station_id": "10145"},
        {"name": "Gura Humorului", "station_id": "10146"},
        {"name": "Hațeg", "station_id": "10147"},
        {"name": "Ilia", "station_id": "10148"},
        {"name": "Intorsura Buzăului", "station_id": "10149"},
        {"name": "Jibou", "station_id": "10150"}
    ]

# Initialize with demo stations immediately to prevent blocking
stations = get_demo_stations()
for station in stations:
    config.global_station_list[station["name"]] = station["station_id"]
logger.info(f"Initially loaded {len(stations)} demo stations")

def background_load_stations():
    global stations
    try:
        logger.info("Background: Fetching real stations from external API...")
        real_stations = StationsGetter.get_stations()
        if real_stations and len(real_stations) > 20:
            stations = real_stations
            # Rebuild lookup table
            new_lookup = {}
            for s in stations:
                new_lookup[s["name"]] = s["station_id"]
            config.global_station_list = new_lookup
            logger.info(f"Background: Successfully updated with {len(stations)} real stations")
    except Exception as e:
        logger.error(f"Background station fetch failed: {e}")

# Start background fetch to avoid blocking the main thread/worker
threading.Thread(target=background_load_stations, daemon=True).start()


@app.route('/api')
def api_status():
    return jsonify({
        "status": "CFR Train Tracker API - Running",
        "version": "2.0",
        "mode": "Enhanced Demo Mode with Real CFR Integration",
        "stations_loaded": len(stations),
        "timestamp": datetime.now().isoformat(),
        "features": {
            "real_cfr_connectivity": True,
            "demo_fallback": True,
            "passenger_community": True,
            "mobile_responsive": True
        }
    })


@app.route('/api/cfr-status')
def cfr_connectivity_status():
    """Check real-time connectivity to CFR Călători website"""
    try:
        import requests
        
        # Test CFR Călători connectivity
        cfr_response = requests.get("https://bilete.cfrcalatori.ro", timeout=5)
        cfr_accessible = cfr_response.status_code == 200
        
        # Test a specific train page
        train_response = requests.get("https://bilete.cfrcalatori.ro/ro-RO/Tren/IR%201621", timeout=5)
        train_pages_accessible = train_response.status_code == 200
        
        # Test stations page
        stations_response = requests.get("https://bilete.cfrcalatori.ro/ro-RO/Stations", timeout=5)
        stations_accessible = stations_response.status_code == 200
        
        return jsonify({
            "cfr_main_site": cfr_accessible,
            "train_pages": train_pages_accessible,
            "stations_page": stations_accessible,
            "overall_status": cfr_accessible and train_pages_accessible,
            "timestamp": datetime.now().isoformat(),
            "note": "When CFR is accessible, app uses enhanced demo data with real connectivity checks"
        })
    
    except Exception as e:
        return jsonify({
            "cfr_main_site": False,
            "train_pages": False,
            "stations_page": False,
            "overall_status": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


@app.route('/api/data-sources')
def data_sources_info():
    """Information about data sources and integration status"""
    return jsonify({
        "stations": {
            "source": "Comprehensive Romanian Railway Network Database",
            "count": len(stations),
            "coverage": "143 stations covering all major cities, regional centers, mountain destinations, and border crossings",
            "real_time_checks": True
        },
        "trains": {
            "source": "Enhanced demo data with real CFR connectivity verification",
            "features": ["Route simulation", "Delay simulation", "Platform information", "Real-time status checks"],
            "cfr_integration": "Attempts real data, falls back to enhanced demo"
        },
        "passenger_reports": {
            "source": "User-generated community data",
            "features": ["Delay reports", "Crowding levels", "Platform changes", "Seat availability"],
            "storage": "Local SQLite database"
        },
        "update_frequency": "Real-time for user reports, 30 seconds for CFR checks when enabled"
    })


@app.route('/api/train/<string:train_id>')
@app.route('/train/<string:train_id>')
def get_train_enhanced(train_id):
    """Enhanced train endpoint: retrieves real train info.

    The implementation now calls :func:`get_train` which prefers the CFR
    Călători ticketing site and falls back to Infofer.  Additional keys such
    as ``services`` and ``composition_html`` are preserved when available.
    """
    try:
        search_date = request.args.get('date')
        filter_stops = request.args.get('filter_stops', 'false').lower() == 'true'

        logger.info(f"Fetching real-time train data for {train_id}")
        train_data = get_train(train_id)
        if train_data and 'stations_data' in train_data:
            source = train_data.get('data_source', 'unknown')
            logger.info(f"✅ Got data from {source} for train {train_id}")
            stations_list = train_data['stations_data']
            branches = train_data.get('branches', [{'label': 'Rută', 'stations_data': stations_list}])

            response = {
                "train_number": train_id,
                "stations": stations_list,
                "stops": stations_list,
                "branches": branches,
                "operator": train_data.get('operator', 'CFR Călători'),
                "category": train_data.get('category', ''),
                "alerts": train_data.get('alerts', []),
                "data_source": {
                    "type": source,
                    "timestamp": datetime.now().isoformat()
                }
            }

            # include CFR-specific extras if present
            if 'services' in train_data:
                response['services'] = train_data['services']
            if 'composition_html' in train_data:
                response['composition_html'] = train_data['composition_html']
            if 'coach_order' in train_data:
                response['coach_order'] = train_data['coach_order']
            if 'coach_classes' in train_data:
                response['coach_classes'] = train_data['coach_classes']
            if 'station_options' in train_data:
                response['station_options'] = train_data['station_options']
            if 'all_coaches' in train_data:
                response['all_coaches'] = train_data['all_coaches']

            return jsonify(response)
        else:
            return jsonify({
                "error": f"Train {train_id} not found",
                "message": "Train not found on official Infofer live boards",
                "data_source": "infofer_live"
            }), 404
            
    except Exception as e:
        logger.error(f"Error fetching train data for {train_id}: {e}")
        return jsonify({
            "error": f"Unable to process request for train {train_id}",
            "details": str(e)
        }), 500


def get_data_validity_info():
    """Return basic information about when data was last refreshed."""
    return {
        "timestamp": datetime.now().isoformat(),
        "valid_until": (datetime.now() + timedelta(minutes=1)).isoformat(),
        "source": "infofer_live",
        "note": "Data is fetched live from Infofer on every request (TTL cache: 45s)"
    }


@app.route('/api/data-validity')
def get_data_validity():
    """Get information about data validity period"""
    try:
        validity_info = get_data_validity_info()
        return jsonify(validity_info)
    except Exception as e:
        return jsonify({
            "error": "Failed to get data validity information",
            "details": str(e)
        }), 500





@app.route('/api/search/trains')
def search_trains_with_date():
    """Search for trains by number.

    - If the query already contains a known prefix (e.g. "IC 534" or "IC534"),
      return only that one canonical suggestion.
    - If the query is a bare number (e.g. "534"), actually fetch the train from
      CFR/Infofer to discover its real category, then return that single real result.
      If the train is not found the result list is empty — no phantom suggestions.
    """
    try:
        query = request.args.get('q', '').upper().strip()
        if not query:
            return jsonify({"results": []})

        # Known Romanian rail categories, longest first to avoid partial matches
        KNOWN_PREFIXES = ["IRN", "R-E", "IC", "IR", "RE", "EN", "EC", "R", "P", "D", "A"]

        detected_prefix = None
        numeric_part = None

        # 1. "PREFIX NUMBER" with space  (e.g. "IC 534")
        if ' ' in query:
            parts = query.split(' ', 1)
            if parts[0] in KNOWN_PREFIXES and parts[1].isdigit():
                detected_prefix = parts[0]
                numeric_part = parts[1]

        # 2. "PREFIXNUMBER" without space  (e.g. "IC534")
        if detected_prefix is None:
            m = re.match(r'^([A-Z][A-Z-]*)(\d+)$', query)
            if m and m.group(1) in KNOWN_PREFIXES:
                detected_prefix = m.group(1)
                numeric_part = m.group(2)

        # 3. Pure number  (e.g. "534")
        if detected_prefix is None and query.isdigit():
            numeric_part = query

        # 4. Last-resort: strip non-digits
        if numeric_part is None:
            stripped = re.sub(r'\D', '', query)
            if stripped:
                numeric_part = stripped

        if not numeric_part:
            return jsonify({"query": query, "results": [], "count": 0,
                            "data_source": "normalized_search"})

        if detected_prefix:
            # User already specified a prefix — return the one canonical form
            canonical = f"{detected_prefix} {numeric_part}"
            results = [{
                "train_number": canonical,
                "route": f"Tren {canonical}",
                "operator": "CFR Călători",
                "id": canonical.replace(' ', '')
            }]
            data_source = "prefix_match"
        else:
            # Bare number — look up the real train to find its actual category
            results = []
            data_source = "live_lookup"
            try:
                train_data = get_train(numeric_part)
                if train_data and train_data.get('stations_data'):
                    # get_train returns 'category' (e.g. "IC", "IR", "R", …)
                    category = (train_data.get('category') or '').strip().upper()
                    if not category:
                        # Try to infer from the page title / header text if category missing
                        category = "R"  # conservative fallback
                    canonical = f"{category} {numeric_part}"
                    operator = train_data.get('operator', 'CFR Călători')
                    # Build a short route hint from first + last stop
                    stops = train_data['stations_data']
                    if len(stops) >= 2:
                        route_hint = f"{stops[0]['station_name']} → {stops[-1]['station_name']}"
                    else:
                        route_hint = f"Tren {canonical}"
                    results = [{
                        "train_number": canonical,
                        "route": route_hint,
                        "operator": operator,
                        "id": canonical.replace(' ', '')
                    }]
            except Exception as lookup_err:
                logger.info(f"Live lookup for '{numeric_part}' failed: {lookup_err}")
                # Return empty — don't show fake suggestions

        return jsonify({
            "query": query,
            "results": results,
            "count": len(results),
            "data_source": data_source
        })

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return jsonify({"error": "Search failed", "details": str(e)}), 500


def generate_realistic_composition(train_id):
    """Generate realistic train composition based on train type"""
    import random
    
    train_type = train_id.upper().split()[0] if ' ' in train_id else train_id.upper()[:2]
    
    compositions = {
        'IR': {  # InterRegio
            'locomotive': {
                'class': 'EA 060',
                'number': f'060-{random.randint(100, 200)}',
                'description': 'Electric locomotive',
                'power': '5100 kW (6840 hp)',
                'vagonweb_ref': 'CFR Class 060-EA'
            },
            'cars': [
                {'position': 1, 'type': 'Apmz', 'class': '1st', 'number': f'61-{random.randint(50, 99)}-123-4', 'description': '1st class air conditioned', 'capacity': '48 seats'},
                {'position': 2, 'type': 'Bmz', 'class': '2nd', 'number': f'61-{random.randint(50, 99)}-234-5', 'description': '2nd class air conditioned', 'capacity': '64 seats'},
                {'position': 3, 'type': 'Bmz', 'class': '2nd', 'number': f'61-{random.randint(50, 99)}-345-6', 'description': '2nd class air conditioned', 'capacity': '64 seats'},
                {'position': 4, 'type': 'ARmz', 'class': 'Restaurant', 'number': f'61-{random.randint(50, 99)}-456-7', 'description': 'Restaurant car', 'capacity': '24 seats + kitchen'}
            ]
        },
        'IC': {  # InterCity
            'locomotive': {
                'class': 'LE 5100',
                'number': f'5100-{random.randint(1, 50)}',
                'description': 'Electric locomotive (Siemens Eurosprinter)',
                'power': '5600 kW (7510 hp)',
                'vagonweb_ref': 'CFR Class LE 5100'
            },
            'cars': [
                {'position': 1, 'type': 'Apmz', 'class': '1st', 'number': f'61-{random.randint(50, 99)}-111-1', 'description': '1st class premium', 'capacity': '42 seats'},
                {'position': 2, 'type': 'Bmz', 'class': '2nd', 'number': f'61-{random.randint(50, 99)}-222-2', 'description': '2nd class comfort', 'capacity': '60 seats'},
                {'position': 3, 'type': 'ARmz', 'class': 'Bistro', 'number': f'61-{random.randint(50, 99)}-333-3', 'description': 'Bistro car', 'capacity': '32 seats + bar'}
            ]
        }
    }
    
    return compositions.get(train_type, compositions['IR'])  # Default to IR composition


@app.route('/get-stations/')
def get_stations():
    """Get stations list with caching for faster response"""
    global stations
    
    if not stations:
        # Return demo stations when external API is down
        stations = get_demo_stations()
        logger.info("Loaded demo stations as fallback")
    
    # Add caching headers for better performance
    response = jsonify({
        "stations": stations,
        "fallback_mode": False,
        "message": f"Loaded {len(stations)} stations",
        "timestamp": datetime.now().isoformat()
    })
    
    # Cache for 5 minutes
    response.headers['Cache-Control'] = 'public, max-age=300'
    return response


@app.route('/api/stations')
def api_get_stations():
    """API endpoint for stations list - uses scraped data only"""
    try:
        # Return whatever we have (demo or real) without blocking
        return jsonify(stations or [])
    except Exception as e:
        logger.error(f"Error getting stations: {e}")
        return jsonify({
            "error": "Station data unavailable",
            "message": str(e)
        }), 503


@app.route('/reload-stations/')
def reload_stations():
    global stations
    try:
        stations = StationsGetter.get_stations()
        config.global_station_list.clear()
        for station in stations:
            config.global_station_list[station["name"]] = station["station_id"]
        logger.info(f"Successfully reloaded {len(stations)} stations from external API")
        return jsonify({
            "success": True,
            "message": f"Successfully loaded {len(stations)} stations from external API",
            "stations_count": len(stations),
            "fallback_mode": False
        })
    except Exception as e:
        logger.error(f"Failed to reload stations from external API: {e}")
        # Fallback to demo stations
        logger.info("Loading demo stations as fallback")
        stations = get_demo_stations()
        config.global_station_list.clear()
        for station in stations:
            config.global_station_list[station["name"]] = station["station_id"]
        return jsonify({
            "success": True,
            "message": f"External API unavailable, loaded {len(stations)} demo stations",
            "stations_count": len(stations),
            "fallback_mode": True
        })

@app.route('/station/<station_id>')
def get_timetable(station_id):
    """Get station timetable ONLY from live Infofer scraper"""
    try:
        # 1. Resolve Name: Map numeric or slug ID to the real station name
        station_name = next((s.get("name") for s in stations if str(s.get("station_id")) == str(station_id)), None)
        
        if not station_name:
            # Check if station_id itself is a known name in config
            if str(station_id) in config.global_station_list:
                station_name = str(station_id)
            else:
                # If not in our list, try using the ID as a slug directly
                station_name = str(station_id).replace('-', ' ').title()
                logger.info(f"Station ID {station_id} not in global list, trying as name: {station_name}")

        # 2. Fetch from Scraper
        logger.info(f"Fetching timetable for {station_name} (ID: {station_id}) from Infofer live")
        timetable = StationTimetableGetter.get_timetable(station_id, station_name)
        
        if not timetable:
            return jsonify({
                "error": "No train data found",
                "message": f"No active trains found for {station_name} on Infofer live boards",
                "station_id": station_id
            }), 404

        for item in timetable:
            item['is_live'] = True
            
        return jsonify(timetable)
            
    except Exception as e:
        logger.error(f"Failed to get timetable for station {station_id}: {e}")
        return jsonify({
            "error": "Timetable data unavailable",
            "message": str(e)
        }), 500


def timetable_departures_filter(timetable):
    departures_timetable = []

    for item in timetable:
        if item['is_origin'] or item['is_stop']:
            departures_timetable.append(item)

    return departures_timetable


def timetable_arrivals_filter(timetable):
    departures_timetable = []

    for item in timetable:
        if item['is_destination'] or item['is_stop']:
            departures_timetable.append(item)

    return departures_timetable


def timestamp_current_filter(timetable):
    """Filter timetable for trains within -1h to +3h window, handling naive/aware datetimes."""
    current_timetable = []
    timezone = tz.gettz('Europe/Bucharest')
    now_aware = datetime.now(tz=timezone)
    now_naive = datetime.now()
    
    beginning_aware = now_aware - timedelta(hours=1)
    end_aware = now_aware + timedelta(hours=3)
    beginning_naive = now_naive - timedelta(hours=1)
    end_naive = now_naive + timedelta(hours=3)

    for item in timetable:
        # Check both arrival and departure
        found = False
        for key in ['arrival_timestamp', 'departure_timestamp']:
            if item.get(key):
                try:
                    ts = parser.isoparse(item[key])
                    
                    # Determine which bounds to use based on offset awareness
                    if ts.tzinfo is not None and ts.tzinfo.utcoffset(ts) is not None:
                        low, high = beginning_aware, end_aware
                    else:
                        low, high = beginning_naive, end_naive
                        
                    if low <= ts <= high:
                        found = True
                        break
                    
                    # Also check with delay
                    delay = item.get('delay', 0)
                    if delay:
                        ts_delayed = ts + timedelta(minutes=delay)
                        if low <= ts_delayed <= high:
                            found = True
                            break
                except Exception as e:
                    logger.error(f"Error parsing timestamp {item[key]}: {e}")
                    continue
        
        if found:
            current_timetable.append(item)

    return current_timetable

@app.route('/station/<int:station_id>/departures')
def get_departures_timetable(station_id):
    try:
        # Resolve station name for Infofer scraper
        station_name = next((s.get("name") for s in stations if str(s.get("station_id")) == str(station_id)), None)
        timetable = StationTimetableGetter.get_timetable(station_id, station_name=station_name)
        timetable = timetable_departures_filter(timetable)
        return jsonify(timetable)
    except Exception as e:
        logger.error(f"Failed to get departures timetable for station {station_id}: {e}")
        return jsonify({
            "error": "Departures timetable unavailable",
            "message": f"Could not fetch departures for station {station_id}",
            "details": str(e)
        }), 503


@app.route('/station/<int:station_id>/departures/current')
def get_current_departures_timetable(station_id):
    """Get current departures (within -1/+3 hour window) from real scraper"""
    try:
        # Resolve station name for Infofer scraper
        station_name = next((s.get("name") for s in stations if str(s.get("station_id")) == str(station_id)), None)
        logger.info(f"Fetching real-time current departures for {station_name or station_id}")
        
        timetable = StationTimetableGetter.get_timetable(station_id, station_name=station_name)
        if not timetable:
            return jsonify([])
            
        # Filter for departures and time window
        timetable = timetable_departures_filter(timetable)
        timetable = timestamp_current_filter(timetable)
        
        return jsonify(timetable)
    except Exception as e:
        logger.error(f"Failed to get current departures for station {station_id}: {e}")
        # Only fallback if absolutely necessary, but preferably return empty list or error
        return jsonify({
            "error": "Real-time data unavailable",
            "message": str(e)
        }), 503


@app.route('/station/<string:station_name>/departures/current')
def get_current_departures_by_name(station_name):
    """Get current departures by station name (converted from URL-friendly format)"""
    try:
        # Convert URL-friendly station name back to proper format
        proper_name = station_name.replace('-', ' ').title()
        
        # Handle specific cases
        name_mappings = {
            'Bucuresti Nord': 'București Nord',
            'Timisoara Nord': 'Timișoara Nord',
            'Cluj Napoca': 'Cluj-Napoca',
            'Targu Mures': 'Târgu Mureș',
            'Baia Mare': 'Baia Mare',
            'Satu Mare': 'Satu Mare'
        }
        
        if proper_name in name_mappings:
            proper_name = name_mappings[proper_name]
            
        # Find station ID from name
        station_id = None
        for station in stations:
            if str(station.get("name", "")).lower() == proper_name.lower():
                raw_id = station.get("station_id", "")
                try:
                    station_id = int(raw_id)
                except (ValueError, TypeError):
                    station_id = raw_id  # keep slug as-is
                break

        if station_id is None:
            # Try to find partial match
            for station in stations:
                if proper_name.lower() in str(station.get("name", "")).lower():
                    raw_id = station.get("station_id", "")
                    try:
                        station_id = int(raw_id)
                    except (ValueError, TypeError):
                        station_id = raw_id
                    break

        if station_id is None:
            logger.warning(f"Station not found: {proper_name}, returning empty list")
            return jsonify([]), 404
            
        logger.info(f"Found station '{proper_name}' with ID {station_id}")
        
        # Use the real-time endpoint instead of demo data
        return get_current_departures_timetable(station_id)
        
    except Exception as e:
        logger.error(f"Failed to get departures for station name {station_name}: {e}")
        return jsonify({"error": "Real-time data unavailable", "message": str(e)}), 503


@app.route('/station/<int:station_id>/arrivals')
def get_arrivals_timetable(station_id):
    try:
        # Resolve station name for Infofer scraper
        station_name = next((s.get("name") for s in stations if str(s.get("station_id")) == str(station_id)), None)
        timetable = StationTimetableGetter.get_timetable(station_id, station_name=station_name)
        timetable = timetable_arrivals_filter(timetable)
        return jsonify(timetable)
    except Exception as e:
        logger.error(f"Failed to get arrivals timetable for station {station_id}: {e}")
        return jsonify({
            "error": "Arrivals timetable unavailable",
            "message": f"Could not fetch arrivals for station {station_id}",
            "details": str(e)
        }), 503


@app.route('/station/<int:station_id>/arrivals/current')
def get_current_arrivals_timetable(station_id):
    """Get current arrivals (within -1/+3 hour window) from real scraper"""
    try:
        # Resolve station name for Infofer scraper
        station_name = next((s.get("name") for s in stations if str(s.get("station_id")) == str(station_id)), None)
        logger.info(f"Fetching real-time current arrivals for {station_name or station_id}")
        
        timetable = StationTimetableGetter.get_timetable(station_id, station_name=station_name)
        if not timetable:
            return jsonify([])
            
        # Filter for arrivals and time window
        timetable = timetable_arrivals_filter(timetable)
        timetable = timestamp_current_filter(timetable)
        
        return jsonify(timetable)
    except Exception as e:
        logger.error(f"Failed to get current arrivals for station {station_id}: {e}")
        return jsonify({
            "error": "Real-time data unavailable",
            "message": str(e)
        }), 503


@app.route('/station/<string:station_name>/arrivals/current')
def get_current_arrivals_by_name(station_name):
    """Get current arrivals by station name (converted from URL-friendly format)"""
    try:
        # Convert URL-friendly station name back to proper format
        proper_name = station_name.replace('-', ' ').title()
        
        # Handle specific cases
        name_mappings = {
            'Bucuresti Nord': 'București Nord',
            'Timisoara Nord': 'Timișoara Nord',
            'Cluj Napoca': 'Cluj-Napoca',
            'Targu Mures': 'Târgu Mureș',
            'Baia Mare': 'Baia Mare',
            'Satu Mare': 'Satu Mare'
        }
        
        if proper_name in name_mappings:
            proper_name = name_mappings[proper_name]
            
        # Find station ID from name
        station_id = None
        for station in stations:
            if str(station.get("name", "")).lower() == proper_name.lower():
                raw_id = station.get("station_id", "")
                try:
                    station_id = int(raw_id)
                except (ValueError, TypeError):
                    station_id = raw_id
                break

        if station_id is None:
            # Try to find partial match
            for station in stations:
                if proper_name.lower() in str(station.get("name", "")).lower():
                    raw_id = station.get("station_id", "")
                    try:
                        station_id = int(raw_id)
                    except (ValueError, TypeError):
                        station_id = raw_id
                    break

        if station_id is None:
            logger.warning(f"Station not found: {proper_name}, returning empty list")
            return jsonify([]), 404
            
        logger.info(f"Found station '{proper_name}' with ID {station_id}")
        
        # Use the real-time endpoint instead of demo data
        return get_current_arrivals_timetable(station_id)
        
    except Exception as e:
        logger.error(f"Failed to get arrivals for station name {station_name}: {e}")
        return jsonify({"error": "Real-time data unavailable", "message": str(e)}), 503


# Demo data generator (used internally for fallbacks)
def generate_demo_station_departures(station_id):
    """Generate demo departures data for fallback"""
    import random
    
    station_names = {
        # Major cities and hubs
        1: "București Nord", 2: "Ploiești Sud", 3: "Brașov", 4: "Cluj-Napoca",
        5: "Timișoara Nord", 6: "Constanța", 7: "Iași", 8: "Craiova", 9: "Galați", 10: "Oradea",
        10001: "București Nord", 10002: "Cluj-Napoca", 10003: "Constanța", 10004: "Brașov", 
        10005: "Timișoara Nord", 10006: "Iași", 10007: "Craiova", 10008: "Galați", 
        10009: "Ploiești Sud", 10010: "Oradea", 10011: "Arad", 10012: "Deva",
        10013: "Târgu Mureș", 10014: "Sibiu", 10015: "Bacău", 10016: "Pitești",
        10017: "Suceava", 10018: "Satu Mare", 10019: "Baia Mare", 10020: "Reșița",
        
        # Additional regional stations
        10021: "Alba Iulia", 10022: "Alexandria", 10023: "Bârlad", 10024: "Bistrița",
        10025: "Botoșani", 10026: "Brăila", 10027: "Buzău", 10028: "Calafat",
        10029: "Caracal", 10030: "Caransebeș", 10031: "Cernavodă", 10032: "Dej",
        10033: "Dorohoi", 10034: "Drăgășani", 10035: "Făgăraș", 10036: "Fetești",
        10037: "Filiași", 10038: "Focșani", 10039: "Giurgiu Nord", 10040: "Hunedoara",
        10041: "Lugoj", 10042: "Mangalia", 10043: "Medgidia", 10044: "Miercurea Ciuc",
        10045: "Moreni", 10046: "Motru", 10047: "Oltenița", 10048: "Onești",
        10049: "Orșova", 10050: "Pascani", 10051: "Petroșani", 10052: "Piatra Neamț",
        10053: "Râmnicu Vâlcea", 10054: "Roman", 10055: "Roșiori Nord", 10056: "Sălaj",
        10057: "Sfântu Gheorghe", 10058: "Sighetu Marmației", 10059: "Sighișoara",
        10060: "Simeria", 10061: "Slobozia", 10062: "Târgoviște", 10063: "Târgu Jiu",
        10064: "Tecuci", 10065: "Tulcea", 10066: "Turda", 10067: "Turnu Severin",
        10068: "Vaslui", 10069: "Vatra Dornei", 10070: "Zalău",
        
        # Mountain and tourism destinations
        10071: "Sinaia", 10072: "Predeal", 10073: "Azuga", 10074: "Busteni",
        10075: "Câmpina", 10076: "Băile Herculane", 10077: "Băile Olănești",
        10078: "Băile Govora", 10079: "Sovata", 10080: "Borșa", 10081: "Vișeu de Sus",
        
        # Additional stations
        10082: "Băicoi", 10083: "Băilești", 10084: "Bălți", 10085: "Bicaz",
        10086: "Blaj", 10087: "Bocșa", 10088: "Boldești Scăeni", 10089: "Borcea",
        10090: "Brad", 10091: "Breaza", 10092: "Budești", 10093: "Carei",
        10094: "Călan", 10095: "Călărași", 10096: "Cărei", 10097: "Codlea",
        10098: "Comănești", 10099: "Corabia", 10100: "Costești",
        
        # Bucharest area
        10101: "București Basarab", 10102: "București Obor", 10109: "Ploiești Vest",
        
        # Extended network (borders and regional)
        10110: "Curtici", 10111: "Episcopia Bihor", 10112: "Halmeu", 10113: "Ianca",
        10114: "Jimbolia", 10115: "Nădlac", 10116: "Petea", 10117: "Rădăuți",
        10118: "Stamora Moravița", 10119: "Vicșani", 10120: "Abrud", 10121: "Alba Iulia Parc",
        10122: "Adjud", 10123: "Agnita", 10124: "Aiud", 10125: "Aleșd", 10126: "Apoldu de Sus",
        10127: "Armășești", 10128: "Avrig", 10129: "Bălan", 10130: "Băneasa",
        10131: "Baru Mare", 10132: "Beclean", 10133: "Beius", 10134: "Bethlen",
        10135: "Câmpia Turzii", 10136: "Capu Midia", 10137: "Ciceu", 10138: "Ciurea",
        10139: "Copșa Mică", 10140: "Coșlariu", 10141: "Criscior", 10142: "Dărmănești",
        10143: "Gheorgheni", 10144: "Gherla", 10145: "Ghimbav", 10146: "Gura Humorului",
        10147: "Hațeg", 10148: "Ilia", 10149: "Intorsura Buzăului", 10150: "Jibou"
    }
    
    # Get station name for this ID
    current_station = station_names.get(station_id, "Unknown Station")
    
    now = datetime.now()
    demo_departures = []
    
    # Different train routes based on station
    if "București" in current_station:
        trains = [
            {"number": "IR 1621", "name": "Transilvania", "destination": "Cluj-Napoca"},
            {"number": "R 2345", "name": "Carpați", "destination": "Brașov"},
            {"number": "IC 581", "name": "Olt", "destination": "Craiova"},
            {"number": "IR 1743", "name": "Mureș", "destination": "Timișoara Nord"},
            {"number": "R 8275", "name": "Litoral", "destination": "Constanța"},
            {"number": "IR 1851", "name": "Moldova", "destination": "Iași"}
        ]
    elif "Cluj" in current_station:
        trains = [
            {"number": "IR 1622", "name": "Transilvania", "destination": "București Nord"},
            {"number": "R 4321", "name": "Apuseni", "destination": "Oradea"},
            {"number": "IR 1744", "name": "Mureș", "destination": "București Nord"},
            {"number": "R 3456", "name": "Someș", "destination": "Baia Mare"}
        ]
    elif "Timișoara" in current_station:
        trains = [
            {"number": "IR 1744", "name": "Mureș", "destination": "București Nord"},
            {"number": "R 1987", "name": "Banat", "destination": "Arad"},
            {"number": "IC 582", "name": "Olt", "destination": "Cluj-Napoca"},
            {"number": "R 6543", "name": "Bega", "destination": "Reșița"}
        ]
    else:
        # Default trains for other stations
        trains = [
            {"number": "IR 1621", "name": "Transilvania", "destination": "Cluj-Napoca"},
            {"number": "R 2345", "name": "Carpați", "destination": "Brașov"},
            {"number": "IC 581", "name": "Olt", "destination": "Craiova"},
            {"number": "R 8275", "name": "Regional", "destination": "București Nord"}
        ]
    
    # Generate 4-6 departures for more realistic feel
    num_trains = random.randint(4, 6)
    selected_trains = random.sample(trains, min(num_trains, len(trains)))
    
    for i, train in enumerate(selected_trains):
        # Create more realistic departure times - some very soon, some later
        # Weight towards sooner departures for a more realistic timetable
        if i == 0:
            # First train leaves very soon (5-15 minutes)
            departure_minutes = random.randint(5, 15)
        elif i == 1:
            # Second train leaves soon (10-30 minutes)
            departure_minutes = random.randint(10, 30)
        else:
            # Other trains spread over next 2-3 hours
            departure_minutes = random.randint(30, 180)
            
        departure_time = now + timedelta(minutes=departure_minutes)
        delay = random.choices([0, 5, 10, 15, 25, 35], weights=[60, 20, 10, 5, 3, 2])[0]  # Most trains on time
        
        demo_departures.append({
            "train_id": f"train_{station_id}_{i}",
            "train_number": train["number"],
            "train_name": train["name"],
            "station_name": current_station,
            "origin": current_station,
            "destination": train["destination"],
            "departure_timestamp": departure_time.isoformat(),
            "arrival_timestamp": None,
            "delay": delay,
            "platform": random.choice(["1", "2", "3", "4", "5", "6", "TBD"]),
            "is_origin": True,
            "is_stop": False,
            "is_destination": False,
            "distance": random.randint(150, 600),
            "travel_time": random.randint(120, 480)
        })
    
    # Sort departures by departure time (closest first)
    demo_departures.sort(key=lambda x: x["departure_timestamp"])
    
    return demo_departures

def generate_demo_station_arrivals(station_id):
    """Generate demo arrivals data for fallback"""
    import random
    
    station_names = {
        # Major cities and hubs
        1: "București Nord", 2: "Ploiești Sud", 3: "Brașov", 4: "Cluj-Napoca",
        5: "Timișoara Nord", 6: "Constanța", 7: "Iași", 8: "Craiova", 9: "Galați", 10: "Oradea",
        10001: "București Nord", 10002: "Cluj-Napoca", 10003: "Constanța", 10004: "Brașov", 
        10005: "Timișoara Nord", 10006: "Iași", 10007: "Craiova", 10008: "Galați", 
        10009: "Ploiești Sud", 10010: "Oradea", 10011: "Arad", 10012: "Deva",
        10013: "Târgu Mureș", 10014: "Sibiu", 10015: "Bacău", 10016: "Pitești",
        10017: "Suceava", 10018: "Satu Mare", 10019: "Baia Mare", 10020: "Reșița",
        
        # Additional regional stations
        10021: "Alba Iulia", 10022: "Alexandria", 10023: "Bârlad", 10024: "Bistrița",
        10025: "Botoșani", 10026: "Brăila", 10027: "Buzău", 10028: "Calafat",
        10029: "Caracal", 10030: "Caransebeș", 10031: "Cernavodă", 10032: "Dej",
        10033: "Dorohoi", 10034: "Drăgășani", 10035: "Făgăraș", 10036: "Fetești",
        10037: "Filiași", 10038: "Focșani", 10039: "Giurgiu Nord", 10040: "Hunedoara",
        10041: "Lugoj", 10042: "Mangalia", 10043: "Medgidia", 10044: "Miercurea Ciuc",
        10045: "Moreni", 10046: "Motru", 10047: "Oltenița", 10048: "Onești",
        10049: "Orșova", 10050: "Pascani", 10051: "Petroșani", 10052: "Piatra Neamț",
        10053: "Râmnicu Vâlcea", 10054: "Roman", 10055: "Roșiori Nord", 10056: "Sălaj",
        10057: "Sfântu Gheorghe", 10058: "Sighetu Marmației", 10059: "Sighișoara",
        10060: "Simeria", 10061: "Slobozia", 10062: "Târgoviște", 10063: "Târgu Jiu",
        10064: "Tecuci", 10065: "Tulcea", 10066: "Turda", 10067: "Turnu Severin",
        10068: "Vaslui", 10069: "Vatra Dornei", 10070: "Zalău",
        
        # Mountain and tourism destinations
        10071: "Sinaia", 10072: "Predeal", 10073: "Azuga", 10074: "Busteni",
        10075: "Câmpina", 10076: "Băile Herculane", 10077: "Băile Olănești",
        10078: "Băile Govora", 10079: "Sovata", 10080: "Borșa", 10081: "Vișeu de Sus",
        
        # Additional stations
        10082: "Băicoi", 10083: "Băilești", 10084: "Bălți", 10085: "Bicaz",
        10086: "Blaj", 10087: "Bocșa", 10088: "Boldești Scăeni", 10089: "Borcea",
        10090: "Brad", 10091: "Breaza", 10092: "Budești", 10093: "Carei",
        10094: "Călan", 10095: "Călărași", 10096: "Cărei", 10097: "Codlea",
        10098: "Comănești", 10099: "Corabia", 10100: "Costești",
        
        # Bucharest area
        10101: "București Basarab", 10102: "București Obor", 10109: "Ploiești Vest",
        
        # Extended network (borders and regional)
        10110: "Curtici", 10111: "Episcopia Bihor", 10112: "Halmeu", 10113: "Ianca",
        10114: "Jimbolia", 10115: "Nădlac", 10116: "Petea", 10117: "Rădăuți",
        10118: "Stamora Moravița", 10119: "Vicșani", 10120: "Abrud", 10121: "Alba Iulia Parc",
        10122: "Adjud", 10123: "Agnita", 10124: "Aiud", 10125: "Aleșd", 10126: "Apoldu de Sus",
        10127: "Armășești", 10128: "Avrig", 10129: "Bălan", 10130: "Băneasa",
        10131: "Baru Mare", 10132: "Beclean", 10133: "Beius", 10134: "Bethlen",
        10135: "Câmpia Turzii", 10136: "Capu Midia", 10137: "Ciceu", 10138: "Ciurea",
        10139: "Copșa Mică", 10140: "Coșlariu", 10141: "Criscior", 10142: "Dărmănești",
        10143: "Gheorgheni", 10144: "Gherla", 10145: "Ghimbav", 10146: "Gura Humorului",
        10147: "Hațeg", 10148: "Ilia", 10149: "Intorsura Buzăului", 10150: "Jibou"
    }
    
    # Get station name for this ID
    current_station = station_names.get(station_id, "Unknown Station")
    
    now = datetime.now()
    demo_arrivals = []
    
    # Different train origins based on station
    if "București" in current_station:
        trains = [
            {"number": "IR 1622", "name": "Transilvania", "origin": "Cluj-Napoca"},
            {"number": "R 2346", "name": "Carpați", "origin": "Brașov"},
            {"number": "IC 582", "name": "Olt", "origin": "Craiova"},
            {"number": "IR 1744", "name": "Mureș", "origin": "Timișoara Nord"},
            {"number": "R 8276", "name": "Litoral", "origin": "Constanța"},
            {"number": "IR 1852", "name": "Moldova", "origin": "Iași"}
        ]
    elif "Cluj" in current_station:
        trains = [
            {"number": "IR 1621", "name": "Transilvania", "origin": "București Nord"},
            {"number": "R 4322", "name": "Apuseni", "origin": "Oradea"},
            {"number": "IR 1743", "name": "Mureș", "origin": "Timișoara Nord"},
            {"number": "R 3457", "name": "Someș", "origin": "Baia Mare"}
        ]
    elif "Timișoara" in current_station:
        trains = [
            {"number": "IR 1743", "name": "Mureș", "origin": "București Nord"},
            {"number": "R 1988", "name": "Banat", "origin": "Arad"},
            {"number": "IC 581", "name": "Olt", "origin": "Cluj-Napoca"},
            {"number": "R 6544", "name": "Bega", "origin": "Reșița"}
        ]
    else:
        # Default trains for other stations
        trains = [
            {"number": "IR 1622", "name": "Transilvania", "origin": "Cluj-Napoca"},
            {"number": "R 2346", "name": "Carpați", "origin": "Brașov"},
            {"number": "IC 582", "name": "Olt", "origin": "Craiova"},
            {"number": "R 8276", "name": "Regional", "origin": "București Nord"}
        ]
    
    # Generate 4-6 arrivals for more realistic feel
    num_trains = random.randint(4, 6)
    selected_trains = random.sample(trains, min(num_trains, len(trains)))
    
    for i, train in enumerate(selected_trains):
        # Create more realistic arrival times - some very soon, some later
        # Weight towards sooner arrivals for a more realistic timetable
        if i == 0:
            # First train arrives very soon (5-15 minutes)
            arrival_minutes = random.randint(5, 15)
        elif i == 1:
            # Second train arrives soon (10-30 minutes)
            arrival_minutes = random.randint(10, 30)
        else:
            # Other trains spread over next 2-3 hours
            arrival_minutes = random.randint(30, 180)
            
        arrival_time = now + timedelta(minutes=arrival_minutes)
        delay = random.choices([0, 5, 10, 15, 25, 35], weights=[60, 20, 10, 5, 3, 2])[0]  # Most trains on time
        
        demo_arrivals.append({
            "train_id": f"train_arr_{station_id}_{i}",
            "train_number": train["number"],
            "train_name": train["name"],
            "station_name": current_station,
            "origin": train["origin"],
            "destination": current_station,
            "departure_timestamp": None,
            "arrival_timestamp": arrival_time.isoformat(),
            "delay": delay,
            "platform": random.choice(["1", "2", "3", "4", "5", "6", "TBD"]),
            "is_origin": False,
            "is_stop": False,
            "is_destination": True,
            "distance": random.randint(150, 600),
            "travel_time": random.randint(120, 480)
        })
    
    # Sort arrivals by arrival time (closest first)
    demo_arrivals.sort(key=lambda x: x["arrival_timestamp"])
    
    return demo_arrivals

def generate_demo_train_details(train_id):
    """Generate demo train journey details for fallback"""
    import random
    
    # Sample route: București Nord -> Cluj-Napoca
    stations_route = [
        "București Nord", "Ploiești Sud", "Câmpina", "Sinaia", 
        "Brașov", "Sighișoara", "Mediaș", "Cluj-Napoca"
    ]
    
    now = datetime.now()
    journey = []
    
    for i, station in enumerate(stations_route):
        arrival_time = now + timedelta(minutes=i * 45) if i > 0 else None
        departure_time = now + timedelta(minutes=i * 45 + 5) if i < len(stations_route) - 1 else None
        delay = random.choice([0, 0, 0, 5, 10])
        
        journey.append({
            "station_name": station,
            "arrival_timestamp": arrival_time.isoformat() if arrival_time else None,
            "departure_timestamp": departure_time.isoformat() if departure_time else None,
            "delay": delay,
            "platform": str(random.randint(1, 6)),
            "is_origin": i == 0,
            "is_destination": i == len(stations_route) - 1,
            "is_stop": 0 < i < len(stations_route) - 1
        })
    
    return journey

def get_train_composition(train_id):
    """Get train composition (locomotive and cars) based on train type and number"""
    train_upper = train_id.upper().replace(" ", "")
    
    # CFR locomotive types and their characteristics
    locomotives = {
        "electric": [
            {"class": "EA", "number": "001-040", "power": "5100 kW", "max_speed": "160 km/h", "description": "Modern electric locomotive"},
            {"class": "060-EA", "number": "001-060", "power": "4800 kW", "max_speed": "140 km/h", "description": "Electric locomotive for passenger service"},
            {"class": "040-EA", "number": "001-040", "power": "4000 kW", "max_speed": "120 km/h", "description": "Electric locomotive"},
            {"class": "060-EC", "number": "001-025", "power": "4800 kW", "max_speed": "120 km/h", "description": "Electric locomotive for mixed service"}
        ],
        "diesel": [
            {"class": "60-1100", "number": "1100-1199", "power": "1470 kW", "max_speed": "120 km/h", "description": "Modern diesel locomotive"},
            {"class": "62-0800", "number": "0800-0899", "power": "1100 kW", "max_speed": "100 km/h", "description": "Diesel locomotive"},
            {"class": "81-0500", "number": "0500-0599", "power": "1470 kW", "max_speed": "120 km/h", "description": "Heavy diesel locomotive"}
        ]
    }
    
    # Car types used by CFR
    car_types = {
        "first_class": [
            {"type": "Aee", "number": "19-70.0 xxx", "seats": 56, "class": "1st", "description": "First class air-conditioned coach"},
            {"type": "Afee", "number": "19-70.1 xxx", "seats": 50, "class": "1st", "description": "First class coach with family compartments"},
            {"type": "Ammz", "number": "19-70.2 xxx", "seats": 48, "class": "1st", "description": "First class open coach"}
        ],
        "second_class": [
            {"type": "Bee", "number": "20-70.0 xxx", "seats": 80, "class": "2nd", "description": "Second class air-conditioned coach"},
            {"type": "Bfee", "number": "20-70.1 xxx", "seats": 72, "class": "2nd", "description": "Second class coach"},
            {"type": "Bmmz", "number": "20-70.2 xxx", "seats": 88, "class": "2nd", "description": "Second class open coach"},
            {"type": "Bhv", "number": "20-70.3 xxx", "seats": 64, "class": "2nd", "description": "Second class coach with bike storage"}
        ],
        "couchette": [
            {"type": "Bcmee", "number": "61-70.0 xxx", "berths": 48, "class": "2nd", "description": "Six-berth couchette coach"},
            {"type": "Bcmee", "number": "61-70.1 xxx", "berths": 44, "class": "2nd", "description": "Four-berth couchette coach"}
        ],
        "sleeper": [
            {"type": "WL", "number": "70-70.0 xxx", "berths": 20, "class": "1st/2nd", "description": "Sleeping car"},
            {"type": "WLmee", "number": "70-70.1 xxx", "berths": 18, "class": "1st", "description": "First class sleeping car"}
        ],
        "restaurant": [
            {"type": "WRmee", "number": "88-70.0 xxx", "seats": 48, "class": "Restaurant", "description": "Restaurant car"},
            {"type": "ARee", "number": "18-70.0 xxx", "seats": 24, "class": "Bistro", "description": "Bistro car with first class seating"}
        ]
    }
    
    # Determine locomotive type based on route (electrified vs non-electrified)
    electrified_routes = ["București", "Ploiești", "Brașov", "Cluj", "Constanța", "Timișoara"]
    route_electrified = any(route in train_id.upper() or route in str(random.choice(electrified_routes)) for route in electrified_routes)
    
    composition = {
        "train_number": train_id,
        "formation_date": datetime.now().strftime("%Y-%m-%d"),
        "total_length": 0,
        "total_weight": 0,
        "max_speed": 0,
        "locomotive": {},
        "cars": [],
        "services": []
    }
    
    # Select locomotive
    if route_electrified and not train_id.upper().startswith('R'):
        # Electric locomotive for main lines
        loco = random.choice(locomotives["electric"])
        loco_number = f"{loco['class']} {random.randint(1, 100):03d}"
    else:
        # Diesel locomotive for regional or non-electrified lines
        loco = random.choice(locomotives["diesel"])
        loco_number = f"{loco['class']} {random.randint(1, 100):03d}"
    
    composition["locomotive"] = {
        "number": loco_number,
        "class": loco["class"],
        "power": loco["power"],
        "max_speed": loco["max_speed"],
        "description": loco["description"],
        "length": "19.5 m",
        "weight": "84 t"
    }
    
    composition["max_speed"] = int(loco["max_speed"].split()[0])
    
    # Select cars based on train type
    if train_id.upper().startswith('IC'):
        # InterCity trains - premium service
        cars = [
            random.choice(car_types["first_class"]),
            random.choice(car_types["restaurant"]),
            random.choice(car_types["second_class"]),
            random.choice(car_types["second_class"]),
            random.choice(car_types["second_class"])
        ]
        composition["services"] = ["First Class", "Restaurant", "Air Conditioning", "Power Outlets"]
        
    elif train_id.upper().startswith('IR'):
        # InterRegio trains - long distance
        cars = [
            random.choice(car_types["first_class"]),
            random.choice(car_types["second_class"]),
            random.choice(car_types["second_class"]),
            random.choice(car_types["second_class"])
        ]
        composition["services"] = ["First Class", "Air Conditioning", "Bicycle Storage"]
        
        # Night trains get sleepers
        if 'N' in train_id.upper():
            cars.extend([
                random.choice(car_types["sleeper"]),
                random.choice(car_types["couchette"])
            ])
            composition["services"].extend(["Sleeping Cars", "Couchettes"])
            
    elif train_id.upper().startswith('R'):
        # Regional trains - basic service  
        cars = [
            random.choice(car_types["second_class"]),
            random.choice(car_types["second_class"])
        ]
        composition["services"] = ["Basic Service", "Bicycle Storage"]
    else:
        # Default composition
        cars = [
            random.choice(car_types["second_class"]),
            random.choice(car_types["second_class"])
        ]
        composition["services"] = ["Standard Service"]
    
    # Add car details with random car numbers
    total_length = 19.5  # locomotive length
    total_weight = 84  # locomotive weight
    
    for i, car in enumerate(cars):
        car_number = f"{car['number'].replace('xxx', f'{random.randint(1, 999):03d}')}"
        car_length = 26.4  # standard passenger car length
        car_weight = random.randint(38, 45)  # typical weight range
        
        car_detail = {
            "position": i + 1,  # position after locomotive
            "number": car_number,
            "type": car["type"],
            "class": car["class"],
            "description": car["description"],
            "length": f"{car_length} m",
            "weight": f"{car_weight} t"
        }
        
        # Add capacity info
        if "seats" in car:
            car_detail["capacity"] = f"{car['seats']} seats"
        elif "berths" in car:
            car_detail["capacity"] = f"{car['berths']} berths"
        else:
            car_detail["capacity"] = "Service car"
            
        composition["cars"].append(car_detail)
        total_length += car_length
        total_weight += car_weight
    
    composition["total_length"] = f"{total_length:.1f} m"
    composition["total_weight"] = f"{total_weight} t"
    composition["car_count"] = len(cars)
    
    return composition

@app.route('/api/train/<string:train_id>/composition')
def get_train_composition_api(train_id):
    """API endpoint to get train composition and facilities.

    When the CFR Călători scraper provides raw ``composition_html`` we
    return it directly; otherwise fall back to the built-in demo generator.
    """
    try:
        # attempt to fetch live train data; this will use CFR first
        live = None
        try:
            live = get_train(train_id)
        except Exception:
            live = None
        if live and live.get('composition_html'):
            resp = {
                'train_number': train_id,
                'composition_html': live['composition_html'],
                'services': live.get('services', []),
                'data_source': live.get('data_source')
            }
            if live.get('coach_order'):
                resp['coach_order'] = live['coach_order']
            if live.get('coach_classes'):
                resp['coach_classes'] = live['coach_classes']
            if live.get('station_options'):
                resp['station_options'] = live['station_options']
            return jsonify(resp)

        # fallback to synthetic demo
        composition = get_train_composition(train_id)
        return jsonify(composition)
    except Exception as e:
        logger.error(f"Failed to get composition for train {train_id}: {e}")
        return jsonify({
            "error": "Failed to get train composition",
            "details": str(e)
        }), 500


# Train suggestion endpoint for live search
@app.route('/api/train-suggestions/<string:query>')
def get_train_suggestions(query):
    """Simple train suggestions that allows direct train number lookup"""
    if len(query) < 2:
        return jsonify([])
    
    try:
        query_upper = query.upper().strip()
        suggestions = [{
            "train_number": query_upper,
            "type": "Tren",
            "description": f"Caută trenul {query_upper} pe Infofer",
            "score": 100
        }]
        
        return jsonify(suggestions)
        
    except Exception as e:
        logger.error(f"Failed to generate train suggestions for '{query}': {e}")
        return jsonify([])

# Enhanced station search
@app.route('/api/stations/search/<string:query>')
def search_stations(query):
    """Search stations by name"""
    if len(query) < 2:
        return jsonify([])
    
    try:
        import unicodedata
        def normalize_str(s):
            return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8').lower()
            
        matching_stations: list[dict] = []
        query_norm = normalize_str(query)
        
        # Point 'bucuresti nord' queries to 'bucuresti nord gr.a'
        if query_norm == "bucuresti nord":
            query_norm = "bucuresti nord gr.a"
        
        for station in stations:
            station_name_norm = normalize_str(str(station.get("name", "")))
            if query_norm in station_name_norm:
                # Calculate relevance score
                score = 100
                if station_name_norm.startswith(query_norm):
                    score = 200  # Higher score for starts with
                if station_name_norm == query_norm:
                    score = 300  # Highest score for exact match
                
                matching_stations.append({
                    **station,
                    "score": score
                })
        
        # Sort by relevance
        matching_stations.sort(key=lambda x: x["score"], reverse=True)
        
        return jsonify(matching_stations[:10])  # Limit to 10 results
        
    except Exception as e:
        logger.error(f"Failed to search stations for '{query}': {e}")
        return jsonify([])


# Enhanced train search (legacy path — kept for back-compat, delegates to /api/search/trains)
@app.route('/api/trains/search/<string:query>')
def search_trains_legacy(query):
    """Legacy train search route — redirects to the canonical normalised endpoint."""
    from flask import redirect, url_for
    return redirect(url_for('search_trains_with_date', q=query))


# Passenger Reports and Social Features (Waze-like functionality)

@app.route('/api/passenger/report', methods=['POST'])
def submit_passenger_report():
    """Submit a passenger report (delay, platform change, crowding, etc.)"""
    try:
        data = request.get_json()
        required_fields = ['train_number', 'report_type']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO passenger_reports 
        (train_number, report_type, message, platform, delay_minutes, crowding_level, station_name, user_ip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['train_number'],
            data['report_type'],
            data.get('message', ''),
            data.get('platform', ''),
            data.get('delay_minutes', 0),
            data.get('crowding_level', ''),
            data.get('station_name', ''),
            request.remote_addr
        ))
        
        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"New passenger report submitted for train {data['train_number']}: {data['report_type']}")
        
        return jsonify({
            "success": True,
            "report_id": report_id,
            "message": "Report submitted successfully! Thank you for helping fellow passengers."
        })
        
    except Exception as e:
        logger.error(f"Failed to submit passenger report: {e}")
        return jsonify({"error": "Failed to submit report"}), 500

@app.route('/api/passenger/reports/<string:train_number>')
def get_passenger_reports(train_number):
    """Get recent passenger reports for a specific train"""
    try:
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        # Get reports from the last 2 hours
        cursor.execute('''
        SELECT report_type, message, platform, delay_minutes, crowding_level, 
               station_name, reported_at, verified_count, helpful_count
        FROM passenger_reports 
        WHERE train_number = ? AND datetime(reported_at) > datetime('now', '-2 hours')
        ORDER BY reported_at DESC
        LIMIT 20
        ''', (train_number,))
        
        reports = []
        for row in cursor.fetchall():
            report = {
                "report_type": row[0],
                "message": row[1],
                "platform": row[2],
                "delay_minutes": row[3],
                "crowding_level": row[4],
                "station_name": row[5],
                "reported_at": row[6],
                "verified_count": row[7],
                "helpful_count": row[8],
                "time_ago": get_time_ago(row[6])
            }
            reports.append(report)
        
        conn.close()
        
        return jsonify({
            "train_number": train_number,
            "reports": reports,
            "total_reports": len(reports)
        })
        
    except Exception as e:
        logger.error(f"Failed to get passenger reports for {train_number}: {e}")
        return jsonify({"error": "Failed to fetch reports"}), 500

@app.route('/api/passenger/seats', methods=['POST'])
def report_seat_availability():
    """Report seat availability in a train car"""
    try:
        data = request.get_json()
        required_fields = ['train_number', 'available_seats', 'total_seats']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO seat_availability 
        (train_number, car_number, available_seats, total_seats, station_name, user_ip)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['train_number'],
            data.get('car_number', ''),
            data['available_seats'],
            data['total_seats'],
            data.get('station_name', ''),
            request.remote_addr
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Seat availability updated! Thanks for helping fellow passengers find seats."
        })
        
    except Exception as e:
        logger.error(f"Failed to report seat availability: {e}")
        return jsonify({"error": "Failed to report seats"}), 500

@app.route('/api/passenger/seats/<string:train_number>')
def get_seat_availability(train_number):
    """Get current seat availability for a train"""
    try:
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        # Get most recent seat reports for each car
        cursor.execute('''
        SELECT car_number, available_seats, total_seats, station_name, reported_at,
               MAX(reported_at) as latest_report
        FROM seat_availability 
        WHERE train_number = ? AND datetime(reported_at) > datetime('now', '-1 hour')
        GROUP BY car_number
        ORDER BY car_number
        ''', (train_number,))
        
        seats = []
        for row in cursor.fetchall():
            seat_info = {
                "car_number": row[0] or "Unknown",
                "available_seats": row[1],
                "total_seats": row[2],
                "occupancy_rate": round((row[2] - row[1]) / row[2] * 100) if row[2] > 0 else 0,
                "station_name": row[3],
                "reported_at": row[4],
                "time_ago": get_time_ago(row[4])
            }
            seats.append(seat_info)
        
        conn.close()
        
        return jsonify({
            "train_number": train_number,
            "seat_availability": seats,
            "cars_reported": len(seats)
        })
        
    except Exception as e:
        logger.error(f"Failed to get seat availability for {train_number}: {e}")
        return jsonify({"error": "Failed to fetch seat data"}), 500

@app.route('/api/passenger/tips', methods=['POST'])
def submit_passenger_tip():
    """Submit a helpful tip for a station or general travel"""
    try:
        data = request.get_json()
        required_fields = ['tip_type', 'message']
        
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO passenger_tips 
        (station_name, tip_type, message, user_ip)
        VALUES (?, ?, ?, ?)
        ''', (
            data.get('station_name', ''),
            data['tip_type'],
            data['message'],
            request.remote_addr
        ))
        
        tip_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "tip_id": tip_id,
            "message": "Tip submitted! It will help other passengers navigate better."
        })
        
    except Exception as e:
        logger.error(f"Failed to submit tip: {e}")
        return jsonify({"error": "Failed to submit tip"}), 500

@app.route('/api/passenger/tips/<string:station_name>')
def get_passenger_tips(station_name):
    """Get passenger tips for a specific station"""
    try:
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT tip_type, message, helpful_count, created_at
        FROM passenger_tips 
        WHERE station_name = ? OR station_name = ''
        ORDER BY helpful_count DESC, created_at DESC
        LIMIT 10
        ''', (station_name,))
        
        tips = []
        for row in cursor.fetchall():
            tip = {
                "tip_type": row[0],
                "message": row[1],
                "helpful_count": row[2],
                "created_at": row[3],
                "time_ago": get_time_ago(row[3])
            }
            tips.append(tip)
        
        conn.close()
        
        return jsonify({
            "station_name": station_name,
            "tips": tips,
            "total_tips": len(tips)
        })
        
    except Exception as e:
        logger.error(f"Failed to get tips for {station_name}: {e}")
        return jsonify({"error": "Failed to fetch tips"}), 500

@app.route('/api/passenger/verify/<int:report_id>', methods=['POST'])
def verify_report(report_id):
    """Verify a passenger report as accurate"""
    try:
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE passenger_reports 
        SET verified_count = verified_count + 1 
        WHERE id = ?
        ''', (report_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Report verified! Thank you for confirming."
        })
        
    except Exception as e:
        logger.error(f"Failed to verify report {report_id}: {e}")
        return jsonify({"error": "Failed to verify report"}), 500

def get_time_ago(timestamp_str):
    """Calculate human-readable time difference"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} min ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"
    except:
        return "Unknown"

@app.route('/api/train/<string:train_id>/reports', methods=['GET'])
def get_train_reports(train_id):
    try:
        conn = sqlite3.connect('passenger_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM passenger_reports 
            WHERE train_number COLLATE NOCASE = ? 
            ORDER BY reported_at DESC LIMIT 50
        ''', (train_id,))
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(reports)
    except Exception as e:
        logger.error(f"Error fetching reports: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/train/<string:train_id>/reports', methods=['POST'])
def add_train_report(train_id):
    try:
        data = request.json
        conn = sqlite3.connect('passenger_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO passenger_reports (train_number, report_type, message, user_ip)
            VALUES (?, ?, ?, ?)
        ''', (train_id, data.get('report_type'), data.get('message'), request.remote_addr))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error adding report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/station-by-name/<path:station_name>')
def get_station_timetable_by_name(station_name):
    """
    Get station timetable by station name (URL-decoded).
    This is the correct endpoint to use from the mobile app — it passes the
    human-readable name directly to the Infofer scraper, which converts it to
    the right slug. This avoids the fake numeric ID problem entirely.

    Optional query param:
      ?date=DD.MM.YYYY  — fetch timetable for a specific date (defaults to today)
    """
    try:
        from urllib.parse import unquote
        decoded_name = unquote(station_name)
        date_str = request.args.get('date')  # e.g. "01.03.2026"
        logger.info(f"Fetching timetable by name: '{decoded_name}', date: {date_str}")

        timetable = StationTimetableGetter.get_timetable(
            station_id=decoded_name,   # used as fallback key only
            station_name=decoded_name, # this drives the actual Infofer slug
            date_str=date_str          # None falls back to today inside the scraper
        )

        if not timetable:
            # Return an empty list so the app can show "no trains" instead of an error
            return jsonify([])

        for item in timetable:
            item['is_live'] = True

        return jsonify(timetable)

    except Exception as e:
        logger.error(f"Failed to get timetable for station name '{station_name}': {e}")
        return jsonify({
            "error": "Timetable data unavailable",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
