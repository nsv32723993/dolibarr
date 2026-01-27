# models/dolibarr_models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# 📦 TABLAS PRINCIPALES DE DOLIBARR (basadas en su estructura)
class LlxProduct(Base):
    """Tabla llx_product de Dolibarr - Productos/Servicios"""
    __tablename__ = "llx_product"
    
    rowid = Column(Integer, primary_key=True, index=True)
    ref = Column(String(128), unique=True, nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text)
    note_public = Column(Text)
    note_private = Column(Text)
    barcode = Column(String(128), index=True)
    price = Column(DECIMAL(24, 8), default=0)  # Precio base
    price_ttc = Column(DECIMAL(24, 8), default=0)  # Precio con IVA
    tva_tx = Column(DECIMAL(6, 3), default=0)  # % IVA
    fk_product_type = Column(Integer, default=0)  # 0=Producto, 1=Servicio
    duration_value = Column(Integer)  # Para servicios
    duration_unit = Column(Integer)  # 1=hora, 2=día, etc.
    weight = Column(Float)  # Peso
    weight_units = Column(Integer, default=-1)  # -1=kg
    length = Column(Float)  # Largo
    length_units = Column(Integer, default=-1)
    surface = Column(Float)  # Superficie
    surface_units = Column(Integer, default=-1)
    volume = Column(Float)  # Volumen
    volume_units = Column(Integer, default=-1)
    tosell = Column(Boolean, default=True)  # Se vende
    tobuy = Column(Boolean, default=True)  # Se compra
    finished = Column(Boolean, default=False)  # Producto terminado
    fk_default_warehouse = Column(Integer)  # Almacén por defecto
    entity = Column(Integer, default=1)  # Para multi-empresa
    datec = Column(DateTime, default=datetime.utcnow)  # Fecha creación
    tms = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LlxProductStock(Base):
    """Tabla llx_product_stock de Dolibarr - Stock por almacén"""
    __tablename__ = "llx_product_stock"
    
    rowid = Column(Integer, primary_key=True, index=True)
    fk_product = Column(Integer, ForeignKey("llx_product.rowid"), nullable=False)
    fk_entrepot = Column(Integer, ForeignKey("llx_entrepot.rowid"), nullable=False)
    reel = Column(Float, default=0)  # Stock real
    pmp = Column(DECIMAL(24, 8), default=0)  # Precio medio ponderado
    pa = Column(DECIMAL(24, 8), default=0)  # Precio de adquisición
    tms = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    product = relationship("LlxProduct", backref="stocks")
    warehouse = relationship("LlxEntrepot")

class LlxEntrepot(Base):
    """Tabla llx_entrepot de Dolibarr - Almacenes/Bodegas"""
    __tablename__ = "llx_entrepot"
    
    rowid = Column(Integer, primary_key=True, index=True)
    ref = Column(String(128), unique=True, nullable=False)
    label = Column(String(255), nullable=False)
    description = Column(Text)
    lieu = Column(String(255))  # Ubicación física
    address = Column(String(255))
    zip = Column(String(25))
    town = Column(String(255))
    fk_departement = Column(Integer)
    fk_pays = Column(Integer, default=1)  # 1=Francia, ajustar según país
    phone = Column(String(20))
    fax = Column(String(20))
    statut = Column(Integer, default=1)  # 1=Activo
    fk_parent = Column(Integer)  # Almacén padre
    entity = Column(Integer, default=1)
    datec = Column(DateTime, default=datetime.utcnow)
    tms = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LlxCommande(Base):
    """Tabla llx_commande de Dolibarr - Órdenes de cliente"""
    __tablename__ = "llx_commande"
    
    rowid = Column(Integer, primary_key=True, index=True)
    ref = Column(String(128), unique=True, nullable=False)
    ref_client = Column(String(255))  # Referencia del cliente
    fk_soc = Column(Integer, ForeignKey("llx_societe.rowid"))  # Cliente
    date_commande = Column(DateTime, default=datetime.utcnow)
    fk_statut = Column(Integer, default=0)  # 0=Borrador, 1=Validada, 2=Cerrada
    total_ht = Column(DECIMAL(24, 8), default=0)
    total_tva = Column(DECIMAL(24, 8), default=0)
    total_ttc = Column(DECIMAL(24, 8), default=0)
    fk_entrepot = Column(Integer)  # Almacén de salida
    entity = Column(Integer, default=1)
    datec = Column(DateTime, default=datetime.utcnow)
    tms = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LlxCommandeDet(Base):
    """Tabla llx_commandedet de Dolibarr - Líneas de órdenes"""
    __tablename__ = "llx_commandedet"
    
    rowid = Column(Integer, primary_key=True, index=True)
    fk_commande = Column(Integer, ForeignKey("llx_commande.rowid"), nullable=False)
    fk_product = Column(Integer, ForeignKey("llx_product.rowid"))
    description = Column(Text)
    qty = Column(Float, default=0)  # Cantidad pedida
    qty_shipped = Column(Float, default=0)  # Cantidad enviada
    subprice = Column(DECIMAL(24, 8), default=0)  # Precio unitario
    total_ht = Column(DECIMAL(24, 8), default=0)
    total_tva = Column(DECIMAL(24, 8), default=0)
    total_ttc = Column(DECIMAL(24, 8), default=0)
    fk_entrepot = Column(Integer)  # Almacén origen
    rang = Column(Integer, default=0)  # Orden de línea

class LlxStockMouvement(Base):
    """Tabla llx_stock_mouvement de Dolibarr - Movimientos de stock"""
    __tablename__ = "llx_stock_mouvement"
    
    rowid = Column(Integer, primary_key=True, index=True)
    tms = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    datem = Column(DateTime, default=datetime.utcnow)  # Fecha movimiento
    fk_product = Column(Integer, ForeignKey("llx_product.rowid"), nullable=False)
    batch = Column(String(128))  # Número de lote
    eatby = Column(DateTime)  # Consumir antes de
    sellby = Column(DateTime)  # Vender antes de
    fk_entrepot = Column(Integer, ForeignKey("llx_entrepot.rowid"), nullable=False)
    value = Column(Float, nullable=False)  # Cantidad (+entrada, -salida)
    price = Column(DECIMAL(24, 8))  # Precio unitario
    fk_user_author = Column(Integer)  # Usuario que creó
    label = Column(String(255))  # Etiqueta/descripción
    inventorycode = Column(String(128))  # Código inventario
    fk_origin = Column(Integer)  # Origen (order, shipment, etc.)
    origintype = Column(String(32))  # Tipo de origen
    entity = Column(Integer, default=1)