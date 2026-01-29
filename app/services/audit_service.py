"""
Servicio para gestión de auditoría y logs del sistema.
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, between
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timedelta
import json

from models.wms_models import AuditLog, User
from core.database import get_wms_db


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_log(self, log_data: Dict[str, Any]) -> AuditLog:
        """Crear registro de auditoría"""
        log = AuditLog(**log_data)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
    
    async def log_action(
        self,
        tenant_id: int,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        action: str = "UNKNOWN",
        resource_type: str = "system",
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request_path: str = "/",
        request_method: str = "GET",
        ip_address: str = "0.0.0.0",
        user_agent: Optional[str] = None,
        status_code: int = 200,
        response_time_ms: Optional[int] = None
    ) -> AuditLog:
        """Método helper para registrar acción de auditoría"""
        
        # Convertir detalles a JSON string si es dict
        details_str = None
        if details:
            if isinstance(details, dict):
                details_str = json.dumps(details, default=str)
            else:
                details_str = str(details)
        
        log_data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "username": username,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details_str,
            "request_path": request_path,
            "request_method": request_method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "status_code": status_code,
            "response_time_ms": response_time_ms
        }
        
        return await self.create_log(log_data)
    
    async def get_log_by_id(self, log_id: int) -> Optional[AuditLog]:
        """Obtener log por ID"""
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_logs(
        self,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_dir: str = "desc"
    ) -> Tuple[List[AuditLog], int]:
        """Obtener logs con filtros y paginación"""
        
        # Query base
        query = select(AuditLog)
        
        # Aplicar filtros
        if tenant_id is not None:
            query = query.where(AuditLog.tenant_id == tenant_id)
        
        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        
        if action:
            query = query.where(AuditLog.action == action)
        
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        
        if resource_id is not None:
            query = query.where(AuditLog.resource_id == resource_id)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
        
        if status_code is not None:
            query = query.where(AuditLog.status_code == status_code)
        
        # Contar total
        count_stmt = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Ordenar
        order_column = getattr(AuditLog, order_by, AuditLog.created_at)
        if order_dir.lower() == "desc":
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(order_column)
        
        # Paginar
        stmt = query.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        return logs, total
    
    async def get_user_activity(
        self,
        user_id: int,
        days: int = 7,
        limit: int = 50
    ) -> List[AuditLog]:
        """Obtener actividad reciente de un usuario"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= since_date
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_tenant_activity_summary(
        self,
        tenant_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """Obtener resumen de actividad por tenant"""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Total logs
        total_stmt = select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at >= since_date
            )
        )
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0
        
        # Por acción
        actions_stmt = (
            select(AuditLog.action, func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= since_date
                )
            )
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc())
        )
        actions_result = await self.db.execute(actions_stmt)
        actions = dict(actions_result.all())
        
        # Por recurso
        resources_stmt = (
            select(AuditLog.resource_type, func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= since_date
                )
            )
            .group_by(AuditLog.resource_type)
            .order_by(func.count(AuditLog.id).desc())
        )
        resources_result = await self.db.execute(resources_stmt)
        resources = dict(resources_result.all())
        
        # Por usuario
        users_stmt = (
            select(AuditLog.user_id, func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= since_date,
                    AuditLog.user_id.is_not(None)
                )
            )
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
        )
        users_result = await self.db.execute(users_stmt)
        users = dict(users_result.all())
        
        # Por código de estado
        status_stmt = (
            select(AuditLog.status_code, func.count(AuditLog.id))
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.created_at >= since_date
                )
            )
            .group_by(AuditLog.status_code)
            .order_by(AuditLog.status_code)
        )
        status_result = await self.db.execute(status_stmt)
        status_codes = dict(status_result.all())
        
        return {
            "period_days": days,
            "total_logs": total,
            "actions": actions,
            "resources": resources,
            "top_users": users,
            "status_codes": status_codes,
            "from_date": since_date.isoformat(),
            "to_date": datetime.utcnow().isoformat()
        }
    
    async def get_failed_logins(
        self,
        tenant_id: int,
        hours: int = 24,
        ip_address: Optional[str] = None
    ) -> List[AuditLog]:
        """Obtener intentos fallidos de login"""
        since_date = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(AuditLog).where(
            and_(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action == "LOGIN_FAILED",
                AuditLog.created_at >= since_date
            )
        )
        
        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
        
        query = query.order_by(desc(AuditLog.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_suspicious_activity(
        self,
        tenant_id: int,
        hours: int = 24,
        threshold: int = 10
    ) -> List[Dict[str, Any]]:
        """Detectar actividad sospechosa (múltiples fallos, IPs diferentes, etc.)"""
        since_date = datetime.utcnow() - timedelta(hours=hours)
        
        # Intentos fallidos por IP
        failed_by_ip_stmt = (
            select(
                AuditLog.ip_address,
                func.count(AuditLog.id).label("attempts"),
                func.array_agg(AuditLog.username.distinct()).label("usernames")
            )
            .where(
                and_(
                    AuditLog.tenant_id == tenant_id,
                    AuditLog.action == "LOGIN_FAILED",
                    AuditLog.created_at >= since_date
                )
            )
            .group_by(AuditLog.ip_address)
            .having(func.count(AuditLog.id) >= threshold)
        )
        
        result = await self.db.execute(failed_by_ip_stmt)
        suspicious_ips = []
        
        for row in result.all():
            suspicious_ips.append({
                "ip_address": row.ip_address,
                "attempts": row.attempts,
                "usernames": row.usernames,
                "type": "multiple_failed_logins"
            })
        
        return suspicious_ips
    
    async def purge_old_logs(
        self,
        older_than_days: int = 90,
        tenant_id: Optional[int] = None
    ) -> int:
        """Eliminar logs antiguos"""
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        from sqlalchemy import delete
        
        query = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        
        if tenant_id is not None:
            query = query.where(AuditLog.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        return result.rowcount
    
    async def export_logs(
        self,
        tenant_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> List[Dict[str, Any]]:
        """Exportar logs en formato específico"""
        logs, _ = await self.get_logs(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Límite para exportación
        )
        
        export_data = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "tenant_id": log.tenant_id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "request_path": log.request_path,
                "request_method": log.request_method,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "status_code": log.status_code,
                "response_time_ms": log.response_time_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            
            # Parsear detalles si existen
            if log.details:
                try:
                    log_dict["details"] = json.loads(log.details)
                except:
                    log_dict["details"] = log.details
            
            export_data.append(log_dict)
        
        return export_data
    
    async def log_login_success(
        self,
        tenant_id: int,
        user_id: int,
        username: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Registrar login exitoso"""
        return await self.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            action="LOGIN_SUCCESS",
            resource_type="user",
            resource_id=user_id,
            details={"event": "user_login", "result": "success"},
            request_path="/api/v1/auth/login",
            request_method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=200
        )
    
    async def log_login_failed(
        self,
        tenant_id: int,
        username: Optional[str],
        ip_address: str,
        user_agent: Optional[str] = None,
        reason: str = "invalid_credentials"
    ) -> AuditLog:
        """Registrar login fallido"""
        return await self.log_action(
            tenant_id=tenant_id,
            username=username,
            action="LOGIN_FAILED",
            resource_type="user",
            details={"event": "user_login", "result": "failed", "reason": reason},
            request_path="/api/v1/auth/login",
            request_method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=401
        )
    
    async def log_user_created(
        self,
        tenant_id: int,
        created_by_user_id: int,
        created_username: str,
        new_user_id: int,
        ip_address: str
    ) -> AuditLog:
        """Registrar creación de usuario"""
        return await self.log_action(
            tenant_id=tenant_id,
            user_id=created_by_user_id,
            username=created_username,
            action="USER_CREATED",
            resource_type="user",
            resource_id=new_user_id,
            details={"event": "user_creation", "created_by": created_by_user_id},
            request_path="/api/v1/users",
            request_method="POST",
            ip_address=ip_address,
            status_code=201
        )
    
    async def log_user_updated(
        self,
        tenant_id: int,
        updated_by_user_id: int,
        updated_username: str,
        target_user_id: int,
        changes: Dict[str, Any],
        ip_address: str
    ) -> AuditLog:
        """Registrar actualización de usuario"""
        return await self.log_action(
            tenant_id=tenant_id,
            user_id=updated_by_user_id,
            username=updated_username,
            action="USER_UPDATED",
            resource_type="user",
            resource_id=target_user_id,
            details={"event": "user_update", "updated_by": updated_by_user_id, "changes": changes},
            request_path=f"/api/v1/users/{target_user_id}",
            request_method="PUT",
            ip_address=ip_address,
            status_code=200
        )
    
    async def log_inbound_received(
        self,
        tenant_id: int,
        user_id: int,
        username: str,
        product_ref: str,
        quantity: float,
        warehouse_id: int,
        evidence_path: str,
        ip_address: str
    ) -> AuditLog:
        """Registrar recepción de mercancía"""
        return await self.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            action="INBOUND_RECEIVED",
            resource_type="inventory",
            details={
                "event": "inbound_reception",
                "product_ref": product_ref,
                "quantity": quantity,
                "warehouse_id": warehouse_id,
                "evidence_path": evidence_path
            },
            request_path="/api/v1/receive",
            request_method="POST",
            ip_address=ip_address,
            status_code=200
        )
    
    async def log_order_picked(
        self,
        tenant_id: int,
        user_id: int,
        username: str,
        order_id: int,
        products: List[Dict[str, Any]],
        ip_address: str
    ) -> AuditLog:
        """Registrar picking de orden"""
        return await self.log_action(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            action="ORDER_PICKED",
            resource_type="order",
            resource_id=order_id,
            details={
                "event": "order_picking",
                "order_id": order_id,
                "products": products
            },
            request_path=f"/api/v1/orders/{order_id}/close",
            request_method="POST",
            ip_address=ip_address,
            status_code=200
        )