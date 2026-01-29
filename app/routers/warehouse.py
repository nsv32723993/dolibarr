# app/routers/warehouse.py - Router para gestión de almacenes y ubicaciones
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..core.database import get_wms_db
from ..core.dependencies import get_current_tenant, get_current_user
from ..services.wms_service import WMSService
from ..models.schemas import (
    Warehouse, WarehouseCreate, WarehouseUpdate,
    Zone, ZoneCreate, ZoneUpdate,
    StockLocation, StockLocationCreate, StockLocationUpdate,
    WarehouseWithZones, ZoneWithLocations,
    StockSearchRequest, StockRelocationRequest
)
from ..models.wms_models import User

router = APIRouter(prefix="/warehouse", tags=["warehouse"])


# ============ WAREHOUSE ENDPOINTS ============
@router.post("/warehouses", response_model=Warehouse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse: WarehouseCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Create a new warehouse."""
    try:
        service = WMSService(db)
        return await service.create_warehouse(warehouse, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating warehouse: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/warehouses", response_model=List[Warehouse])
async def get_warehouses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get all warehouses for the tenant."""
    service = WMSService(db)
    return await service.get_warehouses(tenant_id, skip, limit)


@router.get("/warehouses/{warehouse_id}", response_model=Warehouse)
async def get_warehouse(
    warehouse_id: int = Path(..., gt=0),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get a specific warehouse."""
    service = WMSService(db)
    warehouse = await service.get_warehouse(warehouse_id, tenant_id)
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


@router.put("/warehouses/{warehouse_id}", response_model=Warehouse)
async def update_warehouse(
    warehouse_id: int = Path(..., gt=0),
    warehouse_update: WarehouseUpdate = None,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Update a warehouse."""
    service = WMSService(db)
    # Implementation needed
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


# ============ ZONE ENDPOINTS ============
@router.post("/zones", response_model=Zone, status_code=status.HTTP_201_CREATED)
async def create_zone(
    zone: ZoneCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Create a new zone in a warehouse."""
    try:
        service = WMSService(db)
        return await service.create_zone(zone, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/warehouses/{warehouse_id}/zones", response_model=List[Zone])
async def get_warehouse_zones(
    warehouse_id: int = Path(..., gt=0),
    zone_type: Optional[str] = Query(None),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get all zones in a warehouse."""
    service = WMSService(db)
    zones = await service.get_zones_by_warehouse(warehouse_id, tenant_id, zone_type)
    return zones


# ============ STOCK LOCATION ENDPOINTS ============
@router.post("/locations", response_model=StockLocation, status_code=status.HTTP_201_CREATED)
async def create_stock_location(
    location: StockLocationCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Create a new stock location."""
    try:
        service = WMSService(db)
        return await service.create_stock_location(location, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating stock location: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/locations/available", response_model=Optional[StockLocation])
async def find_available_location(
    warehouse_id: int = Query(..., gt=0),
    required_quantity: int = Query(1, ge=1),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Find an available location for storage."""
    service = WMSService(db)
    return await service.find_available_location(warehouse_id, tenant_id, required_quantity)


@router.get("/locations/barcode/{barcode}", response_model=StockLocation)
async def get_location_by_barcode(
    barcode: str = Path(..., min_length=1),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get location by barcode."""
    service = WMSService(db)
    location = await service.get_location_by_barcode(barcode, tenant_id)
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
    return location


# ============ STOCK OPERATIONS ENDPOINTS ============
@router.post("/stock/search", response_model=List[Dict[str, Any]])
async def search_stock(
    search_request: StockSearchRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Search for stock entries."""
    service = WMSService(db)
    return await service.search_stock(search_request, tenant_id)


@router.post("/stock/relocate", response_model=Dict[str, Any])
async def relocate_stock(
    relocation: StockRelocationRequest,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Relocate stock from one location to another."""
    try:
        service = WMSService(db)
        movement = await service.relocate_stock(relocation, tenant_id)
        return {"success": True, "movement_id": movement.id, "message": "Stock relocated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error relocating stock: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/stock/summary", response_model=Dict[str, Any])
async def get_stock_summary(
    warehouse_id: Optional[int] = Query(None, gt=0),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get stock summary."""
    service = WMSService(db)
    return await service.get_stock_summary(warehouse_id, tenant_id)


# ============ INVENTORY REPORTS ============
@router.get("/reports/picking-performance", response_model=Dict[str, Any])
async def get_picking_performance(
    days: int = Query(30, ge=1, le=365),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get picking performance metrics."""
    service = WMSService(db)
    return await service.get_picking_performance(tenant_id, days)


# Logger para este módulo
import logging
logger = logging.getLogger(__name__)