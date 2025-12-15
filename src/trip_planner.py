# src/trip_planner.py
"""
Trip planning algorithms based on CSES problem 1690 (Hamiltonian Paths)
Calculates number of ways to visit all cities and optimal routes
"""

import requests
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import json


class TripPlanner:
    def __init__(self, aviation_api_key: str):
        self.api_key = aviation_api_key
        self.base_url = "http://api.aviationstack.com/v1/flights"
    
    def count_hamiltonian_paths(self, n: int, adj_matrix: List[List[bool]], 
                                start: int = 0, end: int = None) -> int:
        """
        Count number of Hamiltonian paths from start to end
        Based on CSES 1690 - Dynamic Programming with bitmask
        
        dp[mask][i] = number of ways to reach city i with cities in mask visited
        """
        if end is None:
            end = n - 1
        
        # dp[mask][i] = number of paths ending at i with visited cities represented by mask
        dp = [[0] * n for _ in range(1 << n)]
        dp[1 << start][start] = 1
        
        MOD = 10**9 + 7
        
        for mask in range(1 << n):
            for i in range(n):
                if not (mask & (1 << i)):
                    continue
                if dp[mask][i] == 0:
                    continue
                
                for j in range(n):
                    if mask & (1 << j):
                        continue
                    if not adj_matrix[i][j]:
                        continue
                    
                    new_mask = mask | (1 << j)
                    dp[new_mask][j] = (dp[new_mask][j] + dp[mask][i]) % MOD
        
        # Return paths that visit all cities and end at the target
        full_mask = (1 << n) - 1
        return dp[full_mask][end]
    
    def find_optimal_path_with_costs(self, n: int, cost_matrix: List[List[float]], 
                                     start: int = 0, end: int = None) -> Tuple[float, List[int]]:
        """
        Find minimum cost Hamiltonian path using DP
        Returns (min_cost, path)
        """
        if end is None:
            end = n - 1
        
        INF = float('inf')
        dp = [[INF] * n for _ in range(1 << n)]
        parent = [[None] * n for _ in range(1 << n)]
        
        dp[1 << start][start] = 0
        
        for mask in range(1 << n):
            for i in range(n):
                if not (mask & (1 << i)):
                    continue
                if dp[mask][i] == INF:
                    continue
                
                for j in range(n):
                    if mask & (1 << j):
                        continue
                    if cost_matrix[i][j] == INF:
                        continue
                    
                    new_mask = mask | (1 << j)
                    new_cost = dp[mask][i] + cost_matrix[i][j]
                    
                    if new_cost < dp[new_mask][j]:
                        dp[new_mask][j] = new_cost
                        parent[new_mask][j] = (mask, i)
        
        full_mask = (1 << n) - 1
        min_cost = dp[full_mask][end]
        
        # Reconstruct path
        path = []
        mask = full_mask
        curr = end
        
        while curr is not None:
            path.append(curr)
            if parent[mask][curr] is None:
                break
            mask, curr = parent[mask][curr]
        
        path.reverse()
        return min_cost, path
    
    async def get_flight_costs(self, destinations: List[Dict], travel_class: str = "economy") -> List[List[float]]:
        """
        Get flight costs between all pairs of destinations using Aviation Stack API
        Returns adjacency matrix with costs
        """
        n = len(destinations)
        cost_matrix = [[float('inf')] * n for _ in range(n)]
        
        # Diagonal is 0 (staying in same city)
        for i in range(n):
            cost_matrix[i][i] = 0
        
        # Query flights between each pair
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                
                from_airport = destinations[i].get('airport_code')
                to_airport = destinations[j].get('airport_code')
                
                if not from_airport or not to_airport:
                    continue
                
                try:
                    cost = await self._fetch_flight_cost(
                        from_airport, to_airport, 
                        destinations[i].get('departure_date'),
                        travel_class
                    )
                    if cost is not None:
                        cost_matrix[i][j] = cost
                except Exception as e:
                    print(f"Error fetching flight {from_airport}->{to_airport}: {e}")
        
        return cost_matrix
    
    async def _fetch_flight_cost(self, from_airport: str, to_airport: str, 
                                 date: Optional[datetime], travel_class: str) -> Optional[float]:
        """
        Fetch flight cost from Aviation Stack API
        """
        params = {
            "access_key": self.api_key,
            "dep_iata": from_airport,
            "arr_iata": to_airport,
            "limit": 5
        }
        
        # Note: Free tier doesn't support flight_date, so we get current flights
        # In production, use paid tier or another API with better flight search
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            data = response.json()
            
            if "data" not in data or not data["data"]:
                # No direct flights, estimate based on distance
                return self._estimate_cost_by_distance(from_airport, to_airport, travel_class)
            
            # For demo, use a simple pricing model
            # Real implementation would parse actual flight prices
            base_cost = 200  # Base cost in currency
            
            if travel_class == "business":
                base_cost *= 2.5
            elif travel_class == "first":
                base_cost *= 4
            
            return base_cost
            
        except Exception as e:
            print(f"API Error: {e}")
            return self._estimate_cost_by_distance(from_airport, to_airport, travel_class)
    
    def _estimate_cost_by_distance(self, from_code: str, to_code: str, travel_class: str) -> float:
        """
        Estimate flight cost based on typical distance pricing
        Fallback when API doesn't return results
        """
        # Simple estimation: assume average flight costs
        base_costs = {
            "economy": 250,
            "business": 600,
            "first": 1000
        }
        return base_costs.get(travel_class, 250)
    
    def create_adjacency_matrix(self, destinations: List[Dict]) -> List[List[bool]]:
        """
        Create boolean adjacency matrix (all cities connected for complete graph)
        """
        n = len(destinations)
        return [[i != j for j in range(n)] for i in range(n)]
    
    def calculate_trip_plan(self, destinations: List[Dict], cost_matrix: List[List[float]], 
                           has_dates: bool) -> Dict:
        """
        Main function to calculate trip plan
        Returns dict with paths, costs, and number of ways
        """
        n = len(destinations)
        
        if n < 2:
            return {
                "error": "Need at least 2 destinations",
                "num_ways": 0,
                "optimal_path": [],
                "total_cost": 0
            }
        
        result = {}
        
        if not has_dates:
            # Calculate number of possible ways (Hamiltonian paths)
            adj_matrix = self.create_adjacency_matrix(destinations)
            num_ways = self.count_hamiltonian_paths(n, adj_matrix, 0, n-1)
            result["num_ways"] = num_ways
            result["message"] = f"There are {num_ways} different ways to visit all cities"
        
        # Always calculate optimal path with costs
        min_cost, optimal_path = self.find_optimal_path_with_costs(n, cost_matrix, 0, n-1)
        
        result.update({
            "optimal_path": optimal_path,
            "total_cost": min_cost if min_cost != float('inf') else None,
            "path_details": [
                {
                    "city": destinations[i]["city"],
                    "country": destinations[i]["country"],
                    "order": i + 1
                }
                for i in optimal_path
            ]
        })
        
        return result