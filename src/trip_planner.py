# src/trip_planner.py
"""
Simplified trip planner using Aviation Edge Timetable API
Finds all feasible Hamiltonian paths with flight availability
"""

import requests
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from itertools import permutations
import time

class TripPlanner:
    def __init__(self, aviation_api_key: str):
        self.api_key = aviation_api_key
        self.timetable_url = "https://aviation-edge.com/v2/public/timetable"
        self.flight_cache = {}  
        self.last_request_time = 0
        self.min_request_interval = 1.0 
    
    def get_airport_code(self, city_name: str) -> Optional[str]:
        """Map city names to IATA airport codes"""
        airport_map = {
            # Indian cities
            "bengaluru": "BLR", "bangalore": "BLR",
            "mumbai": "BOM", "bombay": "BOM",
            "delhi": "DEL", "new delhi": "DEL",
            "chennai": "MAA", "madras": "MAA",
            "kolkata": "CCU", "calcutta": "CCU",
            "hyderabad": "HYD",
            "pune": "PNQ",
            "ahmedabad": "AMD",
            "goa": "GOI",
            "kochi": "COK", "cochin": "COK",
            
            # International
            "london": "LHR",
            "paris": "CDG",
            "new york": "JFK",
            "dubai": "DXB",
            "singapore": "SIN",
            "tokyo": "NRT",
            "bangkok": "BKK",
            "hong kong": "HKG",
            "sydney": "SYD",
            "los angeles": "LAX",
            "san francisco": "SFO",
            "chicago": "ORD",
            "miami": "MIA",
            "toronto": "YYZ",
            "vancouver": "YVR",
            "frankfurt": "FRA",
            "amsterdam": "AMS",
            "rome": "FCO",
            "barcelona": "BCN",
            "madrid": "MAD",
            "istanbul": "IST",
            "doha": "DOH",
            "abu dhabi": "AUH",
            "kuala lumpur": "KUL",
            "jakarta": "CGK",
            "seoul": "ICN",
            "beijing": "PEK",
            "shanghai": "PVG",
        }
        
        city_lower = city_name.lower().strip()
        return airport_map.get(city_lower)
    
    def parse_time(self, time_str: str) -> Optional[datetime]:
        """Parse various time formats from API"""
        if not time_str:
            return None
        
        # Try different formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
            "%Y-%m-%dT%H:%M:%S",      # ISO without microseconds
            "%Y-%m-%d %H:%M:%S",      # Space separated
            "%Y-%m-%d",               # Date only
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except:
                continue
        
        print(f"⚠️ Could not parse time: {time_str}")
        return None
    
    def is_daytime_flight(self, dep_time: Optional[datetime]) -> bool:
        """Check if flight departs between 10 AM and 6 PM"""
        if not dep_time:
            return False
        return 10 <= dep_time.hour < 18
    
    def fetch_flights(self, from_airport: str, limit: int = 50) -> List[Dict]:
        """
        Fetch departure flights from an airport with caching and rate limiting
        Returns list of flight dictionaries
        """
        # Check cache first
        if from_airport in self.flight_cache:
            print(f"✅ Using cached data for {from_airport}")
            return self.flight_cache[from_airport]
        
        params = {
            "key": self.api_key,
            "iataCode": from_airport,
            "type": "departure"
        }
        
        try:
            print(f"\n🔍 Fetching flights from {from_airport}...")
            self.last_request_time = time.time()
            response = requests.get(self.timetable_url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ API error: Status {response.status_code} for {from_airport}")
                print(f"Response: {response.text[:200]}")
                return []
            
            data = response.json()
            print(f"📦 Raw API response type: {type(data)}")
            
            # Check if API returned an error
            if isinstance(data, dict):
                if "error" in data:
                    print(f"❌ API Error for {from_airport}: {data.get('error')}")
                    if "rate limit" in str(data.get('error')).lower():
                        print("⚠️ RATE LIMIT EXCEEDED - Free tier limit reached")
                    return []
                if "message" in data:
                    print(f"⚠️ API Message for {from_airport}: {data.get('message')}")
                    return []
                # If it's a dict with 'data' key
                if "data" in data and isinstance(data["data"], list):
                    flights = data["data"][:limit]
                    print(f"✅ Found {len(flights)} flights in nested data")
                    self.flight_cache[from_airport] = flights
                    return flights
                print(f"⚠️ Unexpected dict format for {from_airport}: {list(data.keys())}")
                return []
            
            if not isinstance(data, list):
                print(f"❌ Unexpected response type for {from_airport}: {type(data)}")
                return []
            
            # Cache the results
            flights = data[:limit]
            print(f"✅ Found {len(flights)} flights for {from_airport}")
            
            # Print sample flight for debugging
            if flights:
                sample = flights[0]
                print(f"\n📋 Sample flight structure:")
                print(f"   Airline: {sample.get('airline', {})}")
                print(f"   Flight: {sample.get('flight', {})}")
                print(f"   Departure: {sample.get('departure', {})}")
                print(f"   Arrival: {sample.get('arrival', {})}")
            
            self.flight_cache[from_airport] = flights
            return flights
            
        except Exception as e:
            print(f"❌ Error fetching flights from {from_airport}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def check_flight_exists(self, from_airport: str, to_airport: str) -> bool:
        """
        Check if direct flight exists between two airports
        """
        flights = self.fetch_flights(from_airport)
        
        for flight in flights:
            arrival = flight.get("arrival", {}) or {}
            arr_iata = arrival.get("iataCode")
            
            if arr_iata == to_airport:
                return True
        
        return False
    
    def build_adjacency_matrix(self, cities: List[Dict]) -> List[List[bool]]:
        """
        Build adjacency matrix showing which city pairs have direct flights
        cities: [{"city": "Mumbai", "airport": "BOM"}, ...]
        Returns: n x n boolean matrix
        """
        n = len(cities)
        adj_matrix = [[False] * n for _ in range(n)]
        
        print(f"\n🔍 Checking flight connectivity for {n} cities...")
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    adj_matrix[i][j] = False  # No self-loops
                    continue
                
                from_airport = cities[i]["airport"]
                to_airport = cities[j]["airport"]
                
                print(f"Checking {from_airport} → {to_airport}...", end=" ")
                
                has_flight = self.check_flight_exists(from_airport, to_airport)
                adj_matrix[i][j] = has_flight
                
                print("✓" if has_flight else "✗")
        
        return adj_matrix
    
    def find_all_hamiltonian_cycles(self, n: int, adj_matrix: List[List[bool]], 
                                    start_idx: int) -> List[List[int]]:
        """
        Find all Hamiltonian cycles that start and end at start_idx
        Uses backtracking to enumerate all valid cycles
        """
        all_cycles = []
        visited = [False] * n
        path = []
        
        def backtrack(current: int):
            path.append(current)
            visited[current] = True
            
            # If we've visited all cities
            if len(path) == n:
                # Check if we can return to start
                if adj_matrix[current][start_idx]:
                    # Add the return to start to complete the cycle
                    cycle = path[:] + [start_idx]
                    all_cycles.append(cycle)
            else:
                # Try visiting each unvisited neighbor
                for next_city in range(n):
                    if not visited[next_city] and adj_matrix[current][next_city]:
                        backtrack(next_city)
            
            # Backtrack
            path.pop()
            visited[current] = False
        
        backtrack(start_idx)
        return all_cycles
    
    def get_flight_options(self, from_airport: str, to_airport: str, 
                          travel_date: datetime) -> List[Dict]:
        """
        Get available flights between two airports, preferring daytime flights
        """
        print(f"\n✈️ Finding flights {from_airport} → {to_airport}")
        flights = self.fetch_flights(from_airport)
        
        matching_flights = []
        for flight in flights:
            arrival = flight.get("arrival", {}) or {}
            arr_iata = arrival.get("iataCode")
            
            if arr_iata == to_airport:
                airline_obj = flight.get("airline", {}) or {}
                flight_obj = flight.get("flight", {}) or {}
                dep_obj = flight.get("departure", {}) or {}
                arr_obj = flight.get("arrival", {}) or {}
                
                airline_name = airline_obj.get("name", "Unknown Airline")
                airline_code = airline_obj.get("iataCode", "")
                flight_num = flight_obj.get("iataNumber", flight_obj.get("number", ""))
                
                dep_time_str = dep_obj.get("scheduledTimeLocal") or dep_obj.get("scheduledTime")
                arr_time_str = arr_obj.get("scheduledTimeLocal") or arr_obj.get("scheduledTime")
                
                dep_time = self.parse_time(dep_time_str)
                arr_time = self.parse_time(arr_time_str)
                
                # Check if it's a daytime flight
                is_daytime = self.is_daytime_flight(dep_time)
                
                flight_info = {
                    "airline": airline_name,
                    "airline_code": airline_code,
                    "flight_number": f"{airline_code}{flight_num}" if airline_code and flight_num else flight_num,
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                    "departure_time_str": dep_time.strftime("%I:%M %p") if dep_time else "N/A",
                    "arrival_time_str": arr_time.strftime("%I:%M %p") if arr_time else "N/A",
                    "from_airport": from_airport,
                    "to_airport": to_airport,
                    "is_daytime": is_daytime
                }
                
                matching_flights.append(flight_info)
                
                print(f"   ✓ {flight_info['airline']} {flight_info['flight_number']}")
                print(f"      Dep: {flight_info['departure_time_str']} | Arr: {flight_info['arrival_time_str']}")
                print(f"      {'🌞 DAYTIME FLIGHT' if is_daytime else '🌙 Night flight'}")
        
        # Sort: daytime flights first, then by departure time
        matching_flights.sort(key=lambda x: (not x['is_daytime'], x['departure_time'] or datetime.max))
        
        print(f"\n📊 Total matching flights: {len(matching_flights)}")
        return matching_flights[:5]  # Return top 5
    
    def calculate_trip_plan(self, cities: List[Dict], start_date: datetime) -> Dict:
        """
        Main function to calculate all possible trip plans
        cities: [{"city": "Mumbai", "days": 2, "airport": "BOM", "country": "India"}, ...]
        First city is start, last city is end (both fixed)
        """
        n = len(cities)
        
        if n < 2:
            return {
                "error": "Need at least 2 cities",
                "paths": []
            }
        
        # Add airport codes
        for city in cities:
            if not city.get("airport"):
                airport = self.get_airport_code(city["city"])
                if not airport:
                    return {
                        "error": f"Unknown airport for city: {city['city']}",
                        "paths": []
                    }
                city["airport"] = airport
        
        # Build adjacency matrix (check flight availability)
        adj_matrix = self.build_adjacency_matrix(cities)
        
        # Find all Hamiltonian cycles starting from first city
        start_idx = 0
        
        print(f"\n🔍 Finding all round-trip routes starting from {cities[start_idx]['city']}...")
        all_cycles = self.find_all_hamiltonian_cycles(n, adj_matrix, start_idx)
        
        if not all_cycles:
            return {
                "error": f"No valid round-trip routes found starting from {cities[start_idx]['city']}",
                "paths": [],
                "num_paths": 0
            }
        
        print(f"✅ Found {len(all_cycles)} valid round-trip routes!")
        
        # Format results with flight details
        result_paths = []
        
        for path_idx, cycle in enumerate(all_cycles):
            route_details = []
            flights = []
            current_date = start_date
            
            # Remove the duplicate start city at the end for route display
            cities_to_visit = cycle[:-1]
            
            print(f"\n📍 Processing Route {path_idx + 1}: {' → '.join([cities[i]['city'] for i in cities_to_visit])} → {cities[start_idx]['city']}")
            
            for idx, city_idx in enumerate(cities_to_visit):
                city = cities[city_idx]
                
                arrival_date = current_date
                departure_date = current_date + timedelta(days=city["days"])
                
                route_details.append({
                    "order": idx + 1,
                    "city": city["city"],
                    "country": city["country"],
                    "airport": city["airport"],
                    "days": city["days"],
                    "arrival_date": arrival_date.strftime("%Y-%m-%d"),
                    "departure_date": departure_date.strftime("%Y-%m-%d")
                })
                
                # Get flight to next city (or back to start)
                next_city_idx = cycle[idx + 1]
                next_city = cities[next_city_idx]
                
                flight_options = self.get_flight_options(
                    city["airport"], 
                    next_city["airport"],
                    departure_date
                )
                
                # Convert datetime objects to strings for JSON
                serialized_options = []
                for opt in flight_options:
                    serialized_opt = opt.copy()
                    serialized_opt.pop('departure_time', None)
                    serialized_opt.pop('arrival_time', None)
                    serialized_options.append(serialized_opt)
                
                flights.append({
                    "from": city["city"],
                    "to": next_city["city"],
                    "from_airport": city["airport"],
                    "to_airport": next_city["airport"],
                    "date": departure_date.strftime("%Y-%m-%d"),
                    "options": serialized_options,
                    "is_return_flight": (idx == len(cities_to_visit) - 1)
                })
                
                current_date = departure_date
            
            result_paths.append({
                "path_number": path_idx + 1,
                "path_indices": cities_to_visit,
                "route": route_details,
                "flights": flights,
                "total_duration_days": sum(cities[i]["days"] for i in cities_to_visit),
                "is_round_trip": True
            })
        
        return {
            "num_paths": len(all_cycles),
            "paths": result_paths,
            "start_city": cities[start_idx]["city"],
            "end_city": cities[start_idx]["city"],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "message": f"Found {len(all_cycles)} valid round-trip route(s) starting from {cities[start_idx]['city']}"
        }