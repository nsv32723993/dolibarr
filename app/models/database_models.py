# models/database_models.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subscription_level = Column(String(50), default="basic")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Todos los modelos heredan esto
class TenantBase:
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    middleware.py
class Product(TenantBase, Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    # ... otros campos con tenant_id incluido automáticamente


# models/database_models.py
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

# routers/locations.py
@router.post("/locations/assign/{product_id}")
async def assign_location(
    product_id: int,
    quantity: int,
    assignment_strategy: str = "manual",  # "manual", "fifo", "lifo", "closest"
    tenant_id: int = Depends(get_tenant_id)
):
    if assignment_strategy == "closest":
        # Algoritmo de slotting dinámico
        location = find_closest_available_location(
            product_id, quantity, tenant_id
        )
    # ...