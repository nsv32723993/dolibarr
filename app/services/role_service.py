"""
Servicio para gestión de roles.
Contiene lógica de negocio relacionada con roles y permisos.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
import json

from models.wms_models import Role, UserRole, User


class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_roles(self) -> List[Role]:
        """Obtener todos los roles"""
        stmt = select(Role).order_by(Role.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """Obtener rol por ID"""
        stmt = select(Role).where(Role.id == role_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Obtener rol por nombre"""
        stmt = select(Role).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_role(self, role_data: Dict[str, Any]) -> Role:
        """Crear nuevo rol"""
        # Manejar campo 'permissions' explícitamente para evitar errores
        permissions = role_data.pop("permissions", None)
        role = Role(**role_data)
        if permissions is not None:
            role.permissions = permissions
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role
    
    async def update_role(self, role_id: int, update_data: Dict[str, Any]) -> Optional[Role]:
        """Actualizar rol"""
        update_data.pop("id", None)
        update_data.pop("created_at", None)
        
        stmt = (
            update(Role)
            .where(Role.id == role_id)
            .values(**update_data)
            .returning(Role)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount > 0:
            return await self.get_role_by_id(role_id)
        return None
    
    async def delete_role(self, role_id: int) -> bool:
        """Eliminar rol (si no tiene usuarios asignados)"""
        try:
            # Verificar si tiene usuarios asignados
            stmt = select(func.count(UserRole.user_id)).where(UserRole.role_id == role_id)
            result = await self.db.execute(stmt)
            user_count = result.scalar() or 0
            
            if user_count > 0:
                return False  # No se puede eliminar si tiene usuarios
            
            # Eliminar rol
            stmt = delete(Role).where(Role.id == role_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            return result.rowcount > 0
        except Exception:
            await self.db.rollback()
            return False
    
    async def get_users_with_role(self, role_id: int) -> List[User]:
        """Obtener usuarios que tienen un rol específico"""
        stmt = (
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .where(UserRole.role_id == role_id)
            .options(selectinload(User.roles))
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_role_permissions(self, role_id: int) -> List[str]:
        """Obtener permisos de un rol"""
        role = await self.get_role_by_id(role_id)
        if not role or not role.permissions:
            return []
        
        try:
            return json.loads(role.permissions)
        except:
            return [role.permissions]
    
    async def update_role_permissions(self, role_id: int, permissions: List[str]) -> bool:
        """Actualizar permisos de un rol"""
        try:
            permissions_json = json.dumps(permissions)
            stmt = (
                update(Role)
                .where(Role.id == role_id)
                .values(permissions=permissions_json)
            )
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def add_permission_to_role(self, role_id: int, permission: str) -> bool:
        """Agregar permiso a un rol"""
        current_permissions = await self.get_role_permissions(role_id)
        
        if permission not in current_permissions:
            current_permissions.append(permission)
            return await self.update_role_permissions(role_id, current_permissions)
        
        return True
    
    async def remove_permission_from_role(self, role_id: int, permission: str) -> bool:
        """Remover permiso de un rol"""
        current_permissions = await self.get_role_permissions(role_id)
        
        if permission in current_permissions:
            current_permissions.remove(permission)
            return await self.update_role_permissions(role_id, current_permissions)
        
        return True
    
    async def get_roles_with_permission(self, permission: str) -> List[Role]:
        """Obtener roles que tienen un permiso específico"""
        all_roles = await self.get_all_roles()
        roles_with_permission = []
        
        for role in all_roles:
            if role.permissions:
                try:
                    permissions = json.loads(role.permissions)
                    if permission in permissions:
                        roles_with_permission.append(role)
                except:
                    if permission == role.permissions:
                        roles_with_permission.append(role)
        
        return roles_with_permission
    
    async def create_default_roles(self, tenant_id: int) -> List[Role]:
        """Crear roles por defecto del sistema"""
        default_roles = [
            {
                "name": "admin",
                "description": "Administrador del sistema con acceso completo",
                "permissions": json.dumps([
                    "users:read", "users:create", "users:update", "users:delete",
                    "roles:read", "roles:create", "roles:update", "roles:delete",
                    "inventory:read", "inventory:create", "inventory:update", "inventory:delete",
                    "orders:read", "orders:create", "orders:update", "orders:delete",
                    "audit:read", "settings:read", "settings:update",
                    "dolibarr:integrate", "reports:generate"
                ]),
                "tenant_id": tenant_id
            },
            {
                "name": "operator",
                "description": "Operario de bodega con acceso a operaciones",
                "permissions": json.dumps([
                    "inventory:read", "inventory:update",
                    "orders:read", "orders:update",
                    "reports:read"
                ]),
                "tenant_id": tenant_id
            },
            {
                "name": "auditor",
                "description": "Auditor con acceso de solo lectura",
                "permissions": json.dumps([
                    "audit:read",
                    "inventory:read",
                    "orders:read",
                    "reports:read"
                ]),
                "tenant_id": tenant_id
            },
            {
                "name": "dolibarr_client",
                "description": "Cliente Dolibarr para integraciones automáticas",
                "permissions": json.dumps([
                    "inventory:read", "inventory:update",
                    "orders:read", "orders:create", "orders:update",
                    "dolibarr:integrate"
                ]),
                "tenant_id": tenant_id
            }
        ]
        
        created_roles = []
        for role_data in default_roles:
            # Verificar si ya existe
            existing = await self.get_role_by_name(role_data["name"])
            if not existing:
                role = await self.create_role(role_data)
                created_roles.append(role)
            else:
                created_roles.append(existing)
        
        return created_roles
    
    async def count_users_by_role(self, role_id: int) -> int:
        """Contar usuarios que tienen un rol específico"""
        stmt = select(func.count(UserRole.user_id)).where(UserRole.role_id == role_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def search_roles(self, search_term: str, limit: int = 50) -> List[Role]:
        """Buscar roles por término"""
        search_pattern = f"%{search_term}%"
        
        stmt = (
            select(Role)
            .where(
                or_(
                    Role.name.ilike(search_pattern),
                    Role.description.ilike(search_pattern)
                )
            )
            .order_by(Role.name)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()