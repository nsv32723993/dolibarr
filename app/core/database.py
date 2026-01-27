# core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from core.config import settings

# 🔵 CONEXIÓN A DOLIBARR (SOLO LECTURA EN MVP)
dolibarr_engine = create_engine(
    settings.DOLIBARR_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    echo=False  # True para debug
)

DolibarrSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=dolibarr_engine
)

# 🟢 CONEXIÓN A TU WMS (LECTURA/ESCRITURA)
wms_engine = create_engine(
    settings.WMS_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.WMS_DATABASE_URL else {},
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False
)

# Alias para compatibilidad
engine = wms_engine

WMSSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=wms_engine
)

# Base para tus tablas WMS
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

def get_dolibarr_db():
    """Dependencia para sesión de solo lectura a Dolibarr"""
    db = DolibarrSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_wms_db():
    """Dependencia para sesión de lectura/escritura a WMS"""
    db = WMSSessionLocal()
    try:
        yield db
    finally:
        db.close()