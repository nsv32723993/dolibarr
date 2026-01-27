from pydantic import BaseModel 
from typing import List, Optional 

# --- Modelos Comunes --- 
class ProductBase(BaseModel): 
    ref: str 
    label: str 
    barcode: Optional[str] = None 
# --- Flujo A: Inbound --- 
class InboundReception(BaseModel): 
    product_ref: str 
    warehouse_id: int 
    qty: int 
# La foto se manejará como UploadFile en el endpoint, no aquí 
# --- Flujo B: Outbound --- 
class OrderItem(BaseModel): 
    product_id: int 
    product_ref: str 
    qty_asked: int 
    qty_shipped: int = 0 
class OrderResponse(BaseModel): 
    order_id: int 
    ref: str 
    items: List[OrderItem]

class PickingConfirm(BaseModel): 
    order_id: int 
    items_scanned: List[OrderItem] # Lista final confirmada 
 
# --- Flujo C: Inventario --- 
class StockCheckResponse(ProductBase): 
    stock_real: int 
    warehouse_details: List[dict] # Desglose por almacén 