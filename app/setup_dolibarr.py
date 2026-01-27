#!/usr/bin/env python
"""
Setup script to configure Dolibarr database credentials
"""
import os
import sys

print("\n" + "="*70)
print("⚙️  DOLIBARR DATABASE CONFIGURATION SETUP")
print("="*70)

print("\nPlease provide your Dolibarr database credentials:")
print("(Press Enter to keep default values shown in brackets)\n")

db_host = input("Database Host [localhost]: ").strip() or "localhost"
db_port = input("Database Port [5432]: ").strip() or "5432"
db_name = input("Database Name [dolibarr]: ").strip() or "dolibarr"
db_user = input("Database User [postgres]: ").strip() or "postgres"
db_password = input("Database Password: ").strip()

if not db_password:
    print("❌ Password is required!")
    sys.exit(1)

# Create .env file
env_content = f"""# Dolibarr Database Configuration
DOLIBARR_DB_HOST={db_host}
DOLIBARR_DB_PORT={db_port}
DOLIBARR_DB_NAME={db_name}
DOLIBARR_DB_USER={db_user}
DOLIBARR_DB_PASSWORD={db_password}

# WMS Database Configuration (SQLite for development)
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

print("\n📝 Creating .env file...")
with open(env_path, 'w') as f:
    f.write(env_content)

print(f"✓ Configuration saved to: {env_path}")

# Test the connection
print("\n🔗 Testing connection...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Reload config with new environment
from importlib import reload
import core.config
reload(core.config)
from core.config import settings

from sqlalchemy import create_engine, text

try:
    engine = create_engine(settings.DOLIBARR_DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection SUCCESSFUL!")
        print(f"\n✨ Dolibarr is now configured and ready to use!")
except Exception as e:
    print(f"❌ Connection test failed: {e}")
    print("Please verify your credentials and try again.")
    sys.exit(1)
