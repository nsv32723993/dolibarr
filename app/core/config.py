# core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ⚠️ REEMPLAZA CON TUS DATOS REALES DE DOLIBARR
    DOLIBARR_DB_HOST: str = "localhost"
    DOLIBARR_DB_PORT: str = "5432"  # PostgreSQL default
    DOLIBARR_DB_NAME: str = "dolibarr"  # Nombre de DB de Dolibarr
    DOLIBARR_DB_USER: str = "postgres"  # Usuario de Dolibarr
    DOLIBARR_DB_PASSWORD: str = "tu_password"  # Password de Dolibarr
    
    # Tu WMS local (PostgreSQL separado)
    WMS_DB_HOST: str = "localhost"
    WMS_DB_PORT: str = "5433"  # Puerto diferente para no colisionar
    WMS_DB_NAME: str = "wms_saas"
    WMS_DB_USER: str = "wms_user"
    WMS_DB_PASSWORD: str = "wms_password"
    
    # API Key de Dolibarr (del README)
    DOLIBARR_API_KEY: str = "GrK4KrV8pnWe5YT0j1rPsgmLt9449F4T"
    DOLIBARR_API_URL: str = "http://localhost/dolibarr/api/index.php"
    
    @property
    def DOLIBARR_DATABASE_URL(self) -> str:
        """URL de conexión a PostgreSQL de Dolibarr"""
        return (
            f"postgresql://{self.DOLIBARR_DB_USER}:{self.DOLIBARR_DB_PASSWORD}"
            f"@{self.DOLIBARR_DB_HOST}:{self.DOLIBARR_DB_PORT}/{self.DOLIBARR_DB_NAME}"
        )
    
    @property
    def WMS_DATABASE_URL(self) -> str:
        """URL de conexión a SQLite para desarrollo"""
        return "sqlite:///./wms_test.db"
    
    class Config:
        env_file = ".env"

settings = Settings()