# 🚀 INICIO RÁPIDO - 5 MINUTOS

> Para cuando **NO** tienes tiempo

---

## ⚡ 3 Pasos = Aplicación Lista

### Paso 1️⃣: Configurar (1 minuto)

```powershell
cd "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\app"
$pythonExe = "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr\.venv\Scripts\python.exe"
& $pythonExe auto_detect_postgres.py
```

✅ Copia esto exacto en PowerShell

---

### Paso 2️⃣: Verificar (1 minuto)

```powershell
& $pythonExe test_db_conn.py
```

**Deberías ver:**
```
✅ Connection works!
```

Si NO ves esto → Ve a la sección **Troubleshooting** abajo

---

### Paso 3️⃣: Ejecutar Tests (3 minutos)

```powershell
.\run_all_tests.ps1
```

**Espera a que diga:**
```
✅ TODOS LOS TESTS PASARON
```

---

## ✅ Si Todo Está Bien

Felicidades 🎉 Tu aplicación está lista.

Ahora puedes:
- Iniciar servidor: `& $pythonExe -m uvicorn main:app --host 127.0.0.1 --port 8000`
- Ver API: http://127.0.0.1:8000/docs
- Ejecutar tests: `& $pythonExe test_endpoints_directly.py`

---

## 🆘 Si Algo No Funciona

### Problema: "Connection refused"

```powershell
# Abre otra terminal y ejecuta esto:
netstat -an | findstr "5432"
```

Si no ves `LISTENING` = PostgreSQL no está ejecutándose

**Solución:**
1. Busca "Services" en Windows
2. Encuentra "PostgreSQL"
3. Click derecho → Iniciar

Luego reintenta Paso 1

---

### Problema: "No module named..."

```powershell
& $pythonExe -m pip install -r requirements.txt
```

Luego reintenta Paso 1

---

### Problema: "Port 8000 already in use"

```powershell
netstat -ano | findstr "8000"
# Verás algo como: TCP    127.0.0.1:8000    LISTENING    12345

taskkill /PID 12345 /F
```

Luego reintenta

---

### Problema: Cualquier Otro

Abre [`GUIA_ERRORES_LOGS.md`](GUIA_ERRORES_LOGS.md) y busca tu error

---

## 📚 Necesito Más Info

- ⚡ Comandos rápidos → [`CHEAT_SHEET_TESTS.md`](CHEAT_SHEET_TESTS.md)
- 📖 Guía completa → [`GUIA_TESTS.md`](GUIA_TESTS.md)
- 🔴 Resolver errores → [`GUIA_ERRORES_LOGS.md`](GUIA_ERRORES_LOGS.md)
- 📋 Toda la documentación → [`README_TESTS.md`](README_TESTS.md)

---

**¡Listo! 🚀**
