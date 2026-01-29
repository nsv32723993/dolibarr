# routers/tenant_config.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from datetime import datetime

from core.database import get_wms_db
from core.dependencies import get_current_user, require_admin
from models.wms_models import User
from services.tenant_config_service import TenantConfigService
from services.dolibarr_integration_service import DolibarrIntegrationService
from schemas.tenant_config import (
    TenantConfigCreate, TenantConfigUpdate, 
    TenantConfigResponse, IntegrationStatus
)

router = APIRouter(prefix="/tenant-config", tags=["Tenant Configuration"])


@router.get("/", response_model=TenantConfigResponse)
async def get_tenant_config(
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Obtener configuración del tenant actual."""
    config_service = TenantConfigService(db)
    
    config = await config_service.get_config(current_user.tenant_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada. Use POST para crear."
        )
    
    return config


@router.post("/", response_model=TenantConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant_config(
    config_data: TenantConfigCreate,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Crear configuración para el tenant."""
    config_service = TenantConfigService(db)
    
    try:
        # Asegurar que el tenant_id sea el del usuario
        config_data.tenant_id = current_user.tenant_id
        
        config = await config_service.create_config(config_data)
        return config
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando configuración: {str(e)}"
        )


@router.put("/", response_model=TenantConfigResponse)
async def update_tenant_config(
    config_data: TenantConfigUpdate,
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Actualizar configuración del tenant."""
    config_service = TenantConfigService(db)
    
    try:
        config = await config_service.update_config(current_user.tenant_id, config_data)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuración no encontrada"
            )
        
        return config
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando configuración: {str(e)}"
        )


@router.get("/integration-status", response_model=IntegrationStatus)
async def get_integration_status(
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Obtener estado de integración con Dolibarr."""
    config_service = TenantConfigService(db)
    
    status_data = await config_service.get_integration_status(current_user.tenant_id)
    
    return IntegrationStatus(
        is_connected=status_data["is_connected"],
        last_sync=datetime.fromisoformat(status_data["last_sync"]) if status_data.get("last_sync") else None,
        pending_operations=status_data["pending_operations"],
        error_count=status_data["error_count"],
        connection_test=status_data
    )


@router.post("/test-dolibarr-connection")
async def test_dolibarr_connection(
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Probar conexión con Dolibarr."""
    config_service = TenantConfigService(db)
    
    result = await config_service.test_dolibarr_connection(current_user.tenant_id)
    
    return {
        "tenant_id": current_user.tenant_id,
        "test_result": result,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/sync-picking/{picking_order_id}")
async def sync_picking_to_dolibarr(
    picking_order_id: int,
    force: bool = Query(False, description="Forzar sincronización"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Sincronizar picking completado con Dolibarr."""
    integration_service = DolibarrIntegrationService(db)
    
    try:
        result = await integration_service.notify_picking_completed(
            picking_order_id=picking_order_id,
            tenant_id=current_user.tenant_id,
            force_sync=force
        )
        
        return {
            "success": result["success"],
            "message": "Picking sincronizado" if result["success"] else "Error en sincronización",
            "details": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sincronizando picking: {str(e)}"
        )


@router.post("/sync-stock-differences")
async def sync_stock_differences(
    days: int = Query(7, ge=1, le=90, description="Días hacia atrás"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Sincronizar diferencias de stock con Dolibarr."""
    integration_service = DolibarrIntegrationService(db)
    
    try:
        result = await integration_service.sync_stock_differences(
            tenant_id=current_user.tenant_id,
            days=days
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sincronizando diferencias: {str(e)}"
        )


@router.get("/integration-metrics")
async def get_integration_metrics(
    days: int = Query(30, ge=1, le=365, description="Período en días"),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Obtener métricas de integración."""
    integration_service = DolibarrIntegrationService(db)
    
    try:
        metrics = await integration_service.get_integration_metrics(
            tenant_id=current_user.tenant_id,
            days=days
        )
        
        return metrics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo métricas: {str(e)}"
        )


@router.get("/logs")
async def get_integration_logs(
    start_date: Optional[datetime] = Query(None, description="Fecha inicio"),
    end_date: Optional[datetime] = Query(None, description="Fecha fin"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    action: Optional[str] = Query(None, description="Filtrar por acción"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_wms_db),
    current_user: User = Depends(require_admin)
):
    """Obtener logs de integración."""
    from sqlalchemy import select, and_
    from models.wms_models import IntegrationLog
    
    query = select(IntegrationLog).where(
        IntegrationLog.tenant_id == current_user.tenant_id
    )
    
    if start_date:
        query = query.where(IntegrationLog.created_at >= start_date)
    if end_date:
        query = query.where(IntegrationLog.created_at <= end_date)
    if status:
        query = query.where(IntegrationLog.status == status)
    if action:
        query = query.where(IntegrationLog.action == action)
    
    query = query.order_by(IntegrationLog.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "status": log.status,
                "details": log.details,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
                "updated_at": log.updated_at.isoformat() if log.updated_at else None
            }
            for log in logs
        ]
    }