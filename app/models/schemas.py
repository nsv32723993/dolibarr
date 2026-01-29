# Añadir al archivo existente app/models/schemas.py
from pydantic import BaseModel, Field, ConfigDict, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import re


# Enums para WMS
class WarehouseStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class ZoneType(str, Enum):
    RECEIVING = "receiving"
    STORAGE = "storage"
    PICKING = "picking"
    PACKING = "packing"
    SHIPPING = "shipping"
    QUARANTINE = "quarantine"
    OVERFLOW = "overflow"


class PickingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============ WAREHOUSE SCHEMAS ============
class WarehouseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20, pattern=r'^[A-Z0-9_-]+$')
    description: Optional[str] = None
    address: Optional[str] = None
    status: WarehouseStatus = WarehouseStatus.ACTIVE
    is_default: bool = False
    dolibarr_warehouse_id: Optional[int] = None


class WarehouseCreate(WarehouseBase):
    @validator('code')
    def validate_code(cls, v):
        if not re.match(r'^[A-Z0-9_-]+$', v):
            raise ValueError('Code must contain only uppercase letters, numbers, underscores, and hyphens')
        return v.upper()


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    address: Optional[str] = None
    status: Optional[WarehouseStatus] = None
    is_default: Optional[bool] = None


class Warehouse(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    created_at: datetime
    updated_at: datetime


# ============ ZONE SCHEMAS ============
class ZoneBase(BaseModel):
    warehouse_id: int
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20, pattern=r'^[A-Z0-9_-]+$')
    zone_type: ZoneType
    description: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=0)
    is_active: bool = True


class ZoneCreate(ZoneBase):
    @validator('code')
    def validate_code(cls, v):
        return v.upper()


class ZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class Zone(ZoneBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    current_occupancy: int
    created_at: datetime
    updated_at: datetime


# ============ STOCK LOCATION SCHEMAS ============
class StockLocationBase(BaseModel):
    warehouse_id: int
    zone_id: Optional[int] = None
    rack: str = Field(..., min_length=1, max_length=10, pattern=r'^[A-Z0-9]+$')
    level: int = Field(..., ge=1, le=99)
    position: int = Field(..., ge=1, le=999)
    location_code: str = Field(..., min_length=3, max_length=50, pattern=r'^[A-Z0-9_-]+$')
    max_weight: Optional[float] = Field(None, ge=0)
    max_volume: Optional[float] = Field(None, ge=0)
    max_quantity: Optional[int] = Field(None, ge=0)
    barcode: Optional[str] = Field(None, max_length=100)
    qr_code_data: Optional[str] = None


class StockLocationCreate(StockLocationBase):
    @validator('rack')
    def validate_rack(cls, v):
        return v.upper()
    
    @validator('location_code')
    def validate_location_code(cls, v):
        return v.upper()


class StockLocationUpdate(BaseModel):
    zone_id: Optional[int] = None
    max_weight: Optional[float] = Field(None, ge=0)
    max_volume: Optional[float] = Field(None, ge=0)
    max_quantity: Optional[int] = Field(None, ge=0)
    is_blocked: Optional[bool] = None
    block_reason: Optional[str] = Field(None, max_length=200)
    barcode: Optional[str] = Field(None, max_length=100)


class StockLocation(StockLocationBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    current_quantity: int
    is_occupied: bool
    is_blocked: bool
    block_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============ PICKING ORDER SCHEMAS ============
class PickingOrderBase(BaseModel):
    dolibarr_order_id: int = Field(..., gt=0)
    dolibarr_order_ref: str = Field(..., min_length=1, max_length=100)
    warehouse_id: int
    priority: int = Field(1, ge=1, le=5)
    scheduled_date: Optional[datetime] = None
    assigned_to: Optional[str] = Field(None, max_length=100)


class PickingOrderCreate(PickingOrderBase):
    picking_number: str = Field(..., min_length=1, max_length=50, pattern=r'^PICK-[A-Z0-9-]+$')


class PickingOrderUpdate(BaseModel):
    status: Optional[PickingStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    scheduled_date: Optional[datetime] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PickingOrder(PickingOrderBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    picking_number: str
    status: PickingStatus
    total_items: int
    picked_items: int
    total_discrepancies: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============ PICKING ITEM SCHEMAS ============
class PickingItemBase(BaseModel):
    dolibarr_product_id: int = Field(..., gt=0)
    product_ref: str = Field(..., min_length=1, max_length=100)
    product_label: str = Field(..., min_length=1, max_length=200)
    requested_quantity: int = Field(..., gt=0)
    source_location_id: int


class PickingItemCreate(PickingItemBase):
    picking_order_id: int


class PickingItemUpdate(BaseModel):
    picked_quantity: Optional[int] = Field(None, ge=0)
    confirmed_quantity: Optional[int] = Field(None, ge=0)
    is_completed: Optional[bool] = None
    has_discrepancy: Optional[bool] = None
    discrepancy_type: Optional[str] = Field(None, pattern=r'^(short|over|damaged)$')
    discrepancy_reason: Optional[str] = Field(None, max_length=200)
    picked_by: Optional[str] = Field(None, max_length=100)
    picked_at: Optional[datetime] = None
    confirmed_by: Optional[str] = Field(None, max_length=100)
    confirmed_at: Optional[datetime] = None


class PickingItem(PickingItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    picking_order_id: int
    picked_quantity: int
    confirmed_quantity: int
    is_completed: bool
    has_discrepancy: bool
    discrepancy_type: Optional[str] = None
    discrepancy_reason: Optional[str] = None
    picked_by: Optional[str] = None
    picked_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============ STOCK ENTRY SCHEMAS ============
class StockEntryBase(BaseModel):
    dolibarr_product_id: int = Field(..., gt=0)
    product_ref: str = Field(..., min_length=1, max_length=100)
    location_id: int
    quantity: int = Field(..., gt=0)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    serial_number: Optional[str] = Field(None, max_length=100)
    dolibarr_stock_movement_id: Optional[int] = None


class StockEntryCreate(StockEntryBase):
    pass


class StockEntryUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    batch_number: Optional[str] = Field(None, max_length=100)
    expiry_date: Optional[datetime] = None
    is_reserved: Optional[bool] = None
    reserved_for: Optional[int] = None
    is_blocked: Optional[bool] = None


class StockEntry(StockEntryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    is_reserved: bool
    reserved_for: Optional[int] = None
    is_blocked: bool
    created_at: datetime
    updated_at: datetime


# ============ STOCK MOVEMENT SCHEMAS ============
class StockMovementBase(BaseModel):
    stock_entry_id: int
    movement_type: str
    quantity_change: int
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    reference_id: Optional[int] = None
    reference_type: Optional[str] = Field(None, max_length=50)
    performed_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class StockMovementCreate(StockMovementBase):
    pass


class StockMovement(StockMovementBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tenant_id: int
    previous_quantity: int
    new_quantity: int
    performed_at: datetime
    created_at: datetime


# ============ RESPONSE SCHEMAS WITH RELATIONSHIPS ============
class WarehouseWithZones(Warehouse):
    zones: List[Zone] = []


class ZoneWithLocations(Zone):
    stock_locations: List[StockLocation] = []


class PickingOrderWithItems(PickingOrder):
    picking_items: List[PickingItem] = []


class StockLocationWithEntries(StockLocation):
    stock_entries: List[StockEntry] = []


# ============ OPERATIONAL SCHEMAS ============
class PickingStartRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100, description="Dolibarr user ID")


class PickingConfirmationRequest(BaseModel):
    confirmed_quantity: int = Field(..., ge=0)
    user_id: str = Field(..., min_length=1, max_length=100)
    discrepancy_type: Optional[str] = Field(None, pattern=r'^(short|over|damaged)$')
    discrepancy_reason: Optional[str] = Field(None, max_length=200)


class StockRelocationRequest(BaseModel):
    new_location_id: int
    quantity: int = Field(..., gt=0)
    user_id: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = None


class StockSearchRequest(BaseModel):
    dolibarr_product_id: Optional[int] = None
    product_ref: Optional[str] = None
    location_code: Optional[str] = None
    batch_number: Optional[str] = None
    warehouse_id: Optional[int] = None


class LocationAssignmentRequest(BaseModel):
    stock_entry_id: int
    location_id: int
    user_id: str = Field(..., min_length=1, max_length=100)


# ------- Respuesta simple para checks de stock (compatibilidad con routers/inventory)
class StockCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ref: str
    label: str
    stock_real: int
    warehouse_details: Dict[str, Any]