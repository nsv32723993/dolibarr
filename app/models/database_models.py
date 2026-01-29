# models/database_models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from datetime import datetime
from core.database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subscription_level = Column(String(50), default="basic")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Location(Base):
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False)
    code = Column(String(50), unique=True)  # "A-01-02-03"
    zone = Column(String(50))  # "Recepcion", "Picking", "Almacenaje"
    type = Column(String(50))  # "estanteria", "suelo", "caja"
    capacity = Column(Float)  # Capacidad en unidades o volumen
    current_occupancy = Column(Float, default=0)
    is_available = Column(Boolean, default=True)