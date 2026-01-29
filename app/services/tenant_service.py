"""
Servicio para gestión de tenants (empresas) en el sistema multi-tenant.
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime

from models.wms_models import Tenant, User


class TenantService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """Obtener tenant por ID"""
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_tenant_by_name(self, name: str) -> Optional[Tenant]:
        """Obtener tenant por nombre"""
        stmt = select(Tenant).where(Tenant.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_tenants(
        self, 
        skip: int = 0, 
        limit: int = 100,
        active_only: bool = True
    ) -> Tuple[List[Tenant], int]:
        """Obtener todos los tenants con paginación"""
        query = select(Tenant)
        
        if active_only:
            query = query.where(Tenant.is_active == True)
        
        # Contar total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Obtener datos paginados
        stmt = (
            query
            .order_by(Tenant.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        tenants = result.scalars().all()
        
        return tenants, total
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Tenant:
        """Crear nuevo tenant"""
        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant
    
    async def update_tenant(self, tenant_id: int, update_data: Dict[str, Any]) -> Optional[Tenant]:
        """Actualizar tenant"""
        update_data.pop("id", None)
        update_data.pop("created_at", None)
        update_data["updated_at"] = datetime.utcnow()
        
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(**update_data)
            .returning(Tenant)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        if result.rowcount > 0:
            return await self.get_tenant_by_id(tenant_id)
        return None
    
    async def delete_tenant(self, tenant_id: int) -> bool:
        """Eliminar tenant (marcar como inactivo)"""
        try:
            # En lugar de eliminar, marcamos como inactivo
            stmt = (
                update(Tenant)
                .where(Tenant.id == tenant_id)
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        except Exception:
            await self.db.rollback()
            return False
    
    async def get_tenant_stats(self, tenant_id: int) -> Dict[str, Any]:
        """Obtener estadísticas de un tenant"""
        from services.user_service import UserService
        from services.audit_service import AuditService
        
        user_service = UserService(self.db)
        audit_service = AuditService(self.db)
        
        # Contar usuarios
        total_users = await user_service.count_users_by_tenant(tenant_id)
        active_users = await user_service.count_active_users_by_tenant(tenant_id)
        
        # Obtener actividad reciente (últimos 7 días)
        since_date = datetime.utcnow() - timedelta(days=7)
        logs, _ = await audit_service.get_logs(
            tenant_id=tenant_id,
            start_date=since_date,
            limit=1000
        )
        
        # Contar por tipo de acción
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        return {
            "tenant_id": tenant_id,
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users
            },
            "activity_last_7_days": {
                "total_actions": len(logs),
                "action_breakdown": action_counts
            },
            "subscription": {
                "level": "premium",  # Esto vendría de la base de datos
                "is_active": True
            }
        }
    
    async def search_tenants(self, search_term: str, limit: int = 50) -> List[Tenant]:
        """Buscar tenants por término"""
        search_pattern = f"%{search_term}%"
        
        stmt = (
            select(Tenant)
            .where(
                and_(
                    Tenant.is_active == True,
                    or_(
                        Tenant.name.ilike(search_pattern),
                        Tenant.subscription_level.ilike(search_pattern)
                    )
                )
            )
            .order_by(Tenant.name)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def update_subscription_level(
        self, 
        tenant_id: int, 
        new_level: str
    ) -> bool:
        """Actualizar nivel de suscripción del tenant"""
        valid_levels = ["basic", "premium", "enterprise"]
        
        if new_level not in valid_levels:
            return False
        
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                subscription_level=new_level,
                updated_at=datetime.utcnow()
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def activate_tenant(self, tenant_id: int) -> bool:
        """Activar tenant"""
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                is_active=True,
                updated_at=datetime.utcnow()
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def deactivate_tenant(self, tenant_id: int) -> bool:
        """Desactivar tenant"""
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow()
            )
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def get_tenant_users(self, tenant_id: int) -> List[User]:
        """Obtener usuarios de un tenant"""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .options(selectinload(User.roles))
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()