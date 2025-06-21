# MARA Hackathon 2025 - Data Team Project

JUNE 21, 2025

FORT MASON - GALLERY 308, SAN FRANCISCO

## Project Overview

This project implements an AI-driven trading system that arbitrages between energy and inference marketplace prices to optimize compute allocation. It dynamically allocates bitcoin miners and HPC servers based on real-time market conditions to maximize profitability.

### Key Features

- **Real-time Data Collection**: Continuously monitors energy, hashrate, and token prices
- **Arbitrage Analysis**: Identifies optimal allocation strategies across mining and inference compute
- **Interactive Dashboard**: Visualizes market trends, profitability, and performance metrics
- **Automated Trading**: Can automatically apply optimal allocations via the MARA API
- **Strategy Comparison**: Compares different allocation strategies (optimal, mining-only, inference-only)

### Quick Start

1. Run the setup script:
   ```bash
   python setup.py
   ```

2. Activate the virtual environment:
   ```bash
   source venv/bin/activate  # On Mac/Linux
   venv\Scripts\activate     # On Windows
   ```

3. Run the dashboard to create a site and get your API key:
   ```bash
   streamlit run dashboard.py
   ```

4. Add your API key to the `.env` file

5. Start collecting data (keep this running):
   ```bash
   python data_collector.py
   ```

6. Open the dashboard in another terminal:
   ```bash
   streamlit run dashboard.py
   ```

### Project Structure

- `data_collector.py` - Collects pricing data every 5 minutes
- `arbitrage_analyzer.py` - Analyzes arbitrage opportunities and finds optimal allocations
- `dashboard.py` - Streamlit dashboard for visualization and control
- `setup.py` - Quick setup script
- `mara_data.db` - SQLite database storing historical data

## API

```
https://mara-hackathon-api.onrender.com
```

**NOTE**: All API response values listed in this documentation will most likely change during the event. Use these for reference purposes only. 



### Creating your site and authenticating

#### Create your mining / data center site

Create your `Site` by providing a `Name` to receive your API key (examples provided using HTTPie). You can use whatever name you or your team want, but keep it appropriate!

The most important piece of information here is the `Power` variable, this is your limiting factor in deciding on how much compute your site can offer.

```
http POST https://mara-hackathon-api.onrender.com/sites name=HackFestSite

{
    "api_key": "XXX",
    "name": "HackFestSite",
    "power": 1000000
}
```

Make **SURE** to save this API key as you will need it for future requests. If you forget it, you can always make a new site, but you will lose any progress you may have made. You can always hit the `/sites` endpoint to request information about your current site. You can make as many sites as you want, you will just have to keep track of them.

#### Authenticating

For any future authenticated requests, make you you provide your API Key in an `X-Api-Key` header.



#### Pricing and Inventory

**Pricing**

You can view current historical pricing for energy, inference, and hashrate by going to:

```
HTTP https://mara-hackathon-api.onrender.com/prices
[
    {
        "energy_price": 0.647889223893815,
        "hash_price": 8.448180236220946,
        "timestamp": "2025-06-21T13:00:00",
        "token_price": 2.91225594861526
    },
    {
        "energy_price": 0.6811324570646737,
        "hash_price": 9.255307305610396,
        "timestamp": "2025-06-21T12:55:00",
        "token_price": 2.532149968985806
    },
    {
        "energy_price": 0.6491505669853906,
        "hash_price": 8.32135884623703,
        "timestamp": "2025-06-21T12:50:00",
        "token_price": 3.0
    },
]
```

Prices are updated every 5 minutes throughout the event.

**Inventory**

You can view available inventory by going to:

```
HTTP https://mara-hackathon-api.onrender.com/inventory

{
    "inference": {
        "asic": {
            "power": 15000,
            "tokens": 50000
        },
        "gpu": {
            "power": 5000,
            "tokens": 1000
        }
    },
    "miners": {
        "air": {
            "hashrate": 1000,
            "power": 3500
        },
        "hydro": {
            "hashrate": 5000,
            "power": 5000
        },
        "immersion": {
            "hashrate": 10000,
            "power": 10000
        }
    }
}

```

This prices are static, so they won't change throughout the event. Feel free to cache them locally.


### Building, managing, and viewing your site

When you are ready to go, start by sending an allocation of machine types. **Note**, you can not exceed the maximum power available at a site

```
http PUT https://mara-hackathon-api.onrender.com/machines X-Api-Key:XXX asic_miners=10 gpu_compute=30 asic_compute=5 immersion_miners=10

{
    "air_miners": 0,
    "asic_compute": 5,
    "gpu_compute": 30,
    "hydro_miners": 0,
    "id": 5,
    "immersion_miners": 10,
    "site_id": 2,
    "updated_at": "2025-06-21T13:17:50.126193"
}

```

You can view the status of your site by making a GET request:

```
http https://mara-hackathon-api.onrender.com/machines X-Api-Key:XXX


{
    "air_miners": 0,
    "asic_compute": 5,
    "gpu_compute": 30,
    "hydro_miners": 0,
    "id": 5,
    "immersion_miners": 10,
    "power": {
        "air_miners": 0,
        "asic_compute": 75000,
        "gpu_compute": 150000,
        "hydro_miners": 0,
        "immersion_miners": 100000
    },
    "revenue": {
        "air_miners": 0.0,
        "asic_compute": 212734.43494337276,
        "gpu_compute": 25528.132193204732,
        "hydro_miners": 0.0,
        "immersion_miners": 150596.58003406858
    },
    "site_id": 0,
    "total_power_cost": 238466.35509633605,
    "total_power_used": 325000,
    "total_revenue": 388859.1471706461,
    "updated_at": "2025-06-21T13:17:50.126193"
}

```

This is updated anytime you make a site allocation modification or when underlying pricing changes.


## Feedback, Bugs, Q&A

If you have any issues with the API or notice any bugs, feel free to contact any staff at the event. If there are any API changes needed throughout the day, we will notify attendees. No downtime is expected.


### Additional Resources

**Bitcoin**
- https://mempool.space
- https://data.hashrateindex.com/network-data/bitcoin-hashprice-index

**Inference / Compute**
- https://inference.net
- https://sfcompute.com

**Grid Pricing**
- https://www.gridstatus.io