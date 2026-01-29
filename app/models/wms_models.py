# app/models/wms_models.py - Versión ajustada para consistencia
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, Numeric, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from datetime import datetime
from core.database import Base


# Enums para el WMS
class WarehouseStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class ZoneType(str, enum.Enum):
    RECEIVING = "receiving"
    STORAGE = "storage"
    PICKING = "picking"
    PACKING = "packing"
    SHIPPING = "shipping"
    QUARANTINE = "quarantine"
    OVERFLOW = "overflow"


class PickingStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StockMovementType(str, enum.Enum):
    RECEIPT = "receipt"
    PICKING = "picking"
    RELOCATION = "relocation"
    ADJUSTMENT = "adjustment"
    COUNT = "count"


# Base para modelos WMS con tenant_id
class WMSBase(Base):
    __abstract__ = True
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)


# 🏭 WAREHOUSE (Almacén)
class Warehouse(WMSBase):
    __tablename__ = "warehouses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text)
    address = Column(Text)
    status = Column(Enum(WarehouseStatus), default=WarehouseStatus.ACTIVE)
    is_default = Column(Boolean, default=False)
    
    # External reference to Dolibarr
    dolibarr_warehouse_id = Column(Integer, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    zones = relationship("Zone", back_populates="warehouse", cascade="all, delete-orphan")
    stock_locations = relationship("StockLocation", back_populates="warehouse")
    picking_orders = relationship("PickingOrder", back_populates="warehouse")


# 🗺️ ZONE (Zona dentro del almacén)
class Zone(WMSBase):
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, index=True)
    zone_type = Column(Enum(ZoneType), nullable=False)
    description = Column(Text)
    capacity = Column(Integer)  # Max capacity in units
    current_occupancy = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="zones")
    stock_locations = relationship("StockLocation", back_populates="zone")


# 📍 STOCK LOCATION (Ubicación física)
class StockLocation(WMSBase):
    __tablename__ = "stock_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    
    # Hierarchical location coding
    rack = Column(String(10), nullable=False)
    level = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    
    # Composite location code (e.g., A-01-02-03)
    location_code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Physical characteristics
    max_weight = Column(Numeric(10, 2))
    max_volume = Column(Numeric(10, 2))
    max_quantity = Column(Integer)
    
    # Current status
    current_quantity = Column(Integer, default=0)
    is_occupied = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(String(200))
    
    # Scanner support
    barcode = Column(String(100), unique=True, index=True)
    qr_code_data = Column(Text)  # Base64 QR code data
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="stock_locations")
    zone = relationship("Zone", back_populates="stock_locations")
    stock_entries = relationship("StockEntry", back_populates="location")


# 📦 PICKING ORDER (Orden de picking)
class PickingOrder(WMSBase):
    __tablename__ = "picking_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # External reference to Dolibarr order
    dolibarr_order_id = Column(Integer, nullable=False, index=True)
    dolibarr_order_ref = Column(String(100), nullable=False)
    
    # Picking metadata
    picking_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(Enum(PickingStatus), default=PickingStatus.PENDING)
    priority = Column(Integer, default=1)  # 1=Low, 5=High
    
    # Timing
    scheduled_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Operational info
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    assigned_to = Column(String(100), index=True)  # External user ID from Dolibarr
    
    # Totals
    total_items = Column(Integer, default=0)
    picked_items = Column(Integer, default=0)
    total_discrepancies = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    warehouse = relationship("Warehouse", back_populates="picking_orders")
    picking_items = relationship("PickingItem", back_populates="picking_order", cascade="all, delete-orphan")


# 🏷️ PICKING ITEM (Item dentro de la orden de picking)
class PickingItem(WMSBase):
    __tablename__ = "picking_items"
    
    id = Column(Integer, primary_key=True, index=True)
    picking_order_id = Column(Integer, ForeignKey("picking_orders.id"), nullable=False)
    
    # Product reference to Dolibarr
    dolibarr_product_id = Column(Integer, nullable=False, index=True)
    product_ref = Column(String(100), nullable=False)
    product_label = Column(String(200), nullable=False)
    
    # Quantities
    requested_quantity = Column(Integer, nullable=False)
    picked_quantity = Column(Integer, default=0)
    confirmed_quantity = Column(Integer, default=0)
    
    # Source locations
    source_location_id = Column(Integer, ForeignKey("stock_locations.id"), nullable=False)
    
    # Status
    is_completed = Column(Boolean, default=False)
    has_discrepancy = Column(Boolean, default=False)
    discrepancy_type = Column(String(20))  # "short", "over", "damaged"
    discrepancy_reason = Column(String(200))
    
    # Audit
    picked_by = Column(String(100))  # External user ID from Dolibarr
    picked_at = Column(DateTime, nullable=True)
    confirmed_by = Column(String(100))
    confirmed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    picking_order = relationship("PickingOrder", back_populates="picking_items")
    source_location = relationship("StockLocation")


# 📊 STOCK ENTRY (Entrada de stock por ubicación)
class StockEntry(WMSBase):
    __tablename__ = "stock_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Product reference
    dolibarr_product_id = Column(Integer, nullable=False, index=True)
    product_ref = Column(String(100), nullable=False)
    
    # Location
    location_id = Column(Integer, ForeignKey("stock_locations.id"), nullable=False)
    
    # Stock info
    quantity = Column(Integer, nullable=False)
    batch_number = Column(String(100), index=True)
    expiry_date = Column(DateTime, nullable=True)
    serial_number = Column(String(100), index=True)
    
    # Status
    is_reserved = Column(Boolean, default=False)
    reserved_for = Column(Integer, nullable=True)  # PickingItem ID
    is_blocked = Column(Boolean, default=False)
    
    # External reference
    dolibarr_stock_movement_id = Column(Integer, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location = relationship("StockLocation", back_populates="stock_entries")
    movements = relationship("StockMovement", back_populates="stock_entry", cascade="all, delete-orphan")


# 🔄 STOCK MOVEMENT (Movimiento de stock)
class StockMovement(WMSBase):
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_entry_id = Column(Integer, ForeignKey("stock_entries.id"), nullable=False)
    
    # Movement details
    movement_type = Column(Enum(StockMovementType), nullable=False)
    quantity_change = Column(Integer, nullable=False)  # Positive for receipt, negative for picking
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    
    # Source/Destination
    from_location_id = Column(Integer, ForeignKey("stock_locations.id"), nullable=True)
    to_location_id = Column(Integer, ForeignKey("stock_locations.id"), nullable=True)
    
    # Reference to operation
    reference_id = Column(Integer, nullable=True)  # PickingOrder ID or other
    reference_type = Column(String(50))
    
    # Performed by
    performed_by = Column(String(100))  # External user ID from Dolibarr
    performed_at = Column(DateTime, default=datetime.utcnow)
    
    # Notes
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock_entry = relationship("StockEntry", back_populates="movements")
    from_location = relationship("StockLocation", foreign_keys=[from_location_id])
    to_location = relationship("StockLocation", foreign_keys=[to_location_id])


# ------------------
# Modelos de seguridad y multi-tenant mínimos
# ------------------
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subscription_level = Column(String(50), default="basic")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Relación a TenantConfig
    config = relationship("TenantConfig", back_populates="tenant", uselist=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200))
    permissions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)


class User(WMSBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    full_name = Column(String(200))
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones (no foreign-key constraints explícitos aquí para simplificar)
    roles = relationship("Role", secondary="user_roles", viewonly=True)
    tenant = relationship("Tenant", primaryjoin="Tenant.id==User.tenant_id", viewonly=True)


class IntegrationLog(WMSBase):
    __tablename__ = "integration_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer, nullable=True, index=True)
    details = Column(Text)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(WMSBase):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(150), nullable=True)
    action = Column(String(150), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(Integer, nullable=True, index=True)
    details = Column(Text)
    request_path = Column(String(300), nullable=True)
    request_method = Column(String(10), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(300), nullable=True)
    status_code = Column(Integer, default=200)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)