# 🔍 GUÍA DE LOGS Y ERRORES

> Cómo entender qué está pasando cuando algo falla

---

## 📝 Análisis de Logs

### Ubicación de Logs

Los logs se guardan en:

```
C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app\
├── server.log              # Salida estándar del servidor
├── server_error.log        # Errores del servidor
└── test_results_*.log      # Resultados de tests (si se guardan)
```

---

## 🟢 Logs Exitosos

### Servidor Iniciado Correctamente

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

✅ **Significa:** El servidor está listo

---

### Test de Conexión Exitoso

```
[*] Testing connection...
[*] Session created
[*] Executed query
✅ Connection works!
```

✅ **Significa:** La base de datos responde correctamente

---

### Test de Base de Datos Exitoso

```
✅ Database connection SUCCESSFUL!
📊 Database Tables (276 total):
  ✓ llx_product (0 rows)
  ✓ llx_societe (0 rows)
  ✓ llx_commande (0 rows)
```

✅ **Significa:** Dolibarr está accesible con todas sus tablas

---

### Test de Endpoints Exitoso

```
[1] Testing /api/v1/dolibarr/test-connection
    Status: 200
    ✅ PASS

[2] Testing /api/v1/dolibarr/info
    Status: 200
    ✅ PASS
```

✅ **Significa:** Los endpoints HTTP responden correctamente

---

## 🔴 Logs de Error

### Error: Connection Refused

```
Error: connection refused
```

**Causa:** PostgreSQL no está ejecutándose o no escucha en puerto 5432

**Soluciones:**
1. Iniciar PostgreSQL: `Services` → `PostgreSQL` → Iniciar
2. Verificar puerto: `netstat -an | findstr "5432"`
3. Revisar .env: `cat .env`

---

### Error: Authentication Failed

```
FATAL: password authentication failed for user "dolibarr"
```

**Causa:** Credenciales incorrectas en .env

**Soluciones:**
1. Auto-detectar: `& $pythonExe auto_detect_postgres.py`
2. Verificar credenciales: `cat .env`
3. Si cambió password, editar manualmente

---

### Error: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'fastapi'
```

**Causa:** Dependencias Python no instaladas

**Soluciones:**
```powershell
# Opción 1: Instalar directamente
& $pythonExe -m pip install fastapi uvicorn sqlalchemy psycopg2-binary

# Opción 2: Desde requirements.txt
& $pythonExe -m pip install -r requirements.txt
```

---

### Error: Address Already in Use

```
ERROR: [Errno 10048] Only one usage of each socket address (protocol/TCP port) is normally permitted
OSError: [WinError 10048] Only one usage of each socket address
```

**Causa:** El puerto 8000 ya está siendo usado

**Soluciones:**
```powershell
# Encontrar proceso que usa el puerto
netstat -ano | findstr "8000"

# Salida típica:
# TCP    127.0.0.1:8000            LISTENING       12345

# Matar el proceso
taskkill /PID 12345 /F

# O usar un puerto diferente
& $pythonExe -m uvicorn main:app --port 8001
```

---

### Error: File Not Found

```
FileNotFoundError: [Errno 2] No such file or directory: '.env'
```

**Causa:** El archivo .env no existe

**Soluciones:**
```powershell
# Generar automáticamente
& $pythonExe auto_detect_postgres.py

# O crear manualmente
@"
DOLIBARR_DB_HOST=localhost
DOLIBARR_DB_PORT=5432
DOLIBARR_DB_NAME=dolibarr
DOLIBARR_DB_USER=dolibarr
DOLIBARR_DB_PASSWORD=dolibarr
"@ | Out-File -Encoding UTF8 .env
```

---

### Error: SyntaxError or ImportError

```
SyntaxError: invalid syntax
ImportError: cannot import name 'OrderItem' from 'models.schemas'
```

**Causa:** Hay un error en el código Python

**Soluciones:**
1. Leer el traceback completamente (línea del error)
2. Abrir el archivo en cuestión
3. Buscar la línea indicada
4. Verificar sintaxis (paréntesis, comillas, indentación)

---

### Error: HTTP 500 - Internal Server Error

```
HTTP/1.1 500 Internal Server Error
{"detail":"Internal server error"}
```

**Causa:** Error no manejado en un endpoint

**Soluciones:**
1. Ver logs del servidor en tiempo real
2. Ejecutar con logging debug: `--log-level debug`
3. Revisar el traceback en los logs
4. Buscar la línea del error en el código

---

### Error: HTTP 404 - Not Found

```
HTTP/1.1 404 Not Found
{"detail":"Not Found"}
```

**Causa:** El endpoint solicitado no existe

**Soluciones:**
1. Verificar URL: `curl http://127.0.0.1:8000/api/v1/dolibarr/info`
2. Ver endpoints disponibles: `http://127.0.0.1:8000/docs`
3. Verificar que router está registrado en main.py

---

## 🟡 Advertencias (No son Errores)

### Tabla o Columna No Existe

```
⚠️  Table 'llx_custom_field' does not exist
```

**Significado:** La tabla opcional no está en Dolibarr. Puede ser normal si no la activaste.

**Acción:** Ignorar si no necesitas esa tabla

---

### Datos Vacíos en Base de Datos

```
Response: {'products': 0, 'companies': 0, 'orders': 0}
⚠️  No data in database (expected for new installation)
```

**Significado:** Dolibarr no tiene datos aún. Es normal en instalación nueva.

**Acción:** Crear datos de prueba en Dolibarr para testing

---

### Conexión Lenta

```
[SLOW] Database query took 2.5 seconds
```

**Significado:** Hay latencia en la BD o la consulta es compleja

**Acción:** Optimizar query si es frecuente

---

## 🔧 Debugging Avanzado

### Habilitar Logging Completo

```powershell
# Iniciar servidor con logging debug
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

& $pythonExe -m uvicorn main:app `
    --host 127.0.0.1 `
    --port 8000 `
    --log-level debug `
    --access-log
```

---

### Capturar Logs en Archivo

```powershell
# Guardar todo lo que imprime el servidor
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000 `
    | Tee-Object "servidor_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"
```

---

### Ejecutar Python en Modo Interactivo para Debug

```powershell
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
Set-Location "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"

# Entrar a consola Python
& $pythonExe

# Luego en Python:
>>> from core.database import get_dolibarr_db
>>> db = next(get_dolibarr_db())
>>> db.execute(text("SELECT 1")).fetchone()
(1,)
>>> exit()
```

---

## 📊 Tabla de Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `connection refused` | PostgreSQL offline | Iniciar PostgreSQL |
| `password authentication failed` | Credenciales mal | `auto_detect_postgres.py` |
| `No module named 'fastapi'` | Dependencias faltantes | `pip install -r requirements.txt` |
| `Address already in use :8000` | Puerto ocupado | `taskkill /PID xxx /F` |
| `.env` not found | Falta .env | `auto_detect_postgres.py` |
| `ImportError: cannot import` | Import incorrecto | Verificar sintaxis, línea del error |
| HTTP 500 | Error en endpoint | Ver logs con `--log-level debug` |
| HTTP 404 | Endpoint no existe | Verificar URL en `/docs` |
| `SyntaxError` | Error de sintaxis | Revisar paréntesis, comillas |
| `Timeout` | Servidor no responde | Verificar que servidor está ejecutándose |

---

## ✅ Checklist de Diagnóstico

Cuando algo no funciona, sigue este orden:

```
1. [ ] ¿PostgreSQL está ejecutándose?
       netstat -an | findstr "5432"

2. [ ] ¿El archivo .env existe?
       cat .env

3. [ ] ¿Las credenciales son correctas?
       & $pythonExe test_db_conn.py

4. [ ] ¿La base de datos está accesible?
       & $pythonExe test_dolibarr_connection.py

5. [ ] ¿El servidor inicia sin errores?
       & $pythonExe -m uvicorn main:app --port 8000

6. [ ] ¿Los endpoints responden?
       curl http://127.0.0.1:8000/api/v1/dolibarr/test-connection

7. [ ] ¿Hay error específico en los logs?
       cat server.log | findstr "ERROR"
```

---

## 🎯 Próximos Pasos Si Ves un Error

1. **Lee el error completo** - No solo la última línea
2. **Nota el archivo y línea** - Ej: `file.py:45`
3. **Abre ese archivo** - En VS Code
4. **Busca la línea** - Presiona Ctrl+G y ve a la línea
5. **Lee el contexto** - 5 líneas antes y después
6. **Consulta esta guía** - Busca el error en la tabla arriba
7. **Ejecuta el script de diagnóstico** - `test_*.py` relevante
8. **Revisa Stackoverflow** - Si no está en esta guía

---

## 📞 Información para Reportar un Bug

Si necesitas ayuda, proporciona:

```
1. Línea exacta del error (copiar todo el traceback)
2. Qué archivo y línea (del traceback)
3. Resultado de: & $pythonExe test_db_conn.py
4. Resultado de: & $pythonExe test_dolibarr_connection.py
5. Versión de Python: & $pythonExe --version
6. Versión de PostgreSQL: SELECT version();
7. Contenido de .env (sin password)
```

---

## 🔗 Enlaces Útiles

- [FastAPI Error Codes](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Connection Errors](https://www.postgresql.org/docs/current/errcodes-appendix.html)
- [Python Exception Types](https://docs.python.org/3/library/exceptions.html)

---

**¿Tienes un error que no aparece aquí?** Crea una issue con los detalles arriba.
