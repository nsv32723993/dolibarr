# routers/picking.py
from enum import Enum

class PickingStrategy(str, Enum):
    SINGLE_ORDER = "single_order"      # Una orden a la vez
    BATCH = "batch"                    # Múltiples órdenes juntas
    ZONE = "zone"                      # Por zonas del almacén
    WAVE = "wave"                      # Por oleadas

@router.post("/picking/start")
async def start_picking_session(
    order_ids: List[int],
    strategy: PickingStrategy = PickingStrategy.SINGLE_ORDER,
    tenant_id: int = Depends(get_tenant_id)
):
    if strategy == PickingStrategy.BATCH:
        return await start_batch_picking(order_ids, tenant_id)
    elif strategy == PickingStrategy.ZONE:
        return await start_zone_picking(order_ids, tenant_id)
    # ...