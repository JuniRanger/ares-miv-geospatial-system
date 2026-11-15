# Implementación: obtener el raster de Marte desde S3

## Resumen ejecutivo

El backend descarga y valida el GeoTIFF de pendiente configurado en S3 hacia una
caché local; el servicio de rutas lo lee con Rasterio. Para que el A* actual
funcione sin cambios de algoritmo, el objeto debe ser el raster de pendiente de
5 m (`slope_5m.tif`), no un archivo suelto de coordenadas ni el MOLA binario
original. Un GeoTIFF ya guarda el vínculo entre píxeles y coordenadas en su
geotransformación y CRS.

La configuración predeterminada usa el bucket, clave y región especificados para
el proyecto. La sesión no ha accedido al objeto real de S3, por lo que su
disponibilidad, permisos y metadatos científicos siguen sin verificarse.

## Estado actual del repositorio

- [`app/services/route_service.py`](../app/services/route_service.py) abre el
  GeoTIFF local indicado por `RUTA_PENDIENTE`. Exige CRS equirectangular esférico
  con radio de Marte, transforma las coordenadas solicitadas a píxeles y lee solo
  una ventana limitada por `max_km`. No descarga de S3.
- El servicio obtiene la pendiente en grados. NoData, valores no finitos,
  pendientes negativas y celdas que superan `pendiente_max_deg` son intransitables.
  El costo es `1 + (pendiente / 10°)²`.
- [`app/algorithms/astar.py`](../app/algorithms/astar.py) busca con ocho vecinos,
  distancia euclidiana y costos promedio entre celdas; evita cortar esquinas entre
  celdas impasables y limita expansiones.
- [`app/config.py`](../app/config.py) define `RUTA_PENDIENTE` desde
  `DATA_LOCAL_DIR`; health y el servicio de rutas comprueban ese mismo GeoTIFF.
- [`app/storage/s3_downloader.py`](../app/storage/s3_downloader.py) descarga en
  bloques, verifica tamaño y SHA-256 cuando está configurado, valida el GeoTIFF,
  escribe un manifiesto y publica el archivo mediante reemplazo atómico. Un lock
  de archivo serializa las actualizaciones entre procesos.
- [`app/main.py`](../app/main.py) lanza la preparación como tarea en segundo plano
  para no bloquear el inicio. Si S3 falla, conserva una caché local válida.
- [`scripts/fetch_route_raster.py`](../scripts/fetch_route_raster.py) permite
  preparar la caché manualmente; `--force` solicita una descarga nueva.
- `requirements.txt` incluye `boto3`. No hay raster local en el repositorio y no
  se ha confirmado el acceso al objeto S3 configurado.
- La documentación plantea un `cost_stack.tif` en almacenamiento estático; el
  lector actual todavía consume un raster local de una sola banda de pendiente.

## Flujo implementado

```text
S3: slope_5m.tif
        │ consulta y descarga en segundo plano al iniciar / actualizar
        ▼
DATA_LOCAL_DIR/slope_5m.tif  + manifiesto de procedencia
        │ validación con Rasterio antes de publicar
        ▼
GET /api/v1/health: dataset disponible o degradado
        │ POST /routes/plan
        ▼
ventana local de pendiente → máscara/costos → A* → ruta GeoJSON
```

### 1. Fijar el contrato del objeto

Para la primera versión, publicar en S3 un **GeoTIFF de una banda** con pendiente
en grados, resolución esperada de 5 m y cobertura que incluya el área de estudio.
Debe declarar geotransformación, nodata y CRS equirectangular compatible con lo
que actualmente espera `route_service.py`, incluido el radio esférico de Marte.
Guardar la procedencia (producto fuente, versión, procesamiento, unidades y
coordenadas) en metadatos/manifest acompañantes.

El MOLA disponible en `data/raw/megt90n000fb.img` es un raster binario global de
topografía, no un GeoTIFF de pendiente de 5 m: primero necesita procesamiento y
georreferenciación. No debe apuntarse el servicio actual directamente a ese `.img`.
Si el objeto en S3 es un DEM y no la pendiente ya preparada, hace falta una etapa
offline de DEM → pendiente → GeoTIFF antes de publicarlo.

### 2. Configurar acceso sin credenciales en el código

La configuración usa estas variables de entorno:

```dotenv
S3_BUCKET=
S3_KEY=
S3_REGION=
S3_VERSION_ID=
S3_SHA256=
DATA_LOCAL_DIR=./data/processed
RUTA_PENDIENTE=./data/processed/slope_5m.tif
```

Usar rol de instancia/tarea o la cadena estándar de credenciales de AWS. No guardar
llaves en `.env.example`, en el repositorio ni en logs. Si el almacenamiento es
S3-compatible, permitir configurar su endpoint. Para un objeto privado la opción
directa es añadir `boto3`; un URL prefirmado puede evitar esa dependencia, pero
expira y debe tratarse como secreto.

### 3. Descargar y publicar localmente de forma segura

El descargador reutilizable se llama desde el lifespan de FastAPI o desde el
comando de mantenimiento:

1. Consultar el objeto (versión, tamaño y checksum si el proveedor lo entrega).
2. Si la versión ya está validada localmente, conservar la copia y no bajarla otra
   vez.
3. Descargar en streaming a `slope_5m.tif.part`; no leer el GeoTIFF completo en RAM.
4. Verificar tamaño y SHA-256 cuando esté configurado.
5. Abrir el temporal con Rasterio y validar: una banda, dimensiones no vacías,
   CRS/proyección/radio requeridos, transformación, nodata y tipo de dato esperados.
6. Solo después de validar, hacer `os.replace()` al destino final y escribir un
   manifiesto local con clave, versión/ETag, checksum, fecha de descarga y metadatos
   del raster. Un fallo no debe reemplazar la copia válida anterior.

No usar ETag como SHA-256: en objetos multipart no necesariamente es un hash del
contenido.

### 4. Integración con FastAPI y A*

- Descargar una vez durante el arranque, nunca en cada llamada de `POST /routes/plan`.
- Si S3 no está disponible o faltan credenciales, registrar el error y permitir que
  FastAPI arranque. Mantener el estado del dataset como no disponible; health queda
  degradado y la planificación conserva su respuesta `503 DATASET_UNAVAILABLE`.
- El servicio seguirá abriendo el archivo local y leyendo su ventana; no hace falta
  cargar el raster completo a memoria. Publicar el archivo mediante reemplazo atómico
  evita que una petición lea una descarga parcial.
- `RUTA_PENDIENTE` es el raster que health valida y el que consume el planificador;
  su default se deriva de `DATA_LOCAL_DIR`. No se valida `cost_stack.tif` mientras
  el servicio consuma el raster de pendiente de una banda.
- Más adelante, al migrar a `cost_stack.tif`, definir explícitamente las bandas y
  adaptar el lector. Renombrar el GeoTIFF de una banda no lo convierte en un cost
  stack.

## Archivos de la implementación

- `app/storage/s3_downloader.py`: descarga, comprobación de hash y reemplazo atómico.
- `scripts/fetch_route_raster.py`: descarga manual/reproducible para desarrollo,
  despliegue o actualización de datos.
- `app/config.py` y `.env.example`: configuración sin secretos.
- `app/main.py`: invocar la comprobación en lifespan sin impedir el arranque si el
  objeto no está disponible.
- `app/api/routes/health.py`: comprobar el mismo archivo que usa el planificador.
- Pruebas: mock de S3 para éxito, objeto inexistente, credenciales faltantes,
  checksum incorrecto, GeoTIFF incompatible y arranque sin red.

## Validación realizada y pendiente

Las pruebas mockeadas verifican descarga/validación, reutilización de caché por
manifiesto, preservación de una copia local válida si falla una descarga, inicio
de FastAPI sin raster remoto y el flujo de rutas existente. No se ha descargado ni
inspeccionado el objeto real de S3, así que todavía no se pueden afirmar sus
metadatos, integridad o accesibilidad en Render.

## Decisiones pendientes

- Confirmar que el objeto configurado existe y que el principal de Render tiene
  permiso de lectura.
- Confirmar que el objeto es `slope_5m.tif` y no el futuro `cost_stack.tif` o un
  DEM que requiera procesamiento offline.
- Versión/checksum esperado y política de actualización/rollback.
- Confirmar que el CRS y el radio del GeoTIFF en S3 cumplen exactamente los
  requisitos actuales del planificador.

