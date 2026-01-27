# 📚 ÍNDICE DE DOCUMENTACIÓN - TESTS Y GUÍAS

Bienvenido a la documentación completa para correr tests en la aplicación WMS con Dolibarr.

---

## 📖 Documentos Disponibles

### 1. **GUIA_TESTS.md** - Guía Completa de Tests ⭐ COMIENZA AQUÍ
📍 **Uso:** Guía paso-a-paso sobre cómo configurar y ejecutar todos los tests

**Secciones:**
- Preparación del ambiente
- Descripción detallada de cada test
- Cómo ejecutarlos
- Interpretación de resultados
- Troubleshooting completo
- Checklist pre-deploy

**Comienza aquí si es tu primera vez**

---

### 2. **CHEAT_SHEET_TESTS.md** - Comandos Rápidos de Referencia
📍 **Uso:** Lista rápida de comandos para desarrolladores

**Contiene:**
- Comando para configurar (1 línea)
- Tests rápidos sin servidor
- Comandos para iniciar servidor
- Verificación de endpoints
- Debugging básico
- Tabla de comandos frecuentes

**Mejor para búsqueda rápida de comandos**

---

### 3. **GUIA_ERRORES_LOGS.md** - Análisis de Errores y Logs
📍 **Uso:** Cómo entender y resolver errores

**Incluye:**
- Logs exitosos vs errores
- Causa y solución de cada error común
- Cómo capturar y analizar logs
- Tabla de errores rápida
- Debugging avanzado
- Checklist de diagnóstico

**Cuando algo no funciona, consulta aquí**

---

### 4. **DOLIBARR_INTEGRATION_README.md** - Estado de la Integración
📍 **Uso:** Información sobre cómo está configurada la integración con Dolibarr

**Muestra:**
- Credenciales detectadas
- Status de conexión
- Endpoints disponibles
- Métodos del servicio
- Cómo usar la API
- Scripts de diagnóstico

**Para entender la arquitectura actual**

---

## 🚀 Flujo Recomendado por Escenario

### Escenario 1: Primera Vez Usando la Aplicación

```
1. Lee: GUIA_TESTS.md → Sección "Preparación"
2. Ejecuta: python auto_detect_postgres.py
3. Ejecuta: python test_db_conn.py
4. Lee: GUIA_TESTS.md → Sección "Tests Disponibles"
5. Consulta: DOLIBARR_INTEGRATION_README.md
```

---

### Escenario 2: Desarrollo Diario

```
1. Consulta: CHEAT_SHEET_TESTS.md → Busca tu comando
2. Ejecuta el comando indicado
3. Si hay error: GUIA_ERRORES_LOGS.md → Busca el error
```

---

### Escenario 3: Algo No Funciona

```
1. Lee el error completamente
2. Consulta: GUIA_ERRORES_LOGS.md → Busca tu error
3. Sigue las soluciones
4. Si sigue fallando: Ve al "Checklist de Diagnóstico"
```

---

### Escenario 4: Correr Tests Automatizados

```
1. Terminal PowerShell
2. cd C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app
3. .\run_all_tests.ps1
4. Espera resultados
```

---

## 📋 Resumen Rápido

| Necesito... | Leo... | Comando |
|------------|--------|---------|
| Aprender a correr tests | GUIA_TESTS.md | N/A |
| Un comando rápido | CHEAT_SHEET_TESTS.md | ✓ Incluido |
| Resolver un error | GUIA_ERRORES_LOGS.md | ✓ Incluido |
| Entender la integración | DOLIBARR_INTEGRATION_README.md | N/A |
| Automatizar todo | run_all_tests.ps1 | `.\run_all_tests.ps1` |
| Ver documentación API | Swagger UI | http://localhost:8000/docs |

---

## 🎯 Comandos Más Usados

### Setup (Primera Vez)
```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
& $pythonExe auto_detect_postgres.py
```

### Test Rápido
```powershell
& $pythonExe test_db_conn.py
```

### Iniciar Servidor
```powershell
& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Tests HTTP (en otra terminal)
```powershell
& $pythonExe test_endpoints_directly.py
```

### Automatizar Todo
```powershell
.\run_all_tests.ps1
```

---

## 🔍 Tests Disponibles

| Test | Archivo | Servidor? | Tiempo | Verifica |
|------|---------|-----------|--------|----------|
| Conexión Básica | `test_db_conn.py` | ❌ | ~2s | Conexión PostgreSQL |
| Diagnóstico BD | `test_dolibarr_connection.py` | ❌ | ~3s | 276 tablas Dolibarr |
| Endpoints HTTP | `test_endpoints_directly.py` | ✅ | ~2s | API responde |
| Integración | `test_dolibarr_integration.py` | ✅ | ~5s | Suite completa |
| Auto-Detección | `auto_detect_postgres.py` | ❌ | ~5s | Credenciales correctas |

---

## ✅ Checklist: Todo Funcionando

- [ ] `test_db_conn.py` pasa ✅
- [ ] `test_dolibarr_connection.py` muestra 276+ tablas ✅
- [ ] Servidor inicia sin errores
- [ ] `test_endpoints_directly.py` muestra 3/3 PASS ✅
- [ ] http://127.0.0.1:8000/docs abre sin errores ✅
- [ ] `.env` existe y tiene credenciales válidas ✅

Si todo está marcado, ¡tu aplicación está lista! 🎉

---

## 🆘 Troubleshooting Rápido

| Problema | Solución Rápida |
|----------|-----------------|
| "Connection refused" | Revisar PostgreSQL está ejecutándose: `netstat -an \| findstr "5432"` |
| "No module named..." | `pip install -r requirements.txt` |
| "Port 8000 already in use" | `taskkill /PID xxx /F` o cambiar puerto |
| ".env not found" | `auto_detect_postgres.py` |
| HTTP 500 Error | Ver con `--log-level debug` |

---

## 📞 Cómo Reportar un Problema

Si necesitas ayuda:

1. Ejecuta `test_db_conn.py` y copia la salida
2. Ejecuta `test_dolibarr_connection.py` y copia la salida
3. Copia el error exacto (traceback completo)
4. Proporciona:
   - Tu sistema operativo (Windows 10/11)
   - Versión Python: `python --version`
   - Estado de PostgreSQL: ¿está ejecutándose?
   - Contenido de `.env` (sin contraseña)

---

## 🔗 Navegación Rápida

- 📖 [Guía Completa de Tests](GUIA_TESTS.md)
- ⚡ [Cheat Sheet Comandos](CHEAT_SHEET_TESTS.md)
- 🔴 [Guía de Errores](GUIA_ERRORES_LOGS.md)
- 🔌 [Integración Dolibarr](DOLIBARR_INTEGRATION_README.md)
- 📝 [Índice de Documentación](README_TESTS.md) ← Estás aquí

---

## 💡 Tips

1. **Siempre en la carpeta correcta**: `C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app`
2. **PowerShell o CMD en modo normal**: (No necesita ser Admin para tests)
3. **Dos terminales para servidor + tests**: Uno para servidor, otro para tests
4. **Lee los logs completos**: No solo la última línea
5. **Usa el Cheat Sheet**: Más rápido que la guía completa

---

## 📚 Estructura de Carpetas

```
app/
├── GUIA_TESTS.md                      ← Comienza aquí
├── CHEAT_SHEET_TESTS.md               ← Comandos rápidos
├── GUIA_ERRORES_LOGS.md               ← Resolver problemas
├── DOLIBARR_INTEGRATION_README.md     ← Info integración
├── README_TESTS.md                    ← Este archivo
├── run_all_tests.ps1                  ← Script automatizado
│
├── test_db_conn.py                    ← Test básico
├── test_dolibarr_connection.py        ← Test diagnóstico
├── test_endpoints_directly.py         ← Test endpoints HTTP
├── test_dolibarr_integration.py       ← Test integración
├── auto_detect_postgres.py            ← Setup auto
│
├── main.py                            ← App principal
├── core/
├── routers/
├── models/
├── services/
└── .env                               ← Credenciales
```

---

**Última actualización:** Enero 2026  
**Estado:** ✅ Documentación completa y lista para usar

---

## 🚀 Próximo Paso

¿Nuevo en esto? → Lee **[GUIA_TESTS.md](GUIA_TESTS.md)**

¿Necesitas un comando? → Abre **[CHEAT_SHEET_TESTS.md](CHEAT_SHEET_TESTS.md)**

¿Algo no funciona? → Consulta **[GUIA_ERRORES_LOGS.md](GUIA_ERRORES_LOGS.md)**

---

**¡Feliz testing! 🎉**
