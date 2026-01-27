"""
Test router to verify Dolibarr database connectivity
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.database import get_dolibarr_db

router = APIRouter()

@router.get("/dolibarr/test-connection")
def test_dolibarr_connection(db: Session = Depends(get_dolibarr_db)):
    """Test Dolibarr database connection"""
    try:
        # Simple query to test connection
        result = db.execute(text("SELECT 1 as test"))
        db.commit()
        return {
            "status": "connected",
            "message": "Successfully connected to Dolibarr database",
            "database": "dolibarr"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dolibarr connection failed: {str(e)}")

@router.get("/dolibarr/info")
def get_dolibarr_info(db: Session = Depends(get_dolibarr_db)):
    """Get basic Dolibarr database info"""
    try:
        # Count products
        prod_query = text("SELECT COUNT(*) as count FROM llx_product WHERE tosell=1")
        prod_result = db.execute(prod_query)
        prod_count = prod_result.scalar() or 0
        
        # Count companies
        comp_query = text("SELECT COUNT(*) as count FROM llx_societe")
        comp_result = db.execute(comp_query)
        comp_count = comp_result.scalar() or 0
        
        # Count orders
        order_query = text("SELECT COUNT(*) as count FROM llx_commande")
        order_result = db.execute(order_query)
        order_count = order_result.scalar() or 0
        
        return {
            "status": "success",
            "data": {
                "products": int(prod_count),
                "companies": int(comp_count),
                "orders": int(order_count)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
