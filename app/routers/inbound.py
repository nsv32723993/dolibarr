# app/routers/inbound.py
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.db import get_db, InboundAuditModel  # Tu modelo local de Postgres
from app.core.dolibarr_client import DolibarrConnect

router = APIRouter()
dolibarr = DolibarrConnect()

@router.post("/receive")
async def receive_items(
    ref_producto: str, 
    cantidad: int, 
    id_almacen: int, 
    foto: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validar existencia en Dolibarr
    prod = dolibarr.get_product_by_ref(ref_producto)
    if not prod:
        return {"error": "Producto no existe en ERP"}

    # 2. Subir Foto (Simulado aquí, usarías boto3 o minio client)
    foto_url = f"https://minio.miwms.com/evidence/{foto.filename}" 
    
    # 3. Guardar Auditoría en TU Postgres (Lo que Dolibarr no tiene)
    audit_entry = InboundAuditModel(
        product_ref=ref_producto,
        qty=cantidad,
        evidence_url=foto_url,
        operator_id=1  # Del token JWT
    )
    db.add(audit_entry)
    db.commit()

    # 4. Impactar Dolibarr (Fuente de verdad financiera)
    dolibarr.create_stock_movement(
        product_id=prod['id'], 
        warehouse_id=id_almacen, 
        qty=cantidad, 
        label=f"Ingreso WMS - Ver evidencia: {foto_url}"
    )

    return {"status": "ok", "evidence": foto_url}