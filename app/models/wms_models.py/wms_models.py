# models/wms_models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime

# 🏢 TENANT (EMPRESA)
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subscription_level = Column(String(20), default="basic")  # basic, premium, enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Configuración por tenant
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#3B82F6")  # Hex color
    secondary_color = Column(String(7), default="#1E40AF")

# 👥 USUARIOS Y ROLES
class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    permissions = Column(Text)  # JSON con permisos

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relaciones
    tenant = relationship("Tenant", backref="users")
    roles = relationship("Role", secondary="user_roles")

class UserRole(Base):
    __tablename__ = "user_roles"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)

# 📝 AUDITORÍA
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=True)
    action = Column(String(100))  # "product_received", "order_picked"
    resource_type = Column(String(50))  # "product", "order"
    resource_id = Column(Integer)
    details = Column(Text)  # JSON con datos
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

# 📦 MOVIMIENTOS WMS
class WMSMovement(Base):
    __tablename__ = "wms_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False)
    dolibarr_movement_id = Column(Integer, nullable=True)
    product_ref = Column(String(128))
    product_label = Column(String(255))
    warehouse_id = Column(Integer)
    quantity = Column(Float)
    movement_type = Column(String(20))  # "inbound", "outbound", "transfer"
    evidence_url = Column(String(500))
    user_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)