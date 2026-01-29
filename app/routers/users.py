"""
Rutas para gestión de usuarios del sistema WMS.
Endpoints protegidos por rol de administrador.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from core.database import get_wms_db
from core.dependencies import get_current_user, require_admin, get_current_tenant
from core.security import get_password_hash
from models.wms_models import User
from services.user_service import UserService
from services.role_service import RoleService

router = APIRouter(prefix="/users", tags=["Users"])


# Schemas específicos para este router
class UserCreateRequest(BaseModel):
    """Request para crear usuario"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    is_active: bool = True
    role_ids: Optional[List[int]] = []

class UserUpdateRequest(BaseModel):
    """Request para actualizar usuario"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    """Response de usuario"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    tenant_id: int
    is_active: bool
    last_login: Optional[str]
    created_at: str
    updated_at: str
    roles: List[dict]
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Response para lista de usuarios"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


@router.get("/", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros por página"),
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    search: Optional[str] = Query(None, description="Buscar por username o email"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Listar usuarios del tenant actual.
    
    Solo administradores pueden ver la lista de usuarios.
    
    Parámetros de query:
    - skip: Paginación (offset)
    - limit: Límite por página (max 200)
    - is_active: Filtrar por estado
    - search: Buscar por username o email
    
    Returns:
    - Lista de usuarios con paginación
    """
    user_service = UserService(db)
    
    # Obtener usuarios del tenant
    users, total = await user_service.get_users_by_tenant_paginated(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
        search=search
    )
    
    # Convertir a response
    user_responses = []
    for user in users:
        user_responses.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            tenant_id=user.tenant_id,
            is_active=user.is_active,
            last_login=user.last_login.isoformat() if user.last_login else None,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat() if user.updated_at else user.created_at.isoformat(),
            roles=[{"id": role.id, "name": role.name} for role in user.roles]
        ))
    
    return UserListResponse(
        users=user_responses,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_wms_db)
):
    """
    Obtener perfil del usuario actual.
    
    Cualquier usuario autenticado puede ver su propio perfil.
    
    Returns:
    - Perfil completo del usuario actual
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(current_user.id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else user.created_at.isoformat(),
        roles=[{"id": role.id, "name": role.name} for role in user.roles]
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Obtener usuario por ID.
    
    Solo administradores pueden ver otros usuarios.
    
    Parámetros:
    - user_id: ID del usuario a consultar
    
    Returns:
    - Información completa del usuario
    """
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar que pertenezca al mismo tenant
    if user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede acceder a usuarios de otros tenants"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        last_login=user.last_login.isoformat() if user.last_login else None,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat() if user.updated_at else user.created_at.isoformat(),
        roles=[{"id": role.id, "name": role.name} for role in user.roles]
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Crear nuevo usuario.
    
    Solo administradores pueden crear usuarios.
    
    Parámetros:
    - user_data: Datos del nuevo usuario
    
    Validaciones:
    - Email único en el sistema
    - Username único en el tenant
    - Password cumple políticas de seguridad
    
    Returns:
    - Usuario creado
    """
    user_service = UserService(db)
    
    # Verificar que email no exista
    existing_user = await user_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email ya registrado en el sistema"
        )
    
    # Verificar que username no exista en el tenant
    existing_username = await user_service.get_user_by_username(user_data.username, tenant_id)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username ya existe en este tenant"
        )
    
    # Validar fortaleza de password (implementación básica)
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres"
        )
    
    # Hash de password
    hashed_password = get_password_hash(user_data.password)
    
    # Crear usuario
    user_dict = user_data.dict(exclude={"password", "role_ids"})
    user_dict.update({
        "hashed_password": hashed_password,
        "tenant_id": tenant_id
    })
    
    user = await user_service.create_user(user_dict)
    
    # Asignar roles si se especificaron
    if user_data.role_ids:
        role_service = RoleService(db)
        
        # Verificar que todos los roles existan
        for role_id in user_data.role_ids:
            role = await role_service.get_role_by_id(role_id)
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Rol ID {role_id} no encontrado"
                )
        
        await user_service.update_user_roles(user.id, user_data.role_ids)
    
    # Obtener usuario con roles
    user_with_roles = await user_service.get_user_by_id(user.id)
    
    return UserResponse(
        id=user_with_roles.id,
        username=user_with_roles.username,
        email=user_with_roles.email,
        full_name=user_with_roles.full_name,
        tenant_id=user_with_roles.tenant_id,
        is_active=user_with_roles.is_active,
        last_login=user_with_roles.last_login.isoformat() if user_with_roles.last_login else None,
        created_at=user_with_roles.created_at.isoformat(),
        updated_at=user_with_roles.updated_at.isoformat() if user_with_roles.updated_at else user_with_roles.created_at.isoformat(),
        roles=[{"id": role.id, "name": role.name} for role in user_with_roles.roles]
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Actualizar usuario existente.
    
    Solo administradores pueden actualizar usuarios.
    Los usuarios pueden actualizar su propio perfil a través de /users/me.
    
    Parámetros:
    - user_id: ID del usuario a actualizar
    - user_data: Campos a actualizar
    
    Validaciones:
    - No se puede cambiar el tenant_id
    - Si se cambia email, debe ser único
    - Si se cambia password, debe cumplir políticas
    
    Returns:
    - Usuario actualizado
    """
    user_service = UserService(db)
    
    # Verificar que usuario exista y sea del mismo tenant
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede modificar usuarios de otros tenants"
        )
    
    # Verificar unicidad de email si se cambia
    if user_data.email and user_data.email != existing_user.email:
        email_user = await user_service.get_user_by_email(user_data.email)
        if email_user and email_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ya registrado en el sistema"
            )
    
    # Hash de password si se proporciona
    update_data = user_data.dict(exclude_unset=True)
    if "password" in update_data:
        if len(update_data["password"]) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 8 caracteres"
            )
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Actualizar usuario
    updated_user = await user_service.update_user(user_id, update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar usuario"
        )
    
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        tenant_id=updated_user.tenant_id,
        is_active=updated_user.is_active,
        last_login=updated_user.last_login.isoformat() if updated_user.last_login else None,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat() if updated_user.updated_at else updated_user.created_at.isoformat(),
        roles=[{"id": role.id, "name": role.name} for role in updated_user.roles]
    )


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualizar perfil del usuario actual.
    
    Cualquier usuario puede actualizar su propio perfil.
    
    Restricciones:
    - No puede cambiar su propio estado (is_active)
    - No puede cambiar su tenant_id
    - Verificaciones de unicidad de email
    
    Returns:
    - Perfil actualizado
    """
    user_service = UserService(db)
    
    # Filtrar campos que no puede cambiar
    update_data = user_data.dict(exclude_unset=True)
    if "is_active" in update_data:
        del update_data["is_active"]  # No puede cambiar su propio estado
    
    # Verificar unicidad de email si se cambia
    if "email" in update_data and update_data["email"] != current_user.email:
        email_user = await user_service.get_user_by_email(update_data["email"])
        if email_user and email_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ya registrado en el sistema"
            )
    
    # Hash de password si se proporciona
    if "password" in update_data:
        if len(update_data["password"]) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña debe tener al menos 8 caracteres"
            )
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    # Actualizar usuario
    updated_user = await user_service.update_user(current_user.id, update_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar perfil"
        )
    
    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        tenant_id=updated_user.tenant_id,
        is_active=updated_user.is_active,
        last_login=updated_user.last_login.isoformat() if updated_user.last_login else None,
        created_at=updated_user.created_at.isoformat(),
        updated_at=updated_user.updated_at.isoformat() if updated_user.updated_at else updated_user.created_at.isoformat(),
        roles=[{"id": role.id, "name": role.name} for role in updated_user.roles]
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Eliminar usuario.
    
    Solo administradores pueden eliminar usuarios.
    
    Restricciones:
    - No puede eliminarse a sí mismo
    - Usuario debe pertenecer al mismo tenant
    
    Returns:
    - 204 No Content si éxito
    """
    user_service = UserService(db)
    
    # Verificar que usuario exista y sea del mismo tenant
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede eliminar usuarios de otros tenants"
        )
    
    # No puede eliminarse a sí mismo
    if existing_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminarse a sí mismo"
        )
    
    # Eliminar usuario
    success = await user_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar usuario"
        )


@router.put("/{user_id}/roles")
async def update_user_roles(
    user_id: int,
    role_ids: List[int],
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Actualizar roles de usuario.
    
    Solo administradores pueden asignar roles.
    
    Parámetros:
    - user_id: ID del usuario
    - role_ids: Lista de IDs de roles a asignar
    
    Returns:
    - Mensaje de confirmación
    """
    user_service = UserService(db)
    
    # Verificar que usuario exista y sea del mismo tenant
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede modificar usuarios de otros tenants"
        )
    
    # Verificar que todos los roles existan
    role_service = RoleService(db)
    for role_id in role_ids:
        role = await role_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rol ID {role_id} no encontrado"
            )
    
    # Actualizar roles
    success = await user_service.update_user_roles(user_id, role_ids)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar roles"
        )
    
    return {"message": "Roles actualizados correctamente"}


@router.put("/{user_id}/activate")
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Activar usuario inactivo.
    
    Solo administradores pueden activar usuarios.
    
    Returns:
    - Mensaje de confirmación
    """
    user_service = UserService(db)
    
    # Verificar que usuario exista y sea del mismo tenant
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede modificar usuarios de otros tenants"
        )
    
    # Activar usuario
    success = await user_service.update_user(user_id, {"is_active": True})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al activar usuario"
        )
    
    return {"message": "Usuario activado correctamente"}


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Desactivar usuario activo.
    
    Solo administradores pueden desactivar usuarios.
    
    Restricciones:
    - No puede desactivarse a sí mismo
    
    Returns:
    - Mensaje de confirmación
    """
    user_service = UserService(db)
    
    # Verificar que usuario exista y sea del mismo tenant
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede modificar usuarios de otros tenants"
        )
    
    # No puede desactivarse a sí mismo
    if existing_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivarse a sí mismo"
        )
    
    # Desactivar usuario
    success = await user_service.update_user(user_id, {"is_active": False})
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al desactivar usuario"
        )
    
    return {"message": "Usuario desactivado correctamente"}


@router.get("/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Obtener permisos de usuario.
    
    Útil para verificar qué permisos tiene un usuario específico.
    
    Returns:
    - Lista de permisos agrupados por rol
    """
    user_service = UserService(db)
    
    # Verificar que usuario exista y sea del mismo tenant
    existing_user = await user_service.get_user_by_id(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if existing_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede acceder a usuarios de otros tenants"
        )
    
    # Obtener permisos de roles
    permissions_by_role = []
    all_permissions = set()
    
    for role in existing_user.roles:
        role_permissions = []
        if role.permissions:
            # Asumiendo que permissions es JSON string
            import json
            try:
                role_permissions = json.loads(role.permissions)
            except:
                role_permissions = [role.permissions]
        
        permissions_by_role.append({
            "role_id": role.id,
            "role_name": role.name,
            "permissions": role_permissions
        })
        
        all_permissions.update(role_permissions)
    
    return {
        "user_id": existing_user.id,
        "username": existing_user.username,
        "permissions_by_role": permissions_by_role,
        "all_permissions": list(all_permissions),
        "effective_permissions_count": len(all_permissions)
    }