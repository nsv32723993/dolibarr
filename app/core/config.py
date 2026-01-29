from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ⚠️ REEMPLAZA CON TUS DATOS REALES DE DOLIBARR cambie user "postgres" y password "tu_password"
    DOLIBARR_DB_HOST: str = "localhost"
    DOLIBARR_DB_PORT: str = "5432"  # PostgreSQL default
    DOLIBARR_DB_NAME: str = "dolibarr"  # Nombre de DB de Dolibarr
    DOLIBARR_DB_USER: str = "dolibarr"  # Usuario de Dolibarr
    DOLIBARR_DB_PASSWORD: str = "dolibarr"  # Password de Dolibarr
    
    # Tu WMS local (PostgreSQL separado)
    WMS_DB_HOST: str = "localhost"
    WMS_DB_PORT: str = "5433"  # Puerto diferente para no colisionar
    WMS_DB_NAME: str = "wms_saas"
    WMS_DB_USER: str = "wms_user"
    WMS_DB_PASSWORD: str = "wms_password"
    # Permitir URL completa de DB desde .env (por compatibilidad)
    WMS_DB_URL: Optional[str] = None
    
    # API Key de Dolibarr (del README)
    DOLIBARR_API_KEY: str = "GrK4KrV8pnWe5YT0j1rPsgmLt9449F4T"
    DOLIBARR_API_URL: str = "http://localhost/dolibarr/api/index.php"
    
    # ⭐ NUEVO desde aqui para abajo: Configuración JWT y seguridad
    JWT_SECRET_KEY: str = "tu-clave-secreta-segura-cambiar-en-produccion"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configuración seguridad
    BCRYPT_ROUNDS: int = 12
    
    # Configuración CORS (para desarrollo)
    ALLOWED_ORIGINS: str = "*"
    ALLOWED_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    ALLOWED_HEADERS: str = "*"
    
    @property
    def DOLIBARR_DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DOLIBARR_DB_USER}:{self.DOLIBARR_DB_PASSWORD}"
            f"@{self.DOLIBARR_DB_HOST}:{self.DOLIBARR_DB_PORT}/{self.DOLIBARR_DB_NAME}"
        )
    
    @property
    def WMS_DATABASE_URL(self) -> str:
        # Si se suministra una URL completa en .env, usarla (compatibilidad)
        if self.WMS_DB_URL:
            return self.WMS_DB_URL

        # Cambiar a PostgreSQL async (construir desde partes)
        return (
            f"postgresql+asyncpg://{self.WMS_DB_USER}:{self.WMS_DB_PASSWORD}"
            f"@{self.WMS_DB_HOST}:{self.WMS_DB_PORT}/{self.WMS_DB_NAME}"
        )
    
    class Config:
        env_file = ".env"

settings = Settings()