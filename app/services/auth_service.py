"""
Servicio de autenticación para WMS API.
Contiene lógica de negocio relacionada con autenticación.
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from models.wms_models import User
from core.security import verify_password, create_access_token, get_password_hash
from core.config import settings


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Autenticar usuario por email y contraseña.
        
        Args:
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            User object si autenticación exitosa, None si falla
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return user
    
    async def create_access_token_for_user(self, user: User) -> Dict[str, Any]:
        """
        Crear token JWT para usuario.
        
        Args:
            user: Objeto User
            
        Returns:
            Dict con token y metadatos
        """
        # Cargar roles del usuario
        await self.db.refresh(user, ["roles"])
        
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": user.tenant_id,
            "roles": [role.name for role in user.roles],
        }
        
        access_token = create_access_token(
            token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.id,
            "email": user.email
        }
    
    async def validate_api_key(self, api_key: str) -> bool:
        """
        Validar API key para integraciones externas.
        
        Args:
            api_key: API key proporcionada
            
        Returns:
            True si es válida, False si no
        """
        # En producción, buscar en base de datos
        valid_keys = [settings.DOLIBARR_API_KEY]
        return api_key in valid_keys
    
    async def create_service_token(self, client_name: str, tenant_id: int, 
                                  permissions: list) -> Dict[str, Any]:
        """
        Crear token para servicios/sistemas (como Dolibarr).
        
        Args:
            client_name: Nombre del cliente/sistema
            tenant_id: ID del tenant
            permissions: Lista de permisos
            
        Returns:
            Dict con token y metadatos
        """
        token_data = {
            "sub": f"service_{client_name}",
            "client": client_name,
            "tenant_id": tenant_id,
            "permissions": permissions,
            "type": "service_token"
        }
        
        # Tokens de servicio duran más
        access_token = create_access_token(
            token_data,
            expires_delta=timedelta(hours=24)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 24 * 60 * 60,
            "client": client_name,
            "tenant_id": tenant_id
        }
    
    async def update_last_login(self, user_id: int) -> bool:
        """
        Actualizar timestamp de último login.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si éxito, False si falla
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.last_login = datetime.utcnow()
                await self.db.commit()
                return True
            return False
        except Exception:
            await self.db.rollback()
            return False
    
    async def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validar fortaleza de contraseña.
        
        Args:
            password: Contraseña a validar
            
        Returns:
            Dict con validaciones
        """
        validations = {
            "length": len(password) >= 8,
            "has_uppercase": any(c.isupper() for c in password),
            "has_lowercase": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(not c.isalnum() for c in password),
        }
        
        is_valid = all(validations.values())
        
        return {
            "is_valid": is_valid,
            "validations": validations,
            "score": sum(validations.values())  # 0-5
        }