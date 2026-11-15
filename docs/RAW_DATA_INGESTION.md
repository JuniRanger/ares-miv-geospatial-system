# Guía breve de `data/raw`

Inventario de los cuatro productos que hay actualmente en `data/raw`, sus campos
según las etiquetas PDS y una base para leerlos en un proceso de ingesta. Los
binarios son big-endian. Se verificó que cada tamaño coincide con las dimensiones
declaradas; esto no sustituye la validación científica ni la comprobación de
procedencia del archivo.

## Productos

| Producto | Contenido y estructura | Uso posible |
|---|---|---|
| [MOLA](../data/raw/megt90n000fb.img) | Topografía global de MGS/MOLA. Raster `5760 × 11520`, `SignedMSB2`, metros, 0,03125° por muestra. Metadatos: [XML](../data/raw/megt90n000fb.xml). | Elevación respecto al areoide declarado; no incluye banda de calidad que distinga las celdas observadas de las interpoladas. |
| [SGS](../data/raw/sgs_04_000_015_00.dat) | Mars Odyssey GRS: 72 filas, 131 356 bytes por fila, 54 campos auxiliares y un arreglo de espectro gamma. Etiqueta: [LBL](../data/raw/sgs_04_000_015_00.lbl); definiciones de campo: [XML](../data/raw/sgs_04_000_015_00.xml). | Espectros y telemetría; solo banda centrada en 87,5° de latitud, celdas de 5° y Ls 0–15. No es cobertura global. |
| [DND](../data/raw/dnd_20260101.dat) | Mars Odyssey Neutron Spectrometer: 4170 registros de 256 bytes. Etiquetas: [LBL](../data/raw/dnd_20260101.lbl), [FMT](../data/raw/DERIV_NEUTRON_DATA_COLS.FMT) y [XML](../data/raw/dnd_20260101.xml). | Serie temporal de conteos/tasas de neutrones durante el 1 ene. 2026, con posiciones asociadas a las mediciones. |
| [AND](../data/raw/and_13_225_240.dat) | Mars Odyssey Neutron Spectrometer: 2592 celdas de 5° × 5°, 44 bytes por registro. Etiqueta: [LBL](../data/raw/and_13_225_240.lbl); campos: [XML](../data/raw/and_13_225_240.xml). | Tasas promedio de neutrones para Ls 225–240; cubre una cuadrícula global gruesa, no elevación. |

### MOLA: raster topográfico

Cada píxel es topografía en metros, descrita como radio planetario menos radio del
areoide. La etiqueta declara valores entre −8206 y 21181 m. El muestreo es de
0,03125°; los metadatos también reportan 1,8522306687 km/píxel, valor que no debe
tratarse como una distancia uniforme en todas las latitudes. El sistema declarado
es planetocéntrico, longitud positiva al este, proyección equirectangular y marco
IAU2000_MARS; meridiano central 180°, paralelo estándar 0° y esquina superior
izquierda declarada en −10 668 848,652 m, 5 334 424,326 m. El areoide indicado es
GMM3. Usa esos metadatos para georreferenciar; no asignes un EPSG terrestre.

### SGS: 54 campos de tabla y espectro

La tabla tiene 54 campos (primeros 284 bytes de cada registro). Los campos de
telemetría son voltios y °C donde se indica; los conteos y relojes conservan las
unidades/semántica PDS. En el mismo registro, desde el byte 285, sigue
`GAMMA_SPECTRUM`: 16 384 valores `IEEE754MSBDouble` (131 072 bytes).

- Coordenadas y tiempo: `AREOCENTRIC_LATITUDE`, `AREOCENTRIC_LONGITUDE`,
  `UTC_START_TIME`, `UTC_STOP_TIME`, `SC_START_TIME`, `SC_STOP_TIME`,
  `CLOCK_TIME`, `RECORD_COUNT`, `BAD_CODE`.
- Conteos/espectro auxiliar: `LLD_SUM`, `ULD_SUM`, `L1_SUM`, `L2_SUM`, `L3_SUM`,
  `PHA_SUM`.
- Monitor de voltaje: `HVBS_MONITOR_MIN`, `HVBS_MONITOR_MAX`,
  `HVBS_MONITOR_MEAN`, `HVBS_MONITOR_STD`.
- Temperaturas, cada familia con sufijos `_MIN`, `_MAX`, `_MEAN`, `_STD`:
  `IS_TEMP_A`, `IS_TEMP_B`, `OS_TEMP_A`, `OS_TEMP_B`, `B170K_TEMP`, `GPA_TEMP`,
  `GAMMA_VREF_TEMP` (°C según el XML).
- Ganancia/canales: `APPS_GAIN_DHK_DEFAULT`, `APPS_GAIN_DHK_MIN`,
  `APPS_GAIN_DHK_MAX`, `GAIN_MEAN`, `OFFSET_MEAN`, `FIRST_CHANNEL_MAX`,
  `LAST_CHANNEL_MIN`.
- Arreglo: `GAMMA_SPECTRUM`, espectro gamma corregido acumulado por celda y
  intervalo solar.

### DND: los 53 campos por registro

- Tiempo y órbita: `SC_RECV_TIME`, `CEB_TIME`, `UTC`, `GRS_PIXEL_NUMBER`,
  `GRS_ORBIT_NUMBER`, `ODY_ORBIT_NUMBER`.
- Punto/posición: `AREOCENTRIC_LATITUDE`, `AREOCENTRIC_EAST_LONGITUDE`, `ALTITUDE`,
  `SCPOS_INERT`, `SCVEL_INERT`, `MARSPOS_INSTR`, `MARSVEL_INSTR`. Los cuatro
  últimos son vectores XYZ de tres componentes.
- Tiempo local y estado del instrumento: `DAY_INDEX`, `LOCAL_HOUR`,
  `LOCAL_MINUTE`, `PIXEL_DURATION`, `POWER_SUPPLY`, `SWAP_FLAG`, `POWER_LEVEL`,
  `DIRECTION`, `LIVETIME`, `DEADTIME_PERCENT`, `OVERLOAD_RATE`, `HVPS_MNTR_2`.
- Coordenadas asociadas a canales: `LAT_1`, `LON_1`, `LAT_4_5`, `LON_4_5`.
- Tasas y errores: `CAT1_PRISM1_PEAK_AREA`, `CAT1_PRISM1_ERROR`,
  `CAT1_PRISM2_PEAK_AREA`, `CAT1_PRISM2_ERROR`, `CAT1_PRISM3_PEAK_AREA`,
  `CAT1_PRISM3_ERROR`, `CAT1_PRISM4_PEAK_AREA`, `CAT1_PRISM4_ERROR`,
  `CAT2_PRISM1_FAST_SUM`, `CAT2_PRISM1_ERROR`, `THERMAL_COUNT_RATE`,
  `THERMAL_ERROR`.
- Correcciones: `CAT1_PRISM1_NORM_SLOPE`, `CAT1_PRISM1_NORM_OFFSET`,
  `CAT1_PRISM2_NORM_SLOPE`, `CAT1_PRISM2_NORM_OFFSET`,
  `CAT1_PRISM3_NORM_SLOPE`, `CAT1_PRISM3_NORM_OFFSET`,
  `CAT1_PRISM4_NORM_SLOPE`, `CAT1_PRISM4_NORM_OFFSET`,
  `CAT2_PRISM1_NORM_SLOPE`, `CAT2_PRISM1_NORM_OFFSET`, `CF_ATM_EPI`,
  `CF_ATM_FAST`.

Los valores de latitud/longitud son coordenadas areocéntricas en Marte fijo;
longitud aumenta hacia el este. `ALTITUDE` está en km. Las tasas/errores tienen
las descripciones y unidades detalladas en el FMT/XML; no son elevación ni
inercia térmica. El FMT marca `0` como inválido para los tres contadores de píxel
y órbita. También describe vectores instrumentales en cero cuando falta actitud:
no interpretar esos ceros como una posición física válida.

### AND: los 11 campos por celda

Todos están declarados como `IEEE754MSBSingle` (float32 big-endian):

| Campo | Significado |
|---|---|
| `AREOCENTRIC_LATITUDE`, `AREOCENTRIC_EAST_LONGITUDE` | Centro de celda, grados; este positivo. |
| `CTHERM`, `STHERM`, `NTHERM` | Tasa térmica promedio, desviación estándar (conteos/s) y número de intervalos. |
| `CEPI`, `SEPI`, `NEPI` | Tasa epitérmica promedio, desviación estándar (conteos/s) y número de intervalos. |
| `CFAST`, `SFAST`, `NFAST` | Tasa rápida, desviación estándar (conteos/s) y número de intervalos. |

**Revisar antes de usar:** el XML describe `CFAST` como tasa térmica, aunque el
nombre del campo y `SFAST` indican neutrones rápidos. Confirmar esta discrepancia
con la fuente del producto; no corregirla silenciosamente.

## Lectura para la ingesta

Mantén los originales sin cambios en `data/raw/`. La extracción siguiente es
solo lectura y usa NumPy, ya incluido en el proyecto:

```python
from pathlib import Path
import numpy as np

# Raster MOLA: usar lectura por ventanas/memmap; no cargar/copiar todo en memoria.
mola = np.memmap(
    "data/raw/megt90n000fb.img",
    dtype=">i2", mode="r", shape=(5760, 11520),
)

# AND: 11 valores float32 big-endian por fila; tamaño esperado: 2592 × 44.
and_dtype = np.dtype([
    ("AREOCENTRIC_LATITUDE", ">f4"), ("AREOCENTRIC_EAST_LONGITUDE", ">f4"),
    ("CTHERM", ">f4"), ("NTHERM", ">f4"), ("STHERM", ">f4"),
    ("CEPI", ">f4"), ("NEPI", ">f4"), ("SEPI", ">f4"),
    ("CFAST", ">f4"), ("NFAST", ">f4"), ("SFAST", ">f4"),
])
and_rows = np.fromfile("data/raw/and_13_225_240.dat", dtype=and_dtype)
assert len(and_rows) == 2592
```

Para DND, genera el `numpy.dtype` con los 53 campos desde el FMT: convierta
`START_BYTE` de base 1 a offset base 0; use `>u8`, `>u4`, `>u2`, `>u1`, `>f4`
según tipo y tamaño; `UTC` es 23 bytes ASCII; los cuatro vectores son `>f4` con
forma `(3,)`. El `itemsize` del registro debe ser 256. Ejemplo de lectura puntual:

```python
import struct

with open("data/raw/dnd_20260101.dat", "rb") as stream:
    record = stream.read(256)
utc = record[16:39].decode("ascii").strip()  # START_BYTE 17, longitud 23
latitude = struct.unpack_from(">f", record, 51)[0]  # START_BYTE 52
spacecraft_xyz = np.frombuffer(record, dtype=">f4", count=3, offset=63)
```

Para SGS, parsea las definiciones PDS4 del XML (los 54 campos indican tipo,
longitud y ubicación) y el grupo del espectro. Por fila, el espectro empieza en
offset 284 y tiene 16 384 `>f8`:

```python
with open("data/raw/sgs_04_000_015_00.dat", "rb") as stream:
    record = stream.read(131356)
spectrum = np.frombuffer(record, dtype=">f8", count=16384, offset=284)
```

El XML de MOLA empieza con una frase de presentación ajena al XML; para parsearlo
sin alterar el original, omite esa primera línea en memoria antes de pasarlo a
`xml.etree.ElementTree`. Los `.FMT` de SGS y AND no están en la carpeta, aunque
sus XML contienen las definiciones de campos.

## Validaciones antes de cargar a la aplicación

1. Comprobar tamaños: MOLA `132710400` bytes; SGS `72 × 131356`; DND
   `4170 × 256`; AND `2592 × 44`.
2. Guardar producto/versión, fechas, instrumento, unidades, resolución/cobertura
   y sistema de coordenadas desde las etiquetas, no desde supuestos.
3. Mantener campos originales junto con cualquier nombre normalizado y conservar
   valores inválidos/nulos según las reglas PDS.
4. No asignar un SRID terrestre. MOLA usa planetocéntricas y longitud este;
   los productos GRS describen posiciones areocéntricas. Verifica convención y
   orden al transformarlos al contrato de API.
5. MOLA puede alimentar elevación tras validar georreferenciación. SGS/DND/AND
   son mediciones espectrales/neutrónicas: no las conviertas directamente en
   pendiente, rugosidad, inercia térmica o riesgo de ruta sin una metodología
   científica validada.
