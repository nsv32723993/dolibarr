from fastapi import APIRouter, HTTPException 
from core.client_dolibarr import doli_client 
from models.schemas import StockCheckResponse 
 
router = APIRouter() 
 
@router.get("/check/{barcode}", response_model=StockCheckResponse) 
async def check_stock(barcode: str): 
    product = await doli_client.get_product_by_barcode(barcode) 
    if not product: 
        raise HTTPException(status_code=404, detail="Producto no existe") 
     
    stock_data = await doli_client.get_product_stock(product['id']) 
     
    return StockCheckResponse( 
        ref=product['ref'], 
        label=product['label'], 
        stock_real=int(stock_data.get('stock_reel', 0)), 
        warehouse_details=stock_data.get('stock_warehouses', {}) 
    )