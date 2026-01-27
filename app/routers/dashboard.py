# routers/dashboard.py
@router.get("/dashboard/kpis")
async def get_dashboard_kpis(tenant_id: int = Depends(get_tenant_id)):
    # KPIs críticos mencionados en tu documento
    today = datetime.utcnow().date()
    
    return {
        "inbound_today": get_inbound_count(tenant_id, today),
        "outbound_today": get_outbound_count(tenant_id, today),
        "picking_accuracy": get_picking_accuracy(tenant_id),
        "inventory_turnover": get_inventory_turnover(tenant_id),
        "locations_utilization": get_locations_utilization(tenant_id),
        "pending_orders": get_pending_orders_count(tenant_id)
    }