"""
MARA Hackathon Data Collector
Collects pricing data every 5 minutes and stores it in a SQLite database
"""

import requests
import sqlite3
import json
import time
import schedule
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv('API_BASE_URL', 'https://mara-hackathon-api.onrender.com')
API_KEY = os.getenv('API_KEY')

class DataCollector:
    def __init__(self, db_path='mara_data.db'):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create pricing table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pricing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                energy_price REAL,
                hash_price REAL,
                token_price REAL,
                collected_at TEXT
            )
        ''')
        
        # Create inventory table (static data)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                subtype TEXT,
                power INTEGER,
                capability INTEGER,
                collected_at TEXT
            )
        ''')
        
        # Create site status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                total_power_used INTEGER,
                total_power_cost REAL,
                total_revenue REAL,
                allocation TEXT,
                revenue_breakdown TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def fetch_prices(self):
        """Fetch current pricing data"""
        try:
            response = requests.get(f"{API_BASE_URL}/prices")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching prices: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching prices: {e}")
            return None
            
    def fetch_inventory(self):
        """Fetch inventory data (static, only needs to be called once)"""
        try:
            response = requests.get(f"{API_BASE_URL}/inventory")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching inventory: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching inventory: {e}")
            return None
            
    def fetch_site_status(self):
        """Fetch current site status"""
        if not API_KEY:
            print("No API key configured")
            return None
            
        try:
            headers = {'X-Api-Key': API_KEY}
            response = requests.get(f"{API_BASE_URL}/machines", headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching site status: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching site status: {e}")
            return None
            
    def store_prices(self, prices):
        """Store pricing data in database"""
        if not prices:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        collected_at = datetime.now().isoformat()
        
        # Store only the most recent price point
        if prices and len(prices) > 0:
            latest = prices[0]
            cursor.execute('''
                INSERT INTO pricing (timestamp, energy_price, hash_price, token_price, collected_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                latest['timestamp'],
                latest['energy_price'],
                latest['hash_price'],
                latest['token_price'],
                collected_at
            ))
            
        conn.commit()
        conn.close()
        print(f"Stored pricing data at {collected_at}")
        
    def store_inventory(self, inventory):
        """Store inventory data (only needs to be done once)"""
        if not inventory:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        collected_at = datetime.now().isoformat()
        
        # Clear existing inventory data
        cursor.execute('DELETE FROM inventory')
        
        # Store miners
        for miner_type, specs in inventory.get('miners', {}).items():
            cursor.execute('''
                INSERT INTO inventory (type, subtype, power, capability, collected_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ('miner', miner_type, specs['power'], specs['hashrate'], collected_at))
            
        # Store inference compute
        for compute_type, specs in inventory.get('inference', {}).items():
            cursor.execute('''
                INSERT INTO inventory (type, subtype, power, capability, collected_at)
                VALUES (?, ?, ?, ?, ?)
            ''', ('inference', compute_type, specs['power'], specs['tokens'], collected_at))
            
        conn.commit()
        conn.close()
        print(f"Stored inventory data at {collected_at}")
        
    def store_site_status(self, status):
        """Store site status data"""
        if not status:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # Extract allocation data
        allocation = {
            'air_miners': status.get('air_miners', 0),
            'hydro_miners': status.get('hydro_miners', 0),
            'immersion_miners': status.get('immersion_miners', 0),
            'gpu_compute': status.get('gpu_compute', 0),
            'asic_compute': status.get('asic_compute', 0)
        }
        
        cursor.execute('''
            INSERT INTO site_status (timestamp, total_power_used, total_power_cost, 
                                   total_revenue, allocation, revenue_breakdown)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            timestamp,
            status.get('total_power_used', 0),
            status.get('total_power_cost', 0),
            status.get('total_revenue', 0),
            json.dumps(allocation),
            json.dumps(status.get('revenue', {}))
        ))
        
        conn.commit()
        conn.close()
        print(f"Stored site status at {timestamp}")
        
    def collect_data(self):
        """Main data collection function"""
        print("\nCollecting data...")
        
        # Fetch and store prices
        prices = self.fetch_prices()
        self.store_prices(prices)
        
        # Fetch and store site status if API key is available
        if API_KEY:
            status = self.fetch_site_status()
            self.store_site_status(status)
            
    def run_continuous(self):
        """Run data collection continuously every 5 minutes"""
        # Collect inventory once at startup
        inventory = self.fetch_inventory()
        self.store_inventory(inventory)
        
        # Initial collection
        self.collect_data()
        
        # Schedule collection every 5 minutes
        schedule.every(5).minutes.do(self.collect_data)
        
        print("Data collector started. Collecting data every 5 minutes...")
        print("Press Ctrl+C to stop")
        
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    collector = DataCollector()
    
    # If running as main, start continuous collection
    try:
        collector.run_continuous()
    except KeyboardInterrupt:
        print("\nData collection stopped.") 