import httpx 
from fastapi import HTTPException 
 
class DolibarrClient: 
    def __init__(self, base_url: str, api_key: str): 
        self.base_url = base_url.rstrip('/') 
        self.headers = {"DOLAPIKEY": api_key, "Accept": "application/json"} 
 
    async def get_product_by_barcode(self, barcode: str): 
        # Dolibarr filtra por sqlfilters o parámetros directos 
        params = {"sqlfilters": f"(t.barcode:like:'{barcode}')"} 
        async with httpx.AsyncClient() as client: 
            resp = await client.get(f"{self.base_url}/products", headers=self.headers, params=params) 
            if resp.status_code == 200 and resp.json(): 
                return resp.json()[0] # Retorna el primer match 
            return None 
 
    async def get_product_stock(self, product_id: int): 
        async with httpx.AsyncClient() as client: 
            resp = await client.get(f"{self.base_url}/products/{product_id}/stock", headers=self.headers) 
            return resp.json() if resp.status_code == 200 else {} 
 
    async def create_stock_movement(self, product_id: int, warehouse_id: int, qty: int, label: str): 
        """ 
        Suma stock (Recepción). En Dolibarr direction=1 es corrección (sumar/restar). 
        Para recepción formal se usa 'mouvement' 
        """ 
        payload = { 
            "product_id": product_id, 
            "warehouse_id": warehouse_id, 
            "qty": qty, 
            "movementlabel": label, 
            "type": "3" # Tipo 3 suele ser 'Recepción' o 'Corrección' según config 
        } 
        async with httpx.AsyncClient() as client: 
            resp = await client.post(f"{self.base_url}/stockmovements", headers=self.headers, 
json=payload) 
            if resp.status_code != 200: 
                raise HTTPException(status_code=400, detail=f"Error Dolibarr: {resp.text}") 
            return resp.json() # Retorna ID del movimiento 
 
    async def get_pending_orders(self): 
        # Status 1 = Validada (lista para picking) 
        params = {"sqlfilters": "(t.fk_statut:=:1)"} 
        async with httpx.AsyncClient() as client: 
            resp = await client.get(f"{self.base_url}/orders", headers=self.headers, params=params) 
            return resp.json() if resp.status_code == 200 else [] 
 
    async def get_order_lines(self, order_id: int): 
        async with httpx.AsyncClient() as client: 
            resp = await client.get(f"{self.base_url}/orders/{order_id}/lines", headers=self.headers) 
            return resp.json() if resp.status_code == 200 else [] 
 
    async def create_shipment_from_order(self, order_id: int, warehouse_id: int): 
        # Crear expedición (Shipment) es el paso previo a descontar stock en ventas 
        # Nota: Esta es una operación compleja en Dolibarr API. Simplificamos creando el objeto Shipment. 
        payload = { 
            "origin_id": order_id, 
            "origin_type": "commande", 
            "entrepot_id": warehouse_id  
            # Se requeriría iterar las líneas para setear cantidades exactas 
        } 
        async with httpx.AsyncClient() as client: 
            resp = await client.post(f"{self.base_url}/shipments", headers=self.headers, json=payload) 
            if resp.status_code != 200: 
                raise HTTPException(status_code=400, detail="Fallo al crear envío en Dolibarr") 
            return resp.json() 
 
# Instancia Global (Configura tu URL aquí o en .env) 
DOLIBARR_URL= "http://dolibarr-app/api/index.php"
DOLIBARR_KEY = "Web7NFpgu9NIP5U2vm1sby6IU4P261Vo" 
doli_client = DolibarrClient(DOLIBARR_URL, DOLIBARR_KEY) 