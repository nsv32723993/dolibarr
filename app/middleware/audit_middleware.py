"""
Middleware para logging automático de todas las requests HTTP.
Registra automáticamente en la base de datos todas las acciones del sistema.
"""
import time
import json
from typing import Dict, Any, Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uuid

from core.database import get_wms_db
from services.audit_service import AuditService
from core.dependencies import decode_token
from sqlalchemy.ext.asyncio import AsyncSession


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta todas las requests y responses
    para registrar auditoría automática en la base de datos.
    
    Características:
    - Registra todas las requests HTTP entrantes
    - Extrae información del usuario del token JWT
    - Registra tiempo de respuesta
    - Excluye endpoints no críticos (health checks, docs)
    - Maneja errores sin romper el flujo principal
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None,
        sensitive_fields: Optional[list] = None,
        log_errors: bool = True,
        max_request_size: int = 1024 * 10  # 10KB
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/favicon.ico",
            "/health",
            "/api/v1/auth/login",  # El login se registra manualmente
            "/api/v1/auth/refresh",
            "/api/v1/auth/validate-token"
        ]
        self.sensitive_fields = sensitive_fields or [
            "password",
            "token",
            "authorization",
            "api_key",
            "secret",
            "credit_card",
            "cvv"
        ]
        self.log_errors = log_errors
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercepta cada request/response para registrar auditoría.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        # Verificar si la ruta está excluida
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Información básica de la request
        request_info = await self._extract_request_info(request, request_id)
        
        # Intentar extraer información del usuario
        user_info = await self._extract_user_info(request)
        
        # Estado inicial
        status_code = 500  # Default si hay error
        error_details = None
        response_body = None
        
        try:
            # Ejecutar la request normal
            response = await call_next(request)
            status_code = response.status_code
            
            # Intentar capturar body de response si es pequeño
            if hasattr(response, 'body') and response.status_code >= 400:
                response_body = await self._capture_response_body(response)
            
            return response
            
        except HTTPException as http_exc:
            # Manejar excepciones HTTP de FastAPI
            status_code = http_exc.status_code
            error_details = {
                "type": "HTTPException",
                "detail": http_exc.detail,
                "headers": dict(http_exc.headers) if http_exc.headers else None
            }
            raise
            
        except Exception as exc:
            # Manejar excepciones no controladas
            status_code = 500
            error_details = {
                "type": type(exc).__name__,
                "detail": str(exc),
                "traceback": self._safe_traceback(exc)
            }
            raise
            
        finally:
            # Siempre registrar la auditoría, incluso si hay error
            response_time = int((time.time() - start_time) * 1000)  # ms
            
            # Determinar acción basada en método HTTP y ruta
            action = self._determine_action(request.method, request.url.path, status_code)
            
            # Determinar tipo de recurso basado en la ruta
            resource_type = self._determine_resource_type(request.url.path)
            
            # Extraer resource_id de la ruta si existe
            resource_id = self._extract_resource_id(request.url.path, request.path_params)
            
            # Preparar detalles de la auditoría
            audit_details = self._prepare_audit_details(
                request_info, 
                user_info, 
                status_code, 
                error_details,
                response_body
            )
            
            # Registrar en base de datos de manera asíncrona (no bloqueante)
            # Usamos asyncio.create_task para no bloquear la response
            await self._log_async(
                tenant_id=user_info.get("tenant_id", 1),
                user_id=user_info.get("user_id"),
                username=user_info.get("username"),
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=audit_details,
                request_path=request.url.path,
                request_method=request.method,
                ip_address=request_info["ip_address"],
                user_agent=request_info["user_agent"],
                status_code=status_code,
                response_time_ms=response_time,
                request_id=request_id
            )
    
    def _should_exclude(self, path: str) -> bool:
        """Determinar si una ruta debe ser excluida del logging."""
        # Excluir rutas específicas
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return True
        
        # Excluir archivos estáticos (opcional)
        if any(path.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.ico']):
            return True
            
        return False
    
    async def _extract_request_info(self, request: Request, request_id: str) -> Dict[str, Any]:
        """Extraer información de la request."""
        # Obtener IP del cliente
        ip_address = request.client.host if request.client else "0.0.0.0"
        
        # Obtener headers importantes
        user_agent = request.headers.get("user-agent", "")
        referer = request.headers.get("referer", "")
        content_type = request.headers.get("content-type", "")
        
        # Obtener query parameters (sanitizados)
        query_params = dict(request.query_params)
        query_params = self._sanitize_sensitive_data(query_params)
        
        # Intentar obtener body de la request si es pequeño
        request_body = None
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                content_length = int(request.headers.get("content-length", 0))
                if 0 < content_length < self.max_request_size:
                    body_bytes = await request.body()
                    if body_bytes:
                        # Guardar el body para poder leerlo después
                        request_body = body_bytes.decode('utf-8', errors='replace')
                        request_body = self._sanitize_sensitive_data_json(request_body)
                        # Resetear el body para que pueda ser leído por la aplicación
                        await request.body()
        except Exception:
            # Si hay error, simplemente no capturamos el body
            pass
        
        return {
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "referer": referer,
            "content_type": content_type,
            "query_params": query_params,
            "body": request_body,
            "headers": {k: v for k, v in request.headers.items() 
                       if k.lower() not in ['authorization', 'cookie']}
        }
    
    async def _extract_user_info(self, request: Request) -> Dict[str, Any]:
        """Extraer información del usuario del token JWT."""
        user_info = {
            "user_id": None,
            "username": None,
            "tenant_id": 1,  # Default
            "roles": []
        }
        
        try:
            # Intentar obtener token del header Authorization
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                
                if payload:
                    # Extraer información del payload
                    user_info["user_id"] = payload.get("sub")
                    user_info["username"] = payload.get("email") or payload.get("username")
                    user_info["tenant_id"] = payload.get("tenant_id", 1)
                    user_info["roles"] = payload.get("roles", [])
                    
                    # Si es usuario de servicio (Dolibarr)
                    if user_info["user_id"] and str(user_info["user_id"]).startswith("service_"):
                        user_info["username"] = payload.get("client", "service")
                        user_info["is_service"] = True
        
        except Exception:
            # Si hay error decodificando el token, continuamos sin información de usuario
            pass
        
        # También intentar obtener tenant_id de headers personalizados
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                user_info["tenant_id"] = int(tenant_header)
            except (ValueError, TypeError):
                pass
        
        return user_info
    
    def _determine_action(self, method: str, path: str, status_code: int) -> str:
        """Determinar la acción basada en método HTTP y ruta."""
        # Mapeo de métodos HTTP a acciones
        method_actions = {
            "GET": "VIEW",
            "POST": "CREATE",
            "PUT": "UPDATE", 
            "PATCH": "UPDATE",
            "DELETE": "DELETE",
            "OPTIONS": "OPTIONS",
            "HEAD": "VIEW"
        }
        
        base_action = method_actions.get(method, "UNKNOWN")
        
        # Acciones específicas por ruta
        if "/api/v1/auth/login" in path:
            if status_code == 200:
                return "LOGIN_SUCCESS"
            else:
                return "LOGIN_FAILED"
        elif "/api/v1/auth/logout" in path:
            return "LOGOUT"
        elif "/api/v1/users" in path and method == "POST":
            return "USER_CREATED"
        elif "/api/v1/users" in path and method in ["PUT", "PATCH"]:
            return "USER_UPDATED"
        elif "/api/v1/users" in path and method == "DELETE":
            return "USER_DELETED"
        elif "/api/v1/receive" in path and method == "POST":
            return "INBOUND_RECEIVED"
        elif "/api/v1/orders" in path and "close" in path:
            return "ORDER_PICKED"
        
        return base_action
    
    def _determine_resource_type(self, path: str) -> str:
        """Determinar el tipo de recurso basado en la ruta."""
        path_lower = path.lower()
        
        if "/api/v1/users" in path_lower:
            return "user"
        elif "/api/v1/roles" in path_lower:
            return "role"
        elif "/api/v1/receive" in path_lower:
            return "inbound"
        elif "/api/v1/orders" in path_lower:
            return "order"
        elif "/api/v1/inventory" in path_lower:
            return "inventory"
        elif "/api/v1/auth" in path_lower:
            return "auth"
        elif "/api/v1/audit" in path_lower:
            return "audit"
        elif "/api/v1/dashboard" in path_lower:
            return "dashboard"
        else:
            # Extraer primer segmento después de /api/v1/
            parts = path_lower.split("/")
            if len(parts) > 3:
                return parts[3]
            return "system"
    
    def _extract_resource_id(self, path: str, path_params: dict) -> Optional[int]:
        """Extraer ID de recurso de la ruta o parámetros."""
        try:
            # Buscar patrones comunes de IDs en la ruta
            parts = path.strip("/").split("/")
            
            # Patrón: /resource/{id}
            for i, part in enumerate(parts):
                if part.isdigit():
                    # Verificar que la parte anterior sea un recurso conocido
                    if i > 0 and parts[i-1] in ["users", "roles", "orders", "products"]:
                        return int(part)
            
            # Buscar en path_params
            for key, value in path_params.items():
                if key.endswith("_id") or key == "id":
                    if isinstance(value, (int, str)) and str(value).isdigit():
                        return int(value)
            
            return None
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _prepare_audit_details(
        self, 
        request_info: Dict[str, Any],
        user_info: Dict[str, Any],
        status_code: int,
        error_details: Optional[Dict[str, Any]],
        response_body: Optional[str]
    ) -> Dict[str, Any]:
        """Preparar detalles para el registro de auditoría."""
        details = {
            "request_id": request_info.get("request_id"),
            "user_info": {
                "user_id": user_info.get("user_id"),
                "username": user_info.get("username"),
                "tenant_id": user_info.get("tenant_id"),
                "is_service": user_info.get("is_service", False)
            },
            "request": {
                "method": request_info.get("method", "UNKNOWN"),
                "query_params": request_info.get("query_params", {}),
                "content_type": request_info.get("content_type"),
                "referer": request_info.get("referer")
            },
            "response": {
                "status_code": status_code,
                "success": 200 <= status_code < 400
            }
        }
        
        # Agregar body de request si existe y es pequeño
        if request_info.get("body"):
            details["request"]["body_preview"] = self._truncate_string(
                request_info["body"], 500
            )
        
        # Agregar error si existe
        if error_details:
            details["error"] = error_details
        
        # Agregar preview de response body para errores
        if response_body and status_code >= 400:
            details["response"]["body_preview"] = self._truncate_string(
                response_body, 500
            )
        
        return details
    
    async def _capture_response_body(self, response: Response) -> Optional[str]:
        """Capturar body de response para errores."""
        try:
            # Solo para responses pequeñas
            if hasattr(response, 'body_iterator'):
                body_chunks = []
                async for chunk in response.body_iterator:
                    body_chunks.append(chunk)
                
                # Reconstruir el iterador para que la app pueda usarlo
                response.body_iterator = self._recreate_iterator(body_chunks)
                
                # Unir y decodificar
                body = b"".join(body_chunks)
                if len(body) < self.max_request_size:
                    return body.decode('utf-8', errors='replace')
        except Exception:
            pass
        return None
    
    def _recreate_iterator(self, chunks: list):
        """Recrear un iterator a partir de chunks."""
        async def iterator():
            for chunk in chunks:
                yield chunk
        return iterator()
    
    def _sanitize_sensitive_data(self, data: dict) -> dict:
        """Sanitizar datos sensibles en un diccionario."""
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def _sanitize_sensitive_data_json(self, json_str: str) -> str:
        """Sanitizar datos sensibles en un string JSON."""
        try:
            if not json_str or not json_str.strip():
                return json_str
            
            # Intentar parsear como JSON
            data = json.loads(json_str)
            
            # Función recursiva para sanitizar
            def sanitize_recursive(obj):
                if isinstance(obj, dict):
                    return {
                        k: "[REDACTED]" if any(sensitive in k.lower() 
                            for sensitive in self.sensitive_fields) 
                           else sanitize_recursive(v)
                        for k, v in obj.items()
                    }
                elif isinstance(obj, list):
                    return [sanitize_recursive(item) for item in obj]
                else:
                    return obj
            
            sanitized = sanitize_recursive(data)
            return json.dumps(sanitized)
            
        except (json.JSONDecodeError, TypeError):
            # Si no es JSON válido, buscar patrones sensibles
            lower_str = json_str.lower()
            for sensitive in self.sensitive_fields:
                if sensitive in lower_str:
                    return "[REDACTED_CONTAINS_SENSITIVE_DATA]"
            return json_str
    
    def _safe_traceback(self, exc: Exception) -> Optional[str]:
        """Obtener traceback de forma segura."""
        import traceback
        try:
            return traceback.format_exc()
        except:
            return str(exc)
    
    def _truncate_string(self, text: str, max_length: int) -> str:
        """Truncar string si es muy largo."""
        if not text or len(text) <= max_length:
            return text
        return text[:max_length] + f"... [truncated, total {len(text)} chars]"
    
    async def _log_async(
        self,
        tenant_id: int,
        user_id: Optional[int],
        username: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        details: Dict[str, Any],
        request_path: str,
        request_method: str,
        ip_address: str,
        user_agent: Optional[str],
        status_code: int,
        response_time_ms: int,
        request_id: str
    ):
        """
        Registrar auditoría de forma asíncrona (no bloqueante).
        """
        try:
            # Crear sesión de base de datos
            from core.database import WMSAsyncSessionLocal
            async with WMSAsyncSessionLocal() as session:
                audit_service = AuditService(session)
                
                # Crear el registro de auditoría
                await audit_service.log_action(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    username=username,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    request_path=request_path,
                    request_method=request_method,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status_code=status_code,
                    response_time_ms=response_time_ms
                )
                
        except Exception as e:
            # Registrar error del middleware sin romper la aplicación
            # Podríamos loggear a un archivo o servicio externo aquí
            print(f"Error en middleware de auditoría (request_id: {request_id}): {e}")


# Configuración rápida para desarrollo
def setup_audit_middleware(app) -> 'FastAPI':
    """
    Función de conveniencia para configurar el middleware de auditoría.
    
    Uso en main.py:
        app = FastAPI()
        app = setup_audit_middleware(app)
    """
    # Configuración personalizada
    exclude_paths = [
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/favicon.ico",
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/validate-token",
        "/metrics",  # Si tienes métricas
        "/static/"   # Archivos estáticos
    ]
    
    sensitive_fields = [
        "password",
        "token",
        "authorization",
        "api_key",
        "secret",
        "credit_card",
        "cvv",
        "ssn",
        "phone",
        "email"  # Podrías querer redactar emails también
    ]
    
    # Crear y agregar middleware a la app
    app.add_middleware(
        AuditMiddleware,
        exclude_paths=exclude_paths,
        sensitive_fields=sensitive_fields,
        log_errors=True,
        max_request_size=1024 * 5  # 5KB
    )
    
    return app