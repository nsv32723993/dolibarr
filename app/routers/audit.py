"""
Rutas para consulta de logs de auditoría del sistema WMS.
Endpoints protegidos por roles de administrador o auditor.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta

from core.database import get_wms_db
from core.dependencies import get_current_user, require_admin, require_auditor
from models.wms_models import User
from services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


# Schemas para auditoría
class AuditLogResponse(BaseModel):
    """Response de log de auditoría"""
    id: int
    tenant_id: int
    user_id: Optional[int]
    username: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[int]
    details: Optional[Dict[str, Any]]
    request_path: str
    request_method: str
    ip_address: str
    user_agent: Optional[str]
    status_code: int
    response_time_ms: Optional[int]
    created_at: str
    
    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Response para lista de logs"""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
    filters: Dict[str, Any]


class ActivitySummaryResponse(BaseModel):
    """Response para resumen de actividad"""
    period_days: int
    total_logs: int
    actions: Dict[str, int]
    resources: Dict[str, int]
    top_users: Dict[int, int]
    status_codes: Dict[int, int]
    from_date: str
    to_date: str


class SuspiciousActivityItem(BaseModel):
    """Item de actividad sospechosa"""
    ip_address: str
    attempts: int
    usernames: List[str]
    type: str


@router.get("/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    start_date: Optional[datetime] = Query(None, description="Fecha inicial (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Fecha final (ISO 8601)"),
    user_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    action: Optional[str] = Query(None, description="Filtrar por acción específica"),
    resource_type: Optional[str] = Query(None, description="Filtrar por tipo de recurso"),
    resource_id: Optional[int] = Query(None, description="Filtrar por ID de recurso"),
    ip_address: Optional[str] = Query(None, description="Filtrar por dirección IP"),
    status_code: Optional[int] = Query(None, description="Filtrar por código de estado HTTP"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros por página"),
    order_by: str = Query("created_at", description="Campo para ordenar"),
    order_dir: str = Query("desc", description="Dirección de orden (asc/desc)"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_auditor),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Consultar logs de auditoría del sistema.
    
    Solo administradores y auditores pueden ver logs.
    
    Parámetros de query:
    - start_date, end_date: Rango de fechas
    - user_id: Filtrar por usuario específico
    - action: Filtrar por acción (LOGIN_SUCCESS, USER_CREATED, etc.)
    - resource_type: Filtrar por tipo de recurso (user, order, inventory, etc.)
    - resource_id: Filtrar por ID de recurso específico
    - ip_address: Filtrar por dirección IP
    - status_code: Filtrar por código HTTP
    - skip, limit: Paginación
    - order_by, order_dir: Ordenamiento
    
    Returns:
    - Lista de logs con paginación
    """
    audit_service = AuditService(db)
    
    # Obtener logs
    logs, total = await audit_service.get_logs(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        ip_address=ip_address,
        status_code=status_code,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir
    )
    
    # Construir response
    log_responses = []
    for log in logs:
        # Parsear detalles JSON
        details = None
        if log.details:
            try:
                import json
                details = json.loads(log.details)
            except:
                details = {"raw": log.details}
        
        log_responses.append(AuditLogResponse(
            id=log.id,
            tenant_id=log.tenant_id,
            user_id=log.user_id,
            username=log.username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=details,
            request_path=log.request_path,
            request_method=log.request_method,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            status_code=log.status_code,
            response_time_ms=log.response_time_ms,
            created_at=log.created_at.isoformat() if log.created_at else ""
        ))
    
    # Información de filtros aplicados
    filters = {
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip_address": ip_address,
        "status_code": status_code,
        "tenant_id": tenant_id
    }
    
    return AuditLogListResponse(
        logs=log_responses,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        filters={k: v for k, v in filters.items() if v is not None}
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_auditor),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Obtener log específico por ID.
    
    Solo administradores y auditores pueden ver logs individuales.
    
    Parámetros:
    - log_id: ID del log a consultar
    
    Returns:
    - Log de auditoría completo
    """
    audit_service = AuditService(db)
    
    log = await audit_service.get_log_by_id(log_id)
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log no encontrado"
        )
    
    # Verificar que pertenezca al mismo tenant
    if log.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede acceder a logs de otros tenants"
        )
    
    # Parsear detalles JSON
    details = None
    if log.details:
        try:
            import json
            details = json.loads(log.details)
        except:
            details = {"raw": log.details}
    
    return AuditLogResponse(
        id=log.id,
        tenant_id=log.tenant_id,
        user_id=log.user_id,
        username=log.username,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        details=details,
        request_path=log.request_path,
        request_method=log.request_method,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        status_code=log.status_code,
        response_time_ms=log.response_time_ms,
        created_at=log.created_at.isoformat() if log.created_at else ""
    )


@router.get("/activity/summary", response_model=ActivitySummaryResponse)
async def get_activity_summary(
    days: int = Query(7, ge=1, le=365, description="Número de días a analizar"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_auditor),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Obtener resumen de actividad del sistema.
    
    Útil para dashboards y análisis de uso.
    
    Parámetros:
    - days: Número de días hacia atrás para analizar
    
    Returns:
    - Resumen estadístico de actividad
    """
    audit_service = AuditService(db)
    
    summary = await audit_service.get_tenant_activity_summary(tenant_id, days)
    
    return ActivitySummaryResponse(**summary)


@router.get("/user/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    days: int = Query(7, ge=1, le=30, description="Número de días a analizar"),
    limit: int = Query(50, ge=1, le=200, description="Límite de registros"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtener actividad reciente de un usuario específico.
    
    Solo administradores pueden ver actividad de otros usuarios.
    
    Parámetros:
    - user_id: ID del usuario
    - days: Período de días
    - limit: Límite de registros
    
    Returns:
    - Lista de actividad del usuario
    """
    audit_service = AuditService(db)
    
    # Verificar permisos (solo puede ver usuarios del mismo tenant)
    from services.user_service import UserService
    user_service = UserService(db)
    target_user = await user_service.get_user_by_id(user_id)
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puede acceder a actividad de usuarios de otros tenants"
        )
    
    logs = await audit_service.get_user_activity(user_id, days, limit)
    
    # Formatear response
    activity = []
    for log in logs:
        details = None
        if log.details:
            try:
                import json
                details = json.loads(log.details)
            except:
                details = {"raw": log.details}
        
        activity.append({
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": details,
            "request_path": log.request_path,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else ""
        })
    
    return {
        "user_id": user_id,
        "username": target_user.username,
        "period_days": days,
        "total_activities": len(logs),
        "activities": activity
    }


@router.get("/failed-logins")
async def get_failed_logins(
    hours: int = Query(24, ge=1, le=168, description="Horas hacia atrás para analizar"),
    ip_address: Optional[str] = Query(None, description="Filtrar por dirección IP"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_auditor),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Obtener intentos fallidos de login.
    
    Útil para detección de ataques de fuerza bruta.
    
    Parámetros:
    - hours: Período de horas a analizar
    - ip_address: Filtrar por IP específica
    
    Returns:
    - Lista de intentos fallidos
    """
    audit_service = AuditService(db)
    
    failed_logins = await audit_service.get_failed_logins(tenant_id, hours, ip_address)
    
    # Formatear response
    attempts = []
    for log in failed_logins:
        attempts.append({
            "id": log.id,
            "username": log.username,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat() if log.created_at else ""
        })
    
    return {
        "period_hours": hours,
        "ip_address": ip_address,
        "total_attempts": len(failed_logins),
        "attempts": attempts
    }


@router.get("/suspicious-activity")
async def get_suspicious_activity(
    hours: int = Query(24, ge=1, le=168, description="Horas hacia atrás para analizar"),
    threshold: int = Query(10, ge=1, le=100, description="Umbral mínimo de intentos"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Detectar actividad sospechosa en el sistema.
    
    Solo administradores pueden ver esta información.
    
    Parámetros:
    - hours: Período de horas a analizar
    - threshold: Umbral mínimo de intentos para considerar sospechoso
    
    Returns:
    - Lista de IPs con actividad sospechosa
    """
    audit_service = AuditService(db)
    
    suspicious = await audit_service.get_suspicious_activity(tenant_id, hours, threshold)
    
    return {
        "period_hours": hours,
        "threshold": threshold,
        "total_suspicious": len(suspicious),
        "suspicious_ips": suspicious
    }


@router.post("/export")
async def export_audit_logs(
    format: str = Query("json", description="Formato de exportación (json/csv)"),
    start_date: Optional[datetime] = Query(None, description="Fecha inicial"),
    end_date: Optional[datetime] = Query(None, description="Fecha final"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Exportar logs de auditoría.
    
    Solo administradores pueden exportar logs.
    
    Parámetros:
    - format: Formato de exportación (json o csv)
    - start_date, end_date: Rango de fechas
    
    Returns:
    - Logs exportados en el formato solicitado
    """
    audit_service = AuditService(db)
    
    if format not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Use 'json' o 'csv'"
        )
    
    # Exportar logs
    export_data = await audit_service.export_logs(tenant_id, start_date, end_date, format)
    
    if format == "json":
        return {
            "format": "json",
            "count": len(export_data),
            "data": export_data
        }
    elif format == "csv":
        # Generar CSV (simplificado)
        import csv
        import io
        
        if not export_data:
            return {"format": "csv", "count": 0, "csv": ""}
        
        # Obtener headers del primer item
        headers = list(export_data[0].keys())
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        
        for row in export_data:
            # Aplanar detalles si es dict
            if "details" in row and isinstance(row["details"], dict):
                row["details"] = str(row["details"])
            writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return {
            "format": "csv",
            "count": len(export_data),
            "csv": csv_content
        }


@router.delete("/purge-old", status_code=status.HTTP_200_OK)
async def purge_old_logs(
    older_than_days: int = Query(90, ge=30, le=365, description="Eliminar logs más antiguos que X días"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin),
    tenant_id: int = Depends(lambda: getattr(current_user, 'tenant_id', 1))
):
    """
    Eliminar logs antiguos para liberar espacio.
    
    Solo administradores pueden ejecutar esta acción.
    
    Parámetros:
    - older_than_days: Eliminar logs más antiguos que este número de días
    
    Returns:
    - Número de logs eliminados
    """
    audit_service = AuditService(db)
    
    deleted_count = await audit_service.purge_old_logs(older_than_days, tenant_id)
    
    return {
        "message": f"Se eliminaron {deleted_count} logs antiguos",
        "older_than_days": older_than_days,
        "deleted_count": deleted_count
    }


@router.get("/actions")
async def get_available_actions(
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_auditor)
):
    """
    Obtener lista de acciones disponibles en el sistema.
    
    Útil para filtros en la interfaz de auditoría.
    
    Returns:
    - Lista de acciones únicas registradas
    """
    audit_service = AuditService(db)
    
    # Obtener acciones únicas (simplificado)
    from sqlalchemy import distinct
    stmt = select(distinct(AuditLog.action)).where(
        AuditLog.tenant_id == current_user.tenant_id
    ).order_by(AuditLog.action)
    
    result = await self.db.execute(stmt)
    actions = result.scalars().all()
    
    # Categorizar acciones comunes
    categories = {
        "authentication": ["LOGIN_SUCCESS", "LOGIN_FAILED", "LOGOUT"],
        "user_management": ["USER_CREATED", "USER_UPDATED", "USER_DELETED", "ROLE_ASSIGNED"],
        "inventory": ["INBOUND_RECEIVED", "INVENTORY_UPDATED", "STOCK_ADJUSTED"],
        "orders": ["ORDER_CREATED", "ORDER_PICKED", "ORDER_SHIPPED"],
        "system": ["CONFIG_UPDATED", "BACKUP_CREATED", "EXPORT_GENERATED"]
    }
    
    return {
        "total_actions": len(actions),
        "actions": actions,
        "categories": categories
    }