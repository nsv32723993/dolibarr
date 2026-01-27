# app/routers/outbound.py

@router.get("/generate-wave")
def generate_picking_wave():
    # 1. Traer todos los pedidos pendientes de Dolibarr
    orders = dolibarr.get_orders_to_ship()
    
    picking_list = {}
    
    # 2. Algoritmo de Agrupación (Lo que falta en Dolibarr)
    for order in orders:
        # Dolibarr API devuelve las líneas del pedido en una llamada separada o expandida
        lines = dolibarr.get_order_lines(order['id']) 
        
        for line in lines:
            prod_id = line['fk_product']
            location = "A-12-B" # En un caso real, consultas tu tabla de ubicaciones WMS
            
            if location not in picking_list:
                picking_list[location] = []
            
            picking_list[location].append({
                "product": line['product_ref'],
                "qty": line['qty'],
                "order_ref": order['ref']
            })
            
    # 3. Devolver lista ordenada por ubicación (Ruta óptima)
    # El Frontend mostrará: "Ve al pasillo A, recoge 5 unidades de X (3 para pedido A, 2 para pedido B)"
    return sorted(picking_list.items())