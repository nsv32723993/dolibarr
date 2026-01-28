from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import SessionLocal, get_db
from core.client_dolibarr import doli_client
from typing import Optional

# Dependencia para validar API key (si necesitas seguridad extra)
def verify_api_key(api_key: str = Depends(lambda: "dummy-key-for-now")):
    # Implementar lógica real de validación
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida"
        )
    return api_key

# Dependencia para obtener cliente Dolibarr
def get_doli_client():
    return doli_client

# Dependencia combinada para DB + Dolibarr
class Dependencies:
    def __init__(
        self,
        db: Session = Depends(get_db),
        dolibarr = Depends(get_doli_client)
    ):
        self.db = db
        self.dolibarr = dolibarr

async def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> int:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID requerido")
    return int(x_tenant_id)

async def get_tenant_db(tenant_id: int = Depends(get_tenant_id)):
    # Crear conexión específica para este tenant
    db_url = f"postgresql://user:pass@localhost/wms_tenant_{tenant_id}"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()