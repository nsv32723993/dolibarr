#!/usr/bin/env python
"""
Auto-detect and try common PostgreSQL configurations
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

print("\n" + "="*70)
print("🔍 AUTO-DETECTING POSTGRESQL CONFIGURATION")
print("="*70)

# Try different password combinations
configs = [
    {"user": "postgres", "password": ""},
    {"user": "postgres", "password": "postgres"},
    {"user": "postgres", "password": "password"},
    {"user": "postgres", "password": "dolibarr"},
    {"user": "dolibarr", "password": "dolibarr"},
]

success_config = None

for i, config in enumerate(configs, 1):
    user = config["user"]
    password = config["password"]
    pwd_str = f"'{password}'" if password else "NO PASSWORD"
    
    print(f"\n[{i}] Trying: user={user}, password={pwd_str}")
    
    conn_string = f"postgresql://{user}"
    if password:
        conn_string += f":{password}"
    conn_string += "@localhost:5432/dolibarr"
    
    try:
        engine = create_engine(conn_string, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"    ✅ SUCCESS!")
            success_config = config
            break
    except OperationalError as e:
        if "password authentication failed" in str(e):
            print(f"    ✗ Authentication failed")
        elif "does not exist" in str(e):
            print(f"    ✗ User does not exist")
        else:
            print(f"    ✗ Connection failed: {str(e)[:60]}")
    except Exception as e:
        print(f"    ✗ Error: {str(e)[:60]}")

if success_config:
    print("\n" + "="*70)
    print(f"✨ FOUND WORKING CONFIGURATION!")
    print("="*70)
    print(f"  User: {success_config['user']}")
    print(f"  Password: {'(empty)' if not success_config['password'] else success_config['password']}")
    
    # Create .env file with working credentials
    env_content = f"""# Dolibarr Database Configuration (Auto-detected)
DOLIBARR_DB_HOST=localhost
DOLIBARR_DB_PORT=5432
DOLIBARR_DB_NAME=dolibarr
DOLIBARR_DB_USER={success_config['user']}
DOLIBARR_DB_PASSWORD={success_config['password']}

# WMS Database Configuration
WMS_DB_HOST=localhost
WMS_DB_PORT=5433
WMS_DB_NAME=wms_saas
WMS_DB_USER=wms_user
WMS_DB_PASSWORD=wms_password

# Dolibarr API Configuration
DOLIBARR_API_KEY=GrK4KrV8pnWe5YT0j1rPsgmLt9449F4T
DOLIBARR_API_URL=http://localhost/dolibarr/api/index.php
"""
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_path, 'w') as f:
        f.write(env_content)
    print(f"\n  ✓ Saved to: .env")
    
else:
    print("\n" + "="*70)
    print("❌ NO WORKING CONFIGURATION FOUND")
    print("="*70)
    print("\n💡 Please check:")
    print("  1. PostgreSQL is running: pg_ctl status")
    print("  2. Database 'dolibarr' exists")
    print("  3. User credentials are correct")
    print("  4. Run 'python setup_dolibarr.py' for manual configuration")
    sys.exit(1)
