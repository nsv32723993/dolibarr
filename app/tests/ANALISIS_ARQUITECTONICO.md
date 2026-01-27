# 📊 ANÁLISIS ARQUITECTÓNICO COMPLETO - APP WMS DOLIBARR

## 🎯 RESUMEN EJECUTIVO

### ¿Qué es esta aplicación?
Una **API REST moderna (FastAPI)** que funciona como **capa intermedia inteligente** entre:
- 📦 **Dolibarr** (ERP con base de datos PostgreSQL) ← Fuente de verdad
- 🏭 **Sistema WMS local** (Warehouse Management System) ← Tu negocio

### Propósito Principal
Automatizar procesos de almacén (recepción, picking, inventario) usando datos en tiempo real de Dolibarr, sin modificar Dolibarr.

### Arquitectura en Una Línea
```
Dolibarr DB (READ-ONLY) ← [API REST FastAPI] → WMS Local DB (READ-WRITE)
```

---

## 🏗️ ARQUITECTURA GENERAL

### Capas de la Aplicación

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE HTTP                             │
│                    (Postman, Navegador, App)                    │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
│              (Aplicación FastAPI Principal)                     │
│  - Middleware CORS (Seguridad)                                 │
│  - Rutas: /api/v1/receive, /api/v1/orders, /api/v1/check      │
└────────────┬──────────────────────────┬────────────────────────┘
             ↓                          ↓
    ┌──────────────────┐      ┌──────────────────┐
    │   ROUTERS        │      │  SERVICES        │
    │ (Endpoints)      │      │ (Lógica)         │
    │                  │      │                  │
    │ - inbound.py     │      │ dolibarr_        │
    │ - outbound.py    │      │ service.py       │
    │ - inventory.py   │      │                  │
    │ - dolibarr_test  │      │ (Queries a BD)   │
    └────────┬─────────┘      └────────┬─────────┘
             │                         │
             └──────────┬──────────────┘
                        ↓
        ┌───────────────────────────────────┐
        │         DATABASE LAYER             │
        │  (core/database.py)                │
        │                                   │
        │ - DolibarrSessionLocal (READ)     │
        │ - WMSSessionLocal (READ/WRITE)    │
        └─┬──────────────────────────────┬──┘
          ↓                              ↓
    ┌─────────────────┐      ┌──────────────────┐
    │   POSTGRESQL    │      │    SQLITE        │
    │  (Dolibarr)     │      │   (WMS Local)    │
    │                 │      │                  │
    │ 276 tablas      │      │ Tablas WMS       │
    │ Productos       │      │ Movimientos      │
    │ Órdenes         │      │ Ubicaciones      │
    │ Stock           │      │ Tenants (SaaS)   │
    │ Almacenes       │      │                  │
    └─────────────────┘      └──────────────────┘
```

---

## 📁 ESTRUCTURA DE CARPETAS Y PROPÓSITO

```
app/
├── main.py                          # 🎯 ENTRADA PRINCIPAL
│   └─ Crea app FastAPI, monta routers, middleware CORS
│
├── core/                            # ⚙️ CONFIGURACIÓN Y BASE DATOS
│   ├── config.py                    # Credenciales BD en .env
│   ├── database.py                  # 2 conexiones: Dolibarr + WMS
│   ├── middleware.py                # Multi-tenant (por implementar)
│   └── client_dolibarr.py           # Cliente HTTP para API Dolibarr
│
├── routers/                         # 🛣️ ENDPOINTS (FUNCIONALIDAD)
│   ├── inbound.py                   # POST /receive - Recibir mercadería
│   ├── outbound.py                  # GET /orders - Picking y envíos
│   ├── inventory.py                 # GET /check/{barcode} - Chequear stock
│   ├── picking.py                   # Picking avanzado (extensión)
│   ├── dashboard.py                 # Reportes (extensión)
│   └── dolibarr_test.py             # Test endpoints
│
├── services/                        # 🔧 LÓGICA DE NEGOCIO
│   └── dolibarr_service.py          # Clase DolibarrService
│       ├─ get_product_by_ref()
│       ├─ get_product_stock()
│       ├─ get_pending_orders()
│       ├─ create_stock_movement()
│       └─ (Métodos de consulta)
│
├── models/                          # 📊 MODELOS DE DATOS
│   ├── schemas.py                   # Pydantic (Validación HTTP)
│   │   └─ ProductBase, OrderItem, StockCheckResponse
│   ├── database_models.py           # SQLAlchemy (Tablas WMS local)
│   │   └─ Tenant, Location, Product, Movement
│   ├── dolibarr_models.py           # SQLAlchemy (Tablas Dolibarr READ-ONLY)
│   │   └─ LlxProduct, LlxProductStock, LlxCommande, etc.
│   └── wms_models.py                # Modelos específicos WMS
│
├── migrations/                      # 🔄 CONTROL DE VERSIONES BD
│   └── create_wms_tables.py         # Script para crear tablas iniciales
│
├── .env                             # 🔐 CREDENCIALES
│   ├─ DOLIBARR_DB_HOST=localhost
│   ├─ DOLIBARR_DB_USER=dolibarr
│   └─ WMS_DB_*
│
└── tests/                           # ✅ TESTS
    ├── test_db_conn.py              # Verifica conexión básica
    ├── test_dolibarr_connection.py  # Inspecciona BD Dolibarr
    ├── test_endpoints_directly.py   # Tests de endpoints
    └── run_all_tests.ps1            # Automatización
```

---

## 🔄 FLUJOS DE DATOS Y PROCESOS

### Flujo 1: INBOUND (Recepción de Mercadería)

```
POST /api/v1/receive
↓
1. Cliente envía:
   - product_ref: "PROD001"
   - warehouse_id: 1
   - qty: 100
   - evidence: foto.jpg

2. Endpoint (inbound.py):
   ├─ Busca producto en Dolibarr (READ)
   ├─ Valida cantidad
   ├─ Guarda foto localmente
   └─ Registra movimiento

3. DolibarrService.get_product_by_ref()
   └─ Query: SELECT * FROM llx_product WHERE ref = 'PROD001'

4. Resultado:
   └─ Producto encontrado (ej: id=123)

5. DolibarrService.create_stock_movement()
   └─ INSERT INTO llx_stock_mouvement
       (fk_product, fk_entrepot, qty, label, datec, ...)

6. Respuesta HTTP:
   {
     "status": "success",
     "product_id": 123,
     "warehouse_id": 1,
     "quantity": 100,
     "evidence": "uuid-12345.jpg"
   }
```

### Flujo 2: OUTBOUND (Picking y Envío)

```
GET /api/v1/orders
↓
1. Endpoint (outbound.py):
   ├─ Obtiene órdenes de Dolibarr (READ)
   └─ Limpia y formatea datos

2. DolibarrService.get_pending_orders()
   └─ Query: SELECT * FROM llx_commande WHERE fk_statut = 1

3. Resultado:
   [
     {
       "id": 456,
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

4. Operario pasa por picking con escáner:
   - Escanea códigos de barras
   - Confirma cantidades

5. POST /api/v1/orders/456/close
   ├─ Crea envío (Shipment) en Dolibarr
   ├─ Descuenta stock
   └─ Retorna: { "status": "shipped", "shipment_id": 789 }
```

### Flujo 3: INVENTORY (Chequeo de Stock)

```
GET /api/v1/check/7891234567890
↓
1. Barcode scanned: 7891234567890

2. Endpoint (inventory.py):
   ├─ Busca producto por barcode
   └─ Obtiene stock por almacén

3. DolibarrService.get_product_by_barcode()
   └─ Query: SELECT * FROM llx_product WHERE barcode = '7891234567890'

4. DolibarrService.get_product_stock()
   └─ Query: SELECT stock FROM llx_product_stock
             WHERE fk_product = 123 AND fk_entrepot IN (1,2,3)

5. Resultado:
   {
     "ref": "PROD001",
     "label": "Producto A",
     "stock_real": 150,
     "warehouse_details": [
       { "warehouse": "Almacén A", "stock": 80 },
       { "warehouse": "Almacén B", "stock": 70 }
     ]
   }
```

---

## 🎯 DECISIONES ARQUITECTÓNICAS Y POR QUÉ

### 1️⃣ FASTAPI (vs Django o Flask)

| Característica | FastAPI | Django | Flask |
|---|---|---|---|
| Velocidad | ⚡⚡⚡ Ultra rápido | ⚡ Lento | ⚡⚡ Medio |
| Async Nativo | ✅ Sí | ❌ No | ⚠️ Parcial |
| Validación Auto | ✅ Pydantic | ⚠️ Manual | ❌ No |
| Docs Auto | ✅ Swagger | ❌ No | ❌ No |
| API REST | ✅ Perfecto | ⚠️ Complejo | ⚠️ Complejo |

**Por qué FastAPI:**
- ✅ Perfecto para API REST (tu caso)
- ✅ Documentación Swagger automática
- ✅ Validación de datos con Pydantic
- ✅ Async/await para operaciones de BD
- ✅ Moderno y mantenido activamente

---

### 2️⃣ DOS BASES DE DATOS (Dolibarr READ-ONLY vs WMS READ-WRITE)

```
DECISIÓN: Nunca modificar Dolibarr directamente
```

**Por qué esta arquitectura:**

```
❌ MAL (Modificar Dolibarr):
  Dolibarr → Modificas datos → Conflictos con Dolibarr UI
  
✅ BIEN (Leer de Dolibarr, escribir en WMS):
  Dolibarr (fuente verdad) → [LECTURA PURA]
                          ↓
                    [Procesos WMS]
                          ↓
                    [SQL a WMS local]
```

**Ventajas:**
1. ✅ Dolibarr no se corrompe
2. ✅ WMS es independiente
3. ✅ Puedes hacer rollback en WMS
4. ✅ Historia/auditoría en WMS

---

### 3️⃣ ARQUITECTURA EN CAPAS (Routers → Services → Models → DB)

```
Separación de responsabilidades:

┌─────────────────────────────────────────┐
│ ROUTERS (inbound.py, outbound.py)      │ ← QUÉ: Endpoints HTTP
│ Responsabilidad: Mapear HTTP ↔ funciones│
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│ SERVICES (dolibarr_service.py)          │ ← CÓMO: Lógica de negocio
│ Responsabilidad: Queries a BD, cálculos │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│ MODELS (schemas.py, dolibarr_models.py) │ ← CON QUÉ: Estructura datos
│ Responsabilidad: Validación, ORM        │
└────────────┬────────────────────────────┘
             ↓
┌─────────────────────────────────────────┐
│ DATABASE (core/database.py)             │ ← DÓNDE: Conexión raw
│ Responsabilidad: Pools de conexión      │
└─────────────────────────────────────────┘
```

**Beneficio:** Si cambias BD, solo modifica la capa de database.

---

### 4️⃣ SQLALCHEMY ORM (vs SQL Raw)

```
❌ RAW SQL:
  query = """SELECT * FROM llx_product WHERE ref = %s"""
  db.execute(query, (ref,))  # Vulnerable a SQL Injection

✅ SQLALCHEMY ORM:
  self.db.query(LlxProduct).filter(LlxProduct.ref == ref).first()
  # Type-safe, auto-escaped
```

**Por qué ORM:**
- ✅ Previene SQL Injection
- ✅ Type-safe (Python objects)
- ✅ Portable entre DBs
- ✅ Transacciones automáticas

---

### 5️⃣ PYDANTIC SCHEMAS (Validación HTTP)

```python
# Sin Pydantic (INSEGURO):
@router.post("/receive")
def receive(data: dict):  # ← ¿Qué datos?
    qty = int(data.get("qty"))  # ← Podría fallar

# Con Pydantic (SEGURO):
class InboundReception(BaseModel):
    product_ref: str
    warehouse_id: int
    qty: float  # ← Validado y convertido automáticamente

@router.post("/receive")
def receive(data: InboundReception):
    # ← data.qty ya es float, validado
```

**Beneficios:**
- ✅ Validación automática
- ✅ Conversión de tipos
- ✅ Documentación auto (Swagger)
- ✅ Error messages claros

---

## 🔑 COMPONENTES PRINCIPALES

### 1. **main.py** - El corazón

```python
app = FastAPI(title="WMS API para Dolibarr", ...)
app.add_middleware(CORSMiddleware, ...)  # Seguridad
app.include_router(inbound.router, prefix="/api/v1", tags=["Inbound"])
app.include_router(outbound.router, prefix="/api/v1", tags=["Outbound"])
```

**Lo que hace:**
1. Crea la app FastAPI
2. Configura CORS (permite requests desde otros dominios)
3. Registra todos los routers
4. Define endpoints de salud (/health, /)

---

### 2. **core/config.py** - Credenciales y configuración

```python
class Settings(BaseSettings):
    DOLIBARR_DB_HOST = "localhost"
    DOLIBARR_DB_USER = "dolibarr"
    DOLIBARR_DB_PASSWORD = "dolibarr"  # ← Desde .env
    
    @property
    def DOLIBARR_DATABASE_URL(self):
        return f"postgresql://{user}:{password}@{host}/{db}"
```

**Patrón 12-Factor:**
- ✅ Config en variables de entorno (.env)
- ✅ No hard-coded credentials
- ✅ Diferente por dev/prod

---

### 3. **core/database.py** - Dos conexiones

```python
# DOLIBARR: Solo lectura, pool pequeño
dolibarr_engine = create_engine(
    DOLIBARR_DATABASE_URL,
    pool_size=5,  # Menos conexiones (solo lectura)
    max_overflow=10
)

# WMS: Lectura/Escritura, pool grande
wms_engine = create_engine(
    WMS_DATABASE_URL,
    pool_size=10,  # Más conexiones (operaciones intensivas)
    max_overflow=20
)
```

**Por qué dos engines:**
- ✅ Aislamiento: No comparten pool
- ✅ Performance: Cada uno optimizado
- ✅ Seguridad: Credenciales separadas

---

### 4. **routers/** - Los endpoints

```
inbound.py:
  POST /api/v1/receive
    ├─ Recibe producto + cantidad + foto
    ├─ Busca en Dolibarr
    └─ Crea movimiento de stock

outbound.py:
  GET /api/v1/orders
    ├─ Lista órdenes pendientes
    └─ Retorna items a pickear
  
  POST /api/v1/orders/{id}/close
    ├─ Crea envío en Dolibarr
    └─ Descuenta stock

inventory.py:
  GET /api/v1/check/{barcode}
    ├─ Busca producto por barcode
    └─ Retorna stock por almacén
```

---

### 5. **services/dolibarr_service.py** - Lógica de BD

```python
class DolibarrService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_product_by_ref(self, ref: str):
        return self.db.query(LlxProduct).filter(
            LlxProduct.ref == ref
        ).first()
    
    def get_product_stock(self, product_id: int):
        return self.db.query(
            LlxProductStock, LlxEntrepot.label
        ).join(
            LlxEntrepot, ...
        ).filter(
            LlxProductStock.fk_product == product_id
        ).all()
```

**Ventaja:**
- ✅ Reutilizable (misma query desde múltiples endpoints)
- ✅ Testeable (inyecta BD como parámetro)
- ✅ Mantenible (queries centralizadas)

---

### 6. **models/** - Esquemas de datos

#### `schemas.py` - Para HTTP (Pydantic)
```python
class ProductBase(BaseModel):
    ref: str
    label: str
    barcode: Optional[str] = None

class StockCheckResponse(ProductBase):
    stock_real: int
    warehouse_details: List[dict]
```
✅ Validación de requests/responses HTTP

#### `dolibarr_models.py` - Para Dolibarr (SQLAlchemy)
```python
class LlxProduct(Base):
    __tablename__ = "llx_product"
    rowid = Column(Integer, primary_key=True)
    ref = Column(String(128), unique=True)
    label = Column(String(255))
    barcode = Column(String(128))
```
✅ Mapeo de tablas Dolibarr

#### `database_models.py` - Para WMS (SQLAlchemy)
```python
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer)  # Multi-tenant
```
✅ Tablas locales WMS

---

## 📊 TABLA DE CORRESPONDENCIAS: ENDPOINT → SERVICIO → BD

| Endpoint | Method | Router | Service | Query |
|---|---|---|---|---|
| `/receive` | POST | inbound.py | get_product_by_ref() | SELECT FROM llx_product |
| `/orders` | GET | outbound.py | get_pending_orders() | SELECT FROM llx_commande |
| `/check/{barcode}` | GET | inventory.py | get_product_by_barcode() | SELECT FROM llx_product |
| `/orders/{id}/close` | POST | outbound.py | create_shipment() | INSERT INTO llx_expeditiondet |

---

## 🔐 SEGURIDAD

### 1. CORS (Cross-Origin Resource Sharing)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ EN PROD: especifica dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. .env (No commitear credenciales)
```python
# ✅ CORRECTO
from core.config import settings
db_password = settings.DOLIBARR_DB_PASSWORD  # Desde .env

# ❌ INCORRECTO
db_password = "dolibarr"  # Hard-coded
```

### 3. Session Injection (Dependencias)
```python
def receive_goods(
    dolibarr_db: Session = Depends(get_dolibarr_db),  # ← Inyectada
    wms_db: Session = Depends(get_wms_db)
):
    # Las sesiones se cierran automáticamente
```

---

## 🚀 POR QUÉ ESTA ARQUITECTURA FUNCIONA

### ✅ Escalabilidad
```
Con SQLAlchemy + Pydantic:
- Cambia DB: Actualiza 1 archivo (database.py)
- Agrega endpoint: Copia función, cambia query
- Multi-tenant: Agrega tenant_id a todas las tablas
```

### ✅ Mantenibilidad
```
Cambios concentrados en capas:
- Nueva validación HTTP? → models/schemas.py
- Nueva query? → services/dolibarr_service.py
- Nuevo endpoint? → routers/nuevo.py
```

### ✅ Testabilidad
```python
# Tests fáciles porque servicios reciben DB como parámetro
def test_get_product():
    mock_db = MagicMock()
    service = DolibarrService(mock_db)
    result = service.get_product_by_ref("PROD001")
    # ← Testeado sin BD real
```

### ✅ Independencia de Dolibarr
```
- Dolibarr se actualiza? No hay problema.
- La API WMS sigue funcionando (lectura pura).
- Tus datos en WMS están protegidos.
```

---

## 🎓 FLUJO DE UNA REQUEST COMPLETA

```
1. Cliente HTTP:
   POST /api/v1/receive
   {
     "product_ref": "PROD001",
     "warehouse_id": 1,
     "qty": 100
   }

2. main.py:
   app.include_router(inbound.router, prefix="/api/v1")
   ↓ ENRUTA A: inbound.py

3. routers/inbound.py:
   @router.post("/receive")
   async def receive_goods(...):
   ↓ INYECTA DEPENDENCIAS:
   
   dolibarr_db: Session = Depends(get_dolibarr_db)
   wms_db: Session = Depends(get_wms_db)
   ↓ LLAMA SERVICIO:

4. services/dolibarr_service.py:
   service = DolibarrService(dolibarr_db)
   product = service.get_product_by_ref("PROD001")
   ↓ QUERY A BD:

5. core/database.py:
   dolibarr_engine.connect()
   SELECT * FROM llx_product WHERE ref = 'PROD001'
   ↓ RESULTADO:

6. Python Object:
   product = LlxProduct(rowid=123, ref="PROD001", ...)
   ↓ CONTINÚA LÓGICA:

7. Validación:
   if not product:
       raise HTTPException(404, "Producto no encontrado")
   ↓ OK

8. Guardar evidencia:
   with open("evidence/tenant_1/uuid.jpg", "wb") as f:
       f.write(evidence.file)
   ↓ CREA MOVIMIENTO:

9. Stock Movement:
   service.create_stock_movement(
       product_id=123,
       warehouse_id=1,
       qty=100
   )
   ↓ INSERT en Dolibarr:
   INSERT INTO llx_stock_mouvement (...)
   ↓ RESPUESTA HTTP:

10. Cliente:
    {
      "status": "success",
      "product_id": 123,
      "quantity": 100,
      "evidence": "uuid-xyz.jpg"
    }
    ✅ 200 OK
```

---

## 📈 CRECIMIENTO FUTURO (Ya preparado)

La arquitectura soporta:

### 1. Multi-Tenant
```python
# Ya en database_models.py:
class Product(Base):
    tenant_id = Column(Integer, ForeignKey("tenants.id"))

# En routers, agregamos:
def receive_goods(
    ...,
    tenant_id: int = Depends(get_tenant_from_token)
):
    # Aisla datos por cliente
```

### 2. Más Routers
```
routers/
├── picking.py       # Picking optimizado
├── dashboard.py     # Reportes en tiempo real
├── returns.py       # Devoluciones
└── kpi.py          # KPIs de almacén
```

### 3. Webhooks
```python
@router.post("/webhooks/dolibarr")
async def webhook_product_updated(event: dict):
    # Dolibarr notifica cambios
    # Sincroniza a WMS automáticamente
```

### 4. Integración Múltiples Dolibarr
```python
# En config:
DOLIBARR_INSTANCES = [
    {"name": "HQ", "db": "..."},
    {"name": "Sucursal", "db": "..."}
]

# En services:
class DolibarrService:
    def __init__(self, db, instance_name):
        # Soporte para múltiples Dolibarr
```

---

## 🎯 RESUMEN FINAL

### ¿Por qué esta arquitectura?

| Aspecto | Decisión | Beneficio |
|---|---|---|
| **Framework** | FastAPI | Rápido, async, documentación auto |
| **BDs Separadas** | Dolibarr READ + WMS READ/WRITE | Seguridad, independencia |
| **Capas (Routers → Services → Models)** | Separación responsabilidades | Mantenible, testeable |
| **SQLAlchemy ORM** | Type-safe queries | SQL injection protection |
| **Pydantic Schemas** | Validación HTTP | Data integrity |
| **Dependency Injection** | FastAPI Depends() | Testeable, limpio |
| **Config en .env** | 12-Factor | No credenciales en código |

### ¿Qué puede hacer?

✅ **Recibir mercadería** con foto (Inbound)  
✅ **Crear órdenes de picking** (Outbound)  
✅ **Verificar stock** en tiempo real  
✅ **Crear movimientos en Dolibarr** (sin modificar BD)  
✅ **Multi-tenant** (clientes separados)  
✅ **Escalable** (add routers fácilmente)  
✅ **Testeable** (todas las funciones aisladas)  

### Próximos pasos recomendados:

1. Entender los 3 flujos (Inbound, Outbound, Inventory)
2. Ver cómo correr tests (GUIA_TESTS.md)
3. Customizar routers según tu negocio
4. Activar webhooks con Dolibarr
5. Agregar reportes (dashboard.py)

---

**Conclusión:** Una arquitectura moderna, segura y escalable para conectar WMS con Dolibarr. 🚀
