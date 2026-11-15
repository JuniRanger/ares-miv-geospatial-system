# Tarea: Implementar la descarga del raster de pendiente desde AWS S3 y su caché local

## 1. Contexto

Tengo un backend FastAPI para la planificación de rutas sobre Marte. Actualmente, la arquitectura funciona de la siguiente manera:

- `app/services/route_service.py` abre un GeoTIFF local utilizando Rasterio. La ruta del archivo se configura mediante `RUTA_PENDIENTE`.
- Exige un CRS equirectangular esférico con el radio de Marte, transforma las coordenadas geográficas a píxeles y lee únicamente una ventana delimitada por `max_km`.
- Lee los valores de pendiente expresados en grados.
- Los valores NoData, no finitos, las pendientes negativas y las celdas que superan `pendiente_max_deg` se consideran intransitables.
- El costo de desplazamiento se calcula mediante `1 + (pendiente / 10°)^2`.
- `app/algorithms/astar.py` implementa A* con 8 vecinos, distancia euclidiana, costos promedio entre celdas, prevención de cortes diagonales entre celdas intransitables y un límite de expansiones.
- `app/config.py` define actualmente `DATA_LOCAL_DIR` con el valor predeterminado `data/processed`, pero `RUTA_PENDIENTE` apunta por defecto a `map_mart/slope_5m.tif`.
- El endpoint de health actualmente verifica `data/processed/cost_stack.tif`, lo cual es inconsistente con el raster que realmente utiliza el planificador.
- No existe actualmente una integración con AWS S3.
- No existe un script de ingesta de datos.
- `requirements.txt` no incluye el SDK de AWS.

### Infraestructura AWS existente

El bucket de S3 ya está creado y contiene los datos necesarios:

- Bucket: `mars-terrain-data-2026`
- Región: `us-east-2`
- Objeto: `slope_5m.tif`
- Tamaño aproximado: 289 MB.

Ya existe un usuario IAM exclusivo para el backend, con permisos restringidos de lectura sobre el objeto mediante `s3:GetObject`.

El backend se desplegará en **Render**, no en infraestructura de AWS.

## 2. Objetivo

Implementar un servicio de almacenamiento que descargue el GeoTIFF de pendiente (`slope_5m.tif`) desde AWS S3 hacia el almacenamiento local de Render.

El archivo debe descargarse una sola vez por instancia cuando sea necesario, validarse y conservarse como caché local mientras la instancia permanezca activa.

El servicio de rutas debe continuar consumiendo el GeoTIFF local mediante Rasterio.

**No se debe modificar el algoritmo A* ni la lógica de planificación de rutas**, excepto los cambios estrictamente necesarios para unificar la configuración de la ruta del archivo y manejar correctamente la disponibilidad del dataset.

## 3. Restricciones técnicas

- No modificar el algoritmo A* ni sus límites actuales: cobertura, pendiente máxima, distancia o expansiones.
- No utilizar el archivo MOLA binario `data/raw/megt90n000fb.img`. No es el GeoTIFF de pendiente que necesita el planificador.
- No incluir credenciales en el código fuente, `.env.example`, repositorio ni logs.
- Utilizar la cadena estándar de credenciales de AWS mediante variables de entorno, perfiles o roles cuando estén disponibles.
- Utilizar `boto3` para la integración con S3.
- Permitir la configuración de un endpoint S3 compatible mediante `S3_ENDPOINT_URL`, que será opcional.
- Nunca descargar el raster en cada petición a `POST /routes/plan`.
- No cargar el GeoTIFF completo en RAM para descargarlo o procesarlo.
- Realizar la descarga mediante streaming.
- No utilizar el ETag como SHA-256. En objetos multipart, el ETag no representa necesariamente el hash del contenido.
- No requerir `s3:ListBucket`: el backend debe acceder directamente al objeto mediante el bucket y la key configurados. Los permisos deben limitarse a lo estrictamente necesario.
- No introducir dependencias de infraestructura específicas de AWS en el servicio de planificación de rutas.

## 4. Implementación

### 4.1. Dependencias y configuración

Agregar `boto3` a `requirements.txt`.

Actualizar `app/config.py` y `.env.example` con las siguientes variables:

```dotenv
# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-2

# S3
S3_BUCKET=mars-terrain-data-2026
S3_KEY=slope_5m.tif
S3_REGION=us-east-2
S3_ENDPOINT_URL=
S3_VERSION_ID=
S3_SHA256=

# Almacenamiento local
DATA_LOCAL_DIR=./data/processed
RUTA_PENDIENTE=./data/processed/slope_5m.tif
```

Consideraciones:

- `S3_BUCKET`, `S3_KEY` y `S3_REGION` deben ser configurables.
- `S3_ENDPOINT_URL` debe ser opcional.
- `S3_VERSION_ID` debe permitir fijar una versión específica del objeto cuando se utilice versionado en S3.
- `S3_SHA256` debe permitir configurar un hash SHA-256 esperado.
- `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` deben obtenerse exclusivamente del entorno o de la cadena estándar de credenciales de AWS.
- No agregar valores reales de credenciales a `.env.example`.
- Crear automáticamente el directorio local si no existe.
- El valor predeterminado de `RUTA_PENDIENTE` debe construirse a partir de `DATA_LOCAL_DIR`, apuntando a `slope_5m.tif`.

Para Render, las variables de almacenamiento deben configurarse así:

```dotenv
DATA_LOCAL_DIR=/tmp/mars-data
RUTA_PENDIENTE=/tmp/mars-data/slope_5m.tif
```

El directorio `/tmp/mars-data` será una caché temporal. S3 será la fuente persistente de los datos.

### 4.2. Servicio de descarga: `app/storage/s3_downloader.py`

Crear un módulo responsable de descargar, verificar, validar y publicar el GeoTIFF.

El flujo debe seguir este orden:

**1. Consultar metadatos del objeto**

Utilizar `head_object` para obtener:

- VersionId, si está disponible.
- ContentLength.
- ETag.
- Checksum, si está disponible.

La consulta debe realizarse directamente sobre el objeto configurado, sin listar el bucket.

**2. Comprobar la caché local**

Antes de descargar:

- Verificar si existe `RUTA_PENDIENTE`.
- Verificar si existe un manifiesto asociado.
- Comprobar que el raster local continúa siendo válido.
- Comparar la versión o ETag del objeto remoto con la información del manifiesto.

Si la copia local es válida y corresponde a la misma versión del objeto remoto, no volver a descargar.

Si no hay una copia local válida o el objeto cambió, iniciar una nueva descarga.

No confiar únicamente en la existencia del archivo. La validez debe verificarse.

**3. Descargar el objeto**

- Descargar mediante streaming a un archivo temporal.
- Utilizar el nombre `slope_5m.tif.part` o un nombre temporal único por proceso.
- Guardar el archivo temporal en el mismo directorio que el destino final para permitir un reemplazo atómico.
- No cargar el contenido completo del objeto en memoria.

**4. Verificar la descarga**

Comprobar:

- Que el tamaño descargado coincida con `ContentLength`.
- Que el archivo no esté vacío.
- Que el SHA-256 coincida con `S3_SHA256`, cuando esté configurado.

No utilizar el ETag como sustituto del SHA-256.

**5. Validar el GeoTIFF**

Abrir el archivo temporal con Rasterio y verificar:

- Que tenga exactamente una banda.
- Que las dimensiones sean mayores que cero.
- Que el CRS sea compatible con el sistema de coordenadas utilizado por `route_service.py`.
- Que la proyección y el radio de Marte coincidan con los requisitos existentes.
- Que la resolución corresponda a 5 metros por píxel, según la geotransformación y las unidades del CRS.
- Que la geotransformación sea válida.
- Que los metadatos NoData sean compatibles.
- Que el dtype sea compatible con las operaciones actuales del servicio.

**Importante:** no inventar valores esperados para CRS, radio, resolución, NoData o dtype. Inspeccionar el raster disponible y la lógica actual de validación de `route_service.py`.

Reutilizar la lógica de validación existente siempre que sea posible. No duplicar validaciones innecesariamente.

También inspeccionar si `slope_5m.tif.aux.xml` contiene metadatos indispensables para abrir y utilizar correctamente el GeoTIFF. No asumir que el archivo sidecar es prescindible sin verificarlo.

Si los criterios esperados no están definidos o no pueden verificarse, informar antes de introducir una nueva validación.

**6. Publicar el archivo**

Solamente cuando todas las verificaciones hayan terminado correctamente:

- Utilizar `os.replace()` para mover el archivo temporal al destino definitivo.
- Generar `slope_5m.manifest.json`.
- El manifiesto debe contener:
  - Bucket.
  - Key.
  - VersionId, cuando esté disponible.
  - ETag.
  - SHA-256 calculado localmente.
  - Tamaño del archivo.
  - Fecha de descarga.
  - Metadatos relevantes del raster.

No publicar un raster incompleto o inválido.

**7. Manejo de errores**

Ante cualquier fallo:

- Eliminar el archivo temporal.
- Conservar la última copia local válida.
- Registrar un error claro sin exponer credenciales ni información sensible.
- Devolver un resultado tipado que permita conocer el estado de la operación.
- No lanzar una excepción que impida iniciar FastAPI.

Si no existe una copia local válida, el dataset debe permanecer como no disponible.

### 4.3. Concurrencia y seguridad de archivos

Evitar que múltiples procesos o tareas intenten descargar y publicar simultáneamente el mismo raster.

Implementar un mecanismo de sincronización apropiado para evitar:

- Descargas duplicadas dentro de una misma instancia.
- Publicaciones simultáneas.
- Lecturas de archivos temporales incompletos.
- Eliminación accidental de una copia válida utilizada por otras solicitudes.

Utilizar nombres temporales únicos por proceso o un mecanismo de bloqueo adecuado.

El archivo definitivo solo debe reemplazarse después de completar todas las verificaciones.

No eliminar ni sobrescribir una copia válida antes de que la nueva versión esté completamente descargada y validada.

### 4.4. Script de mantenimiento: `scripts/fetch_route_raster.py`

Crear un comando CLI que reutilice exactamente el mismo servicio de descarga.

Debe permitir:

- Descargar el raster manualmente.
- Verificar la validez de la copia local.
- Comprobar si existe una nueva versión en S3.
- Forzar una descarga mediante `--force`.

El script debe:

- Utilizar la misma configuración que FastAPI.
- No duplicar la lógica de descarga o validación.
- Mostrar mensajes claros sobre el resultado.
- Devolver un código de salida distinto de cero cuando la operación falle.

Ejemplo de uso:

```bash
python scripts/fetch_route_raster.py
```

Para forzar una descarga:

```bash
python scripts/fetch_route_raster.py --force
```

### 4.5. Integración en `app/main.py` mediante lifespan

Integrar el servicio de descarga en el ciclo de vida de FastAPI.

**Comportamiento esperado:**

1. Al iniciar la aplicación, comprobar si existe una copia local válida.
2. Si existe, permitir que FastAPI utilice esa copia inmediatamente.
3. Consultar S3 y comprobar si existe una versión nueva.
4. Si hace falta descargar, iniciar la operación en segundo plano.
5. No bloquear el event loop.
6. Si S3 no está disponible, faltan credenciales o falla la validación, registrar el error y permitir que FastAPI continúe funcionando.
7. Si no existe una copia local válida, mantener el dataset como no disponible.
8. Cuando la descarga termine y el raster sea validado y publicado, actualizar el estado del dataset para permitir nuevas solicitudes.

Mientras el dataset no esté disponible:

- `/health` debe informar `degraded`.
- `POST /routes/plan` debe responder `503 DATASET_UNAVAILABLE`.

La descarga debe ejecutarse en un hilo o executor, evitando bloquear el event loop.

No hacer que el servidor espere obligatoriamente a que S3 termine la descarga para comenzar a aceptar solicitudes.

### 4.6. Health endpoint: `app/api/routes/health.py`

Corregir la inconsistencia actual.

El health endpoint debe comprobar exactamente el archivo utilizado por el planificador:

`RUTA_PENDIENTE`

No debe seguir verificando `cost_stack.tif`, ya que ese archivo no forma parte del flujo actual de planificación.

Estados:

- `ok`: existe un raster local válido y disponible.
- `degraded`: el raster no existe, está siendo descargado o no superó la validación.

Opcionalmente, exponer información no sensible del manifiesto, como la versión del objeto o la fecha de descarga.

No exponer credenciales, secretos ni información interna innecesaria.

### 4.7. Integración con `route_service.py`

El servicio de rutas debe continuar utilizando Rasterio y leyendo ventanas del archivo local.

Realizar únicamente los cambios estrictamente necesarios para:

- Unificar la ruta del raster con `RUTA_PENDIENTE`.
- Comprobar que el dataset está disponible antes de iniciar la planificación.
- Responder `503 DATASET_UNAVAILABLE` cuando no exista un raster válido.

No modificar:

- La función de costo.
- La interpretación de las pendientes.
- La conversión de coordenadas.
- La selección de ventanas.
- Los límites de distancia.
- La lógica de obstáculos.
- El algoritmo A*.

No descargar datos desde S3 durante una petición de planificación.

## 5. Pruebas

Agregar pruebas con `pytest`, utilizando `moto`, `botocore.stub.Stubber` o mocks adecuados para simular S3 sin depender de AWS real.

Cubrir los siguientes casos:

1. Descarga exitosa y publicación atómica.
2. Generación correcta del manifiesto.
3. Objeto inexistente en S3.
4. Credenciales faltantes.
5. Error de conexión con S3.
6. Checksum incorrecto: no debe reemplazar una copia local válida.
7. GeoTIFF incompatible: no debe reemplazar una copia local válida.
8. CRS incorrecto.
9. Radio de Marte incorrecto.
10. Número de bandas incorrecto.
11. Versión sin cambios: no debe volver a descargar.
12. Nueva versión: debe descargar y validar el nuevo archivo.
13. Arranque sin conexión a S3: FastAPI debe iniciar correctamente.
14. Sin raster local válido: health `degraded` y `POST /routes/plan` responde `503 DATASET_UNAVAILABLE`.
15. Archivo `.part` incompleto: nunca debe considerarse un dataset disponible.
16. Descargas concurrentes: no deben producir archivos corruptos ni publicaciones simultáneas.
17. Integración: con el raster válido presente, el resultado de una ruta debe ser idéntico al obtenido con una copia local del mismo GeoTIFF.

Las pruebas no deben requerir credenciales reales de AWS.

## 6. Criterios de aceptación

- [ ] El raster se descarga únicamente cuando falta, es inválido o cambió su versión.
- [ ] La descarga se realiza desde S3 mediante streaming.
- [ ] No se requiere `s3:ListBucket`.
- [ ] El archivo temporal incompleto nunca se considera un dataset disponible.
- [ ] Una descarga inválida no reemplaza una copia local válida.
- [ ] La publicación del archivo definitivo es atómica.
- [ ] El manifiesto permite identificar la versión de los datos descargados.
- [ ] La API inicia aunque S3 esté temporalmente fuera de servicio.
- [ ] Si no hay raster válido, health informa `degraded`.
- [ ] Si no hay raster válido, el planificador responde `503 DATASET_UNAVAILABLE`.
- [ ] Cuando existe un raster válido, las solicitudes llegan al A* existente.
- [ ] Se conservan todos los límites y reglas actuales del algoritmo.
- [ ] Health y route service verifican el mismo archivo.
- [ ] Las descargas concurrentes están controladas.
- [ ] No existen credenciales en el repositorio ni en los logs.
- [ ] Todas las pruebas pasan.

## 7. Forma de trabajo

Antes de modificar cualquier archivo:

1. Inspeccionar el repositorio y leer los archivos relevantes.
2. Revisar específicamente:
   - `app/config.py`
   - `app/main.py`
   - `app/services/route_service.py`
   - `app/algorithms/astar.py`
   - `app/api/routes/health.py`
   - `requirements.txt`
   - `.gitignore`
   - `.env.example`
   - La estructura actual de directorios.
3. Resumir brevemente cómo funciona actualmente el flujo de rutas.
4. Identificar inconsistencias entre el código existente y esta especificación.
5. Presentar un plan breve de implementación.

Si el repositorio contradice este documento, informar de la discrepancia antes de asumir cómo resolverla.

Después del diagnóstico, implementar los cambios de forma incremental.

Al terminar:

- Listar todos los archivos modificados.
- Listar todos los archivos creados.
- Explicar brevemente las decisiones técnicas relevantes.
- Indicar cómo configurar las variables de entorno.
- Indicar cómo ejecutar el script de descarga.
- Indicar cómo ejecutar las pruebas.
- Informar cualquier limitación o prueba que no haya podido completarse.

Realizar cambios mínimos, enfocados y coherentes con la arquitectura existente.

No refactorizar componentes fuera del alcance de esta tarea.

## 8. Fuera de alcance

No implementar todavía:

- Migración a `cost_stack.tif` multibanda.
- Procesamiento offline de DEM a pendiente.
- Pipeline de procesamiento de datos MOLA.
- Actualización automática periódica del raster.
- Estrategias complejas de rollback.
- Lectura directa del GeoTIFF desde S3 mediante HTTP Range Requests.
- Migración a CloudFront u otro servicio de distribución.
- Cambios en el algoritmo A*.

**Prioridad principal:** conseguir que el backend FastAPI descargue, valide y mantenga disponible el GeoTIFF de pendiente desde S3 en el almacenamiento local de Render, sin alterar el comportamiento actual del planificador de rutas.