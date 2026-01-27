# 📚 CHEAT SHEET - Comandos Rápidos para Tests

> **Ubicación:** Todo se ejecuta desde `C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app`

---

## 🟢 Configuración Inicial (Primera Vez)

```powershell
# Ir a la carpeta correcta
cd "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

# Auto-detectar credenciales de PostgreSQL
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe auto_detect_postgres.py

# Verificar que el archivo .env se creó
cat .env
```

---

## 🔧 Tests Básicos (Sin Servidor)

### Test 1: Conexión Simple

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe test_db_conn.py
```

**Salida esperada:**
```
✅ Connection works!
```

---

### Test 2: Diagnóstico Completo

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe test_dolibarr_connection.py
```

**Salida esperada:**
```
✅ Database connection SUCCESSFUL!
📊 Database Tables (276 total):
```

---

## 🚀 Ejecutar Servidor

### Opción 1: Uvicorn Directo

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Luego abre: http://127.0.0.1:8000/docs

---

### Opción 2: Python Directo

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe main.py
```

---

### Opción 3: Con Logging Detallado

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level debug
```

---

## 🧪 Tests HTTP (Requiere Servidor Corriendo)

### En Terminal A: Iniciar Servidor

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### En Terminal B: Ejecutar Tests

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe test_endpoints_directly.py
```

---

## 🤖 Automatización - Script Completo

```powershell
# Ejecutar toda la suite de tests automáticamente
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
. .\run_all_tests.ps1
```

---

## 📋 Opciones del Script run_all_tests.ps1

```powershell
# Suite Completa (Defecto - todos los tests)
.\run_all_tests.ps1

# Solo tests rápidos (sin servidor)
.\run_all_tests.ps1 -Quick

# Solo iniciar servidor
.\run_all_tests.ps1 -ServerOnly

# Solo tests de endpoints (requiere servidor ya ejecutándose)
.\run_all_tests.ps1 -EndpointsOnly

# Cambiar puerto (defecto: 8000)
.\run_all_tests.ps1 -Port 8001
```

---

## 🔍 Verificación de Endpoints

### Con curl (PowerShell)

```powershell
# Test de conexión
curl.exe http://127.0.0.1:8000/api/v1/dolibarr/test-connection

# Información de BD
curl.exe http://127.0.0.1:8000/api/v1/dolibarr/info

# Root endpoint
curl.exe http://127.0.0.1:8000/

# Documentación Swagger
Start-Process "http://127.0.0.1:8000/docs"
```

---

### Con Requests (Python)

```python
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe -c @"
import requests
r = requests.get('http://127.0.0.1:8000/api/v1/dolibarr/info')
print(r.json())
"@
```

---

## 🐛 Debugging

### Ver logs del servidor

```powershell
# Si guardaste en un archivo
Get-Content "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app\server.log"

# O en tiempo real con tail
Get-Content "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app\server.log" -Tail 20 -Wait
```

---

### Verificar proceso de Python

```powershell
# Ver todos los procesos Python ejecutándose
Get-Process python

# Matar un proceso específico (reemplaza PID)
Stop-Process -Id 12345 -Force

# Buscar proceso usando puerto 8000
netstat -ano | findstr "8000"
```

---

### Verificar PostgreSQL

```powershell
# Ver si PostgreSQL está escuchando
netstat -an | findstr "5432"

# Probar conexión manual a BD
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe -c @"
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://dolibarr:dolibarr@localhost:5432/dolibarr')
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print(result.fetchone())
"@
```

---

## 📊 Validar Setup Completo

```powershell
# Script de validación rápida
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

Write-Host "✓ Verificando Python..." -ForegroundColor Yellow
& $pythonExe --version

Write-Host "✓ Verificando .env..." -ForegroundColor Yellow
if (Test-Path ".env") { Write-Host "  .env exists ✅" } else { Write-Host "  .env NOT FOUND ❌" }

Write-Host "✓ Test de conexión BD..." -ForegroundColor Yellow
& $pythonExe test_db_conn.py

Write-Host "✓ Verificando módulos..." -ForegroundColor Yellow
& $pythonExe -c "import fastapi, sqlalchemy, psycopg2; print('All modules OK ✅')"
```

---

## ⚡ Workflow Recomendado para Desarrollo

```powershell
# 1. Setup inicial (una sola vez)
cd "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe auto_detect_postgres.py

# 2. Verificación rápida
& $pythonExe test_db_conn.py

# 3. Iniciar servidor en una terminal
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000

# 4. En otra terminal, tests
& $pythonExe test_endpoints_directly.py

# 5. Abre Swagger UI
Start-Process "http://127.0.0.1:8000/docs"
```

---

## 🆘 Troubleshooting Rápido

| Problema | Comando para Verificar | Solución |
|----------|----------------------|----------|
| No hay conexión a BD | `& $pythonExe test_db_conn.py` | Ejecutar `auto_detect_postgres.py` |
| Servidor no inicia | `& $pythonExe -m uvicorn main:app --port 8001` | Cambiar puerto (8000 en uso?) |
| Puerto en uso | `netstat -ano \| findstr "8000"` | `taskkill /PID xxx /F` |
| Módulos faltantes | `& $pythonExe -m pip list` | `pip install -r requirements.txt` |
| .env no existe | `cat .env` | `& $pythonExe auto_detect_postgres.py` |

---

## 💾 Guardar Logs

```powershell
# Guardar salida de tests
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"

& $pythonExe test_endpoints_directly.py | Tee-Object "test_results_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"

# O directamente
& $pythonExe test_endpoints_directly.py > "test_results.log" 2>&1
```

---

## 🎯 Sumario de Comandos Más Usados

```powershell
# Configurar (1 vez)
cd "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe auto_detect_postgres.py

# Test rápido
& $pythonExe test_db_conn.py

# Iniciar servidor
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000

# Tests (en otra terminal)
& $pythonExe test_endpoints_directly.py

# Automatizar todo
.\run_all_tests.ps1

# Documentación
http://127.0.0.1:8000/docs
```
