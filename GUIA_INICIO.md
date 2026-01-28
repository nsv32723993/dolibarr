# 🚀 Guía de Inicio - Levantar Dolibarr con Docker en PowerShell

Esta guía te explicará cómo levantar el proyecto Dolibarr desde cero en Windows usando Docker y PowerShell.

---

## 📋 Requisitos Previos

Asegúrate de tener instalado lo siguiente:

- **Docker Desktop** (con Docker Engine y Docker Compose)
  - Descargar desde: https://www.docker.com/products/docker-desktop
  - Verifica la instalación ejecutando en PowerShell:
    ```powershell
    docker --version
    docker-compose --version
    ```

- **Python 3.8+** (opcional, solo si quieres usar los scripts de configuración)
  - Verifica: `python --version`

- **PowerShell 5.1 o superior**
  - Debería estar disponible en Windows 10/11

---

## 🔧 Pasos para Levantar el Proyecto

### Paso 1: Navega a la carpeta del proyecto

```powershell
cd "C:\Users\naiko\OneDrive\Desktop\doli\dolibarr"
```

### Paso 2: Inicia Docker Desktop

Si Docker Desktop no está corriendo, abrelo desde el menú de inicio de Windows.

Verifica que esté corriendo:
```powershell
docker info
```

### Paso 3: Levanta los contenedores con Docker Compose

El archivo `docker-compose.yml` define dos servicios:
- **dolibarr**: Aplicación ERP (Puerto 8080)
- **postgres**: Base de datos PostgreSQL (Puerto 5432)

Ejecuta:
```powershell
docker-compose up -d
```

**Nota:** 
- El parámetro `-d` ejecuta en segundo plano (detached mode)
- Para ver los logs en tiempo real: `docker-compose logs -f`
- Para ver solo la app: `docker-compose logs -f dolibarr`

### Paso 4: Verifica que los contenedores estén corriendo

```powershell
docker-compose ps
```

Deberías ver algo como:
```
NAME               STATUS              PORTS
dolibarr-app      Up X seconds        0.0.0.0:8080->80/tcp
dolibarr-postgres Up X seconds        0.0.0.0:5432->5432/tcp
```

---

## 🌐 Acceso a la Aplicación

Una vez que los contenedores estén corriendo:

1. **Abre tu navegador** y ve a:
   ```
   http://localhost:8080
   ```

2. **Verás la pantalla de instalación de Dolibarr**
   - Sigue los pasos del instalador
   - Credenciales de BD: Usuario `dolibarr`, Contraseña `dolibarr`

3. **Acceso a PostgreSQL** (si necesitas conectarte directamente):
   - Host: `localhost:5432`
   - Usuario: `dolibarr`
   - Contraseña: `dolibarr`
   - BD: `dolibarr`

---

## 🐍 (Opcional) Configurar la API Python

Si quieres usar los scripts Python para interactuar con Dolibarr:

### 1. Instala las dependencias Python

```powershell
# Navega a la carpeta app
cd app

# Instala las dependencias del proyecto (si existe requirements.txt o pyproject.toml)
pip install -r requirements.txt
# O si usa pyproject.toml:
pip install -e .
```

### 2. Ejecuta el script de configuración

```powershell
python setup_dolibarr.py
```

Este script te pedirá:
- Host de BD: `localhost`
- Puerto de BD: `5432`
- Nombre de BD: `dolibarr`
- Usuario: `dolibarr`
- Contraseña: `dolibarr`

Esto creará un archivo `.env` con la configuración.

### 3. Inicia la API FastAPI

```powershell
python main.py
```

La API estará disponible en:
- Endpoint principal: `http://localhost:8000`
- Documentación Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## 📊 Monitoreo y Mantenimiento

### Ver logs en tiempo real
```powershell
# Todos los contenedores
docker-compose logs -f

# Solo la app Dolibarr
docker-compose logs -f dolibarr

# Solo PostgreSQL
docker-compose logs -f postgres
```

### Detener los contenedores (sin eliminarlos)
```powershell
docker-compose stop
```

### Iniciar nuevamente
```powershell
docker-compose start
```

### Detener y eliminar todo (limpia también volúmenes)
```powershell
docker-compose down

# Con volúmenes (-v elimina datos):
docker-compose down -v
```

### Reconstruir los contenedores (si hiciste cambios)
```powershell
docker-compose build --no-cache
docker-compose up -d
```

---

## ⚠️ Troubleshooting

### Los contenedores no inician
**Solución:**
```powershell
# Revisa los logs detalladamente
docker-compose logs

# Asegúrate que Docker esté corriendo
docker info

# Reinicia Docker Desktop (cierra y abre)
```

### Puerto ya en uso (8080 o 5432)
```powershell
# Ver qué está usando el puerto
netstat -ano | findstr :8080

# O cambia el puerto en docker-compose.yml:
# Reemplaza "8080:80" por "8081:80"
```

### BD no se conecta
- Espera 10-15 segundos antes de acceder (la BD tarda en iniciarse)
- Verifica credenciales en docker-compose.yml
- Revisa logs de postgres: `docker-compose logs postgres`

### Necesitas limpiar todo y empezar de cero
```powershell
docker-compose down -v
docker-compose up -d
```

---

## 📁 Estructura del Proyecto

```
/
├── docker-compose.yml       ← Configuración de contenedores
├── app/
│   ├── main.py              ← API FastAPI principal
│   ├── setup_dolibarr.py    ← Script de configuración
│   ├── core/
│   │   └── client_dolibarr.py ← Cliente para API Dolibarr
│   └── tests/               ← Scripts de prueba
├── htdocs/                  ← Archivos web de Dolibarr
└── conf.php                 ← Configuración de Dolibarr
```

---

## ✅ Verificación Rápida

Para confirmar que todo está funcionando:

```powershell
# 1. Verifica contenedores
docker-compose ps

# 2. Prueba la conectividad a Dolibarr
curl http://localhost:8080

# 3. Prueba la BD
docker-compose exec postgres psql -U dolibarr -d dolibarr -c "SELECT 1;"

# 4. Verifica la API (si la ejecutaste)
curl http://localhost:8000/health
```

---

## 🎯 Próximos Pasos

1. **Completar instalación**: Termina el wizard de instalación en http://localhost:8080
2. **Crear usuario admin**: Sigue las instrucciones del instalador
3. **Explorar la API**: Accede a http://localhost:8000/docs para ver todos los endpoints
4. **Configurar módulos**: En la sección de admin, habilita los módulos que necesites

---

## 📞 Comandos Útiles Rápidos

```powershell
# Iniciar todo
docker-compose up -d

# Ver estado
docker-compose ps

# Ver logs
docker-compose logs -f

# Detener
docker-compose stop

# Reiniciar
docker-compose restart

# Limpiar todo
docker-compose down -v

# Ejecutar comando en contenedor
docker-compose exec dolibarr bash
docker-compose exec postgres psql -U dolibarr -d dolibarr
```

---

¡Ya debería estar funcionando! 🎉 Si tienes problemas, revisa la sección de Troubleshooting o consulta los logs.

Perfecto. He creado una guía completa en GUIA_INICIO.md que te explica paso a paso cómo levantar el proyecto Dolibarr en Windows con Docker y PowerShell.

Resumen rápido:

Asegúrate que Docker Desktop esté instalado y corriendo
Abre PowerShell y ve a la carpeta del proyecto:
Levanta los contenedores:
Accede a http://localhost:8080 en tu navegador
La guía incluye:

✅ Requisitos previos
✅ Pasos detallados para Docker
✅ Cómo acceder a la aplicación
✅ Configuración opcional de Python/API
✅ Comandos para monitoreo y mantenimiento
✅ Sección de troubleshooting
✅ Comandos útiles rápidos
¿Necesitas ayuda con algo específico para poner en marcha el proyecto?