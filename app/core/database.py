# core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from core.config import settings


# Conexión ASYNC a WMS
if "sqlite" in settings.WMS_DATABASE_URL:
    wms_async_engine = create_async_engine(
        settings.WMS_DATABASE_URL,
        echo=False
    )
else:
    wms_async_engine = create_async_engine(
        settings.WMS_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

WMSAsyncSessionLocal = async_sessionmaker(
    bind=wms_async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Conexión a Dolibarr (mantener sync por compatibilidad)
from sqlalchemy import create_engine
dolibarr_engine = create_engine(
    settings.DOLIBARR_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    echo=False
)

DolibarrSessionLocal = async_sessionmaker(
    bind=dolibarr_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()



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
if "sqlite" in settings.WMS_DATABASE_URL:
    wms_engine = create_engine(
        settings.WMS_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    wms_engine = create_engine(
        settings.WMS_DATABASE_URL,
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

async def get_wms_db():
    async with WMSAsyncSessionLocal() as session:
        yield session

async def get_dolibarr_db():
    async with DolibarrSessionLocal() as session:
        yield session