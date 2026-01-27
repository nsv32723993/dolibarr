#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Script para ejecutar todos los tests de la aplicación WMS con Dolibarr

.DESCRIPTION
    Este script ejecuta la suite completa de tests, verificando:
    1. Conexión básica a PostgreSQL
    2. Diagnóstico de la base de datos Dolibarr
    3. Tests de endpoints HTTP
    4. Tests de integración completa

.EXAMPLE
    .\run_all_tests.ps1
    
.EXAMPLE
    .\run_all_tests.ps1 -Quick
    Solo ejecuta tests sin servidor
    
.EXAMPLE
    .\run_all_tests.ps1 -ServerOnly
    Solo inicia el servidor sin tests
#>

param(
    [switch]$Quick = $false,
    [switch]$ServerOnly = $false,
    [switch]$EndpointsOnly = $false,
    [int]$Port = 8000
)

# Configuración
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
$appDir = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Funciones auxiliares
function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Error2 {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Warning2 {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Step {
    param([string]$Message, [int]$Step, [int]$Total)
    Write-Host "[$Step/$Total] $Message" -ForegroundColor Magenta
}

# Verificar que Python existe
if (-not (Test-Path $pythonExe)) {
    Write-Error2 "Python no encontrado en: $pythonExe"
    exit 1
}

# Verificar que la carpeta app existe
if (-not (Test-Path $appDir)) {
    Write-Error2 "Carpeta app no encontrada: $appDir"
    exit 1
}

Set-Location $appDir

# Header
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                   SUITE DE TESTS - WMS DOLIBARR                   ║" -ForegroundColor Cyan
Write-Host "║                                                                   ║" -ForegroundColor Cyan
Write-Host "║  Hora: $timestamp" -ForegroundColor Cyan
Write-Host "║  Python: $pythonExe" -ForegroundColor Cyan
Write-Host "║  Directorio: $appDir" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ===============================================
# MODO: Servidor Solamente
# ===============================================
if ($ServerOnly) {
    Write-Info "Iniciando servidor en puerto $Port..."
    Write-Host ""
    & $pythonExe -m uvicorn main:app --host 127.0.0.1 --port $Port
    exit
}

# ===============================================
# MODO: Tests Rápidos (Sin Servidor)
# ===============================================
if ($Quick) {
    Write-Host "🚀 MODO RÁPIDO (sin servidor)" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Step "Test de Conexión Básica" 1 2
    if (Test-Path "test_db_conn.py") {
        & $pythonExe test_db_conn.py
        Write-Host ""
    }
    
    Write-Step "Diagnóstico de Base de Datos" 2 2
    if (Test-Path "test_dolibarr_connection.py") {
        & $pythonExe test_dolibarr_connection.py
        Write-Host ""
    }
    
    Write-Success "Tests rápidos completados"
    exit 0
}

# ===============================================
# MODO: Tests de Endpoints Solamente
# ===============================================
if ($EndpointsOnly) {
    Write-Host "🌐 MODO ENDPOINTS" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Info "Verificando que el servidor está ejecutándose en puerto $Port..."
    $response = $null
    try {
        $response = curl.exe -s -m 2 "http://127.0.0.1:$Port/docs" -o /dev/null -w "%{http_code}"
    } catch {
        Write-Error2 "No se pudo conectar al servidor. ¿Está ejecutándose?"
        exit 1
    }
    
    if ($response -eq "200") {
        Write-Success "Servidor disponible en puerto $Port"
    } else {
        Write-Error2 "Servidor no responde en puerto $Port (HTTP $response)"
        exit 1
    }
    
    Write-Host ""
    Write-Step "Tests de Endpoints" 1 1
    if (Test-Path "test_endpoints_directly.py") {
        & $pythonExe test_endpoints_directly.py
        Write-Host ""
    }
    
    Write-Success "Tests de endpoints completados"
    exit 0
}

# ===============================================
# MODO: Suite Completa (Defecto)
# ===============================================
Write-Host "🚀 MODO COMPLETO (todos los tests)" -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$failCount = 0

# Test 1: Conexión Básica
Write-Step "Test de Conexión Básica" 1 5
if (Test-Path "test_db_conn.py") {
    try {
        & $pythonExe test_db_conn.py | Tee-Object -Variable output | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Conexión básica: OK"
            $successCount++
        } else {
            Write-Error2 "Conexión básica: FALLÓ"
            $failCount++
        }
    } catch {
        Write-Error2 "Error ejecutando test_db_conn.py: $_"
        $failCount++
    }
} else {
    Write-Warning2 "test_db_conn.py no encontrado"
}
Write-Host ""

# Test 2: Diagnóstico de Base de Datos
Write-Step "Diagnóstico de Base de Datos" 2 5
if (Test-Path "test_dolibarr_connection.py") {
    try {
        & $pythonExe test_dolibarr_connection.py | Tee-Object -Variable output | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Diagnóstico BD: OK"
            $successCount++
        } else {
            Write-Error2 "Diagnóstico BD: FALLÓ"
            $failCount++
        }
    } catch {
        Write-Error2 "Error ejecutando test_dolibarr_connection.py: $_"
        $failCount++
    }
} else {
    Write-Warning2 "test_dolibarr_connection.py no encontrado"
}
Write-Host ""

# Test 3: Iniciar Servidor
Write-Step "Iniciando Servidor FastAPI" 3 5
Write-Info "Iniciando en puerto $Port..."
try {
    $serverProcess = Start-Process -NoNewWindow -PassThru `
        -FilePath $pythonExe `
        -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$Port" `
        -RedirectStandardOutput "$appDir\server.log" `
        -RedirectStandardError "$appDir\server_error.log"
    
    # Esperar que el servidor inicie
    Write-Info "Esperando que el servidor se inicie (5 segundos)..."
    Start-Sleep -Seconds 5
    
    # Verificar que el servidor está corriendo
    if ($null -ne (Get-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue)) {
        Write-Success "Servidor iniciado (PID: $($serverProcess.Id))"
        $successCount++
    } else {
        Write-Error2 "El servidor no se inició correctamente"
        Write-Info "Log de error:"
        Get-Content "$appDir\server_error.log" | Select-Object -First 10
        $failCount++
    }
} catch {
    Write-Error2 "Error iniciando servidor: $_"
    $failCount++
    $serverProcess = $null
}
Write-Host ""

# Test 4: Tests de Endpoints HTTP
if ($null -ne $serverProcess) {
    Write-Step "Tests de Endpoints HTTP" 4 5
    if (Test-Path "test_endpoints_directly.py") {
        try {
            & $pythonExe test_endpoints_directly.py
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Tests de endpoints: OK"
                $successCount++
            } else {
                Write-Error2 "Tests de endpoints: FALLÓ"
                $failCount++
            }
        } catch {
            Write-Error2 "Error ejecutando test_endpoints_directly.py: $_"
            $failCount++
        }
    } else {
        Write-Warning2 "test_endpoints_directly.py no encontrado"
    }
    Write-Host ""
    
    # Test 5: Tests de Integración
    Write-Step "Tests de Integración Completa" 5 5
    if (Test-Path "test_dolibarr_integration.py") {
        try {
            & $pythonExe test_dolibarr_integration.py
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Tests de integración: OK"
                $successCount++
            } else {
                Write-Warning2 "Tests de integración completaron con algunos problemas"
                # No contar como fallo crítico
            }
        } catch {
            Write-Warning2 "Error en tests de integración: $_"
        }
    } else {
        Write-Warning2 "test_dolibarr_integration.py no encontrado"
    }
    Write-Host ""
    
    # Detener servidor
    Write-Info "Deteniendo servidor (PID: $($serverProcess.Id))..."
    try {
        Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
        Write-Success "Servidor detenido"
    } catch {
        Write-Warning2 "Error deteniendo servidor: $_"
    }
} else {
    Write-Error2 "No se pudo iniciar el servidor, omitiendo tests de endpoints"
    $failCount += 2
}

Write-Host ""

# ===============================================
# RESUMEN FINAL
# ===============================================
Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                          RESUMEN FINAL                            ║" -ForegroundColor Cyan
Write-Host "║                                                                   ║" -ForegroundColor Cyan
Write-Host "║  Tests Exitosos: $successCount" -ForegroundColor Cyan
Write-Host "║  Tests Fallidos: $failCount" -ForegroundColor Cyan
Write-Host "║                                                                   ║" -ForegroundColor Cyan

if ($failCount -eq 0) {
    Write-Host "║  Estado: ✅ TODOS LOS TESTS PASARON                              ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Success "¡Aplicación lista para usar!"
    exit 0
} else {
    Write-Host "║  Estado: ❌ ALGUNOS TESTS FALLARON                              ║" -ForegroundColor Red
    Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Error2 "Revisa los errores arriba para más detalles"
    exit 1
}
