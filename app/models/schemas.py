from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime
from decimal import Decimal

# --- Schemas para validación de entrada ---
class ProductRefSchema(BaseModel):
    ref: str = Field(..., min_length=1, max_length=128)
    
    @validator('ref')
    def ref_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Referencia no puede estar vacía')
        return v.strip()

class InboundReceptionSchema(ProductRefSchema):
    warehouse_id: int = Field(..., gt=0)
    qty: int = Field(..., gt=0)
    
class BarcodeSchema(BaseModel):
    barcode: str = Field(..., min_length=1, max_length=128)
    
    @validator('barcode')
    def barcode_valid(cls, v):
        if not v.strip():
            raise ValueError('Código de barras no puede estar vacío')
        # Validar formato básico (puedes ajustar según tus necesidades)
        if len(v.strip()) < 3:
            raise ValueError('Código de barras muy corto')
        return v.strip()

class StockCheckSchema(BarcodeSchema):
    pass

# --- Schemas para respuesta ---
class ProductResponse(BaseModel):
    id: int
    ref: str
    label: str
    barcode: Optional[str]
    current_stock: Optional[float] = 0
    
    class Config:
        from_attributes = True

class WarehouseStockDetail(BaseModel):
    warehouse_id: int
    warehouse_label: str
    stock: float
    location: Optional[str]
    
class StockCheckResponse(ProductResponse):
    stock_real: float
    warehouse_details: List[WarehouseStockDetail] = []
    
class OrderItemResponse(BaseModel):
    product_id: int
    product_ref: str
    qty_asked: float
    qty_available: Optional[float] = 0
    
    @validator('qty_asked')
    def validate_qty(cls, v):
        if v <= 0:
            raise ValueError('Cantidad debe ser mayor a 0')
        return v

class OrderResponse(BaseModel):
    order_id: int
    ref: str
    customer_id: Optional[int]
    order_date: Optional[datetime]
    status: int
    items: List[OrderItemResponse]
    total_items: int
    
    @property
    def status_label(self) -> str:
        status_map = {0: "Borrador", 1: "Validada", 2: "Cerrada", 3: "Cancelada"}
        return status_map.get(self.status, "Desconocido")

class MovementResponse(BaseModel):
    id: int
    dolibarr_movement_id: Optional[int]
    product_ref: str
    quantity: int
    movement_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Alias para compatibilidad
OrderItem = OrderItemResponse