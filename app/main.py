from fastapi import FastAPI
# Quita el "app." porque estás en la raíz
from routers import inbound, outbound, inventory # Sin el "app." delante

app = FastAPI(title="WMS API para Dolibarr")

app.include_router(inbound.router)
app.include_router(outbound.router)
app.include_router(inventory.router)

@app.get("/")
def home():
    return {"message": "WMS API Integrada con Dolibarr ejecutándose"}