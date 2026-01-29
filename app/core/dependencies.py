"""
Dependencias de FastAPI para seguridad y autenticación.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import decode_token
from core.database import get_wms_db
from models.wms_models import User
from services.user_service import UserService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_wms_db)
) -> User:
    """
    Obtener usuario actual a partir del token JWT.
    
    Esta dependencia se usa para proteger endpoints que requieren autenticación.
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    
    # Si es token de servicio (Dolibarr)
    if user_id.startswith("service_"):
        # Crear usuario mock para servicios
        # En producción, crear un modelo específico para servicios
        from models.wms_models import User
        service_user = User(
            id=0,  # ID especial para servicios
            username=payload.get("client", "service"),
            email=f"{payload.get('client')}@system",
            tenant_id=payload.get("tenant_id", 0),
            is_active=True
        )
        return service_user
    
    # Buscar usuario real en DB
    user_service = UserService(db)
    user = await user_service.get_user_by_id(int(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependencia que asegura que el usuario está activo.
    """
    return current_user


def require_role(required_roles: List[str]):
    """
    Decorator para requerir roles específicos.
    
    Uso:
        @router.get("/endpoint")
        async def endpoint(
            current_user: User = Depends(require_role(["admin", "manager"]))
        ):
            # Solo usuarios con rol admin o manager pueden acceder
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        user_roles = [role.name for role in current_user.roles]
        
        # Usuarios de servicio (como Dolibarr) tienen permisos especiales
        if hasattr(current_user, 'id') and current_user.id == 0:
            # Es un usuario de servicio, verificar permisos en token
            return current_user
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes",
            )
        return current_user
    return role_checker


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
) -> int:
    """
    Obtener tenant_id del usuario actual.
    """
    return current_user.tenant_id


async def get_current_user_id(
    current_user: User = Depends(get_current_user),
) -> int:
    """
    Obtener user_id del usuario actual.
    """
    return current_user.id


# Permisos predefinidos para uso común
require_admin = require_role(["admin"])
require_operator = require_role(["operator", "admin"])
require_auditor = require_role(["auditor", "admin"])
require_dolibarr_client = require_role(["dolibarr_client", "admin"])