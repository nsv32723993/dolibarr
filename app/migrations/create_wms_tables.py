# migrations/create_wms_tables.py
from core.database import wms_engine, Base
from models.wms_models import *  # Tus modelos WMS

async def create_wms_schema():
    """Crear tablas de tu WMS local"""
    print("Creando tablas WMS...")
    async with wms_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tablas WMS creadas exitosamente")

async def create_sample_data():
    """Crear datos de prueba para MVP"""
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from core.security import get_password_hash
    
    async with AsyncSession(wms_async_engine) as session:
        # Crear tenant de prueba
        tenant = Tenant(
            name="Empresa Demo",
            subscription_level="premium",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant)
        await session.commit()
        
        # Crear roles básicos
        roles_data = [
            {"name": "admin", "description": "Administrador del sistema"},
            {"name": "operator", "description": "Operario de bodega"},
            {"name": "auditor", "description": "Auditor de procesos"}
        ]
        
        for role_data in roles_data:
            role = Role(**role_data)
            session.add(role)
        
        await session.commit()
        
        # Crear usuario admin
        admin_user = User(
            username="admin",
            email="admin@empresa.com",
            full_name="Administrador Demo",
            tenant_id=tenant.id,
            hashed_password=get_password_hash("Admin123!"),
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(admin_user)
        await session.commit()
        
        # Asignar rol admin al usuario
        stmt = select(Role).where(Role.name == "admin")
        result = await session.execute(stmt)
        admin_role = result.scalar_one()
        
        user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
        session.add(user_role)
        
        await session.commit()
        print("✅ Datos de prueba creados")

if __name__ == "__main__":
    asyncio.run(create_wms_schema())
    asyncio.run(create_sample_data())