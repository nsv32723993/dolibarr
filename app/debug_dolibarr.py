#!/usr/bin/env python
"""
Debug script to test Dolibarr endpoint directly
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from core.database import get_dolibarr_db
from services.dolibarr_service import DolibarrService

print("Testing direct database access...")

try:
    # Get database session
    db_gen = get_dolibarr_db()
    db = next(db_gen)
    
    print("✓ Database session created")
    
    # Create service
    service = DolibarrService(db)
    print("✓ Service created")
    
    # Test getting products
    products = service.get_products(limit=1)
    print(f"✓ Got {len(products)} products")
    print(f"  Products: {products}")
    
    # Clean up
    db.close()
    
    print("\n✅ All direct tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
