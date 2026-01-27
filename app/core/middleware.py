# core/middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extraer tenant_id de:
        # 1. Subdominio (tenant1.tudominio.com)
        # 2. Header HTTP (X-Tenant-ID)
        # 3. JWT token
        # 4. Parámetro de query
        
        tenant_id = request.headers.get("X-Tenant-ID") or 1
        
        # Validar que tenant exista y esté activo
        # Conectar a DB específica del tenant
        
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response