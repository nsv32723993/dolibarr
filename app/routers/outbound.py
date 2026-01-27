from fastapi import APIRouter
from pydantic import BaseModel 
from core.client_dolibarr import doli_client 
from typing import List
from models.schemas import OrderResponse, OrderItem 
 
router = APIRouter() 

class OrderResponse(BaseModel):
    id: int
    ref: str
    status: str
 
@router.get("/orders", response_model=List[OrderResponse]) 
async def get_orders_to_pick(): 
    raw_orders = await doli_client.get_pending_orders() 
    clean_orders = [] 
     
    # Transformamos el JSON sucio de Dolibarr a nuestro Schema limpio 
    for o in raw_orders: 
        lines = await doli_client.get_order_lines(o['id']) 
        items = [ 
            OrderItem( 
                product_id=int(l['fk_product']), 
                product_ref=l['product_ref'], 
                qty_asked=int(float(l['qty'])) 
            ) for l in lines 
        ] 
        clean_orders.append(OrderResponse(order_id=int(o['id']), ref=o['ref'], items=items)) 
         
    return clean_orders 
 
@router.post("/orders/{order_id}/close") 
async def finish_picking(order_id: int): 
    # En el MVP, asumimos que si llama a cerrar, todo fue pickeado. 
    # Se crea el envío (Shipment) en Dolibarr y se valida. 
    shipment_id = await doli_client.create_shipment_from_order(order_id, warehouse_id=1) 
     
    # Opcional: Validar el envío automáticamente para descontar stock 
    return {"status": "shipped", "dolibarr_shipment_id": shipment_id}