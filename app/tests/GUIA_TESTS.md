# 🧪 GUÍA COMPLETA DE TESTS - WMS Dolibarr

## 📋 Tabla de Contenidos
1. [Preparación del Ambiente](#preparación)
2. [Tests Disponibles](#tests-disponibles)
3. [Cómo Correr los Tests](#cómo-correr-los-tests)
4. [Interpretación de Resultados](#interpretación-de-resultados)
5. [Troubleshooting](#troubleshooting)
6. [Flujo Completo Recomendado](#flujo-completo-recomendado)

---

## 🚀 Preparación {#preparación}

### Paso 1: Verificar Ambiente Python

```powershell
# Abrir PowerShell y verificar que el virtualenv está disponible
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"

# Verificar que Python funciona
& $pythonExe --version
# Debe mostrar: Python 3.11.9
```

### Paso 2: Navegar a la Carpeta Correcta

```powershell
cd "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
```

### Paso 3: Verificar Archivo .env

```powershell
# El archivo .env debe existir en la carpeta app/
# Debe contener:
cat .env

# Salida esperada:
# DOLIBARR_DB_HOST=localhost
# DOLIBARR_DB_PORT=5432
# DOLIBARR_DB_NAME=dolibarr
# DOLIBARR_DB_USER=dolibarr
# DOLIBARR_DB_PASSWORD=dolibarr
```

Si el archivo `.env` no existe, ejecuta el script de auto-detección:

```powershell
& $pythonExe auto_detect_postgres.py
```

### Paso 4: Verificar que PostgreSQL está Corriendo

```powershell
# En otra terminal, verifica que PostgreSQL está en el puerto 5432
netstat -an | findstr "5432"

# Debe mostrar algo como:
# TCP    127.0.0.1:5432            LISTENING
```

---

## 🧪 Tests Disponibles {#tests-disponibles}

### 1. **test_db_conn.py** - Test Básico de Conexión
**Propósito:** Verificar que la conexión a la base de datos funciona  
**Dependencias:** PostgreSQL ejecutándose, .env configurado  
**Tiempo de ejecución:** ~2 segundos  
**Nivel:** 🟢 Fundamental

```powershell
& $pythonExe test_db_conn.py
```

**Salida esperada:**
```
[*] Testing connection...
[*] Session created
[*] Executed query
✅ Connection works!
```

---

### 2. **test_dolibarr_connection.py** - Diagnóstico Completo de BD
**Propósito:** Inspeccionar la base de datos Dolibarr en detalle  
**Dependencias:** PostgreSQL ejecutándose, .env configurado  
**Tiempo de ejecución:** ~3-5 segundos  
**Nivel:** 🟢 Fundamental

```powershell
& $pythonExe test_dolibarr_connection.py
```

**Salida esperada:**
```
======================================================================
🔍 DOLIBARR DATABASE CONNECTION DIAGNOSTIC
======================================================================

📋 Configuration Summary:
  Host: localhost
  Port: 5432
  Database: dolibarr
  User: dolibarr
  Connection String: postgresql://dolibarr:***@localhost:5432/dolibarr

🔗 Attempting Database Connection...
✅ Database connection SUCCESSFUL!

📊 Database Tables (276 total):
  ✓ llx_product
  ✓ llx_societe
  ✓ llx_commande
  ✓ llx_stock_mouvement
  ... (y 272 tablas más)
```

---

### 3. **test_endpoints_directly.py** - Test de Endpoints HTTP
**Propósito:** Verificar que los endpoints API funcionan correctamente  
**Dependencias:** Aplicación FastAPI debe estar ejecutándose  
**Tiempo de ejecución:** ~2-3 segundos  
**Nivel:** 🟡 Intermedio

```powershell
# En una terminal (Terminal A), inicia el servidor:
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000

# En OTRA terminal (Terminal B), ejecuta los tests:
& $pythonExe test_endpoints_directly.py
```

**Salida esperada:**
```
======================================================================
Testing Dolibarr Endpoints
======================================================================

[1] Testing /api/v1/dolibarr/test-connection
    Status: 200
    Response: {'status': 'connected', 'message': 'Successfully connected to Dolibarr database', 'database': 'dolibarr'}
    ✅ PASS

[2] Testing /api/v1/dolibarr/info
    Status: 200
    Response: {'status': 'success', 'data': {'products': 0, 'companies': 0, 'orders': 0}}
    ✅ PASS

[3] Testing GET /
    Status: 200
    Response: {'message': 'WMS API Integrada con Dolibarr ejecutándose', 'version': '1.0.0', ...}
    ✅ PASS

======================================================================
✨ Test complete
```

---

### 4. **test_dolibarr_integration.py** - Tests Integrales
**Propósito:** Suite completa de tests de integración  
**Dependencias:** PostgreSQL + Servidor FastAPI ejecutándose  
**Tiempo de ejecución:** ~5-10 segundos  
**Nivel:** 🔴 Avanzado

```powershell
# En una terminal (Terminal A), inicia el servidor:
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000

# En OTRA terminal (Terminal B), ejecuta los tests:
& $pythonExe test_dolibarr_integration.py
```

---

### 5. **auto_detect_postgres.py** - Auto-detección de Credenciales
**Propósito:** Detectar automáticamente las credenciales de PostgreSQL  
**Dependencias:** PostgreSQL ejecutándose  
**Tiempo de ejecución:** ~5-30 segundos (depende de los intentos)  
**Nivel:** 🟢 Fundamental

```powershell
& $pythonExe auto_detect_postgres.py
```

**Salida esperada:**
```
[*] Probando credenciales de PostgreSQL...
[*] Intentando con usuario: dolibarr, contraseña: dolibarr
✅ ¡Credenciales encontradas!

Credenciales detectadas:
  Host: localhost
  Port: 5432
  User: dolibarr
  Password: dolibarr
  Database: dolibarr

✅ Archivo .env creado exitosamente
```

---

## 🏃 Cómo Correr los Tests {#cómo-correr-los-tests}

### Opción 1: Tests Rápidos (Sin Servidor)

Estos tests NO requieren que el servidor esté ejecutándose:

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

# Test 1: Conexión básica
Write-Host "▶️  Ejecutando test_db_conn.py..."
& $pythonExe test_db_conn.py
Write-Host ""

# Test 2: Diagnóstico detallado
Write-Host "▶️  Ejecutando test_dolibarr_connection.py..."
& $pythonExe test_dolibarr_connection.py
Write-Host ""

Write-Host "✅ Tests rápidos completados"
```

### Opción 2: Tests con Servidor HTTP

Requiere que el servidor esté ejecutándose:

```powershell
# Terminal A: Iniciar el servidor
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal B: Ejecutar los tests
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe test_endpoints_directly.py
```

### Opción 3: Automatizar Todo con Script

Crea un archivo `run_all_tests.ps1`:

```powershell
#!/usr/bin/env pwsh

$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
$appDir = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

Set-Location $appDir

Write-Host "🧪 EJECUTANDO SUITE COMPLETA DE TESTS" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host ""

# Tests Rápidos
Write-Host "[1/5] Test de Conexión Básica..." -ForegroundColor Yellow
& $pythonExe test_db_conn.py
Write-Host ""

Write-Host "[2/5] Diagnóstico de Base de Datos..." -ForegroundColor Yellow
& $pythonExe test_dolibarr_connection.py
Write-Host ""

Write-Host "[3/5] Iniciando Servidor..." -ForegroundColor Yellow
$serverProcess = Start-Process -NoNewWindow -PassThru -FilePath $pythonExe -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"

# Esperar que el servidor inicie
Start-Sleep -Seconds 3

Write-Host "[4/5] Tests de Endpoints..." -ForegroundColor Yellow
& $pythonExe test_endpoints_directly.py
Write-Host ""

Write-Host "[5/5] Tests de Integración..." -ForegroundColor Yellow
& $pythonExe test_dolibarr_integration.py
Write-Host ""

# Detener el servidor
Write-Host "Deteniendo servidor..." -ForegroundColor Yellow
Stop-Process -Id $serverProcess.Id

Write-Host "✅ Suite de tests completada" -ForegroundColor Green
```

Ejecutar:
```powershell
. .\run_all_tests.ps1
```

---

## 📊 Interpretación de Resultados {#interpretación-de-resultados}

### ✅ Test Exitoso

Indicadores:
- Status HTTP 200
- Mensaje diciendo `✅ PASS` o `✅ Connection works!`
- No hay mensajes de error en rojo

Ejemplo:
```
[1] Testing /api/v1/dolibarr/test-connection
    Status: 200
    ✅ PASS
```

---

### ❌ Test Fallido

Indicadores:
- Status HTTP diferente de 200 (400, 500, etc.)
- Mensaje de error en la salida
- Excepción de Python visible

**Ejemplo de fallo:**
```
[1] Testing /api/v1/dolibarr/test-connection
    Status: 500
    Error: Connection refused
    ❌ FAIL
```

---

### 🟡 Test Advertencia

Indicadores:
- Status 200 pero datos vacíos o inesperados
- Ejemplo: Database conecta pero no hay productos

```
[2] Testing /api/v1/dolibarr/info
    Status: 200
    Response: {'products': 0, 'companies': 0, 'orders': 0}
    ⚠️  No data in database (expected for new installation)
```

---

## 🔧 Troubleshooting {#troubleshooting}

### Problema: "Connection refused"

**Causa:** PostgreSQL no está ejecutándose o no está en el puerto correcto

**Solución:**
```powershell
# Verificar que PostgreSQL está escuchando
netstat -an | findstr "5432"

# Si no aparece, inicia PostgreSQL:
# Windows: Services > PostgreSQL > Iniciar
# O desde línea de comandos:
# pg_ctl -D "C:\Program Files\PostgreSQL\data" start
```

---

### Problema: "Authentication failed"

**Causa:** Credenciales incorrectas en .env

**Solución:**
```powershell
# Re-ejecutar auto-detección
& $pythonExe auto_detect_postgres.py

# O editar .env manualmente:
# DOLIBARR_DB_USER=dolibarr
# DOLIBARR_DB_PASSWORD=dolibarr
```

---

### Problema: "ModuleNotFoundError: No module named 'fastapi'"

**Causa:** Las dependencias no están instaladas

**Solución:**
```powershell
# Instalar dependencias
& $pythonExe -m pip install -r requirements.txt

# O manualmente:
& $pythonExe -m pip install fastapi uvicorn sqlalchemy psycopg2-binary requests httpx pydantic-settings python-multipart
```

---

### Problema: "Address already in use :8000"

**Causa:** El servidor ya está ejecutándose en el puerto 8000

**Solución:**
```powershell
# Encontrar el proceso que usa el puerto 8000
netstat -ano | findstr "8000"

# Matar el proceso (reemplaza PID)
taskkill /PID 12345 /F

# O usar un puerto diferente:
& $pythonExe -m uvicorn main:app --port 8001
```

---

### Problema: "No such file or directory: .env"

**Causa:** El archivo .env no existe

**Solución:**
```powershell
# Crear .env automáticamente
& $pythonExe auto_detect_postgres.py

# O crearlo manualmente
$env = @"
DOLIBARR_DB_HOST=localhost
DOLIBARR_DB_PORT=5432
DOLIBARR_DB_NAME=dolibarr
DOLIBARR_DB_USER=dolibarr
DOLIBARR_DB_PASSWORD=dolibarr
"@
$env | Out-File -Encoding utf8 .env
```

---

### Problema: "OSError: [WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions"

**Causa:** Firewall bloqueando el puerto 8000

**Solución:**
```powershell
# Permitir Python en firewall (ejecutar como Admin)
New-NetFirewallRule -DisplayName "Allow Python 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000

# O ejecutar con un puerto diferente
& $pythonExe -m uvicorn main:app --port 8001
```

---

## ✨ Flujo Completo Recomendado {#flujo-completo-recomendado}

### Para Primera Vez / Configuración Inicial

```powershell
# 1. Auto-detectar credenciales
Write-Host "Paso 1: Auto-detectando credenciales de PostgreSQL..."
& $pythonExe auto_detect_postgres.py

# 2. Test de conexión básica
Write-Host "Paso 2: Verificando conexión a base de datos..."
& $pythonExe test_db_conn.py

# 3. Diagnóstico detallado
Write-Host "Paso 3: Inspección de base de datos..."
& $pythonExe test_dolibarr_connection.py

Write-Host "✅ Configuración inicial completada"
```

### Para Desarrollo Diario

```powershell
# 1. Quick check de conexión
& $pythonExe test_db_conn.py

# 2. Iniciar servidor
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000

# 3. En otra terminal, test endpoints
& $pythonExe test_endpoints_directly.py
```

### Para CI/CD o Tests Automatizados

```powershell
# Ejecutar todos los tests sin requiere supervisión manual
& .\run_all_tests.ps1
```

---

## 📝 Checklist Pre-Deploy

Antes de desplegar la aplicación, asegúrate que:

- [ ] ✅ `test_db_conn.py` pasa exitosamente
- [ ] ✅ `test_dolibarr_connection.py` muestra 276+ tablas
- [ ] ✅ `test_endpoints_directly.py` muestra 3/3 tests pasados
- [ ] ✅ El servidor inicia sin errores de importación
- [ ] ✅ Puedes acceder a http://127.0.0.1:8000/docs (Swagger UI)
- [ ] ✅ PostgreSQL está ejecutándose y responde
- [ ] ✅ El archivo `.env` contiene credenciales válidas

---

## 🎯 Resumen Rápido

| Test | Comando | Servidor Requerido | Tiempo |
|------|---------|-------------------|--------|
| Conexión Básica | `test_db_conn.py` | ❌ No | ~2s |
| Diagnóstico BD | `test_dolibarr_connection.py` | ❌ No | ~3s |
| Endpoints HTTP | `test_endpoints_directly.py` | ✅ Sí | ~2s |
| Integración Completa | `test_dolibarr_integration.py` | ✅ Sí | ~5s |
| Auto-detección | `auto_detect_postgres.py` | ❌ No | ~5s |

---

**¿Preguntas?** Consulta la sección [Troubleshooting](#troubleshooting) o revisa los archivos de test directamente.
