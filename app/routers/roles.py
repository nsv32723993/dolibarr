"""
Rutas para gestión de roles del sistema WMS.
Endpoints protegidos por rol de administrador.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json

from core.database import get_wms_db
from core.dependencies import get_current_user, require_admin
from models.wms_models import Role, User
from services.role_service import RoleService
from services.user_service import UserService

router = APIRouter(prefix="/roles", tags=["Roles"])


# Schemas para roles
class PermissionItem(BaseModel):
    """Item de permiso"""
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None


class RoleBase(BaseModel):
    """Base para roles"""
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class RoleCreate(RoleBase):
    """Request para crear rol"""
    permissions: Optional[List[str]] = []


class RoleUpdate(BaseModel):
    """Request para actualizar rol"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    """Response de rol"""
    id: int
    permissions: List[str] = []
    created_at: str
    user_count: int = 0
    
    class Config:
        from_attributes = True


class RoleDetailResponse(RoleResponse):
    """Response detallado de rol"""
    users: List[Dict[str, Any]] = []


class RoleListResponse(BaseModel):
    """Response para lista de roles"""
    roles: List[RoleResponse]
    total: int
    page: int
    page_size: int


class PermissionListResponse(BaseModel):
    """Response para lista de permisos disponibles"""
    permissions: List[PermissionItem]
    categories: List[str]
    total: int


@router.get("/", response_model=RoleListResponse)
async def list_roles(
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros por página"),
    search: Optional[str] = Query(None, description="Buscar por nombre o descripción"),
    include_user_count: bool = Query(False, description="Incluir conteo de usuarios"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Listar roles del sistema.
    
    Solo administradores pueden ver y gestionar roles.
    
    Parámetros de query:
    - skip: Paginación (offset)
    - limit: Límite por página (max 200)
    - search: Buscar por nombre o descripción
    - include_user_count: Incluir conteo de usuarios por rol
    
    Returns:
    - Lista de roles con paginación
    """
    role_service = RoleService(db)
    
    if search:
        roles = await role_service.search_roles(search, limit)
        total = len(roles)
        roles = roles[skip:skip + limit]
    else:
        roles = await role_service.get_all_roles()
        total = len(roles)
        roles = roles[skip:skip + limit]
    
    # Construir response
    role_responses = []
    for role in roles:
        permissions = []
        if role.permissions:
            try:
                permissions = json.loads(role.permissions)
            except:
                permissions = [role.permissions]
        
        user_count = 0
        if include_user_count:
            user_count = await role_service.count_users_by_role(role.id)
        
        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at.isoformat() if role.created_at else "",
            user_count=user_count
        ))
    
    return RoleListResponse(
        roles=role_responses,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/available-permissions", response_model=PermissionListResponse)
async def get_available_permissions(
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtener lista de permisos disponibles en el sistema.
    
    Útil para asignar permisos a roles nuevos o existentes.
    
    Returns:
    - Lista de permisos organizados por categorías
    """
    # Permisos predefinidos del sistema WMS
    permissions_db = [
        # Usuarios y roles
        PermissionItem(code="users:read", name="Ver usuarios", 
                      description="Ver lista de usuarios", category="users"),
        PermissionItem(code="users:create", name="Crear usuarios", 
                      description="Crear nuevos usuarios", category="users"),
        PermissionItem(code="users:update", name="Actualizar usuarios", 
                      description="Modificar usuarios existentes", category="users"),
        PermissionItem(code="users:delete", name="Eliminar usuarios", 
                      description="Eliminar usuarios del sistema", category="users"),
        
        PermissionItem(code="roles:read", name="Ver roles", 
                      description="Ver lista de roles", category="roles"),
        PermissionItem(code="roles:create", name="Crear roles", 
                      description="Crear nuevos roles", category="roles"),
        PermissionItem(code="roles:update", name="Actualizar roles", 
                      description="Modificar roles existentes", category="roles"),
        PermissionItem(code="roles:delete", name="Eliminar roles", 
                      description="Eliminar roles del sistema", category="roles"),
        
        # Inventario
        PermissionItem(code="inventory:read", name="Ver inventario", 
                      description="Consultar stock y ubicaciones", category="inventory"),
        PermissionItem(code="inventory:create", name="Crear inventario", 
                      description="Agregar productos al inventario", category="inventory"),
        PermissionItem(code="inventory:update", name="Actualizar inventario", 
                      description="Modificar existencias", category="inventory"),
        PermissionItem(code="inventory:delete", name="Eliminar inventario", 
                      description="Eliminar productos del inventario", category="inventory"),
        
        # Órdenes
        PermissionItem(code="orders:read", name="Ver órdenes", 
                      description="Consultar órdenes de picking", category="orders"),
        PermissionItem(code="orders:create", name="Crear órdenes", 
                      description="Crear nuevas órdenes", category="orders"),
        PermissionItem(code="orders:update", name="Actualizar órdenes", 
                      description="Modificar órdenes existentes", category="orders"),
        PermissionItem(code="orders:delete", name="Eliminar órdenes", 
                      description="Eliminar órdenes del sistema", category="orders"),
        
        # Recepción (Inbound)
        PermissionItem(code="inbound:read", name="Ver recepciones", 
                      description="Consultar recepciones de mercancía", category="inbound"),
        PermissionItem(code="inbound:create", name="Registrar recepción", 
                      description="Registrar nueva recepción", category="inbound"),
        PermissionItem(code="inbound:update", name="Actualizar recepción", 
                      description="Modificar recepciones existentes", category="inbound"),
        
        # Auditoría
        PermissionItem(code="audit:read", name="Ver auditoría", 
                      description="Consultar logs de auditoría", category="audit"),
        PermissionItem(code="audit:export", name="Exportar auditoría", 
                      description="Exportar logs de auditoría", category="audit"),
        
        # Reportes
        PermissionItem(code="reports:read", name="Ver reportes", 
                      description="Consultar reportes del sistema", category="reports"),
        PermissionItem(code="reports:generate", name="Generar reportes", 
                      description="Generar nuevos reportes", category="reports"),
        PermissionItem(code="reports:export", name="Exportar reportes", 
                      description="Exportar reportes a diferentes formatos", category="reports"),
        
        # Configuración
        PermissionItem(code="settings:read", name="Ver configuración", 
                      description="Consultar configuración del sistema", category="settings"),
        PermissionItem(code="settings:update", name="Actualizar configuración", 
                      description="Modificar configuración del sistema", category="settings"),
        
        # Integración Dolibarr
        PermissionItem(code="dolibarr:integrate", name="Integración Dolibarr", 
                      description="Acceder a funciones de integración con Dolibarr", category="integration"),
        PermissionItem(code="dolibarr:sync", name="Sincronización Dolibarr", 
                      description="Sincronizar datos con Dolibarr", category="integration"),
        
        # Dashboard
        PermissionItem(code="dashboard:view", name="Ver dashboard", 
                      description="Acceder al dashboard principal", category="dashboard"),
        PermissionItem(code="dashboard:customize", name="Personalizar dashboard", 
                      description="Personalizar widgets del dashboard", category="dashboard"),
    ]
    
    # Extraer categorías únicas
    categories = sorted(list(set([p.category for p in permissions_db if p.category])))
    
    return PermissionListResponse(
        permissions=permissions_db,
        categories=categories,
        total=len(permissions_db)
    )


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: int,
    include_users: bool = Query(False, description="Incluir lista de usuarios"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtener rol por ID con detalles.
    
    Solo administradores pueden ver detalles de roles.
    
    Parámetros:
    - role_id: ID del rol a consultar
    - include_users: Incluir lista de usuarios que tienen este rol
    
    Returns:
    - Información detallada del rol
    """
    role_service = RoleService(db)
    role = await role_service.get_role_by_id(role_id)
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Obtener permisos
    permissions = []
    if role.permissions:
        try:
            permissions = json.loads(role.permissions)
        except:
            permissions = [role.permissions]
    
    # Obtener usuarios si se solicita
    users_list = []
    if include_users:
        users = await role_service.get_users_with_role(role_id)
        users_list = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active
            }
            for user in users
        ]
    
    # Contar usuarios
    user_count = await role_service.count_users_by_role(role_id)
    
    return RoleDetailResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=permissions,
        created_at=role.created_at.isoformat() if role.created_at else "",
        user_count=user_count,
        users=users_list
    )


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Crear nuevo rol.
    
    Solo administradores pueden crear roles.
    
    Parámetros:
    - role_data: Datos del nuevo rol
    
    Validaciones:
    - Nombre único en el sistema
    - Permisos deben existir en la lista de permisos disponibles
    
    Returns:
    - Rol creado
    """
    role_service = RoleService(db)
    
    # Verificar que nombre no exista
    existing_role = await role_service.get_role_by_name(role_data.name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese nombre"
        )
    
    # Validar permisos (opcional, se podría validar contra lista de permisos disponibles)
    
    # Crear rol
    role_dict = role_data.dict(exclude={"permissions"})
    
    # Convertir permisos a JSON
    if role_data.permissions:
        role_dict["permissions"] = json.dumps(role_data.permissions)
    
    role = await role_service.create_role(role_dict)
    
    # Obtener permisos para response
    permissions = role_data.permissions if role_data.permissions else []
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=permissions,
        created_at=role.created_at.isoformat() if role.created_at else "",
        user_count=0
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Actualizar rol existente.
    
    Solo administradores pueden actualizar roles.
    
    Parámetros:
    - role_id: ID del rol a actualizar
    - role_data: Campos a actualizar
    
    Validaciones:
    - Si se cambia nombre, debe ser único
    - No se pueden modificar roles del sistema (admin, operator, etc.)
    
    Returns:
    - Rol actualizado
    """
    role_service = RoleService(db)
    
    # Verificar que rol exista
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Verificar que no sea un rol del sistema (si aplica)
    system_roles = ["admin", "operator", "auditor", "dolibarr_client"]
    if existing_role.name in system_roles and role_data.name and role_data.name != existing_role.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cambiar el nombre de roles del sistema"
        )
    
    # Verificar unicidad de nombre si se cambia
    if role_data.name and role_data.name != existing_role.name:
        name_role = await role_service.get_role_by_name(role_data.name)
        if name_role and name_role.id != role_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un rol con ese nombre"
            )
    
    # Preparar datos de actualización
    update_data = role_data.dict(exclude_unset=True)
    
    # Convertir permisos a JSON si se proporcionan
    if "permissions" in update_data:
        update_data["permissions"] = json.dumps(update_data["permissions"])
    
    # Actualizar rol
    updated_role = await role_service.update_role(role_id, update_data)
    
    if not updated_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar rol"
        )
    
    # Obtener permisos actualizados
    permissions = []
    if updated_role.permissions:
        try:
            permissions = json.loads(updated_role.permissions)
        except:
            permissions = [updated_role.permissions]
    
    # Contar usuarios
    user_count = await role_service.count_users_by_role(role_id)
    
    return RoleResponse(
        id=updated_role.id,
        name=updated_role.name,
        description=updated_role.description,
        permissions=permissions,
        created_at=updated_role.created_at.isoformat() if updated_role.created_at else "",
        user_count=user_count
    )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    force: bool = Query(False, description="Forzar eliminación incluso si tiene usuarios"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Eliminar rol.
    
    Solo administradores pueden eliminar roles.
    
    Restricciones:
    - No se pueden eliminar roles del sistema
    - No se pueden eliminar roles con usuarios asignados (a menos que force=True)
    
    Parámetros:
    - role_id: ID del rol a eliminar
    - force: Forzar eliminación incluso si tiene usuarios
    
    Returns:
    - 204 No Content si éxito
    """
    role_service = RoleService(db)
    
    # Verificar que rol exista
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Verificar que no sea un rol del sistema
    system_roles = ["admin", "operator", "auditor", "dolibarr_client"]
    if existing_role.name in system_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden eliminar roles del sistema"
        )
    
    # Verificar si tiene usuarios asignados
    user_count = await role_service.count_users_by_role(role_id)
    
    if user_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol tiene {user_count} usuarios asignados. Use force=true para eliminar de todos modos."
        )
    
    # Si force=True y tiene usuarios, primero eliminar relaciones
    if user_count > 0 and force:
        user_service = UserService(db)
        users = await role_service.get_users_with_role(role_id)
        
        for user in users:
            await user_service.remove_role_from_user(user.id, role_id)
    
    # Eliminar rol
    success = await role_service.delete_role(role_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al eliminar rol"
        )


@router.put("/{role_id}/permissions")
async def update_role_permissions(
    role_id: int,
    permissions: List[str],
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Actualizar permisos de un rol.
    
    Solo administradores pueden modificar permisos de roles.
    
    Parámetros:
    - role_id: ID del rol
    - permissions: Lista de códigos de permisos
    
    Returns:
    - Mensaje de confirmación
    """
    role_service = RoleService(db)
    
    # Verificar que rol exista
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Actualizar permisos
    success = await role_service.update_role_permissions(role_id, permissions)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar permisos"
        )
    
    return {
        "message": "Permisos actualizados correctamente",
        "role_id": role_id,
        "permissions_count": len(permissions)
    }


@router.post("/{role_id}/permissions/{permission}")
async def add_permission_to_role(
    role_id: int,
    permission: str,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Agregar permiso a un rol.
    
    Solo administradores pueden agregar permisos.
    
    Parámetros:
    - role_id: ID del rol
    - permission: Código del permiso a agregar
    
    Returns:
    - Mensaje de confirmación
    """
    role_service = RoleService(db)
    
    # Verificar que rol exista
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Agregar permiso
    success = await role_service.add_permission_to_role(role_id, permission)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al agregar permiso"
        )
    
    return {
        "message": f"Permiso '{permission}' agregado correctamente",
        "role_id": role_id,
        "permission": permission
    }


@router.delete("/{role_id}/permissions/{permission}")
async def remove_permission_from_role(
    role_id: int,
    permission: str,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Remover permiso de un rol.
    
    Solo administradores pueden remover permisos.
    
    Parámetros:
    - role_id: ID del rol
    - permission: Código del permiso a remover
    
    Returns:
    - Mensaje de confirmación
    """
    role_service = RoleService(db)
    
    # Verificar que rol exista
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Verificar que no sea un permiso crítico de roles del sistema
    system_roles = ["admin", "operator", "auditor"]
    critical_permissions = {
        "admin": ["users:create", "roles:create"],
        "operator": ["inventory:update", "orders:update"]
    }
    
    if existing_role.name in system_roles and permission in critical_permissions.get(existing_role.name, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede remover el permiso '{permission}' del rol '{existing_role.name}'"
        )
    
    # Remover permiso
    success = await role_service.remove_permission_from_role(role_id, permission)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al remover permiso"
        )
    
    return {
        "message": f"Permiso '{permission}' removido correctamente",
        "role_id": role_id,
        "permission": permission
    }


@router.get("/{role_id}/users")
async def get_role_users(
    role_id: int,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=200, description="Límite de registros por página"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtener usuarios que tienen un rol específico.
    
    Solo administradores pueden ver esta información.
    
    Parámetros:
    - role_id: ID del rol
    - skip: Paginación (offset)
    - limit: Límite por página
    
    Returns:
    - Lista de usuarios con paginación
    """
    role_service = RoleService(db)
    user_service = UserService(db)
    
    # Verificar que rol exista
    existing_role = await role_service.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Obtener usuarios
    all_users = await role_service.get_users_with_role(role_id)
    total = len(all_users)
    
    # Paginar
    users = all_users[skip:skip + limit]
    
    # Formatear response
    user_list = []
    for user in users:
        user_list.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
            "tenant_id": user.tenant_id
        })
    
    return {
        "role_id": role_id,
        "role_name": existing_role.name,
        "users": user_list,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit
    }


@router.post("/initialize-defaults")
async def initialize_default_roles(
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Inicializar roles por defecto del sistema.
    
    Crea los roles básicos necesarios para el funcionamiento del WMS:
    - admin: Administrador completo
    - operator: Operario de bodega
    - auditor: Auditor de procesos
    - dolibarr_client: Cliente para integración con Dolibarr
    
    Solo administradores pueden ejecutar esta acción.
    
    Returns:
    - Lista de roles creados/actualizados
    """
    role_service = RoleService(db)
    
    # Crear roles por defecto
    roles = await role_service.create_default_roles()
    
    return {
        "message": "Roles por defecto inicializados correctamente",
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "created": True
            }
            for role in roles
        ],
        "total_created": len(roles)
    }


@router.get("/check-permission/{permission}")
async def check_who_has_permission(
    permission: str,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Verificar qué roles tienen un permiso específico.
    
    Útil para auditoría y gestión de permisos.
    
    Parámetros:
    - permission: Código del permiso a verificar
    
    Returns:
    - Lista de roles que tienen el permiso
    """
    role_service = RoleService(db)
    
    roles = await role_service.get_roles_with_permission(permission)
    
    return {
        "permission": permission,
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description
            }
            for role in roles
        ],
        "total_roles": len(roles)
    }