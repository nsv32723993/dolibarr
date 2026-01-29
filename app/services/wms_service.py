# app/services/wms_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
import qrcode
import io
import base64

from models.wms_models import (
    Warehouse, Zone, StockLocation, PickingOrder, 
    PickingItem, StockEntry, StockMovement, TenantConfig
)
from models.schemas import (
    PickingOrderCreate, PickingOrderUpdate, PickingItemCreate,
    PickingItemUpdate, StockEntryCreate, StockRelocationRequest
)

logger = logging.getLogger(__name__)


class WMSService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ============ UTILITY METHODS ============
    def _generate_qr_code(self, data: str) -> str:
        """Generate QR code base64 data"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    
    def _validate_location_code(self, rack: str, level: int, position: int) -> str:
        """Generate location code from components"""
        return f"{rack}-{level:02d}-{position:03d}"
    
    # ============ WAREHOUSE OPERATIONS ============
    async def create_warehouse(self, warehouse_data: WarehouseCreate, tenant_id: int) -> Warehouse:
        """Create a new warehouse."""
        try:
            # Check if code already exists for this tenant
            stmt = select(Warehouse).where(
                and_(
                    Warehouse.tenant_id == tenant_id,
                    Warehouse.code == warehouse_data.code
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                raise ValueError(f"Warehouse code '{warehouse_data.code}' already exists")
            
            # Create warehouse
            warehouse = Warehouse(
                **warehouse_data.model_dump(),
                tenant_id=tenant_id
            )
            
            # If this is set as default, unset other defaults
            if warehouse.is_default:
                await self._unset_other_defaults(tenant_id)
            
            self.db.add(warehouse)
            await self.db.commit()
            await self.db.refresh(warehouse)
            
            logger.info(f"Created warehouse {warehouse.id} for tenant {tenant_id}")
            return warehouse
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating warehouse: {e}")
            raise
    
    async def get_warehouse(self, warehouse_id: int, tenant_id: int) -> Optional[Warehouse]:
        """Get a warehouse by ID."""
        stmt = select(Warehouse).where(
            and_(
                Warehouse.id == warehouse_id,
                Warehouse.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_warehouses(self, tenant_id: int, skip: int = 0, limit: int = 100) -> List[Warehouse]:
        """Get all warehouses for a tenant."""
        stmt = select(Warehouse).where(
            Warehouse.tenant_id == tenant_id
        ).offset(skip).limit(limit).order_by(desc(Warehouse.created_at))
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _unset_other_defaults(self, tenant_id: int):
        """Unset is_default flag from all other warehouses."""
        stmt = update(Warehouse).where(
            and_(
                Warehouse.tenant_id == tenant_id,
                Warehouse.is_default == True
            )
        ).values(is_default=False)
        
        await self.db.execute(stmt)
    
    # ============ ZONE OPERATIONS ============
    async def create_zone(self, zone_data: ZoneCreate, tenant_id: int) -> Zone:
        """Create a new zone in a warehouse."""
        try:
            # Verify warehouse exists
            warehouse = await self.get_warehouse(zone_data.warehouse_id, tenant_id)
            if not warehouse:
                raise ValueError(f"Warehouse {zone_data.warehouse_id} not found")
            
            # Check if zone code already exists in this warehouse
            stmt = select(Zone).where(
                and_(
                    Zone.tenant_id == tenant_id,
                    Zone.warehouse_id == zone_data.warehouse_id,
                    Zone.code == zone_data.code
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                raise ValueError(f"Zone code '{zone_data.code}' already exists in this warehouse")
            
            # Create zone
            zone = Zone(
                **zone_data.model_dump(),
                tenant_id=tenant_id
            )
            
            self.db.add(zone)
            await self.db.commit()
            await self.db.refresh(zone)
            
            logger.info(f"Created zone {zone.id} in warehouse {zone_data.warehouse_id}")
            return zone
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating zone: {e}")
            raise
    
    async def get_zones_by_warehouse(self, warehouse_id: int, tenant_id: int, 
                                   zone_type: Optional[ZoneType] = None) -> List[Zone]:
        """Get all zones in a warehouse."""
        stmt = select(Zone).where(
            and_(
                Zone.tenant_id == tenant_id,
                Zone.warehouse_id == warehouse_id
            )
        )
        
        if zone_type:
            stmt = stmt.where(Zone.zone_type == zone_type)
        
        stmt = stmt.order_by(asc(Zone.code))
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    # ============ STOCK LOCATION OPERATIONS ============
    async def create_stock_location(self, location_data: StockLocationCreate, tenant_id: int) -> StockLocation:
        """Create a new stock location."""
        try:
            # Verify warehouse exists
            warehouse = await self.get_warehouse(location_data.warehouse_id, tenant_id)
            if not warehouse:
                raise ValueError(f"Warehouse {location_data.warehouse_id} not found")
            
            # Verify zone exists if provided
            if location_data.zone_id:
                stmt = select(Zone).where(
                    and_(
                        Zone.id == location_data.zone_id,
                        Zone.tenant_id == tenant_id,
                        Zone.warehouse_id == location_data.warehouse_id
                    )
                )
                result = await self.db.execute(stmt)
                zone = result.scalar_one_or_none()
                if not zone:
                    raise ValueError(f"Zone {location_data.zone_id} not found in this warehouse")
            
            # Generate location code if not provided
            if not location_data.location_code:
                location_data.location_code = self._validate_location_code(
                    location_data.rack, location_data.level, location_data.position
                )
            
            # Check if location code already exists
            stmt = select(StockLocation).where(
                and_(
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.location_code == location_data.location_code
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                raise ValueError(f"Location code '{location_data.location_code}' already exists")
            
            # Generate QR code if not provided
            qr_code_data = location_data.qr_code_data
            if not qr_code_data and location_data.barcode:
                qr_code_data = self._generate_qr_code(location_data.barcode)
            
            # Create location
            location = StockLocation(
                **location_data.model_dump(exclude={'qr_code_data'}),
                qr_code_data=qr_code_data,
                tenant_id=tenant_id
            )
            
            self.db.add(location)
            await self.db.commit()
            await self.db.refresh(location)
            
            logger.info(f"Created stock location {location.id} with code {location_data.location_code}")
            return location
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating stock location: {e}")
            raise
    
    async def find_available_location(self, warehouse_id: int, tenant_id: int, 
                                    required_quantity: int = 1) -> Optional[StockLocation]:
        """Find an available location for storage."""
        stmt = select(StockLocation).where(
            and_(
                StockLocation.tenant_id == tenant_id,
                StockLocation.warehouse_id == warehouse_id,
                StockLocation.is_blocked == False,
                or_(
                    StockLocation.max_quantity.is_(None),
                    StockLocation.max_quantity >= (StockLocation.current_quantity + required_quantity)
                )
            )
        ).order_by(
            asc(StockLocation.rack),
            asc(StockLocation.level),
            asc(StockLocation.position)
        ).limit(1)
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_location_by_barcode(self, barcode: str, tenant_id: int) -> Optional[StockLocation]:
        """Find location by barcode."""
        stmt = select(StockLocation).where(
            and_(
                StockLocation.tenant_id == tenant_id,
                StockLocation.barcode == barcode
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    # ============ PICKING ORDER OPERATIONS ============
    async def create_picking_order(self, picking_data: PickingOrderCreate, tenant_id: int) -> PickingOrder:
        """Create a new picking order from Dolibarr."""
        try:
            # Verify warehouse exists
            warehouse = await self.get_warehouse(picking_data.warehouse_id, tenant_id)
            if not warehouse:
                raise ValueError(f"Warehouse {picking_data.warehouse_id} not found")
            
            # Check if picking number already exists
            stmt = select(PickingOrder).where(
                and_(
                    PickingOrder.tenant_id == tenant_id,
                    PickingOrder.picking_number == picking_data.picking_number
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                raise ValueError(f"Picking number '{picking_data.picking_number}' already exists")
            
            # Create picking order
            picking_order = PickingOrder(
                **picking_data.model_dump(),
                tenant_id=tenant_id,
                status=PickingStatus.PENDING
            )
            
            self.db.add(picking_order)
            await self.db.commit()
            await self.db.refresh(picking_order)
            
            logger.info(f"Created picking order {picking_order.id} for Dolibarr order {picking_data.dolibarr_order_id}")
            return picking_order
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating picking order: {e}")
            raise
    
    async def get_picking_order(self, picking_order_id: int, tenant_id: int) -> Optional[PickingOrder]:
        """Get picking order by ID."""
        stmt = select(PickingOrder).options(
            selectinload(PickingOrder.picking_items)
        ).where(
            and_(
                PickingOrder.id == picking_order_id,
                PickingOrder.tenant_id == tenant_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_picking_orders(self, tenant_id: int, status: Optional[PickingStatus] = None,
                               warehouse_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[PickingOrder]:
        """Get picking orders with filters."""
        stmt = select(PickingOrder).where(
            PickingOrder.tenant_id == tenant_id
        )
        
        if status:
            stmt = stmt.where(PickingOrder.status == status)
        
        if warehouse_id:
            stmt = stmt.where(PickingOrder.warehouse_id == warehouse_id)
        
        stmt = stmt.order_by(
            desc(PickingOrder.priority),
            asc(PickingOrder.created_at)
        ).offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def start_picking(self, picking_order_id: int, user_id: str, tenant_id: int) -> Optional[PickingOrder]:
        """Start a picking order."""
        try:
            picking_order = await self.get_picking_order(picking_order_id, tenant_id)
            if not picking_order:
                return None
            
            if picking_order.status != PickingStatus.PENDING:
                raise ValueError(f"Cannot start picking order with status {picking_order.status}")
            
            picking_order.status = PickingStatus.IN_PROGRESS
            picking_order.assigned_to = user_id
            picking_order.started_at = datetime.utcnow()
            picking_order.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(picking_order)
            
            logger.info(f"Started picking order {picking_order_id} by user {user_id}")
            return picking_order
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error starting picking order {picking_order_id}: {e}")
            raise
    
    async def complete_picking(self, picking_order_id: int, tenant_id: int) -> Optional[PickingOrder]:
        """Complete a picking order."""
        try:
            picking_order = await self.get_picking_order(picking_order_id, tenant_id)
            if not picking_order:
                return None
            
            if picking_order.status != PickingStatus.IN_PROGRESS:
                raise ValueError(f"Cannot complete picking order with status {picking_order.status}")
            
            # Check if all items are completed
            incomplete_items = [item for item in picking_order.picking_items if not item.is_completed]
            if incomplete_items:
                raise ValueError(f"Cannot complete picking order with {len(incomplete_items)} incomplete items")
            
            picking_order.status = PickingStatus.COMPLETED
            picking_order.completed_at = datetime.utcnow()
            picking_order.updated_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(picking_order)
            
            logger.info(f"Completed picking order {picking_order_id}")
            return picking_order
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error completing picking order {picking_order_id}: {e}")
            raise
    
    # ============ PICKING ITEM OPERATIONS ============
    async def add_picking_item(self, item_data: PickingItemCreate, tenant_id: int) -> PickingItem:
        """Add an item to a picking order."""
        try:
            # Verify picking order exists
            stmt = select(PickingOrder).where(
                and_(
                    PickingOrder.id == item_data.picking_order_id,
                    PickingOrder.tenant_id == tenant_id
                )
            )
            result = await self.db.execute(stmt)
            picking_order = result.scalar_one_or_none()
            
            if not picking_order:
                raise ValueError(f"Picking order {item_data.picking_order_id} not found")
            
            if picking_order.status != PickingStatus.PENDING:
                raise ValueError("Cannot add items to a picking order that is not pending")
            
            # Verify source location exists and has available stock
            stmt = select(StockEntry).where(
                and_(
                    StockEntry.dolibarr_product_id == item_data.dolibarr_product_id,
                    StockEntry.location_id == item_data.source_location_id,
                    StockEntry.tenant_id == tenant_id,
                    StockEntry.is_reserved == False,
                    StockEntry.is_blocked == False
                )
            )
            result = await self.db.execute(stmt)
            stock_entries = result.scalars().all()
            
            total_available = sum(entry.quantity for entry in stock_entries)
            if total_available < item_data.requested_quantity:
                raise ValueError(f"Insufficient stock. Available: {total_available}, Requested: {item_data.requested_quantity}")
            
            # Create picking item
            picking_item = PickingItem(
                **item_data.model_dump(),
                tenant_id=tenant_id
            )
            
            # Update picking order totals
            picking_order.total_items += 1
            picking_order.updated_at = datetime.utcnow()
            
            self.db.add(picking_item)
            await self.db.commit()
            await self.db.refresh(picking_item)
            
            logger.info(f"Added picking item {picking_item.id} to order {item_data.picking_order_id}")
            return picking_item
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding picking item: {e}")
            raise
    
    async def confirm_picking_item(self, picking_item_id: int, confirmation: PickingConfirmationRequest, 
                                  tenant_id: int) -> Optional[PickingItem]:
        """Confirm picking of an item with actual quantity."""
        try:
            stmt = select(PickingItem).options(
                joinedload(PickingItem.picking_order)
            ).where(
                and_(
                    PickingItem.id == picking_item_id,
                    PickingItem.tenant_id == tenant_id
                )
            )
            result = await self.db.execute(stmt)
            picking_item = result.scalar_one_or_none()
            
            if not picking_item:
                return None
            
            if picking_item.is_completed:
                raise ValueError("Picking item already completed")
            
            picking_order = picking_item.picking_order
            if picking_order.status != PickingStatus.IN_PROGRESS:
                raise ValueError("Picking order is not in progress")
            
            # Update quantities
            picking_item.picked_quantity = confirmation.confirmed_quantity
            picking_item.confirmed_quantity = confirmation.confirmed_quantity
            picking_item.confirmed_by = confirmation.user_id
            picking_item.confirmed_at = datetime.utcnow()
            picking_item.updated_at = datetime.utcnow()
            
            # Check for discrepancies
            if confirmation.confirmed_quantity != picking_item.requested_quantity:
                picking_item.has_discrepancy = True
                picking_item.discrepancy_type = confirmation.discrepancy_type
                picking_item.discrepancy_reason = confirmation.discrepancy_reason
                picking_order.total_discrepancies += 1
            
            # Mark as completed if confirmed quantity > 0
            picking_item.is_completed = confirmation.confirmed_quantity > 0
            
            # Update picking order
            picking_order.picked_items += 1
            picking_order.updated_at = datetime.utcnow()
            
            # Deduct stock from source location
            await self._deduct_stock_for_picking(
                picking_item.dolibarr_product_id,
                picking_item.source_location_id,
                confirmation.confirmed_quantity,
                picking_item.id,
                confirmation.user_id,
                tenant_id
            )
            
            await self.db.commit()
            await self.db.refresh(picking_item)
            
            logger.info(f"Confirmed picking item {picking_item_id} with quantity {confirmation.confirmed_quantity}")
            return picking_item
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error confirming picking item {picking_item_id}: {e}")
            raise
    
    async def _deduct_stock_for_picking(self, product_id: int, location_id: int, quantity: int,
                                      picking_item_id: int, user_id: str, tenant_id: int):
        """Deduct stock for a picking item."""
        # Find available stock entries
        stmt = select(StockEntry).where(
            and_(
                StockEntry.dolibarr_product_id == product_id,
                StockEntry.location_id == location_id,
                StockEntry.tenant_id == tenant_id,
                StockEntry.is_reserved == False,
                StockEntry.is_blocked == False,
                StockEntry.quantity > 0
            )
        ).order_by(
            asc(StockEntry.expiry_date)  # FIFO: First In, First Out
        )
        
        result = await self.db.execute(stmt)
        stock_entries = result.scalars().all()
        
        remaining_quantity = quantity
        for entry in stock_entries:
            if remaining_quantity <= 0:
                break
            
            deduct_quantity = min(entry.quantity, remaining_quantity)
            
            # Create stock movement
            movement = StockMovement(
                stock_entry_id=entry.id,
                movement_type=StockMovementType.PICKING,
                quantity_change=-deduct_quantity,
                previous_quantity=entry.quantity,
                new_quantity=entry.quantity - deduct_quantity,
                from_location_id=location_id,
                reference_id=picking_item_id,
                reference_type="picking_item",
                performed_by=user_id,
                notes=f"Picking for order item {picking_item_id}",
                tenant_id=tenant_id
            )
            
            # Update stock entry
            entry.quantity -= deduct_quantity
            if entry.quantity == 0:
                await self.db.delete(entry)
            
            self.db.add(movement)
            remaining_quantity -= deduct_quantity
        
        if remaining_quantity > 0:
            raise ValueError(f"Insufficient stock to deduct {quantity} units")
    
    # ============ STOCK ENTRY OPERATIONS ============
    async def create_stock_entry(self, stock_data: StockEntryCreate, tenant_id: int) -> StockEntry:
        """Create a stock entry (receipt of goods)."""
        try:
            # Verify location exists
            stmt = select(StockLocation).where(
                and_(
                    StockLocation.id == stock_data.location_id,
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.is_blocked == False
                )
            )
            result = await self.db.execute(stmt)
            location = result.scalar_one_or_none()
            
            if not location:
                raise ValueError(f"Location {stock_data.location_id} not found or blocked")
            
            # Check location capacity
            if location.max_quantity and (location.current_quantity + stock_data.quantity) > location.max_quantity:
                raise ValueError(f"Location capacity exceeded. Max: {location.max_quantity}, Current: {location.current_quantity}")
            
            # Create stock entry
            stock_entry = StockEntry(
                **stock_data.model_dump(),
                tenant_id=tenant_id
            )
            
            # Update location occupancy
            location.current_quantity += stock_data.quantity
            location.is_occupied = location.current_quantity > 0
            location.updated_at = datetime.utcnow()
            
            self.db.add(stock_entry)
            
            # Create stock movement
            movement = StockMovement(
                stock_entry_id=stock_entry.id,
                movement_type=StockMovementType.RECEIPT,
                quantity_change=stock_data.quantity,
                previous_quantity=location.current_quantity - stock_data.quantity,
                new_quantity=location.current_quantity,
                to_location_id=stock_data.location_id,
                reference_id=stock_data.dolibarr_stock_movement_id,
                reference_type="dolibarr_movement",
                performed_by="system",
                notes="Initial receipt",
                tenant_id=tenant_id
            )
            
            self.db.add(movement)
            await self.db.commit()
            await self.db.refresh(stock_entry)
            
            logger.info(f"Created stock entry {stock_entry.id} for product {stock_data.dolibarr_product_id}")
            return stock_entry
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating stock entry: {e}")
            raise
    
    async def search_stock(self, search_request: StockSearchRequest, tenant_id: int) -> List[Dict[str, Any]]:
        """Search for stock entries."""
        stmt = select(StockEntry).options(
            joinedload(StockEntry.location)
        ).where(
            StockEntry.tenant_id == tenant_id
        )
        
        if search_request.dolibarr_product_id:
            stmt = stmt.where(StockEntry.dolibarr_product_id == search_request.dolibarr_product_id)
        
        if search_request.product_ref:
            stmt = stmt.where(StockEntry.product_ref.ilike(f"%{search_request.product_ref}%"))
        
        if search_request.batch_number:
            stmt = stmt.where(StockEntry.batch_number == search_request.batch_number)
        
        if search_request.location_code:
            location_subq = select(StockLocation.id).where(
                and_(
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.location_code == search_request.location_code
                )
            ).scalar_subquery()
            stmt = stmt.where(StockEntry.location_id == location_subq)
        
        if search_request.warehouse_id:
            warehouse_subq = select(StockLocation.id).where(
                and_(
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.warehouse_id == search_request.warehouse_id
                )
            ).scalar_subquery()
            stmt = stmt.where(StockEntry.location_id.in_(warehouse_subq))
        
        stmt = stmt.order_by(desc(StockEntry.created_at))
        
        result = await self.db.execute(stmt)
        entries = result.scalars().all()
        
        return [
            {
                "id": entry.id,
                "dolibarr_product_id": entry.dolibarr_product_id,
                "product_ref": entry.product_ref,
                "quantity": entry.quantity,
                "batch_number": entry.batch_number,
                "expiry_date": entry.expiry_date,
                "serial_number": entry.serial_number,
                "location_id": entry.location_id,
                "location_code": entry.location.location_code if entry.location else None,
                "warehouse_id": entry.location.warehouse_id if entry.location else None,
                "is_reserved": entry.is_reserved,
                "is_blocked": entry.is_blocked,
                "created_at": entry.created_at
            }
            for entry in entries
        ]
    
    # ============ STOCK RELOCATION ============
    async def relocate_stock(self, relocation: StockRelocationRequest, tenant_id: int) -> StockMovement:
        """Relocate stock from one location to another."""
        try:
            # Get stock entry
            stmt = select(StockEntry).options(
                joinedload(StockEntry.location)
            ).where(
                and_(
                    StockEntry.id == relocation.stock_entry_id,
                    StockEntry.tenant_id == tenant_id,
                    StockEntry.is_blocked == False
                )
            )
            result = await self.db.execute(stmt)
            stock_entry = result.scalar_one_or_none()
            
            if not stock_entry:
                raise ValueError(f"Stock entry {relocation.stock_entry_id} not found or blocked")
            
            if stock_entry.is_reserved:
                raise ValueError("Cannot relocate reserved stock")
            
            if stock_entry.quantity < relocation.quantity:
                raise ValueError(f"Insufficient stock. Available: {stock_entry.quantity}, Requested: {relocation.quantity}")
            
            # Verify new location exists
            stmt = select(StockLocation).where(
                and_(
                    StockLocation.id == relocation.new_location_id,
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.is_blocked == False,
                    StockLocation.warehouse_id == stock_entry.location.warehouse_id
                )
            )
            result = await self.db.execute(stmt)
            new_location = result.scalar_one_or_none()
            
            if not new_location:
                raise ValueError(f"New location {relocation.new_location_id} not found, blocked, or in different warehouse")
            
            # Check new location capacity
            if new_location.max_quantity and (new_location.current_quantity + relocation.quantity) > new_location.max_quantity:
                raise ValueError(f"New location capacity exceeded")
            
            # Update old location
            old_location = stock_entry.location
            old_location.current_quantity -= relocation.quantity
            old_location.is_occupied = old_location.current_quantity > 0
            old_location.updated_at = datetime.utcnow()
            
            # Update new location
            new_location.current_quantity += relocation.quantity
            new_location.is_occupied = new_location.current_quantity > 0
            new_location.updated_at = datetime.utcnow()
            
            # Create movement for old location
            movement_out = StockMovement(
                stock_entry_id=stock_entry.id,
                movement_type=StockMovementType.RELOCATION,
                quantity_change=-relocation.quantity,
                previous_quantity=stock_entry.quantity,
                new_quantity=stock_entry.quantity - relocation.quantity,
                from_location_id=old_location.id,
                to_location_id=new_location.id,
                reference_id=stock_entry.id,
                reference_type="relocation",
                performed_by=relocation.user_id,
                notes=relocation.notes,
                tenant_id=tenant_id
            )
            
            self.db.add(movement_out)
            
            # If moving entire stock entry, update location
            if relocation.quantity == stock_entry.quantity:
                stock_entry.location_id = new_location.id
            else:
                # Reduce quantity in old stock entry
                stock_entry.quantity -= relocation.quantity
                
                # Create new stock entry at new location
                new_stock_entry = StockEntry(
                    dolibarr_product_id=stock_entry.dolibarr_product_id,
                    product_ref=stock_entry.product_ref,
                    location_id=new_location.id,
                    quantity=relocation.quantity,
                    batch_number=stock_entry.batch_number,
                    expiry_date=stock_entry.expiry_date,
                    serial_number=stock_entry.serial_number,
                    dolibarr_stock_movement_id=stock_entry.dolibarr_stock_movement_id,
                    tenant_id=tenant_id
                )
                self.db.add(new_stock_entry)
            
            await self.db.commit()
            await self.db.refresh(movement_out)
            
            logger.info(f"Relocated {relocation.quantity} units from location {old_location.id} to {new_location.id}")
            return movement_out
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error relocating stock: {e}")
            raise
    
    # ============ INVENTORY REPORTS ============
    async def get_stock_summary(self, warehouse_id: Optional[int], tenant_id: int) -> Dict[str, Any]:
        """Get stock summary for warehouse."""
        # Base query
        if warehouse_id:
            # Get locations in specific warehouse
            location_subq = select(StockLocation.id).where(
                and_(
                    StockLocation.tenant_id == tenant_id,
                    StockLocation.warehouse_id == warehouse_id
                )
            ).scalar_subquery()
            
            stmt = select(
                func.sum(StockEntry.quantity).label("total_quantity"),
                func.count(StockEntry.id).label("total_entries"),
                func.count(func.distinct(StockEntry.dolibarr_product_id)).label("unique_products")
            ).where(
                and_(
                    StockEntry.tenant_id == tenant_id,
                    StockEntry.location_id.in_(location_subq)
                )
            )
        else:
            # Get all stock for tenant
            stmt = select(
                func.sum(StockEntry.quantity).label("total_quantity"),
                func.count(StockEntry.id).label("total_entries"),
                func.count(func.distinct(StockEntry.dolibarr_product_id)).label("unique_products")
            ).where(
                StockEntry.tenant_id == tenant_id
            )
        
        result = await self.db.execute(stmt)
        summary = result.first()
        
        # Get stock by warehouse
        stmt = select(
            StockLocation.warehouse_id,
            func.sum(StockEntry.quantity).label("quantity"),
            func.count(StockEntry.id).label("entries")
        ).join(
            StockEntry, StockLocation.id == StockEntry.location_id
        ).where(
            and_(
                StockLocation.tenant_id == tenant_id,
                StockEntry.tenant_id == tenant_id
            )
        ).group_by(StockLocation.warehouse_id)
        
        result = await self.db.execute(stmt)
        by_warehouse = result.all()
        
        return {
            "total_quantity": summary.total_quantity or 0,
            "total_entries": summary.total_entries or 0,
            "unique_products": summary.unique_products or 0,
            "by_warehouse": [
                {
                    "warehouse_id": row.warehouse_id,
                    "quantity": row.quantity or 0,
                    "entries": row.entries or 0
                }
                for row in by_warehouse
            ]
        }
    
    async def get_picking_performance(self, tenant_id: int, days: int = 30) -> Dict[str, Any]:
        """Get picking performance metrics."""
        since_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
        
        # Total picking orders
        total_stmt = select(func.count(PickingOrder.id)).where(
            and_(
                PickingOrder.tenant_id == tenant_id,
                PickingOrder.created_at >= since_date
            )
        )
        total_result = await self.db.execute(total_stmt)
        total_orders = total_result.scalar() or 0
        
        # Completed orders
        completed_stmt = select(func.count(PickingOrder.id)).where(
            and_(
                PickingOrder.tenant_id == tenant_id,
                PickingOrder.status == PickingStatus.COMPLETED,
                PickingOrder.created_at >= since_date
            )
        )
        completed_result = await self.db.execute(completed_stmt)
        completed_orders = completed_result.scalar() or 0
        
        # Items picked
        items_stmt = select(
            func.sum(PickingItem.requested_quantity).label("requested"),
            func.sum(PickingItem.confirmed_quantity).label("picked"),
            func.sum(case(
                (PickingItem.has_discrepancy == True, 1),
                else_=0
            )).label("discrepancies")
        ).join(PickingOrder).where(
            and_(
                PickingItem.tenant_id == tenant_id,
                PickingOrder.created_at >= since_date
            )
        )
        items_result = await self.db.execute(items_stmt)
        items_data = items_result.first()
        
        # Average picking time
        time_stmt = select(
            func.avg(func.extract('epoch', PickingOrder.completed_at - PickingOrder.started_at)).label("avg_time")
        ).where(
            and_(
                PickingOrder.tenant_id == tenant_id,
                PickingOrder.status == PickingStatus.COMPLETED,
                PickingOrder.started_at.is_not(None),
                PickingOrder.completed_at.is_not(None),
                PickingOrder.created_at >= since_date
            )
        )
        time_result = await self.db.execute(time_stmt)
        avg_time = time_result.scalar() or 0
        
        return {
            "period_days": days,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "completion_rate": (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            "items_requested": items_data.requested or 0,
            "items_picked": items_data.picked or 0,
            "discrepancies": items_data.discrepancies or 0,
            "accuracy_rate": (items_data.picked / items_data.requested * 100) if items_data.requested and items_data.requested > 0 else 100,
            "average_picking_time_seconds": round(avg_time, 2)
        }