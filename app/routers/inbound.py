# routers/inbound.py - VERSIÓN CON SQLALCHEMY DIRECTO
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from services.dolibarr_service import DolibarrService
from core.database import get_dolibarr_db, get_wms_db
import shutil
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/receive")
async def receive_goods(
    product_ref: str = Form(...),
    warehouse_id: int = Form(...),
    qty: float = Form(...),  # Cambiado a float para Dolibarr
    evidence: UploadFile = File(...),
    dolibarr_db: Session = Depends(get_dolibarr_db),
    wms_db: Session = Depends(get_wms_db)
):
    # 1. Buscar producto directamente en Dolibarr
    dolibarr_service = DolibarrService(dolibarr_db)
    
    # Intentar por referencia
    product = dolibarr_service.get_product_by_ref(product_ref)
    
    # Si no, intentar por código de barras
    if not product:
        product = dolibarr_service.get_product_by_barcode(product_ref)
    
    if not product:
        raise HTTPException(
            status_code=404, 
            detail=f"Producto '{product_ref}' no encontrado en Dolibarr"
        )
    
    # 2. Guardar evidencia
    file_extension = evidence.filename.split('.')[-1] if '.' in evidence.filename else 'jpg'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_location = f"evidence/tenant_1/{unique_filename}"  # TODO: multi-tenant
    
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(evidence.file, buffer)
    
    # 3. Crear movimiento en Dolibarr (CAUTELA)
    movement_success = dolibarr_service.create_stock_movement(
        product_id=product.rowid,
        warehouse_id=warehouse_id,
        quantity=qty,
        label=f"Recepción WMS - {evidence.filename}",
        user_id=1  # TODO: obtener de autenticación
    )
    
    if not movement_success:
        raise HTTPException(
            status_code=500,
            detail="Error al registrar movimiento en Dolibarr"
        )
    
    # 4. Registrar en WMS local
    # TODO: Crear modelo WMSMovement y guardar aquí
    
    return {
        "status": "success",
        "product_id": product.rowid,
        "product_ref": product.ref,
        "product_label": product.label,
        "quantity": qty,
        "warehouse_id": warehouse_id,
        "evidence_path": file_location,
        "dolibarr_updated": True
    }

@router.get("/product/{product_ref}/stock")
async def get_product_stock(
    product_ref: str,
    dolibarr_db: Session = Depends(get_dolibarr_db)
):
    """Consulta directa de stock desde Dolibarr"""
    service = DolibarrService(dolibarr_db)
    
    product = service.get_product_by_ref(product_ref)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    stock_details = service.get_product_stock(product.rowid)
    total_stock = service.get_total_stock(product.rowid)
    
    return {
        "product": {
            "id": product.rowid,
            "ref": product.ref,
            "label": product.label,
            "barcode": product.barcode,
            "price": float(product.price) if product.price else 0.0
        },
        "total_stock": total_stock,
        "stock_by_warehouse": stock_details
    }
