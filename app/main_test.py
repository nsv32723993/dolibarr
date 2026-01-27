from fastapi import FastAPI

app = FastAPI(
    title="WMS API para Dolibarr - TEST",
    description="API para gestión de almacén integrada con Dolibarr",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "WMS API Integrada con Dolibarr ejecutándose",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_test:app", host="127.0.0.1", port=8000)
