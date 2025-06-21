"""
MARA Hackathon Arbitrage Analyzer
Analyzes pricing data to find optimal compute allocation strategies
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'https://mara-hackathon-api.onrender.com')
API_KEY = os.getenv('API_KEY')

class ArbitrageAnalyzer:
    def __init__(self, db_path='mara_data.db'):
        self.db_path = db_path
        self.inventory = self.load_inventory()
        self.site_power_limit = 1000000  # Default 1MW
        
    def load_inventory(self):
        """Load inventory from database or API"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check if inventory table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory'")
            if not cursor.fetchone():
                conn.close()
                # Table doesn't exist, fetch from API
                response = requests.get(f"{API_BASE_URL}/inventory")
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"Failed to fetch inventory from API: {response.status_code}")
            
            # Try to load from database
            df = pd.read_sql_query("SELECT * FROM inventory", conn)
            conn.close()
            
            if df.empty:
                # Fetch from API if no data in database
                response = requests.get(f"{API_BASE_URL}/inventory")
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"Failed to fetch inventory from API: {response.status_code}")
            else:
                # Convert database format to API format
                inventory = {'miners': {}, 'inference': {}}
                for _, row in df.iterrows():
                    if row['type'] == 'miner':
                        inventory['miners'][row['subtype']] = {
                            'power': row['power'],
                            'hashrate': row['capability']
                        }
                    else:
                        inventory['inference'][row['subtype']] = {
                            'power': row['power'],
                            'tokens': row['capability']
                        }
                return inventory
                
        except Exception as e:
            # If all else fails, fetch from API
            print(f"Warning: {e}")
            response = requests.get(f"{API_BASE_URL}/inventory")
            if response.status_code == 200:
                return response.json()
            else:
                # Return a default inventory structure if API also fails
                print("Using default inventory structure")
                return {
                    'miners': {
                        'air': {'power': 3500, 'hashrate': 1000},
                        'hydro': {'power': 5000, 'hashrate': 5000},
                        'immersion': {'power': 10000, 'hashrate': 10000}
                    },
                    'inference': {
                        'gpu': {'power': 5000, 'tokens': 1000},
                        'asic': {'power': 15000, 'tokens': 50000}
                    }
                }
            
    def get_latest_prices(self):
        """Get the most recent pricing data"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check if pricing table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pricing'")
            if not cursor.fetchone():
                conn.close()
                # Table doesn't exist, fetch from API
                response = requests.get(f"{API_BASE_URL}/prices")
                if response.status_code == 200:
                    prices = response.json()
                    if prices:
                        return prices[0]
                else:
                    raise Exception(f"Failed to fetch prices from API: {response.status_code}")
            
            query = """
                SELECT * FROM pricing 
                ORDER BY collected_at DESC 
                LIMIT 1
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                # Fetch from API if no data
                response = requests.get(f"{API_BASE_URL}/prices")
                if response.status_code == 200:
                    prices = response.json()
                    if prices:
                        return prices[0]
            else:
                return df.iloc[0].to_dict()
                
        except Exception as e:
            # If all else fails, fetch from API
            print(f"Warning: {e}")
            response = requests.get(f"{API_BASE_URL}/prices")
            if response.status_code == 200:
                prices = response.json()
                if prices:
                    return prices[0]
            
            # Return default prices if API also fails
            print("Using default prices")
            return {
                'energy_price': 0.65,
                'hash_price': 8.5,
                'token_price': 3.0,
                'timestamp': datetime.now().isoformat()
            }
            
    def calculate_roi(self, machine_type, machine_subtype, quantity, current_prices):
        """Calculate ROI for a specific machine allocation"""
        if machine_type == 'miner':
            specs = self.inventory['miners'][machine_subtype]
            revenue_per_unit = specs['hashrate'] * current_prices['hash_price']
        else:  # inference
            specs = self.inventory['inference'][machine_subtype]
            revenue_per_unit = specs['tokens'] * current_prices['token_price']
            
        power_per_unit = specs['power']
        cost_per_unit = power_per_unit * current_prices['energy_price']
        profit_per_unit = revenue_per_unit - cost_per_unit
        
        return {
            'revenue': revenue_per_unit * quantity,
            'cost': cost_per_unit * quantity,
            'profit': profit_per_unit * quantity,
            'roi_percentage': (profit_per_unit / cost_per_unit * 100) if cost_per_unit > 0 else 0,
            'power_used': power_per_unit * quantity
        }
        
    def find_optimal_allocation(self, current_prices=None):
        """Find the optimal allocation of machines given current prices"""
        if current_prices is None:
            current_prices = self.get_latest_prices()
            
        # Calculate profit per watt for each machine type
        machine_efficiency = []
        
        # Analyze miners
        for miner_type, specs in self.inventory['miners'].items():
            revenue_per_watt = (specs['hashrate'] * current_prices['hash_price']) / specs['power']
            cost_per_watt = current_prices['energy_price']
            profit_per_watt = revenue_per_watt - cost_per_watt
            
            machine_efficiency.append({
                'type': 'miner',
                'subtype': miner_type,
                'power': specs['power'],
                'profit_per_watt': profit_per_watt,
                'revenue_per_watt': revenue_per_watt,
                'capability': specs['hashrate'],
                'price_type': 'hash_price'
            })
            
        # Analyze inference
        for compute_type, specs in self.inventory['inference'].items():
            revenue_per_watt = (specs['tokens'] * current_prices['token_price']) / specs['power']
            cost_per_watt = current_prices['energy_price']
            profit_per_watt = revenue_per_watt - cost_per_watt
            
            machine_efficiency.append({
                'type': 'inference',
                'subtype': compute_type,
                'power': specs['power'],
                'profit_per_watt': profit_per_watt,
                'revenue_per_watt': revenue_per_watt,
                'capability': specs['tokens'],
                'price_type': 'token_price'
            })
            
        # Sort by profit per watt (descending)
        machine_efficiency.sort(key=lambda x: x['profit_per_watt'], reverse=True)
        
        # Greedy allocation based on profit per watt
        allocation = {}
        remaining_power = self.site_power_limit
        total_profit = 0
        total_revenue = 0
        total_cost = 0
        
        for machine in machine_efficiency:
            if machine['profit_per_watt'] <= 0:
                continue  # Skip unprofitable machines
                
            # Calculate how many units we can fit
            max_units = remaining_power // machine['power']
            if max_units > 0:
                allocation[f"{machine['subtype']}_{machine['type']}"] = {
                    'units': max_units,
                    'type': machine['type'],
                    'subtype': machine['subtype'],
                    'power_used': max_units * machine['power'],
                    'profit': max_units * machine['power'] * machine['profit_per_watt'],
                    'revenue': max_units * machine['power'] * machine['revenue_per_watt'],
                    'cost': max_units * machine['power'] * current_prices['energy_price']
                }
                
                remaining_power -= max_units * machine['power']
                total_profit += allocation[f"{machine['subtype']}_{machine['type']}"]['profit']
                total_revenue += allocation[f"{machine['subtype']}_{machine['type']}"]['revenue']
                total_cost += allocation[f"{machine['subtype']}_{machine['type']}"]['cost']
                
        return {
            'allocation': allocation,
            'total_power_used': self.site_power_limit - remaining_power,
            'total_profit': total_profit,
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'roi_percentage': (total_profit / total_cost * 100) if total_cost > 0 else 0,
            'prices': current_prices,
            'timestamp': datetime.now().isoformat()
        }
        
    def analyze_price_trends(self, hours=24):
        """Analyze price trends over a specified period"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check if pricing table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pricing'")
            if not cursor.fetchone():
                conn.close()
                return None
            
            # Get data for the last N hours
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            query = f"""
                SELECT * FROM pricing 
                WHERE collected_at >= '{since}'
                ORDER BY collected_at
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return None
        except Exception as e:
            print(f"Error analyzing price trends: {e}")
            return None
            
        # Calculate statistics
        stats = {
            'energy_price': {
                'mean': df['energy_price'].mean(),
                'std': df['energy_price'].std(),
                'min': df['energy_price'].min(),
                'max': df['energy_price'].max(),
                'current': df['energy_price'].iloc[-1]
            },
            'hash_price': {
                'mean': df['hash_price'].mean(),
                'std': df['hash_price'].std(),
                'min': df['hash_price'].min(),
                'max': df['hash_price'].max(),
                'current': df['hash_price'].iloc[-1]
            },
            'token_price': {
                'mean': df['token_price'].mean(),
                'std': df['token_price'].std(),
                'min': df['token_price'].min(),
                'max': df['token_price'].max(),
                'current': df['token_price'].iloc[-1]
            }
        }
        
        # Calculate correlations
        correlations = {
            'energy_hash': df['energy_price'].corr(df['hash_price']),
            'energy_token': df['energy_price'].corr(df['token_price']),
            'hash_token': df['hash_price'].corr(df['token_price'])
        }
        
        return {
            'stats': stats,
            'correlations': correlations,
            'data_points': len(df),
            'period_hours': hours
        }
        
    def simulate_strategy(self, strategy='optimal', hours=24):
        """Simulate a strategy over historical data"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Check if pricing table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pricing'")
            if not cursor.fetchone():
                conn.close()
                return None
            
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            query = f"""
                SELECT * FROM pricing 
                WHERE collected_at >= '{since}'
                ORDER BY collected_at
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return None
        except Exception as e:
            print(f"Error simulating strategy: {e}")
            return None
            
        results = []
        
        for _, row in df.iterrows():
            prices = {
                'energy_price': row['energy_price'],
                'hash_price': row['hash_price'],
                'token_price': row['token_price']
            }
            
            if strategy == 'optimal':
                result = self.find_optimal_allocation(prices)
            elif strategy == 'mining_only':
                # Allocate all power to most efficient miner
                result = self._mining_only_strategy(prices)
            elif strategy == 'inference_only':
                # Allocate all power to most efficient inference
                result = self._inference_only_strategy(prices)
                
            results.append({
                'timestamp': row['timestamp'],
                'profit': result['total_profit'],
                'revenue': result['total_revenue'],
                'cost': result['total_cost'],
                'roi': result['roi_percentage']
            })
            
        return pd.DataFrame(results)
        
    def _mining_only_strategy(self, prices):
        """Strategy that only uses mining"""
        best_miner = None
        best_profit_per_watt = -float('inf')
        
        for miner_type, specs in self.inventory['miners'].items():
            revenue_per_watt = (specs['hashrate'] * prices['hash_price']) / specs['power']
            profit_per_watt = revenue_per_watt - prices['energy_price']
            
            if profit_per_watt > best_profit_per_watt:
                best_profit_per_watt = profit_per_watt
                best_miner = (miner_type, specs)
                
        if best_miner:
            units = self.site_power_limit // best_miner[1]['power']
            total_power = units * best_miner[1]['power']
            total_revenue = units * best_miner[1]['hashrate'] * prices['hash_price']
            total_cost = total_power * prices['energy_price']
            
            return {
                'total_profit': total_revenue - total_cost,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'roi_percentage': ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
            }
            
        return {'total_profit': 0, 'total_revenue': 0, 'total_cost': 0, 'roi_percentage': 0}
        
    def _inference_only_strategy(self, prices):
        """Strategy that only uses inference"""
        best_compute = None
        best_profit_per_watt = -float('inf')
        
        for compute_type, specs in self.inventory['inference'].items():
            revenue_per_watt = (specs['tokens'] * prices['token_price']) / specs['power']
            profit_per_watt = revenue_per_watt - prices['energy_price']
            
            if profit_per_watt > best_profit_per_watt:
                best_profit_per_watt = profit_per_watt
                best_compute = (compute_type, specs)
                
        if best_compute:
            units = self.site_power_limit // best_compute[1]['power']
            total_power = units * best_compute[1]['power']
            total_revenue = units * best_compute[1]['tokens'] * prices['token_price']
            total_cost = total_power * prices['energy_price']
            
            return {
                'total_profit': total_revenue - total_cost,
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'roi_percentage': ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
            }
            
        return {'total_profit': 0, 'total_revenue': 0, 'total_cost': 0, 'roi_percentage': 0}


if __name__ == "__main__":
    analyzer = ArbitrageAnalyzer()
    
    # Get current optimal allocation
    print("=== Current Optimal Allocation ===")
    optimal = analyzer.find_optimal_allocation()
    
    print(f"\nTotal Power Used: {optimal['total_power_used']:,} W")
    print(f"Total Revenue: ${optimal['total_revenue']:,.2f}")
    print(f"Total Cost: ${optimal['total_cost']:,.2f}")
    print(f"Total Profit: ${optimal['total_profit']:,.2f}")
    print(f"ROI: {optimal['roi_percentage']:.2f}%")
    
    print("\nAllocation Details:")
    for name, details in optimal['allocation'].items():
        print(f"  {name}: {details['units']} units, ${details['profit']:,.2f} profit")
        
    # Analyze price trends
    print("\n=== Price Trends (Last 24 Hours) ===")
    trends = analyzer.analyze_price_trends(24)
    if trends:
        for price_type, stats in trends['stats'].items():
            print(f"\n{price_type}:")
            print(f"  Current: ${stats['current']:.4f}")
            print(f"  Mean: ${stats['mean']:.4f}")
            print(f"  Range: ${stats['min']:.4f} - ${stats['max']:.4f}")
            
        print("\nPrice Correlations:")
        for pair, corr in trends['correlations'].items():
            print(f"  {pair}: {corr:.3f}") 