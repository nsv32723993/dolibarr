from sqlalchemy import text
from core.database import get_dolibarr_db

print("[*] Testing connection...")

try:
    db_gen = get_dolibarr_db()
    db = next(db_gen)
    print("[*] Session created")
    
    result = db.execute(text("SELECT 1"))
    print("[*] Executed query")
    
    print("✅ Connection works!")
    db.close()
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
