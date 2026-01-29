# models/tenant_config.py
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base


class TenantConfig(Base):
    """
    Configuración técnica por tenant para WMS.
    Contiene parámetros operativos y de integración específicos por tenant.
    """
    __tablename__ = "tenant_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    
    # Configuración WMS
    allow_overpicking = Column(Boolean, default=False)
    allow_partial_picking = Column(Boolean, default=True)
    auto_reserve_stock = Column(Boolean, default=True)
    require_picking_confirmation = Column(Boolean, default=True)
    default_warehouse_id = Column(Integer, nullable=True)
    
    # Configuración de integración Dolibarr
    dolibarr_api_url = Column(String(500))
    dolibarr_api_key = Column(String(200))
    dolibarr_warehouse_id = Column(Integer, nullable=True)
    webhook_url = Column(String(500))  # URL para notificar a Dolibarr
    
    # Configuración de notificaciones
    notify_on_picking_complete = Column(Boolean, default=True)
    notify_on_stock_difference = Column(Boolean, default=True)
    notify_on_integration_error = Column(Boolean, default=True)
    
    # Branding técnico (para futuras UIs o emails)
    brand_name = Column(String(100))
    brand_logo_url = Column(String(500))
    brand_primary_color = Column(String(7))  # HEX color
    
    # Configuración de reintentos de integración
    max_retry_attempts = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)
    
    # Configuración de auditoría
    audit_retention_days = Column(Integer, default=90)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación inversa (opcional)
    tenant = relationship("Tenant", back_populates="config", uselist=False)