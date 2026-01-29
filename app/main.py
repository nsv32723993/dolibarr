"""
Punto de entrada principal de la API WMS.
Incluye todos los routers y middleware configurados.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import uvicorn
from routers.tenant_config import router as tenant_config_router

# Importar routers existentes
from routers import inbound, outbound, inventory, dolibarr_test

# Importar nuevos routers de seguridad
from routers import auth, users, roles, audit

# Importar middleware
from middleware.audit_middleware import setup_audit_middleware

# Importar configuración de base de datos
from core.database import Base, wms_async_engine
import asyncio

# Crear aplicación FastAPI
app = FastAPI(
    title="WMS API para Dolibarr",
    description="Sistema de Gestión de Almacenes integrado con Dolibarr ERP",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Equipo de Desarrollo WMS",
        "email": "soporte@wms-dolibarr.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# ======================
# MIDDLEWARE
# ======================

# 1. HTTPS Redirect (solo en producción)
# app.add_middleware(HTTPSRedirectMiddleware)

# 2. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Request-ID"],
    max_age=3600
)

# 3. Middleware de Auditoría Automática
app = setup_audit_middleware(app)

# ======================
# ROUTERS
# ======================

# Router de Autenticación
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# Router de Usuarios
app.include_router(users.router, prefix="/api/v1", tags=["Users"])

# Router de Roles
app.include_router(roles.router, prefix="/api/v1", tags=["Roles"])

# Router de Auditoría
app.include_router(audit.router, prefix="/api/v1", tags=["Audit"])

# Routers existentes de WMS
app.include_router(inbound.router, prefix="/api/v1", tags=["Inbound"])
app.include_router(outbound.router, prefix="/api/v1", tags=["Outbound"])
app.include_router(inventory.router, prefix="/api/v1", tags=["Inventory"])
app.include_router(dolibarr_test.router, prefix="/api/v1", tags=["Dolibarr"])

# Router de Configuración del Tenant
app.include_router(tenant_config_router, prefix="/api/v1", tags=["Tenant Configuration"])

# ======================
# EVENT HANDLERS
# ======================

async def create_tables():
    """Crear tablas de base de datos al iniciar (solo desarrollo)."""
    try:
        async with wms_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Tablas de base de datos creadas/verificadas")
    except Exception as e:
        print(f"⚠️ Error creando tablas: {e}")

async def create_initial_data():
    """Crear datos iniciales del sistema."""
    try:
        from services.role_service import RoleService
        from services.user_service import UserService
        from services.tenant_service import TenantService
        from core.database import WMSAsyncSessionLocal
        
        async with WMSAsyncSessionLocal() as session:
            # 1. Crear tenant por defecto si no existe
            tenant_service = TenantService(session)
            tenant = await tenant_service.get_tenant_by_id(1)
            
            if not tenant:
                print("🔧 Creando tenant por defecto...")
                tenant = await tenant_service.create_tenant({
                    "name": "Empresa Demo",
                    "subscription_level": "premium",
                    "is_active": True
                })
            
            # 2. Crear roles por defecto (asociados al tenant)
            role_service = RoleService(session)
            print("🔧 Creando roles por defecto...")
            # Pasar tenant_id a create_default_roles para crear roles con tenant_id correcto
            await role_service.create_default_roles(tenant.id)
            
            # 3. Crear usuario admin si no existe
            user_service = UserService(session)
            admin = await user_service.get_user_by_username("admin", tenant.id)
            
            if not admin:
                print("🔧 Creando usuario administrador por defecto...")
                await user_service.create_initial_admin(tenant.id)
                print("✅ Usuario admin creado: admin / Admin123!")
            
        print("✅ Datos iniciales configurados")
    except Exception as e:
        print(f"⚠️ Error creando datos iniciales: {e}")

@app.on_event("startup")
async def startup_event():
    """Evento ejecutado al iniciar la aplicación."""
    print("🚀 Iniciando WMS API...")
    
    # Crear tablas
    await create_tables()
    
    # Crear datos iniciales
    await create_initial_data()
    
    print("✅ WMS API lista en http://localhost:8000")
    print("📚 Documentación: http://localhost:8000/docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento ejecutado al apagar la aplicación."""
    print("👋 Cerrando WMS API...")

# ======================
# ENDPOINTS BÁSICOS
# ======================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "message": "Bienvenido al Sistema de Gestión de Almacenes (WMS)",
        "version": "2.0.0",
        "status": "operational",
        "documentation": "/docs",
        "authentication_required": "JWT Bearer Token",
        "modules": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/users",
            "roles": "/api/v1/roles",
            "audit": "/api/v1/audit",
            "inbound": "/api/v1/receive",
            "outbound": "/api/v1/orders",
            "inventory": "/api/v1/inventory",
            "dolibarr_integration": "/api/v1/dolibarr"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint de health check para monitoreo."""
    import psutil
    import platform
    
    try:
        # Información del sistema
        system_info = {
            "status": "healthy",
            "timestamp": "now",
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent
        }
        
        # Verificar conexión a base de datos
        from core.database import wms_async_engine
        try:
            async with wms_async_engine.connect() as conn:
                await conn.execute("SELECT 1")
            system_info["database"] = "connected"
        except Exception as e:
            system_info["database"] = f"error: {str(e)}"
        
        return system_info
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "now"
        }

@app.get("/version", tags=["Info"])
async def get_version():
    """Obtener información de versión de la API."""
    return {
        "name": "WMS API para Dolibarr",
        "version": "2.0.0",
        "description": "Sistema de Gestión de Almacenes SaaS",
        "license": "MIT",
        "repository": "https://github.com/tu-usuario/wms-dolibarr",
        "features": [
            "Autenticación JWT",
            "Gestión Multi-Tenant",
            "Auditoría Automática",
            "Integración Dolibarr ERP",
            "Operaciones de Bodega"
        ]
    }

# ======================
# MAIN EXECUTION
# ======================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True,
        workers=1  # Para desarrollo, en producción usar más workers
    )