# tests/test_fase3.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

# Tests para FASE 3 - Integración avanzada


@pytest.mark.asyncio
async def test_tenant_config_endpoints(client: AsyncClient, admin_token: str):
    """Test endpoints de configuración de tenant."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Crear configuración
    config_data = {
        "tenant_id": 1,  # Será sobrescrito por el middleware
        "allow_overpicking": False,
        "allow_partial_picking": True,
        "default_warehouse_id": 1,
        "dolibarr_api_url": "http://test.dolibarr/api",
        "dolibarr_api_key": "test_key",
        "brand_name": "Test Tenant"
    }
    
    response = await client.post("/api/v1/tenant-config/", 
                                json=config_data, headers=headers)
    assert response.status_code == 201
    config = response.json()
    assert config["tenant_id"] == 1
    assert config["allow_overpicking"] is False
    
    # 2. Obtener configuración
    response = await client.get("/api/v1/tenant-config/", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == config["id"]
    
    # 3. Actualizar configuración
    update_data = {"allow_overpicking": True}
    response = await client.put("/api/v1/tenant-config/", 
                               json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["allow_overpicking"] is True
    
    # 4. Test conexión Dolibarr
    response = await client.post("/api/v1/tenant-config/test-dolibarr-connection", 
                                headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert "test_result" in result


@pytest.mark.asyncio
async def test_integration_metrics(client: AsyncClient, admin_token: str):
    """Test métricas de integración."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = await client.get("/api/v1/tenant-config/integration-metrics?days=7", 
                               headers=headers)
    
    assert response.status_code == 200
    metrics = response.json()
    
    assert "total_operations" in metrics
    assert "success_rate" in metrics
    assert "period_days" in metrics


@pytest.mark.asyncio
async def test_integration_logs(client: AsyncClient, admin_token: str):
    """Test logs de integración."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = await client.get("/api/v1/tenant-config/logs?limit=10", 
                               headers=headers)
    
    assert response.status_code == 200
    logs_data = response.json()
    
    assert "total" in logs_data
    assert "logs" in logs_data
    assert isinstance(logs_data["logs"], list)


@pytest.mark.asyncio
async def test_multi_tenant_isolation(db: AsyncSession):
    """Test aislamiento de datos por tenant."""
    from services.tenant_config_service import TenantConfigService
    
    service = TenantConfigService(db)
    
    # Crear configuración para tenant 1
    config1 = await service.create_config({
        "tenant_id": 1,
        "allow_overpicking": True,
        "brand_name": "Tenant 1"
    })
    
    # Crear configuración para tenant 2
    config2 = await service.create_config({
        "tenant_id": 2,
        "allow_overpicking": False,
        "brand_name": "Tenant 2"
    })
    
    # Verificar aislamiento
    config1_fetched = await service.get_config(1)
    config2_fetched = await service.get_config(2)
    
    assert config1_fetched is not None
    assert config2_fetched is not None
    assert config1_fetched.tenant_id == 1
    assert config2_fetched.tenant_id == 2
    assert config1_fetched.allow_overpicking is True
    assert config2_fetched.allow_overpicking is False


@pytest.mark.asyncio
async def test_jwt_security(client: AsyncClient):
    """Test seguridad JWT."""
    # 1. Token inválido
    response = await client.get("/api/v1/tenant-config/", 
                               headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    
    # 2. Sin token
    response = await client.get("/api/v1/tenant-config/")
    assert response.status_code == 403
    
    # 3. Token expirado (test manual)
    # (Requiere token con expiración pasada)


@pytest.mark.asyncio
async def test_critical_wms_flows(db: AsyncSession):
    """Test flujos críticos del WMS."""
    from services.wms_service import WMSService
    from schemas.wms_schemas import PickingOrderCreate
    
    service = WMSService(db)
    
    # 1. Crear picking order
    picking_data = {
        "dolibarr_order_id": 999,
        "dolibarr_order_ref": "TEST-ORDER-001",
        "picking_number": "PICK-TEST-001",
        "warehouse_id": 1,
        "priority": 1
    }
    
    picking_order = await service.create_picking_order(
        PickingOrderCreate(**picking_data),
        tenant_id=1
    )
    
    assert picking_order is not None
    assert picking_order.dolibarr_order_ref == "TEST-ORDER-001"
    assert picking_order.status == "pending"
    
    # 2. Start picking
    started_order = await service.start_picking(
        picking_order.id,
        user_id="test_user",
        tenant_id=1
    )
    
    assert started_order.status == "in_progress"
    assert started_order.assigned_to == "test_user"
    assert started_order.started_at is not None
    
    # 3. Cleanup
    await db.rollback()  # No guardar datos de test