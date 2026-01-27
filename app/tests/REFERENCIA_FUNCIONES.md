# 🔧 REFERENCIA COMPLETA - FUNCIONES Y MÉTODOS

## 📍 main.py - Punto de Entrada

### Función 1: Crear aplicación FastAPI

```python
app = FastAPI(
    title="WMS API para Dolibarr",
    description="API para gestión de almacén integrada con Dolibarr",
    version="1.0.0"
)
```

**Propósito:** Crear la instancia principal de la aplicación  
**Parámetros:**
- `title`: Nombre en documentación Swagger
- `description`: Descripción del API
- `version`: Versión del API

**Resultado:** Objeto FastAPI listo para recibir requests

---

### Función 2: Configurar CORS (Seguridad)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Propósito:** Permitir requests desde otros dominios  
**Parámetros:**
- `allow_origins=["*"]`: Permite cualquier origen (⚠️ EN PROD: especifica dominios)
- `allow_credentials=True`: Permite cookies/tokens
- `allow_methods=["*"]`: Permite GET, POST, PUT, DELETE, etc.
- `allow_headers=["*"]`: Permite cualquier header

**Por qué:** Sin CORS, navegadores bloquerían requests desde otros dominios

---

### Función 3: Registrar routers

```python
app.include_router(inbound.router, prefix="/api/v1", tags=["Inbound"])
app.include_router(outbound.router, prefix="/api/v1", tags=["Outbound"])
app.include_router(inventory.router, prefix="/api/v1", tags=["Inventory"])
app.include_router(dolibarr_test.router, prefix="/api/v1", tags=["Dolibarr"])
```

**Propósito:** Montar todos los routers bajo `/api/v1`  
**Parámetros:**
- `prefix="/api/v1"`: Prefijo de URL (ej: `/api/v1/receive`)
- `tags=["Inbound"]`: Agrupa endpoints en Swagger UI

**Ejemplo de resultado:**
```
POST /api/v1/receive (de inbound.py)
GET /api/v1/orders (de outbound.py)
GET /api/v1/check/{barcode} (de inventory.py)
```

---

### Función 4: Crear tablas locales (WMS)

```python
Base.metadata.create_all(bind=engine)
```

**Propósito:** Crear tablas en BD WMS si no existen  
**Parámetro:**
- `bind=engine`: Motor SQLAlchemy de WMS

**Lo que hace:**
- Lee todas las clases `Base` de `models/database_models.py`
- Crea las tablas correspondientes si no existen
- Idempotente (ejecutar múltiples veces no causa error)

---

### Función 5: Endpoint de salud

```python
@app.get("/")
def home():
    return {
        "message": "WMS API Integrada con Dolibarr ejecutándose",
        "version": "1.0.0",
        "endpoints": {...}
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "connected"}
```

**Propósito:** 
- `/` - Punto de entrada, documentación de endpoints
- `/health` - Health check para monitoreo

**Respuestas:**
```json
GET / → {"message": "...", "endpoints": {...}}
GET /health → {"status": "healthy"}
```

---

## 🔑 core/config.py - Configuración

### Clase: Settings

```python
class Settings(BaseSettings):
    DOLIBARR_DB_HOST: str = "localhost"
    DOLIBARR_DB_PORT: str = "5432"
    DOLIBARR_DB_NAME: str = "dolibarr"
    DOLIBARR_DB_USER: str = "postgres"
    DOLIBARR_DB_PASSWORD: str = "tu_password"
```

**Propósito:** Centralizar todas las configuraciones  
**Patrón:** Pydantic BaseSettings (soporta .env)

**Ejemplo de .env:**
```
DOLIBARR_DB_HOST=localhost
DOLIBARR_DB_USER=dolibarr
DOLIBARR_DB_PASSWORD=micontraseña
```

### Propiedad: DOLIBARR_DATABASE_URL

```python
@property
def DOLIBARR_DATABASE_URL(self) -> str:
    return (
        f"postgresql://{self.DOLIBARR_DB_USER}:{self.DOLIBARR_DB_PASSWORD}"
        f"@{self.DOLIBARR_DB_HOST}:{self.DOLIBARR_DB_PORT}/{self.DOLIBARR_DB_NAME}"
    )
```

**Propósito:** Construir URL de conexión PostgreSQL  
**Resultado ejemplo:**
```
postgresql://dolibarr:micontraseña@localhost:5432/dolibarr
```

---

## 🔌 core/database.py - Conexiones a BD

### Objeto: dolibarr_engine

```python
dolibarr_engine = create_engine(
    settings.DOLIBARR_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    echo=False
)
```

**Propósito:** Motor de BD para Dolibarr (solo lectura)  
**Parámetros:**
- `pool_pre_ping=True`: Verifica conexión antes de usar
- `pool_recycle=300`: Recicla conexiones cada 300s
- `pool_size=5`: 5 conexiones simultáneas
- `max_overflow=10`: Hasta 10 conexiones adicionales si necesita
- `echo=False`: No loguea SQL (False en prod)

**Por qué pool_size=5:** Solo lectura, no necesita muchas conexiones

---

### Función: get_dolibarr_db()

```python
def get_dolibarr_db():
    """Dependencia para sesión de solo lectura a Dolibarr"""
    db = DolibarrSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Propósito:** Factory para crear sesiones (FastAPI Dependency)  
**Patrón:** Context manager (yield automáticamente cierra)

**Uso en routers:**
```python
@router.get("/products")
def get_products(db: Session = Depends(get_dolibarr_db)):
    # db es una sesión lista para usar
    products = db.query(LlxProduct).all()
    # Al salir, db.close() se ejecuta automáticamente
```

---

### Objeto: wms_engine

```python
wms_engine = create_engine(
    settings.WMS_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
```

**Propósito:** Motor de BD para WMS (lectura/escritura)  
**Diferencias con dolibarr_engine:**
- `pool_size=10` (vs 5): Más conexiones simultáneas
- `max_overflow=20` (vs 10): Permite más desborde
- SQLite específico: `check_same_thread=False`

**Por qué pool_size=10:** Escrituras son más lentas, necesita buffer

---

## 📦 routers/inbound.py - Recepción

### Endpoint: POST /api/v1/receive

```python
@router.post("/receive")
async def receive_goods(
    product_ref: str = Form(...),
    warehouse_id: int = Form(...),
    qty: float = Form(...),
    evidence: UploadFile = File(...),
    dolibarr_db: Session = Depends(get_dolibarr_db),
    wms_db: Session = Depends(get_wms_db)
):
```

**Propósito:** Recibir mercadería en almacén  
**Parámetros:**
- `product_ref`: Referencia del producto (ej: "PROD001")
- `warehouse_id`: ID del almacén (ej: 1)
- `qty`: Cantidad recibida (ej: 100.5)
- `evidence`: Foto o documento de prueba
- `dolibarr_db`: Sesión inyectada para consultar Dolibarr
- `wms_db`: Sesión inyectada para guardar en WMS

**Flujo:**
```python
1. Buscar producto en Dolibarr:
   product = dolibarr_service.get_product_by_ref(product_ref)
   
2. Validar que existe:
   if not product:
       raise HTTPException(404, "Producto no encontrado")
   
3. Guardar evidencia (foto):
   unique_filename = f"{uuid.uuid4()}.jpg"
   with open(f"evidence/tenant_1/{unique_filename}", "wb") as f:
       f.write(evidence.file)
   
4. Crear movimiento en Dolibarr:
   service.create_stock_movement(
       product_id=product.rowid,
       warehouse_id=warehouse_id,
       quantity=qty
   )
   
5. Retornar respuesta:
   return {
       "status": "success",
       "product_id": product.rowid,
       "quantity": qty
   }
```

---

## 📋 routers/outbound.py - Picking y Envío

### Endpoint: GET /api/v1/orders

```python
@router.get("/orders", response_model=List[OrderResponse])
async def get_orders_to_pick():
```

**Propósito:** Obtener órdenes listas para picking  
**Respuesta:** Lista de `OrderResponse` (Pydantic schema)

**Respuesta ejemplo:**
```json
[
  {
    "order_id": 456,
    "ref": "CMD-001",
    "items": [
      {
        "product_id": 123,
        "product_ref": "PROD001",
        "qty_asked": 50
      }
    ]
  }
]
```

**Flujo:**
```python
1. Obtener órdenes validadas:
   raw_orders = dolibarr_service.get_pending_orders()
   
2. Para cada orden, obtener líneas:
   for order in raw_orders:
       lines = dolibarr_service.get_order_lines(order.id)
       
3. Transformar a OrderItem:
       items = [OrderItem(...) for line in lines]
       
4. Retornar lista formateada
```

---

### Endpoint: POST /api/v1/orders/{order_id}/close

```python
@router.post("/orders/{order_id}/close")
async def finish_picking(order_id: int):
```

**Propósito:** Crear envío y descontar stock  
**Parámetro:** `order_id` (ej: 456)

**Lo que hace:**
```python
1. Crea envío (shipment) en Dolibarr:
   shipment_id = dolibarr_service.create_shipment_from_order(order_id)
   
2. Valida automáticamente (opcional):
   dolibarr_service.validate_shipment(shipment_id)
   
3. Stock se descuenta automáticamente
   
4. Retorna:
   {
       "status": "shipped",
       "shipment_id": 789
   }
```

---

## 🔍 routers/inventory.py - Chequeo de Stock

### Endpoint: GET /api/v1/check/{barcode}

```python
@router.get("/check/{barcode}", response_model=StockCheckResponse)
async def check_stock(barcode: str):
```

**Propósito:** Verificar stock de un producto por código de barras  
**Parámetro:** `barcode` (ej: "7891234567890")

**Respuesta:**
```json
{
  "ref": "PROD001",
  "label": "Producto A",
  "stock_real": 150,
  "warehouse_details": [
    {
      "warehouse": "Almacén A",
      "stock": 80
    },
    {
      "warehouse": "Almacén B",
      "stock": 70
    }
  ]
}
```

**Flujo:**
```python
1. Buscar producto por barcode:
   product = dolibarr_service.get_product_by_barcode(barcode)
   
2. Validar que existe:
   if not product:
       raise HTTPException(404, "Producto no existe")
   
3. Obtener stock por almacén:
   stock_data = dolibarr_service.get_product_stock(product.id)
   
4. Transformar a respuesta:
   return StockCheckResponse(
       ref=product.ref,
       label=product.label,
       stock_real=sum de stocks,
       warehouse_details=[...]
   )
```

---

## 🔧 services/dolibarr_service.py - Lógica de Negocio

### Clase: DolibarrService

```python
class DolibarrService:
    def __init__(self, db: Session):
        self.db = db  # Sesión inyectada
```

**Propósito:** Centralizar todas las queries a Dolibarr  
**Patrón:** Inyección de dependencias (db como parámetro)

---

### Método: get_product_by_ref()

```python
def get_product_by_ref(self, ref: str) -> Optional[LlxProduct]:
    return self.db.query(LlxProduct).filter(
        LlxProduct.ref == ref
    ).first()
```

**Propósito:** Buscar producto por referencia  
**Parámetro:** `ref` (ej: "PROD001")  
**Retorna:** Objeto `LlxProduct` o `None`

**Query SQL generada:**
```sql
SELECT * FROM llx_product WHERE ref = 'PROD001' LIMIT 1
```

---

### Método: get_product_by_barcode()

```python
def get_product_by_barcode(self, barcode: str) -> Optional[LlxProduct]:
    return self.db.query(LlxProduct).filter(
        LlxProduct.barcode == barcode
    ).first()
```

**Propósito:** Buscar producto por código de barras  
**Parámetro:** `barcode` (ej: "7891234567890")  
**Retorna:** Objeto `LlxProduct` o `None`

---

### Método: get_product_stock()

```python
def get_product_stock(self, product_id: int, 
                     warehouse_id: Optional[int] = None) -> List[dict]:
    query = self.db.query(
        LlxProductStock,
        LlxEntrepot.label
    ).join(
        LlxEntrepot, LlxProductStock.fk_entrepot == LlxEntrepot.rowid
    ).filter(
        LlxProductStock.fk_product == product_id
    )
    
    if warehouse_id:
        query = query.filter(LlxProductStock.fk_entrepot == warehouse_id)
    
    results = query.all()
    
    return [
        {
            "warehouse_id": stock.fk_entrepot,
            "warehouse_label": label,
            "stock": stock.reel
        }
        for stock, label in results
    ]
```

**Propósito:** Obtener stock de un producto  
**Parámetros:**
- `product_id`: ID del producto (ej: 123)
- `warehouse_id`: ID del almacén (opcional, ej: 1)

**Retorna:** Lista de dicts con stock por almacén

**Query SQL (sin warehouse_id):**
```sql
SELECT ps.*, e.label
FROM llx_product_stock ps
JOIN llx_entrepot e ON ps.fk_entrepot = e.rowid
WHERE ps.fk_product = 123
```

**Respuesta:**
```python
[
    {"warehouse_id": 1, "warehouse_label": "Almacén A", "stock": 80},
    {"warehouse_id": 2, "warehouse_label": "Almacén B", "stock": 70}
]
```

---

### Método: get_total_stock()

```python
def get_total_stock(self, product_id: int) -> float:
    result = self.db.query(
        func.sum(LlxProductStock.reel)
    ).filter(
        LlxProductStock.fk_product == product_id
    ).scalar()
    
    return result or 0.0
```

**Propósito:** Obtener stock TOTAL en todos los almacenes  
**Parámetro:** `product_id` (ej: 123)  
**Retorna:** Float (ej: 150.5)

**Query SQL:**
```sql
SELECT SUM(reel) FROM llx_product_stock WHERE fk_product = 123
```

---

### Método: get_pending_orders()

```python
def get_pending_orders(self, warehouse_id: Optional[int] = None) -> List[dict]:
    query = self.db.query(LlxCommande).filter(
        LlxCommande.fk_statut == 1  # Estado = Validada
    )
    
    if warehouse_id:
        query = query.filter(LlxCommande.fk_entrepot == warehouse_id)
    
    orders = query.order_by(LlxCommande.date_commande.asc()).all()
    
    return [
        {
            "id": order.rowid,
            "ref": order.ref,
            "client_ref": order.ref_client,
            "date": order.date_commande,
            "warehouse_id": order.fk_entrepot,
            "total": float(order.total_ttc) if order.total_ttc else 0.0
        }
        for order in orders
    ]
```

**Propósito:** Obtener órdenes listas para picking  
**Parámetro:** `warehouse_id` (opcional)  
**Retorna:** Lista de dicts con datos de órdenes

**Query SQL:**
```sql
SELECT * FROM llx_commande
WHERE fk_statut = 1
ORDER BY date_commande ASC
```

**Respuesta:**
```python
[
    {
        "id": 456,
        "ref": "CMD-001",
        "client_ref": "PO-12345",
        "date": "2026-01-27",
        "warehouse_id": 1,
        "total": 1500.00
    }
]
```

---

### Método: create_stock_movement()

```python
def create_stock_movement(self, product_id: int, warehouse_id: int, 
                         quantity: float, label: str = ""):
    movement = LlxStockMouvement(
        fk_product=product_id,
        fk_entrepot=warehouse_id,
        qty=quantity,
        type="in" if quantity > 0 else "out",
        label=label,
        datec=datetime.utcnow()
    )
    self.db.add(movement)
    self.db.commit()
    
    return movement
```

**Propósito:** Crear movimiento de stock en Dolibarr  
**Parámetros:**
- `product_id`: ID del producto
- `warehouse_id`: ID del almacén
- `quantity`: Cantidad (positiva=entrada, negativa=salida)
- `label`: Descripción (ej: "Recepción WMS - IMG123.jpg")

**Lo que hace:**
1. Crea objeto `LlxStockMouvement`
2. Lo agrega a la sesión
3. Ejecuta COMMIT
4. Retorna el objeto creado

**Query SQL resultante:**
```sql
INSERT INTO llx_stock_mouvement 
(fk_product, fk_entrepot, qty, type, label, datec)
VALUES (123, 1, 100, 'in', 'Recepción WMS', '2026-01-27')
```

---

## 📊 models/ - Esquemas de Datos

### Pydantic (HTTP Validation): schemas.py

```python
class ProductBase(BaseModel):
    ref: str
    label: str
    barcode: Optional[str] = None

class StockCheckResponse(ProductBase):
    stock_real: int
    warehouse_details: List[dict]
```

**Propósito:** Validar y documentar requests/responses HTTP

**Validación automática:**
```python
# ✅ VÁLIDO
{
    "ref": "PROD001",
    "label": "Producto A",
    "stock_real": 150
}

# ❌ INVÁLIDO (falta 'label')
{
    "ref": "PROD001",
    "stock_real": 150
}
# → 422 Unprocessable Entity

# ❌ INVÁLIDO (stock_real no es int)
{
    "ref": "PROD001",
    "label": "Producto A",
    "stock_real": "150 unidades"  # String, no int
}
# → Convertido automáticamente a 150
```

---

### SQLAlchemy ORM: dolibarr_models.py

```python
class LlxProduct(Base):
    __tablename__ = "llx_product"
    
    rowid = Column(Integer, primary_key=True, index=True)
    ref = Column(String(128), unique=True, nullable=False)
    label = Column(String(255), nullable=False)
    barcode = Column(String(128), index=True)
    price = Column(DECIMAL(24, 8), default=0)
```

**Propósito:** Mapear tabla Dolibarr a clase Python

**Ventajas:**
- Type-safe (LlxProduct.ref es string)
- Previene SQL Injection
- Relaciones automáticas

**Ejemplo de uso:**
```python
# Query ORM
product = db.query(LlxProduct).filter(
    LlxProduct.ref == "PROD001"
).first()

# Acceso a propiedades
print(product.label)  # "Producto A"
print(product.price)  # Decimal('99.99')
```

---

## 📋 Tabla Resumen: Función → Propósito → Entrada → Salida

| Función | Archivo | Propósito | Entrada | Salida |
|---|---|---|---|---|
| `app = FastAPI()` | main.py | Crear app | - | FastAPI app |
| `app.add_middleware()` | main.py | Seguridad CORS | Middleware config | - |
| `get_dolibarr_db()` | core/database.py | Factory sesión | - | Session |
| `DolibarrService.__init__()` | services | Init servicio | Session | Service obj |
| `get_product_by_ref()` | services | Buscar producto | ref (str) | LlxProduct \| None |
| `get_product_stock()` | services | Stock por almacén | product_id | List[dict] |
| `receive_goods()` | routers | Recibir mercadería | form data | {"status": "success"} |
| `get_orders_to_pick()` | routers | Órdenes pending | - | List[OrderResponse] |
| `check_stock()` | routers | Chequear stock | barcode (str) | StockCheckResponse |

---

**Conclusión:** Cada función tiene una responsabilidad clara, parámetros validados, y retorna datos estructurados. 🎯
