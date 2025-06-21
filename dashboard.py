"""
MARA Hackathon Dashboard
Interactive dashboard for monitoring and controlling the arbitrage system
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
import requests
import json
import os
from dotenv import load_dotenv
from arbitrage_analyzer import ArbitrageAnalyzer

load_dotenv()

st.set_page_config(
    page_title="MARA Arbitrage Dashboard",
    page_icon="⚡",
    layout="wide"
)

API_BASE_URL = os.getenv('API_BASE_URL', 'https://mara-hackathon-api.onrender.com')
API_KEY = os.getenv('API_KEY')

@st.cache_resource
def get_analyzer():
    return ArbitrageAnalyzer()

def load_pricing_data(hours=24):
    """Load pricing data from database"""
    try:
        conn = sqlite3.connect('mara_data.db')
        
        # Check if pricing table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pricing'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()  # Return empty dataframe
        
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        query = f"""
            SELECT * FROM pricing 
            WHERE collected_at >= '{since}'
            ORDER BY collected_at
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error loading pricing data: {e}")
        return pd.DataFrame()  # Return empty dataframe on error

def create_price_chart(df):
    """Create interactive price chart"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=('Energy Price', 'Hash Price', 'Token Price'),
        vertical_spacing=0.1
    )
    
    # Energy price
    fig.add_trace(
        go.Scatter(x=df['collected_at'], y=df['energy_price'], 
                  mode='lines', name='Energy Price', line=dict(color='red')),
        row=1, col=1
    )
    
    # Hash price
    fig.add_trace(
        go.Scatter(x=df['collected_at'], y=df['hash_price'], 
                  mode='lines', name='Hash Price', line=dict(color='orange')),
        row=2, col=1
    )
    
    # Token price
    fig.add_trace(
        go.Scatter(x=df['collected_at'], y=df['token_price'], 
                  mode='lines', name='Token Price', line=dict(color='blue')),
        row=3, col=1
    )
    
    fig.update_layout(height=800, showlegend=False)
    fig.update_xaxes(title_text="Time", row=3, col=1)
    fig.update_yaxes(title_text="$/unit", row=1, col=1)
    fig.update_yaxes(title_text="$/hash", row=2, col=1)
    fig.update_yaxes(title_text="$/token", row=3, col=1)
    
    return fig

def create_profit_comparison(analyzer):
    """Create profit comparison chart for different strategies"""
    strategies = ['optimal', 'mining_only', 'inference_only']
    profits = []
    
    for strategy in strategies:
        sim_results = analyzer.simulate_strategy(strategy, hours=24)
        if sim_results is not None and not sim_results.empty:
            profits.append({
                'Strategy': strategy.replace('_', ' ').title(),
                'Total Profit': sim_results['profit'].sum(),
                'Avg ROI %': sim_results['roi'].mean()
            })
    
    if profits:
        df = pd.DataFrame(profits)
        fig = px.bar(df, x='Strategy', y='Total Profit', 
                     title='24-Hour Profit Comparison by Strategy',
                     text='Total Profit')
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        return fig
    return None

def display_current_allocation(analyzer):
    """Display current optimal allocation"""
    optimal = analyzer.find_optimal_allocation()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Power Used", f"{optimal['total_power_used']:,} W")
    with col2:
        st.metric("Total Revenue", f"${optimal['total_revenue']:,.2f}")
    with col3:
        st.metric("Total Cost", f"${optimal['total_cost']:,.2f}")
    with col4:
        st.metric("Total Profit", f"${optimal['total_profit']:,.2f}", 
                 f"{optimal['roi_percentage']:.1f}% ROI")
    
    # Allocation breakdown
    if optimal['allocation']:
        allocation_df = []
        for name, details in optimal['allocation'].items():
            allocation_df.append({
                'Machine': name.replace('_', ' ').title(),
                'Units': details['units'],
                'Power (W)': details['power_used'],
                'Revenue': f"${details['revenue']:,.2f}",
                'Cost': f"${details['cost']:,.2f}",
                'Profit': f"${details['profit']:,.2f}"
            })
        
        st.dataframe(pd.DataFrame(allocation_df), use_container_width=True)

def create_site_interface():
    """Interface for creating and managing sites"""
    st.header("Site Management")
    
    if not API_KEY:
        with st.form("create_site"):
            site_name = st.text_input("Site Name", value="DataTeamSite")
            submit = st.form_submit_button("Create Site")
            
            if submit and site_name:
                response = requests.post(
                    f"{API_BASE_URL}/sites",
                    json={"name": site_name}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Site created! API Key: {data['api_key']}")
                    st.info("Please save this API key in your .env file as API_KEY")
                else:
                    st.error(f"Error creating site: {response.text}")
    else:
        # Show current site info
        headers = {'X-Api-Key': API_KEY}
        response = requests.get(f"{API_BASE_URL}/sites", headers=headers)
        
        if response.status_code == 200:
            site_data = response.json()
            st.info(f"Current Site: {site_data.get('name', 'Unknown')} | Power Limit: {site_data.get('power', 0):,} W")

def apply_allocation(analyzer, allocation):
    """Apply the suggested allocation to the API"""
    headers = {'X-Api-Key': API_KEY}
    
    # Convert allocation to API format
    api_allocation = {
        'air_miners': 0,
        'hydro_miners': 0,
        'immersion_miners': 0,
        'gpu_compute': 0,
        'asic_compute': 0
    }
    
    for name, details in allocation.items():
        if 'air_miner' in name:
            api_allocation['air_miners'] = details['units']
        elif 'hydro_miner' in name:
            api_allocation['hydro_miners'] = details['units']
        elif 'immersion_miner' in name:
            api_allocation['immersion_miners'] = details['units']
        elif 'gpu_inference' in name:
            api_allocation['gpu_compute'] = details['units']
        elif 'asic_inference' in name:
            api_allocation['asic_compute'] = details['units']
    
    response = requests.put(
        f"{API_BASE_URL}/machines",
        headers=headers,
        json=api_allocation
    )
    
    return response

def main():
    st.title("⚡ MARA Hackathon Arbitrage Dashboard")
    st.markdown("Real-time monitoring and optimization of compute allocation across energy, mining, and inference markets")
    
    analyzer = get_analyzer()
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        time_range = st.slider("Time Range (hours)", 1, 48, 24)
        refresh_rate = st.selectbox("Refresh Rate", ["Manual", "30s", "1m", "5m"])
        
        if refresh_rate != "Manual":
            st.info(f"Auto-refresh every {refresh_rate}")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Data", "💰 Arbitrage Analysis", "🏭 Site Management", "📈 Performance"])
    
    with tab1:
        st.header("Market Prices")
        
        # Load and display price data
        df = load_pricing_data(time_range)
        
        if not df.empty:
            # Current prices
            latest = df.iloc[-1]
            col1, col2, col3 = st.columns(3)
            
            with col1:
                delta = ((latest['energy_price'] - df.iloc[0]['energy_price']) / df.iloc[0]['energy_price'] * 100)
                st.metric("Energy Price", f"${latest['energy_price']:.4f}", f"{delta:.2f}%")
            
            with col2:
                delta = ((latest['hash_price'] - df.iloc[0]['hash_price']) / df.iloc[0]['hash_price'] * 100)
                st.metric("Hash Price", f"${latest['hash_price']:.4f}", f"{delta:.2f}%")
            
            with col3:
                delta = ((latest['token_price'] - df.iloc[0]['token_price']) / df.iloc[0]['token_price'] * 100)
                st.metric("Token Price", f"${latest['token_price']:.4f}", f"{delta:.2f}%")
            
            # Price chart
            st.plotly_chart(create_price_chart(df), use_container_width=True)
            
            # Price statistics
            st.subheader("Price Statistics")
            trends = analyzer.analyze_price_trends(time_range)
            if trends:
                stats_df = pd.DataFrame(trends['stats']).T
                st.dataframe(stats_df.round(4), use_container_width=True)
                
                # Correlations
                st.subheader("Price Correlations")
                corr_df = pd.DataFrame([trends['correlations']])
                st.dataframe(corr_df.round(3), use_container_width=True)
        else:
            st.warning("No pricing data available. Run data_collector.py to start collecting data.")
    
    with tab2:
        st.header("Arbitrage Opportunities")
        
        # Current optimal allocation
        st.subheader("Current Optimal Allocation")
        display_current_allocation(analyzer)
        
        # Apply allocation button
        if API_KEY:
            if st.button("Apply Optimal Allocation", type="primary"):
                optimal = analyzer.find_optimal_allocation()
                response = apply_allocation(analyzer, optimal['allocation'])
                
                if response.status_code == 200:
                    st.success("Allocation applied successfully!")
                    st.json(response.json())
                else:
                    st.error(f"Error applying allocation: {response.text}")
        
        # Strategy comparison
        st.subheader("Strategy Comparison")
        comparison_fig = create_profit_comparison(analyzer)
        if comparison_fig:
            st.plotly_chart(comparison_fig, use_container_width=True)
    
    with tab3:
        create_site_interface()
        
        if API_KEY:
            st.subheader("Current Allocation")
            
            # Fetch current allocation
            headers = {'X-Api-Key': API_KEY}
            response = requests.get(f"{API_BASE_URL}/machines", headers=headers)
            
            if response.status_code == 200:
                current = response.json()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total Power Used", f"{current.get('total_power_used', 0):,} W")
                    st.metric("Total Revenue", f"${current.get('total_revenue', 0):,.2f}")
                
                with col2:
                    st.metric("Total Power Cost", f"${current.get('total_power_cost', 0):,.2f}")
                    profit = current.get('total_revenue', 0) - current.get('total_power_cost', 0)
                    st.metric("Net Profit", f"${profit:,.2f}")
                
                # Show allocation details
                st.subheader("Machine Allocation")
                allocation_data = {
                    'Air Miners': current.get('air_miners', 0),
                    'Hydro Miners': current.get('hydro_miners', 0),
                    'Immersion Miners': current.get('immersion_miners', 0),
                    'GPU Compute': current.get('gpu_compute', 0),
                    'ASIC Compute': current.get('asic_compute', 0)
                }
                
                fig = px.bar(x=list(allocation_data.keys()), y=list(allocation_data.values()),
                            title="Current Machine Allocation")
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.header("Performance Metrics")
        
        # Load site status history
        conn = sqlite3.connect('mara_data.db')
        query = f"""
            SELECT * FROM site_status 
            WHERE timestamp >= datetime('now', '-{time_range} hours')
            ORDER BY timestamp
        """
        status_df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not status_df.empty:
            # Profit over time
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=status_df['timestamp'],
                y=status_df['total_revenue'] - status_df['total_power_cost'],
                mode='lines',
                name='Profit',
                fill='tozeroy'
            ))
            fig.update_layout(title="Profit Over Time", xaxis_title="Time", yaxis_title="Profit ($)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Performance summary
            total_revenue = status_df['total_revenue'].sum()
            total_cost = status_df['total_power_cost'].sum()
            total_profit = total_revenue - total_cost
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Revenue", f"${total_revenue:,.2f}")
            with col2:
                st.metric("Total Cost", f"${total_cost:,.2f}")
            with col3:
                st.metric("Total Profit", f"${total_profit:,.2f}")
        else:
            st.info("No performance data available yet. Make sure the data collector is running.")

if __name__ == "__main__":
    main() 