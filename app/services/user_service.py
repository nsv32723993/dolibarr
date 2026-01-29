"""
Servicio para gestión de usuarios.
Contiene lógica de negocio relacionada con usuarios.
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime

from models.wms_models import User, Role, UserRole, Tenant
from core.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Obtener usuario por ID con roles y tenant"""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.roles),
                joinedload(User.tenant)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtener usuario por email"""
        stmt = (
            select(User)
            .where(func.lower(User.email) == func.lower(email))
            .options(selectinload(User.roles))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str, tenant_id: int) -> Optional[User]:
        """Obtener usuario por username dentro de un tenant"""
        stmt = (
            select(User)
            .where(
                and_(
                    func.lower(User.username) == func.lower(username),
                    User.tenant_id == tenant_id
                )
            )
            .options(selectinload(User.roles))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_users_by_tenant(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """Listar usuarios por tenant"""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
            .options(selectinload(User.roles))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_users_by_tenant_paginated(
        self, 
        tenant_id: int, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """Listar usuarios por tenant con paginación y filtros"""
        # Query base
        query = select(User).where(User.tenant_id == tenant_id)
        
        # Aplicar filtros
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term)
                )
            )
        
        # Contar total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Obtener datos paginados
        stmt = (
            query
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
            .options(selectinload(User.roles))
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        
        return users, total
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Crear nuevo usuario"""
        user = User(**user_data)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
        """Actualizar usuario"""
        # Eliminar campos que no se pueden actualizar directamente
        update_data.pop("id", None)
        update_data.pop("tenant_id", None)  # No se puede cambiar tenant
        update_data.pop("created_at", None)
        
        # Si se actualiza email, asegurar lowercase
        if "email" in update_data:
            update_data["email"] = update_data["email"].lower()
        
        # Si se actualiza username, asegurar lowercase
        if "username" in update_data:
            update_data["username"] = update_data["username"].lower()
        
        # Agregar timestamp de actualización
        update_data["updated_at"] = datetime.utcnow()
        
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
            .returning(User)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount > 0:
            return await self.get_user_by_id(user_id)
        return None
    
    async def delete_user(self, user_id: int) -> bool:
        """Eliminar usuario y sus relaciones"""
        try:
            # Primero eliminar relaciones en user_roles
            delete_roles_stmt = delete(UserRole).where(UserRole.user_id == user_id)
            await self.db.execute(delete_roles_stmt)
            
            # Luego eliminar usuario
            delete_user_stmt = delete(User).where(User.id == user_id)
            result = await self.db.execute(delete_user_stmt)
            await self.db.commit()
            
            return result.rowcount > 0
        except Exception:
            await self.db.rollback()
            return False
    
    async def update_user_roles(self, user_id: int, role_ids: List[int]) -> bool:
        """Actualizar roles de usuario"""
        try:
            # Eliminar roles actuales
            delete_stmt = delete(UserRole).where(UserRole.user_id == user_id)
            await self.db.execute(delete_stmt)
            
            # Agregar nuevos roles
            for role_id in role_ids:
                user_role = UserRole(user_id=user_id, role_id=role_id)
                self.db.add(user_role)
            
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def add_role_to_user(self, user_id: int, role_id: int) -> bool:
        """Agregar rol a usuario"""
        try:
            # Verificar que no exista ya
            stmt = select(UserRole).where(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                return True  # Ya existe, no es error
            
            user_role = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(user_role)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """Remover rol de usuario"""
        try:
            stmt = delete(UserRole).where(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id
                )
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception:
            await self.db.rollback()
            return False
    
    async def update_last_login(self, user_id: int) -> bool:
        """Actualizar timestamp de último login"""
        try:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(last_login=datetime.utcnow())
            )
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def change_password(self, user_id: int, new_password: str) -> bool:
        """Cambiar contraseña de usuario"""
        try:
            hashed_password = get_password_hash(new_password)
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(
                    hashed_password=hashed_password,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def verify_user_password(self, user_id: int, password: str) -> bool:
        """Verificar contraseña de usuario"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        return verify_password(password, user.hashed_password)
    
    async def count_users_by_tenant(self, tenant_id: int) -> int:
        """Contar usuarios por tenant"""
        stmt = select(func.count(User.id)).where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def count_active_users_by_tenant(self, tenant_id: int) -> int:
        """Contar usuarios activos por tenant"""
        stmt = select(func.count(User.id)).where(
            and_(
                User.tenant_id == tenant_id,
                User.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def search_users(
        self, 
        tenant_id: int, 
        search_term: str,
        limit: int = 50
    ) -> List[User]:
        """Buscar usuarios por término"""
        search_pattern = f"%{search_term}%"
        
        stmt = (
            select(User)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    or_(
                        User.username.ilike(search_pattern),
                        User.email.ilike(search_pattern),
                        User.full_name.ilike(search_pattern)
                    )
                )
            )
            .order_by(User.username)
            .limit(limit)
            .options(selectinload(User.roles))
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_users_by_role(self, tenant_id: int, role_name: str) -> List[User]:
        """Obtener usuarios por nombre de rol"""
        stmt = (
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(
                and_(
                    User.tenant_id == tenant_id,
                    User.is_active == True,
                    Role.name == role_name
                )
            )
            .options(selectinload(User.roles))
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def bulk_update_users_status(
        self, 
        tenant_id: int, 
        user_ids: List[int], 
        is_active: bool
    ) -> int:
        """Actualizar estado de múltiples usuarios"""
        try:
            stmt = (
                update(User)
                .where(
                    and_(
                        User.tenant_id == tenant_id,
                        User.id.in_(user_ids)
                    )
                )
                .values(
                    is_active=is_active,
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount
        except Exception:
            await self.db.rollback()
            return 0
    
    async def create_initial_admin(self, tenant_id: int) -> Optional[User]:
        """Crear usuario admin inicial para un tenant"""
        try:
            # Verificar si ya existe admin
            admin_users = await self.get_users_by_role(tenant_id, "admin")
            if admin_users:
                return admin_users[0]
            
            # Crear usuario admin
            admin_data = {
                "username": "admin",
                "email": f"admin@tenant{tenant_id}.com",
                "full_name": "Administrador Inicial",
                "hashed_password": get_password_hash("admin123"),
                "tenant_id": tenant_id,
                "is_active": True
            }
            
            admin = await self.create_user(admin_data)
            
            # Asignar rol admin
            stmt = select(Role).where(Role.name == "admin")
            result = await self.db.execute(stmt)
            admin_role = result.scalar_one_or_none()
            
            if admin_role:
                await self.add_role_to_user(admin.id, admin_role.id)
            
            return await self.get_user_by_id(admin.id)
        except Exception as e:
            print(f"Error creando admin inicial: {e}")
            return None