# services/tenant_config_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, Dict, Any
import logging

from models.tenant_config import TenantConfig
from schemas.tenant_config import TenantConfigCreate, TenantConfigUpdate

logger = logging.getLogger(__name__)


class TenantConfigService:
    """Servicio para gestionar configuración técnica por tenant."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_config(self, tenant_id: int) -> Optional[TenantConfig]:
        """Obtener configuración de un tenant."""
        stmt = select(TenantConfig).where(TenantConfig.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_config(self, config_data: TenantConfigCreate) -> TenantConfig:
        """Crear configuración para un tenant."""
        try:
            # Verificar si ya existe configuración
            existing = await self.get_config(config_data.tenant_id)
            if existing:
                raise ValueError(f"Configuración ya existe para tenant {config_data.tenant_id}")
            
            config = TenantConfig(
                tenant_id=config_data.tenant_id,
                allow_overpicking=config_data.allow_overpicking,
                allow_partial_picking=config_data.allow_partial_picking,
                auto_reserve_stock=config_data.auto_reserve_stock,
                require_picking_confirmation=config_data.require_picking_confirmation,
                default_warehouse_id=config_data.default_warehouse_id,
                dolibarr_api_url=config_data.dolibarr_api_url,
                dolibarr_api_key=config_data.dolibarr_api_key,
                dolibarr_warehouse_id=config_data.dolibarr_warehouse_id,
                webhook_url=config_data.webhook_url,
                notify_on_picking_complete=config_data.notify_on_picking_complete,
                notify_on_stock_difference=config_data.notify_on_stock_difference,
                notify_on_integration_error=config_data.notify_on_integration_error,
                brand_name=config_data.brand_name,
                brand_logo_url=config_data.brand_logo_url,
                brand_primary_color=config_data.brand_primary_color,
                max_retry_attempts=config_data.max_retry_attempts,
                retry_delay_seconds=config_data.retry_delay_seconds,
                audit_retention_days=90  # Valor por defecto
            )
            
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)
            
            logger.info(f"Configuración creada para tenant {config_data.tenant_id}")
            return config
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creando configuración: {e}")
            raise
    
    async def update_config(self, tenant_id: int, config_data: TenantConfigUpdate) -> Optional[TenantConfig]:
        """Actualizar configuración de un tenant."""
        try:
            config = await self.get_config(tenant_id)
            if not config:
                raise ValueError(f"Configuración no encontrada para tenant {tenant_id}")
            
            # Actualizar campos
            for field, value in config_data.model_dump(exclude_unset=True).items():
                if hasattr(config, field):
                    setattr(config, field, value)
            
            await self.db.commit()
            await self.db.refresh(config)
            
            logger.info(f"Configuración actualizada para tenant {tenant_id}")
            return config
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error actualizando configuración: {e}")
            raise
    
    async def get_integration_status(self, tenant_id: int) -> Dict[str, Any]:
        """Obtener estado de integración con Dolibarr."""
        config = await self.get_config(tenant_id)
        if not config:
            return {
                "is_connected": False,
                "error": "Configuración no encontrada",
                "pending_operations": 0,
                "error_count": 0
            }
        
        # Verificar configuración mínima
        has_min_config = bool(config.dolibarr_api_url and config.dolibarr_api_key)
        
        # Contar operaciones pendientes (ejemplo simplificado)
        from sqlalchemy import func
        from models.wms_models import IntegrationLog
        
        stmt_pending = select(func.count()).where(
            IntegrationLog.tenant_id == tenant_id,
            IntegrationLog.status == "pending"
        )
        result = await self.db.execute(stmt_pending)
        pending = result.scalar() or 0
        
        stmt_errors = select(func.count()).where(
            IntegrationLog.tenant_id == tenant_id,
            IntegrationLog.status == "failed"
        )
        result = await self.db.execute(stmt_errors)
        errors = result.scalar() or 0
        
        return {
            "is_connected": has_min_config,
            "config_ok": has_min_config,
            "dolibarr_api_url": bool(config.dolibarr_api_url),
            "dolibarr_api_key": bool(config.dolibarr_api_key),
            "webhook_url": bool(config.webhook_url),
            "pending_operations": pending,
            "error_count": errors,
            "last_sync": config.updated_at.isoformat() if config.updated_at else None
        }
    
    async def test_dolibarr_connection(self, tenant_id: int) -> Dict[str, Any]:
        """Probar conexión con Dolibarr."""
        import httpx
        from datetime import datetime
        
        config = await self.get_config(tenant_id)
        if not config or not config.dolibarr_api_url or not config.dolibarr_api_key:
            return {
                "success": False,
                "error": "Configuración incompleta",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            async with httpx.AsyncClient() as client:
                # Intentar obtener versión de Dolibarr
                response = await client.get(
                    f"{config.dolibarr_api_url}/status",
                    headers={"DOLAPIKEY": config.dolibarr_api_key},
                    timeout=10.0
                )
                
                success = response.status_code == 200
                result = {
                    "success": success,
                    "status_code": response.status_code,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if success and response.text:
                    try:
                        result["data"] = response.json()
                    except:
                        result["data"] = response.text[:500]
                
                # Actualizar última verificación
                if success:
                    config.updated_at = datetime.utcnow()
                    await self.db.commit()
                
                return result
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }