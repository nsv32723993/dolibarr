# services/dolibarr_integration_service.py
import httpx
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json

from core.config import settings
from services.tenant_config_service import TenantConfigService
from models.wms_models import PickingOrder, PickingItem, IntegrationLog

logger = logging.getLogger(__name__)


class DolibarrIntegrationService:
    """
    Servicio avanzado de integración con Dolibarr.
    Maneja notificaciones, webhooks, y sincronización bidireccional.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tenant_config_service = TenantConfigService(db)
    
    async def _get_tenant_config(self, tenant_id: int) -> Dict[str, Any]:
        """Obtener configuración del tenant."""
        config = await self.tenant_config_service.get_config(tenant_id)
        if not config:
            raise ValueError(f"Configuración no encontrada para tenant {tenant_id}")
        
        # Usar configuración específica o valores por defecto
        return {
            "api_url": config.dolibarr_api_url or settings.DOLIBARR_API_URL,
            "api_key": config.dolibarr_api_key or settings.DOLIBARR_API_KEY,
            "warehouse_id": config.dolibarr_warehouse_id,
            "webhook_url": config.webhook_url,
            "max_retries": config.max_retry_attempts,
            "retry_delay": config.retry_delay_seconds
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
    )
    async def notify_picking_completed(
        self,
        picking_order_id: int,
        tenant_id: int,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Notificar a Dolibarr que un picking ha sido completado.
        
        Args:
            picking_order_id: ID de la orden de picking
            tenant_id: ID del tenant
            force_sync: Forzar sincronización incluso si la notificación está deshabilitada
            
        Returns:
            Resultado de la notificación
        """
        try:
            # Obtener orden de picking
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            stmt = select(PickingOrder).options(
                selectinload(PickingOrder.picking_items)
            ).where(
                PickingOrder.id == picking_order_id,
                PickingOrder.tenant_id == tenant_id
            )
            
            result = await self.db.execute(stmt)
            picking_order = result.scalar_one_or_none()
            
            if not picking_order:
                raise ValueError(f"Picking order {picking_order_id} no encontrada")
            
            # Obtener configuración
            config = await self._get_tenant_config(tenant_id)
            
            # Verificar si debemos notificar
            if not force_sync and not config.get("notify_on_picking_complete", True):
                return {
                    "success": True,
                    "skipped": True,
                    "reason": "Notificaciones deshabilitadas"
                }
            
            # Preparar payload
            differences = []
            for item in picking_order.picking_items:
                if item.has_discrepancy:
                    differences.append({
                        "product_id": item.dolibarr_product_id,
                        "product_ref": item.product_ref,
                        "expected": item.requested_quantity,
                        "actual": item.confirmed_quantity,
                        "difference_type": item.discrepancy_type,
                        "reason": item.discrepancy_reason
                    })
            
            payload = {
                "external_order_id": picking_order.dolibarr_order_ref,
                "wms_picking_id": picking_order.id,
                "status": picking_order.status.value,
                "completed_at": picking_order.completed_at.isoformat() if picking_order.completed_at else None,
                "differences": differences,
                "total_items": picking_order.total_items,
                "picked_items": picking_order.picked_items,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Registrar inicio de integración
            log = IntegrationLog(
                tenant_id=tenant_id,
                action="picking_notification_started",
                resource_type="picking_order",
                resource_id=picking_order_id,
                details={"payload": payload},
                status="pending"
            )
            self.db.add(log)
            await self.db.commit()
            
            # Intentar webhook primero (si está configurado)
            success = False
            method = None
            response_data = None
            
            if config.get("webhook_url"):
                success, method, response_data = await self._send_webhook(
                    config["webhook_url"], payload, tenant_id
                )
            
            # Si webhook falla o no está configurado, usar API directa
            if not success and config.get("api_url"):
                success, method, response_data = await self._send_api_request(
                    config["api_url"],
                    config["api_key"],
                    payload,
                    tenant_id
                )
            
            # Actualizar log
            log.status = "completed" if success else "failed"
            log.details = {
                **log.details,
                "method": method,
                "success": success,
                "response": response_data,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            await self.db.commit()
            
            # Crear shipment en Dolibarr si es exitoso
            if success and config.get("warehouse_id"):
                shipment_id = await self._create_dolibarr_shipment(
                    picking_order.dolibarr_order_id,
                    config["warehouse_id"],
                    config["api_url"],
                    config["api_key"],
                    tenant_id
                )
                
                if shipment_id:
                    payload["dolibarr_shipment_id"] = shipment_id
            
            return {
                "success": success,
                "method": method,
                "picking_order_id": picking_order_id,
                "dolibarr_order_ref": picking_order.dolibarr_order_ref,
                "differences_count": len(differences),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error notificando picking {picking_order_id}: {str(e)}")
            
            # Registrar error
            log = IntegrationLog(
                tenant_id=tenant_id,
                action="picking_notification_failed",
                resource_type="picking_order",
                resource_id=picking_order_id,
                details={"error": str(e)},
                status="failed",
                error_message=str(e)
            )
            self.db.add(log)
            await self.db.commit()
            
            raise
    
    async def _send_webhook(self, webhook_url: str, payload: Dict, tenant_id: int) -> Tuple[bool, str, Any]:
        """Enviar notificación vía webhook."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Tenant-ID": str(tenant_id),
                        "X-WMS-Signature": self._generate_signature(payload)
                    },
                    timeout=30.0
                )
                
                success = response.status_code in [200, 201, 202]
                return success, "webhook", response.json() if success else response.text
                
        except Exception as e:
            logger.error(f"Error enviando webhook: {e}")
            return False, "webhook", str(e)
    
    async def _send_api_request(self, api_url: str, api_key: str, payload: Dict, 
                               tenant_id: int) -> Tuple[bool, str, Any]:
        """Enviar notificación vía API directa."""
        try:
            async with httpx.AsyncClient() as client:
                # Endpoint específico para WMS (debe existir en Dolibarr)
                endpoint = f"{api_url.rstrip('/')}/wms/picking/notify"
                
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={
                        "DOLAPIKEY": api_key,
                        "Content-Type": "application/json",
                        "X-Tenant-ID": str(tenant_id)
                    },
                    timeout=30.0
                )
                
                success = response.status_code in [200, 201, 202]
                return success, "api", response.json() if success else response.text
                
        except Exception as e:
            logger.error(f"Error enviando API request: {e}")
            return False, "api", str(e)
    
    async def _create_dolibarr_shipment(self, order_id: int, warehouse_id: int, 
                                       api_url: str, api_key: str, tenant_id: int) -> Optional[int]:
        """Crear shipment en Dolibarr."""
        try:
            # Usar cliente Dolibarr existente o crear uno nuevo
            from core.client_dolibarr import DolibarrClient
            client = DolibarrClient(api_url, api_key)
            
            shipment_data = await client.create_shipment_from_order(order_id, warehouse_id)
            
            if shipment_data and "id" in shipment_data:
                logger.info(f"Shipment creado en Dolibarr: {shipment_data['id']}")
                
                # Registrar integración exitosa
                log = IntegrationLog(
                    tenant_id=tenant_id,
                    action="shipment_created",
                    resource_type="order",
                    resource_id=order_id,
                    details={
                        "shipment_id": shipment_data["id"],
                        "warehouse_id": warehouse_id,
                        "success": True
                    },
                    status="completed"
                )
                self.db.add(log)
                await self.db.commit()
                
                return shipment_data["id"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error creando shipment: {str(e)}")
            
            log = IntegrationLog(
                tenant_id=tenant_id,
                action="shipment_creation_failed",
                resource_type="order",
                resource_id=order_id,
                details={
                    "error": str(e),
                    "success": False
                },
                status="failed",
                error_message=str(e)
            )
            self.db.add(log)
            await self.db.commit()
            
            return None
    
    def _generate_signature(self, payload: Dict) -> str:
        """Generar firma para webhooks."""
        import hashlib
        import hmac
        
        # En producción, usar una clave secreta
        secret = settings.JWT_SECRET_KEY.encode()
        message = json.dumps(payload, sort_keys=True).encode()
        
        signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return f"sha256={signature}"
    
    async def sync_stock_differences(self, tenant_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Sincronizar diferencias de stock con Dolibarr.
        
        Args:
            tenant_id: ID del tenant
            days: Número de días hacia atrás
            
        Returns:
            Resultado de la sincronización
        """
        try:
            from sqlalchemy import select, and_
            from datetime import datetime, timedelta
            
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Buscar picking items con diferencias no sincronizadas
            stmt = select(PickingItem).join(PickingOrder).where(
                and_(
                    PickingItem.tenant_id == tenant_id,
                    PickingItem.has_discrepancy == True,
                    PickingItem.confirmed_at >= since_date,
                    PickingItem.discrepancy_synced == False  # Nuevo campo necesario
                )
            )
            
            result = await self.db.execute(stmt)
            items = result.scalars().all()
            
            if not items:
                return {
                    "success": True,
                    "items_synced": 0,
                    "message": "No hay diferencias para sincronizar"
                }
            
            # Obtener configuración
            config = await self._get_tenant_config(tenant_id)
            
            # Agrupar por producto
            product_differences = {}
            for item in items:
                product_id = item.dolibarr_product_id
                if product_id not in product_differences:
                    product_differences[product_id] = {
                        "product_ref": item.product_ref,
                        "total_difference": 0,
                        "items": []
                    }
                
                difference = item.confirmed_quantity - item.requested_quantity
                product_differences[product_id]["total_difference"] += difference
                product_differences[product_id]["items"].append({
                    "picking_item_id": item.id,
                    "difference": difference,
                    "type": item.discrepancy_type
                })
            
            # Sincronizar cada producto
            synced_count = 0
            errors = []
            
            for product_id, data in product_differences.items():
                try:
                    # Crear ajuste de stock en Dolibarr
                    success = await self._create_stock_adjustment(
                        product_id,
                        data["total_difference"],
                        f"WMS Ajuste: {len(data['items'])} diferencias de picking",
                        config,
                        tenant_id
                    )
                    
                    if success:
                        # Marcar items como sincronizados
                        for item_data in data["items"]:
                            # Actualizar campo discrepancy_synced
                            # Nota: Necesitas agregar este campo al modelo PickingItem
                            pass
                        
                        synced_count += 1
                    else:
                        errors.append(f"Producto {product_id}: Error en ajuste")
                        
                except Exception as e:
                    errors.append(f"Producto {product_id}: {str(e)}")
            
            return {
                "success": len(errors) == 0,
                "items_synced": synced_count,
                "total_items": len(items),
                "errors": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando diferencias: {str(e)}")
            raise
    
    async def get_integration_metrics(self, tenant_id: int, days: int = 30) -> Dict[str, Any]:
        """Obtener métricas de integración."""
        from sqlalchemy import select, func, and_
        from datetime import datetime, timedelta
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Consultas
        stmt_total = select(func.count()).where(
            and_(
                IntegrationLog.tenant_id == tenant_id,
                IntegrationLog.created_at >= since_date
            )
        )
        
        stmt_success = select(func.count()).where(
            and_(
                IntegrationLog.tenant_id == tenant_id,
                IntegrationLog.status == "completed",
                IntegrationLog.created_at >= since_date
            )
        )
        
        stmt_failed = select(func.count()).where(
            and_(
                IntegrationLog.tenant_id == tenant_id,
                IntegrationLog.status == "failed",
                IntegrationLog.created_at >= since_date
            )
        )
        
        stmt_pending = select(func.count()).where(
            and_(
                IntegrationLog.tenant_id == tenant_id,
                IntegrationLog.status == "pending",
                IntegrationLog.created_at >= since_date
            )
        )
        
        # Ejecutar
        result = await self.db.execute(stmt_total)
        total = result.scalar() or 0
        
        result = await self.db.execute(stmt_success)
        success = result.scalar() or 0
        
        result = await self.db.execute(stmt_failed)
        failed = result.scalar() or 0
        
        result = await self.db.execute(stmt_pending)
        pending = result.scalar() or 0
        
        success_rate = (success / total * 100) if total > 0 else 0
        
        # Acciones más comunes
        stmt_actions = select(
            IntegrationLog.action,
            func.count().label("count")
        ).where(
            and_(
                IntegrationLog.tenant_id == tenant_id,
                IntegrationLog.created_at >= since_date
            )
        ).group_by(IntegrationLog.action).order_by(func.count().desc()).limit(10)
        
        result = await self.db.execute(stmt_actions)
        top_actions = [{"action": row[0], "count": row[1]} for row in result.all()]
        
        return {
            "period_days": days,
            "total_operations": total,
            "successful": success,
            "failed": failed,
            "pending": pending,
            "success_rate": round(success_rate, 2),
            "top_actions": top_actions,
            "last_updated": datetime.utcnow().isoformat()
        }