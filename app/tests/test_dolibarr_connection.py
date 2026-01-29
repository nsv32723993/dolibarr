#!/usr/bin/env python
"""
Diagnostic script to check Dolibarr database connectivity
"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import settings
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

print("\n" + "="*70)
print("🔍 DOLIBARR DATABASE CONNECTION DIAGNOSTIC")
print("="*70)

print("\n📋 Configuration Summary:")
print(f"  Host: {settings.DOLIBARR_DB_HOST}")
print(f"  Port: {settings.DOLIBARR_DB_PORT}")
print(f"  Database: {settings.DOLIBARR_DB_NAME}")
print(f"  User: {settings.DOLIBARR_DB_USER}")
print(f"  Connection String: {settings.DOLIBARR_DATABASE_URL}")

print("\n🔗 Attempting Database Connection...")
try:
    engine = create_engine(
        settings.DOLIBARR_DATABASE_URL,
        pool_pre_ping=True
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connection SUCCESSFUL!")
        
        # Get database information
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\n📊 Database Tables ({len(tables)} total):")
        
        # Show key Dolibarr tables
        dolibarr_tables = [t for t in tables if t.startswith('llx_')]
        print(f"  - Dolibarr tables found: {len(dolibarr_tables)}")
        
        key_tables = ['llx_societe', 'llx_product', 'llx_commande', 'llx_stock_mouvement']
        for table in key_tables:
            if table in tables:
                print(f"    ✓ {table} - EXISTS")
            else:
                print(f"    ✗ {table} - NOT FOUND")
        
        # Try to query the products table
        print("\n🏭 Checking Products Table...")
        try:
            result = conn.execute(text("SELECT COUNT(*) as count FROM llx_product WHERE entity IN (0,1) LIMIT 1"))
            count = result.fetchone()[0] if result else 0
            print(f"  ✓ Found {count} products in Dolibarr")
        except Exception as e:
            print(f"  ✗ Could not query products: {e}")
        
        # Try to query companies
        print("\n🏢 Checking Companies...")
        try:
            result = conn.execute(text("SELECT COUNT(*) as count FROM llx_societe LIMIT 1"))
            count = result.fetchone()[0] if result else 0
            print(f"  ✓ Found {count} companies in Dolibarr")
        except Exception as e:
            print(f"  ✗ Could not query companies: {e}")
            
except OperationalError as e:
    print(f"❌ Connection FAILED!")
    print(f"   Error: {e}")
    print("\n💡 Possible solutions:")
    print("   1. Check if PostgreSQL is running")
    print("   2. Verify Dolibarr database exists")
    print("   3. Check username/password credentials")
    print("   4. Verify firewall allows port 5432")
    print("   5. Check PostgreSQL is listening on localhost:5432")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✨ Diagnostic Complete")
print("="*70 + "\n")
