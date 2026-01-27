from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import inbound, outbound, inventory, dolibarr_test
from core.database import Base, engine
import uvicorn

# Crear tablas locales (WMS)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WMS API para Dolibarr",
    description="API para gestión de almacén integrada con Dolibarr",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(inbound.router, prefix="/api/v1", tags=["Inbound"])
app.include_router(outbound.router, prefix="/api/v1", tags=["Outbound"])
app.include_router(inventory.router, prefix="/api/v1", tags=["Inventory"])
app.include_router(dolibarr_test.router, prefix="/api/v1", tags=["Dolibarr"])

@app.get("/")
def home():
    return {
        "message": "WMS API Integrada con Dolibarr ejecutándose",
        "version": "1.0.0",
        "endpoints": {
            "inbound": "/api/v1/receive",
            "outbound": "/api/v1/orders",
            "inventory": "/api/v1/check/{barcode}"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
