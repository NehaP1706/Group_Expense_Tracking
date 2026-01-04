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
        self.flight_cache = {}  # Cache to avoid repeated API calls
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
    
    def get_airport_code(self, city_name: str) -> Optional[str]:
        """Map city names to IATA airport codes"""
        airport_map = {
            # India
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
    
    def fetch_flights(self, from_airport: str, limit: int = 50) -> List[Dict]:
        """
        Fetch departure flights from an airport with caching and rate limiting
        Returns list of flight dictionaries
        """
        # Check cache first
        if from_airport in self.flight_cache:
            print(f"Using cached data for {from_airport}")
            return self.flight_cache[from_airport]
        
        # Rate limiting - wait if needed
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            print(f"Rate limiting: waiting {wait_time:.2f}s...")
            time.sleep(wait_time)
        
        params = {
            "key": self.api_key,
            "iataCode": from_airport,
            "type": "departure"
        }
        
        try:
            self.last_request_time = time.time()
            response = requests.get(self.timetable_url, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"API error: Status {response.status_code} for {from_airport}")
                print(f"Response: {response.text[:200]}")
                return []
            
            data = response.json()
            
            # Check if API returned an error
            if isinstance(data, dict):
                if "error" in data:
                    print(f"API Error for {from_airport}: {data.get('error')}")
                    if "rate limit" in str(data.get('error')).lower():
                        print("⚠️ RATE LIMIT EXCEEDED - Free tier limit reached")
                    return []
                if "message" in data:
                    print(f"API Message for {from_airport}: {data.get('message')}")
                    return []
                # If it's a dict with 'data' key
                if "data" in data and isinstance(data["data"], list):
                    flights = data["data"][:limit]
                    self.flight_cache[from_airport] = flights
                    return flights
                print(f"Unexpected dict format for {from_airport}: {list(data.keys())}")
                print(f"Full response: {data}")
                return []
            
            if not isinstance(data, list):
                print(f"Unexpected response type for {from_airport}: {type(data)}")
                print(f"Response sample: {str(data)[:200]}")
                return []
            
            # Cache the results
            flights = data[:limit]
            self.flight_cache[from_airport] = flights
            return flights
            
        except Exception as e:
            print(f"Error fetching flights from {from_airport}: {e}")
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
        
        print(f"\nChecking flight connectivity for {n} cities...")
        
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
    
    def find_all_hamiltonian_paths(self, n: int, adj_matrix: List[List[bool]], 
                                   start_idx: int, end_idx: int) -> List[List[int]]:
        """
        Find all Hamiltonian paths from start_idx to end_idx
        Uses backtracking to enumerate all valid paths
        """
        all_paths = []
        visited = [False] * n
        path = []
        
        def backtrack(current: int):
            path.append(current)
            visited[current] = True
            
            # If we've visited all cities
            if len(path) == n:
                # Check if we end at the target
                if current == end_idx:
                    all_paths.append(path[:])
            else:
                # Try visiting each unvisited neighbor
                for next_city in range(n):
                    if not visited[next_city] and adj_matrix[current][next_city]:
                        backtrack(next_city)
            
            # Backtrack
            path.pop()
            visited[current] = False
        
        backtrack(start_idx)
        return all_paths
    
    def get_flight_options(self, from_airport: str, to_airport: str, 
                          travel_date: datetime) -> List[Dict]:
        """
        Get available flights between two airports
        """
        flights = self.fetch_flights(from_airport)
        
        matching_flights = []
        for flight in flights:
            arrival = flight.get("arrival", {}) or {}
            arr_iata = arrival.get("iataCode")
            
            if arr_iata == to_airport:
                airline = (flight.get("airline", {}) or {}).get("name", "Unknown")
                flight_num = (flight.get("flight", {}) or {}).get("iataNumber", "")
                
                dep = flight.get("departure", {}) or {}
                arr = flight.get("arrival", {}) or {}
                
                dep_time = dep.get("scheduledTimeLocal") or dep.get("scheduledTime")
                arr_time = arr.get("scheduledTimeLocal") or arr.get("scheduledTime")
                
                matching_flights.append({
                    "airline": airline,
                    "flight_number": flight_num,
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                    "from_airport": from_airport,
                    "to_airport": to_airport
                })
        
        return matching_flights[:5]  # Limit to 5 options per route
    
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
        
        # Find all Hamiltonian paths from first to last city
        start_idx = 0
        end_idx = n - 1
        
        print(f"\nFinding all paths from {cities[start_idx]['city']} to {cities[end_idx]['city']}...")
        all_paths = self.find_all_hamiltonian_paths(n, adj_matrix, start_idx, end_idx)
        
        if not all_paths:
            return {
                "error": f"No valid routes found from {cities[start_idx]['city']} to {cities[end_idx]['city']}",
                "paths": [],
                "num_paths": 0
            }
        
        print(f"Found {len(all_paths)} valid paths!")
        
        # Format results with flight details
        result_paths = []
        current_date = start_date
        
        for path_idx, path in enumerate(all_paths):
            route_details = []
            flights = []
            current_date = start_date
            
            for idx, city_idx in enumerate(path):
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
                
                # Get flight options to next city
                if idx < len(path) - 1:
                    next_city_idx = path[idx + 1]
                    next_city = cities[next_city_idx]
                    
                    flight_options = self.get_flight_options(
                        city["airport"], 
                        next_city["airport"],
                        departure_date
                    )
                    
                    flights.append({
                        "from": city["city"],
                        "to": next_city["city"],
                        "from_airport": city["airport"],
                        "to_airport": next_city["airport"],
                        "date": departure_date.strftime("%Y-%m-%d"),
                        "options": flight_options
                    })
                
                current_date = departure_date
            
            result_paths.append({
                "path_number": path_idx + 1,
                "path_indices": path,
                "route": route_details,
                "flights": flights,
                "total_duration_days": sum(c["days"] for c in cities)
            })
        
        return {
            "num_paths": len(all_paths),
            "paths": result_paths,
            "start_city": cities[start_idx]["city"],
            "end_city": cities[end_idx]["city"],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "message": f"Found {len(all_paths)} valid route(s) from {cities[start_idx]['city']} to {cities[end_idx]['city']}"
        }