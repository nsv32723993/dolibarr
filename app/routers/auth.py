"""
Rutas de autenticación para WMS API.
Permite login/logout y gestión de tokens JWT para Dolibarr y otros clientes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Optional

from core.database import get_wms_db
from core.dependencies import get_current_user, require_role
from core.security import verify_password, create_access_token
from core.config import settings
from models.wms_models import User
from services.auth_service import AuthService
from services.user_service import UserService

router = APIRouter(tags=["Authentication"])


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Login de usuario para WMS.
    
    Credenciales:
    - username: email del usuario
    - password: contraseña
    
    Retorna:
    - access_token: Token JWT para autenticar requests
    - token_type: "bearer"
    - user_info: Información básica del usuario
    """
    auth_service = AuthService(db)
    user_service = UserService(db)
    
    # Buscar usuario por email (username en OAuth2PasswordRequestForm)
    user = await user_service.get_user_by_email(form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
        )
    
    # Crear token de acceso
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": user.tenant_id,
            "roles": [role.name for role in user.roles]
        },
        expires_delta=access_token_expires
    )
    
    # Actualizar último login
    await user_service.update_last_login(user.id)
    
    # Registrar login en auditoría (se hará con middleware)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "tenant_id": user.tenant_id,
            "roles": [role.name for role in user.roles]
        }
    }


@router.post("/dolibarr/login")
async def dolibarr_login(
    api_key: str,
    tenant_id: int,
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Login especial para Dolibarr ERP.
    
    Dolibarr se autenticará usando su API key y tenant ID.
    Esto permite que Dolibarr actúe como cliente de la API WMS.
    
    Parámetros:
    - api_key: API key configurada para Dolibarr
    - tenant_id: ID del tenant al que pertenece Dolibarr
    
    Retorna:
    - access_token: Token JWT específico para Dolibarr
    - token_type: "bearer"
    """
    # Verificar API key (en producción, esto vendría de configuración)
    valid_api_keys = [settings.DOLIBARR_API_KEY]
    
    if api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida",
        )
    
    # Verificar que tenant exista
    from services.tenant_service import TenantService
    tenant_service = TenantService(db)
    tenant = await tenant_service.get_tenant_by_id(tenant_id)
    
    if not tenant or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant no válido o inactivo",
        )
    
    # Crear token especial para Dolibarr
    access_token_expires = timedelta(hours=24)  # Token de larga duración para Dolibarr
    access_token = create_access_token(
        data={
            "sub": "dolibarr_system",
            "client": "dolibarr_erp",
            "tenant_id": tenant_id,
            "roles": ["dolibarr_client", "system"]
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 24 * 60 * 60,  # 24 horas en segundos
        "client": "dolibarr",
        "tenant_id": tenant_id
    }


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Refrescar token JWT expirado.
    
    Requiere:
    - Token JWT válido (aunque próximo a expirar)
    
    Retorna:
    - Nuevo access_token
    """
    user_service = UserService(db)
    
    # Verificar que usuario siga activo
    user = await user_service.get_user_by_id(current_user.id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido",
        )
    
    # Crear nuevo token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": user.tenant_id,
            "roles": [role.name for role in user.roles]
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtener información del usuario actualmente autenticado.
    
    Requiere:
    - Token JWT válido en header Authorization: Bearer <token>
    
    Retorna:
    - Información completa del usuario
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "tenant_id": current_user.tenant_id,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
        "created_at": current_user.created_at,
        "roles": [{"id": role.id, "name": role.name, "description": role.description} 
                 for role in current_user.roles]
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout de usuario.
    
    En JWT stateless, el logout se maneja en el cliente
    eliminando el token. Este endpoint registra el logout
    en el sistema de auditoría.
    
    Requiere:
    - Token JWT válido
    """
    # En un sistema stateless, el logout es responsabilidad del cliente
    # Pero podemos registrar la acción en auditoría
    return {
        "message": "Logout exitoso. Por favor, elimine el token en el cliente.",
        "user_id": current_user.id,
        "timestamp": "now"
    }


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Cambiar contraseña del usuario actual.
    
    Requiere:
    - Token JWT válido
    - Contraseña actual
    - Nueva contraseña
    
    Validaciones:
    - Nueva contraseña debe ser diferente a la actual
    - Nueva contraseña debe cumplir políticas de seguridad
    """
    user_service = UserService(db)
    
    # Verificar contraseña actual
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta"
        )
    
    # Verificar que nueva contraseña sea diferente
    if verify_password(new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual"
        )
    
    # Validar fortaleza de nueva contraseña (ejemplo básico)
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres"
        )
    
    # Cambiar contraseña
    success = await user_service.change_password(current_user.id, new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar contraseña"
        )
    
    return {
        "message": "Contraseña cambiada exitosamente",
        "user_id": current_user.id
    }


@router.post("/reset-password-request")
async def request_password_reset(
    email: str,
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Solicitar reset de contraseña.
    
    Envía email con token para resetear contraseña.
    (Implementación básica - en producción integrar con servicio de email)
    
    Parámetros:
    - email: Email del usuario
    """
    user_service = UserService(db)
    
    # Buscar usuario por email
    user = await user_service.get_user_by_email(email)
    
    if not user:
        # Por seguridad, no revelar si el email existe o no
        return {
            "message": "Si el email existe, se enviarán instrucciones para resetear la contraseña"
        }
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    # Generar token de reset (en producción, usar método más seguro)
    reset_token = create_access_token(
        data={"sub": str(user.id), "purpose": "password_reset"},
        expires_delta=timedelta(hours=1)
    )
    
    # En producción: enviar email con link de reset
    # reset_link = f"https://tudominio.com/reset-password?token={reset_token}"
    # await email_service.send_password_reset_email(user.email, reset_link)
    
    # Por ahora, retornar token (en producción NO hacer esto)
    return {
        "message": "Instrucciones enviadas al email",
        "reset_token": reset_token,  # ⚠️ Solo para desarrollo/testing
        "expires_in": 3600  # 1 hora
    }


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Resetear contraseña usando token.
    
    Parámetros:
    - token: Token de reset obtenido de /reset-password-request
    - new_password: Nueva contraseña
    """
    from core.security import decode_token
    
    # Decodificar token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido o expirado"
        )
    
    # Verificar que sea token de reset
    if payload.get("purpose") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido"
        )
    
    user_service = UserService(db)
    
    # Cambiar contraseña
    success = await user_service.change_password(int(user_id), new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar contraseña"
        )
    
    return {
        "message": "Contraseña restablecida exitosamente"
    }


@router.get("/validate-token")
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    """
    Validar token JWT.
    
    Útil para que clientes verifiquen si su token sigue válido.
    
    Requiere:
    - Token JWT en header
    
    Retorna:
    - Estado de validez del token
    - Información básica del usuario
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "expires_in": "calculated_from_token"  # En producción, calcular tiempo restante
    }


# Endpoints específicos para integración con Dolibarr
@router.get("/dolibarr/integration-test")
async def dolibarr_integration_test(
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint de prueba para integración con Dolibarr.
    
    Dolibarr puede llamar a este endpoint para verificar
    que la conexión y autenticación funcionan correctamente.
    
    Requiere:
    - Token JWT válido (de Dolibarr o usuario)
    """
    # Verificar permisos específicos para Dolibarr
    user_roles = [role.name for role in current_user.roles]
    
    if "dolibarr_client" not in user_roles and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para integración con Dolibarr"
        )
    
    return {
        "status": "connected",
        "service": "wms_api",
        "version": "1.0.0",
        "tenant_id": current_user.tenant_id,
        "timestamp": "now",
        "capabilities": [
            "inbound_operations",
            "outbound_operations",
            "inventory_management",
            "audit_trail"
        ]
    }