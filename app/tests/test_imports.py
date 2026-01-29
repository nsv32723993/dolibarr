"""
Script de prueba para verificar que todos los módulos nuevos se importan correctamente.
"""
import sys
import traceback

test_results = {
    "imports": {},
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
}

def test_import(module_name):
    """Probar importación de un módulo"""
    try:
        __import__(module_name)
        test_results["imports"][module_name] = "✅ PASS"
        test_results["summary"]["passed"] += 1
        return True
    except Exception as e:
        test_results["imports"][module_name] = f"❌ FAIL: {str(e)}"
        test_results["summary"]["failed"] += 1
        traceback.print_exc()
        return False

# Lista de módulos a probar
modules_to_test = [
    # Core
    "core.config",
    "core.database",
    "core.security",
    "core.dependencies",
    "core.middleware",
    
    # Middleware
    "middleware.audit_middleware",
    
    # Models
    "models.schemas",
    "models.database_models",
    "models.dolibarr_models",
    
    # Services
    "services.auth_service",
    "services.user_service",
    "services.role_service",
    "services.audit_service",
    "services.tenant_service",
    
    # Routers
    "routers.auth",
    "routers.users",
    "routers.roles",
    "routers.audit",
    
    # Main app
    "main",
]

print("=" * 80)
print("PRUEBA DE IMPORTACIÓN DE MÓDULOS")
print("=" * 80)

for module in modules_to_test:
    test_results["summary"]["total"] += 1
    test_import(module)

# Resumen
print("\n" + "=" * 80)
print("RESUMEN DE RESULTADOS")
print("=" * 80)
print(f"Total de módulos: {test_results['summary']['total']}")
print(f"Pasaron: {test_results['summary']['passed']} ✅")
print(f"Fallaron: {test_results['summary']['failed']} ❌")
print("\nDetalle de cada módulo:")
for module, result in test_results["imports"].items():
    print(f"  {module:40} {result}")

print("\n" + "=" * 80)
if test_results["summary"]["failed"] == 0:
    print("✅ TODOS LOS MÓDULOS SE IMPORTARON CORRECTAMENTE")
else:
    print(f"❌ {test_results['summary']['failed']} MÓDULO(S) FALLARON")
print("=" * 80)

sys.exit(0 if test_results["summary"]["failed"] == 0 else 1)
