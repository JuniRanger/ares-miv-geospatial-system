# Planificación de rutas peatonales

## Alcance

`POST /api/v1/routes/plan` calcula una ruta para una persona caminando con traje espacial sobre un GeoTIFF de pendiente. No es un modelo de rover ni una predicción validada de una EVA marciana. El raster se abre dentro de cada petición y no se carga en el arranque de FastAPI.

## Configuración

La variable `RUTA_PENDIENTE` apunta al GeoTIFF de pendiente, con una banda de valores en grados y celdas de 5 m. Su valor por defecto es `data/processed/slope_5m.tif`, derivado de `DATA_LOCAL_DIR`. Se puede cambiar en `.env`:

```dotenv
DATA_LOCAL_DIR=./data/processed
RUTA_PENDIENTE=./data/processed/slope_5m.tif
```

Al iniciar FastAPI, una tarea en segundo plano valida la caché local y consulta
el objeto configurado mediante `S3_BUCKET`, `S3_KEY` y `S3_REGION`. Si hace falta,
descarga el objeto en bloques, valida el GeoTIFF y lo publica de forma atómica.
El proceso de arranque no espera a S3: si el raster no está disponible todavía,
la API arranca y las rutas responden `503 DATASET_UNAVAILABLE`. Un raster local
válido se conserva si S3 falla. `python scripts/fetch_route_raster.py` ejecuta la
misma preparación manualmente; `--force` solicita descargar de nuevo.

No copies el DEM original de 1 m para esta ruta: el endpoint consume el raster
de pendiente de 5 m. En Render, el directorio local debe ser escribible y puede
ser efímero; el objeto de S3 debe permanecer como fuente persistente.

El archivo comprobado tiene resolución de 5 m y extensión rectangular de 32,98 × 57,44 km. Un círculo de 10 km de radio alrededor del centro del raster no tenía celdas NoData. `max_km` limita la distancia de una ruta; no configura un centro de sondeo fijo ni reemplaza la cobertura del raster.

## Constantes del modelo

Los valores se definen en `app/config.py` para que se puedan ajustar sin cambiar el algoritmo:

| Constante | Valor | Función |
|---|---:|---|
| `KM_MAX` | 10.0 km | Límite absoluto de ruta solicitado |
| `KM_DEFECTO` | 5.0 km | Límite por defecto para una petición |
| `TRAMO_MIN_KM` / `TRAMO_MAX_KM` | 1.0 / 1.5 km | Ventana para elegir una parada |
| `VEL_MAX_MS` / `VEL_DEFECTO_MS` | 1.0 / 0.7 m/s | Velocidades máxima y por defecto |
| `DESCANSO_MIN_DEFECTO` | 10 min | Descanso por parada |
| `PEND_MAX_DEFECTO` / `PEND_TOPE` | 12° / 20° | Límite por defecto y límite absoluto de pendiente |
| `PEND_REF` | 10° | Escala que pondera la pendiente en el costo de A* |
| `MAX_EXPANSIONES` | 500 000 | Límite de nodos antes de responder 504 |

## Petición

```http
POST /api/v1/routes/plan
Content-Type: application/json
```

```json
{
  "origin": { "latitude": -4.8149309421, "longitude": 137.3720378680 },
  "destination": { "latitude": -4.8221853022, "longitude": 137.3634338595 },
  "max_km": 5.0,
  "descanso_min": 10,
  "velocidad_ms": 0.7,
  "pendiente_max_deg": 12
}
```

`origin` y `destination` son obligatorios. Los demás campos son opcionales:

| Campo | Default | Límites |
|---|---:|---|
| `max_km` | 5.0 km | mayor que 0, máximo 10 km |
| `descanso_min` | 10 min | mayor que 0 |
| `velocidad_ms` | 0.7 m/s | mayor que 0, máximo 1.0 m/s |
| `pendiente_max_deg` | 12° | mayor que 0, máximo 20° |

Campos desconocidos, incluido el antiguo `descanso_km`, producen un `422 VALIDATION_ERROR`.

## Cálculo

1. El servicio abre el GeoTIFF solo al procesar la petición. Comprueba que tenga CRS equirectangular esférico y obtiene del CRS el radio, meridiano central y parámetros de origen.
2. Convierte lon/lat a coordenadas proyectadas usando esos parámetros. Revisa que ambos puntos estén dentro del raster y que su distancia directa no exceda `max_km`.
3. Lee una ventana local alrededor del origen, limitada por `max_km`. No carga todo el GeoTIFF. NoData, valores no finitos, pendientes negativas y celdas por encima de `pendiente_max_deg` son impasables.
4. A* busca con ocho vecinos y distancia euclidiana como heurística; no permite cortar una esquina pasando diagonalmente entre dos celdas impasables. La ponderación aumenta con la pendiente: `1 + (pendiente / PEND_REF)^2`, con `PEND_REF = 10°`. La búsqueda se interrumpe al superar `MAX_EXPANSIONES`.
5. Calcula la distancia de la ruta entre centros de celda. Si la ruta resultante excede `max_km`, devuelve error en vez de entregar una ruta inválida.
6. Recorre el camino acumulando distancia. Si quedan al menos 1,5 km, evalúa los puntos entre 1,0 y 1,5 km desde el inicio o la última parada y elige el de menor pendiente. En empate elige el más cercano a 1,0 km. El destino nunca se usa como parada y las paradas no modifican el camino.
7. Para cada paso calcula `v = velocidad_ms * max(0.2, 1 - pendiente_local / 20)`, donde `pendiente_local` es el promedio de las pendientes de las celdas del paso. El tiempo de descanso es `cantidad_de_paradas * descanso_min / 60`.

Las coordenadas de `puntos` y `parada` son centros de píxel convertidos a `[longitud, latitud]`. La respuesta contiene distancia, resolución, pendiente máxima, tramos, tiempos y `supuestos`.

## Respuesta y errores

En éxito se devuelve `200` con:

- `distancia_km`, `resolucion_m`, `pendiente_max_en_ruta_deg` y `puntos`.
- `tramos`: número, distancia, tiempo caminando y `parada`; la parada del último tramo es `null`.
- `tiempo_caminando_h`, `tiempo_descanso_h` y `tiempo_total_h`.
- `referencia_neutrones`: tasas térmica y epitérmica por cada celda AND de 5° × 5° atravesada, con fuente, fechas, Ls, resolución, dispersión y comparación descriptiva con celdas vecinas.
- `supuestos`: procedencia y límites científicos del modelo.

La referencia se obtiene de `data/raw/and_13_225_240.dat` (Mars Odyssey GRS / Neutron Spectrometer), promediado para Ls 225–240 entre el 13 de febrero y el 9 de marzo de 2026. Sus unidades son cuentas/s. **No son una dosis en mGy ni una predicción de exposición de una persona**, y no se usan como costo de A*. Una ruta de hasta 10 km normalmente queda en una única celda de 5°; por eso el dato no distingue riesgos entre puntos cercanos a 5 m. Las diferencias frente a celdas vecinas son descriptivas y deben leerse junto con las desviaciones reportadas.

Los errores usan `{ "code", "message", "details"? }`:

| HTTP | `code` | Causa |
|---:|---|---|
| 422 | `VALIDATION_ERROR` | Campos o límites de entrada inválidos |
| 422 | `POINT_OUTSIDE_MAP` | Inicio o destino fuera de la cobertura del GeoTIFF |
| 422 | `POINT_NOT_TRAVERSABLE` | Inicio o destino en NoData o sobre la pendiente máxima |
| 422 | `DIRECT_DISTANCE_EXCEEDED` | Distancia directa mayor que `max_km` |
| 422 | `NO_FEASIBLE_ROUTE` | No existe camino transitable |
| 422 | `ROUTE_DISTANCE_EXCEEDED` | El camino calculado supera `max_km` |
| 503 | `DATASET_UNAVAILABLE` | No se encuentra `RUTA_PENDIENTE` |
| 503 | `INVALID_DATASET` | El GeoTIFF no cumple el contrato del raster de pendiente |
| 504 | `SEARCH_LIMIT_EXCEEDED` | A* superó el límite de expansiones |

`GET /api/v1/routes/{route_id}` responde 404 porque el almacenamiento persistente/en memoria de rutas no está implementado.

## Supuestos y límites

- El modelo representa a una persona con traje, no un rover.
- 1.0 m/s (~3,5 km/h) se presenta como máximo nominal basado en caminata Apollo en la Luna; no es una velocidad validada en Marte.
- 0.7 m/s, diez minutos de descanso y la reducción por pendiente son supuestos del modelo.
- El tope de pendiente de 20° y el default de 12° no están validados; la referencia de pruebas NASA con traje (~11°) se usa solo como contexto.
- La pendiente es del DEM de 5 m y no equivale a la inclinación local bajo el traje.
- No hay medición de caminata con traje presurizado en gravedad marciana.

## Pruebas

Los tests generan GeoTIFFs sintéticos dentro de `tmp_path`, configuran `RUTA_PENDIENTE` para cada prueba y no requieren el raster real ni acceso a NASA:

```powershell
python -m pytest -q tests/test_ruta.py
python -m pytest -q
```
