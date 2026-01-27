# migrations/create_wms_tables.py
from core.database import wms_engine, Base
from models.wms_models import *  # Tus modelos WMS

def create_wms_schema():
    """Crear tablas de tu WMS local"""
    print("Creando tablas WMS...")
    Base.metadata.create_all(bind=wms_engine)
    print("✅ Tablas WMS creadas exitosamente")

def create_sample_data():
    """Crear datos de prueba para MVP"""
    from sqlalchemy.orm import Session
    from models.wms_models import Tenant, User, Role
    
    with Session(wms_engine) as session:
        # Crear tenant de prueba
        tenant = Tenant(
            name="Empresa Demo",
            subscription_level="premium",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant)
        session.commit()
        
        # Crear roles
        admin_role = Role(name="admin", description="Administrador del tenant")
        operator_role = Role(name="operator", description="Operario de bodega")
        session.add_all([admin_role, operator_role])
        
        # Crear usuario admin
        admin_user = User(
            username="admin",
            email="admin@empresa.com",
            full_name="Administrador Demo",
            tenant_id=tenant.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(admin_user)
        
        session.commit()
        print("✅ Datos de prueba creados")

if __name__ == "__main__":
    create_wms_schema()
    create_sample_data()