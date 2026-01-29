# app/routers/picking.py - Router para operaciones de picking
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from ..core.database import get_wms_db
from ..core.dependencies import get_current_tenant, get_current_user
from ..services.wms_service import WMSService
from ..models.schemas import (
    PickingOrder, PickingOrderCreate, PickingOrderUpdate,
    PickingItem, PickingItemCreate, PickingItemUpdate,
    PickingOrderWithItems, PickingStatus,
    PickingStartRequest, PickingConfirmationRequest
)
from ..models.wms_models import User

router = APIRouter(prefix="/picking", tags=["picking"])


# ============ PICKING ORDER ENDPOINTS ============
@router.post("/orders", response_model=PickingOrder, status_code=status.HTTP_201_CREATED)
async def create_picking_order(
    order: PickingOrderCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Create a new picking order from Dolibarr."""
    try:
        service = WMSService(db)
        return await service.create_picking_order(order, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating picking order: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/orders", response_model=List[PickingOrder])
async def get_picking_orders(
    status: Optional[PickingStatus] = Query(None),
    warehouse_id: Optional[int] = Query(None, gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get picking orders, optionally filtered by status."""
    service = WMSService(db)
    return await service.get_picking_orders(tenant_id, status, warehouse_id, skip, limit)


@router.get("/orders/{order_id}", response_model=PickingOrder)
async def get_picking_order(
    order_id: int = Path(..., gt=0),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get a specific picking order."""
    service = WMSService(db)
    order = await service.get_picking_order(order_id, tenant_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picking order not found")
    return order


@router.post("/orders/{order_id}/start", response_model=PickingOrder)
async def start_picking_order(
    order_id: int = Path(..., gt=0),
    start_request: PickingStartRequest = None,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Start a picking order."""
    try:
        service = WMSService(db)
        if not start_request:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID required")
        
        order = await service.start_picking(order_id, start_request.user_id, tenant_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picking order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting picking order: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/orders/{order_id}/complete", response_model=PickingOrder)
async def complete_picking_order(
    order_id: int = Path(..., gt=0),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Complete a picking order."""
    try:
        service = WMSService(db)
        order = await service.complete_picking(order_id, tenant_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picking order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing picking order: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# ============ PICKING ITEM ENDPOINTS ============
@router.post("/items", response_model=PickingItem, status_code=status.HTTP_201_CREATED)
async def add_picking_item(
    item: PickingItemCreate,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Add an item to a picking order."""
    try:
        service = WMSService(db)
        return await service.add_picking_item(item, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding picking item: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/items/{item_id}/confirm", response_model=PickingItem)
async def confirm_picking_item(
    item_id: int = Path(..., gt=0),
    confirmation: PickingConfirmationRequest = None,
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Confirm picking of an item with actual quantity."""
    try:
        service = WMSService(db)
        if not confirmation:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation data required")
        
        item = await service.confirm_picking_item(item_id, confirmation, tenant_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picking item not found")
        return item
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error confirming picking item: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/orders/{order_id}/items", response_model=List[PickingItem])
async def get_picking_order_items(
    order_id: int = Path(..., gt=0),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Get all items for a picking order."""
    service = WMSService(db)
    order = await service.get_picking_order(order_id, tenant_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Picking order not found")
    return order.picking_items


# ============ STOCK ENTRY ENDPOINTS (para recepción) ============
@router.post("/stock/entries", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_stock_entry(
    entry_data: dict,  # Will be defined in schemas
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_wms_db)
):
    """Create a stock entry (receipt of goods)."""
    try:
        # Validate and convert entry_data to StockEntryCreate
        from ..models.schemas import StockEntryCreate
        entry_create = StockEntryCreate(**entry_data)
        
        service = WMSService(db)
        entry = await service.create_stock_entry(entry_create, tenant_id)
        return {"success": True, "entry_id": entry.id, "message": "Stock entry created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating stock entry: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# Logger para este módulo
import logging
logger = logging.getLogger(__name__)