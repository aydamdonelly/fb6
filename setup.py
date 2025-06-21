"""
MARA Hackathon Quick Setup Script
"""

import os
import subprocess
import sys
import shutil

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} detected")

def create_virtual_env():
    """Create virtual environment if it doesn't exist"""
    if not os.path.exists('venv'):
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, '-m', 'venv', 'venv'])
        print("✅ Virtual environment created")
    else:
        print("✅ Virtual environment already exists")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    pip_cmd = 'venv\\Scripts\\pip' if sys.platform == 'win32' else 'venv/bin/pip'
    
    # Upgrade pip first
    subprocess.run([pip_cmd, 'install', '--upgrade', 'pip'])
    
    # Install requirements
    subprocess.run([pip_cmd, 'install', '-r', 'requirements.txt'])
    print("✅ Dependencies installed")

def setup_env_file():
    """Set up environment file"""
    if not os.path.exists('.env'):
        shutil.copy('env.example', '.env')
        print("📝 Created .env file from env.example")
        print("⚠️  Please edit .env file and add your API key if you have one")
    else:
        print("✅ .env file already exists")

def print_instructions():
    """Print usage instructions"""
    print("\n" + "="*50)
    print("🚀 MARA Hackathon Setup Complete!")
    print("="*50)
    
    print("\n📋 Next Steps:")
    print("\n1. Activate the virtual environment:")
    if sys.platform == 'win32':
        print("   > venv\\Scripts\\activate")
    else:
        print("   $ source venv/bin/activate")
    
    print("\n2. Create a site and get your API key (if you don't have one):")
    print("   Run the dashboard and go to Site Management tab:")
    print("   $ streamlit run dashboard.py")
    
    print("\n3. Add your API key to the .env file:")
    print("   Edit .env and replace 'your_api_key_here' with your actual key")
    
    print("\n4. Start collecting data:")
    print("   $ python data_collector.py")
    print("   (Keep this running in the background)")
    
    print("\n5. Run the dashboard:")
    print("   $ streamlit run dashboard.py")
    
    print("\n6. Analyze arbitrage opportunities:")
    print("   $ python arbitrage_analyzer.py")
    
    print("\n📊 Dashboard Features:")
    print("   - Real-time price monitoring")
    print("   - Arbitrage opportunity analysis")
    print("   - Automated allocation optimization")
    print("   - Performance tracking")
    
    print("\n💡 Tips:")
    print("   - Prices update every 5 minutes")
    print("   - The analyzer finds the optimal mix of miners and compute")
    print("   - You can apply allocations directly from the dashboard")
    print("   - Monitor correlations between prices for advanced strategies")

if __name__ == "__main__":
    print("🏁 MARA Hackathon Project Setup")
    print("="*50)
    
    check_python_version()
    create_virtual_env()
    install_dependencies()
    setup_env_file()
    print_instructions() 