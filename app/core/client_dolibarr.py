import requests
import os
from fastapi import HTTPException

class DolibarrConnect:
    def __init__(self):
        # Configuración desde variables de entorno
        self.base_url = os.getenv("DOLIBARR_API_URL") # Ej: http://localhost/dolibarr/api/index.php
        self.api_key = os.getenv("DOLIBARR_API_KEY")  # Genérala en el perfil de usuario de Dolibarr
        self.headers = {"DOLAPIKEY": self.api_key, "Accept": "application/json"}

    def _check_resp(self, resp):
        if resp.status_code not in [200, 201]:
            raise HTTPException(status_code=resp.status_code, detail=f"Dolibarr Error: {resp.text}")
        return resp.json()

    # --- Caso de Uso: Consulta de Productos para Validación ---
    def get_product_by_ref(self, ref: str):
        # SQL Filters es potente en Dolibarr API
        endpoint = f"{self.base_url}/products?sqlfilters=(t.ref:like:'{ref}')"
        resp = requests.get(endpoint, headers=self.headers)
        data = self._check_resp(resp)
        return data[0] if data else None

    # --- Caso de Uso: Movimiento de Stock (Finalización) ---
    def create_stock_movement(self, product_id, warehouse_id, qty, label):
        payload = {
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "qty": qty,
            "label": label
        }
        resp = requests.post(f"{self.base_url}/stockmovements", json=payload, headers=self.headers)
        return self._check_resp(resp)

    # --- Caso de Uso: Obtener Pedidos Pendientes (Para Picking) ---
    def get_orders_to_ship(self):
        # Buscamos pedidos con estado 'validado' (status = 1) y que no estén enviados
        endpoint = f"{self.base_url}/orders?sqlfilters=(t.fk_statut:=:1)"
        resp = requests.get(endpoint, headers=self.headers)
        return self._check_resp(resp)