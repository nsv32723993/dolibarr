from fastapi import APIRouter, UploadFile, File, Form, HTTPException 
from core.client_dolibarr import doli_client # Sin el "app." delante
# from app.core.database import db_session (Asumiremos conexión lista) 
import shutil 
 
router = APIRouter() 
 
@router.post("/receive") 
async def receive_goods( 
    product_ref: str = Form(...), 
    warehouse_id: int = Form(...), 
    qty: int = Form(...), 
    evidence: UploadFile = File(...) 
): 
    # 1. Validar producto en Dolibarr 
    product = await doli_client.get_product_by_barcode(product_ref) 
    if not product: 
        raise HTTPException(status_code=404, detail="Producto no encontrado") 
     
    # 2. Subir Evidencia (Simulado localmente, aquí iría código S3/MinIO) 
    file_location = f"evidence_files/{evidence.filename}" 
    with open(file_location, "wb") as buffer: 
        shutil.copyfileobj(evidence.file, buffer) 
     
    # 3. Impactar Stock en Dolibarr 
    movement_id = await doli_client.create_stock_movement( 
        product_id=product['id'], 
        warehouse_id=warehouse_id, 
        qty=qty, 
        label=f"Recepción WMS - {evidence.filename}" 
    ) 
     
    # 4. Guardar relación en Postgres Local (Pseudocódigo SQLAlchemy) 
    # new_evidence = Evidence(dolibarr_movement_id=movement_id, url=file_location) 
    # db.add(new_evidence); db.commit() 
     
    return {"status": "ok", "movement_id": movement_id, "evidence_saved": True}