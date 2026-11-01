# Explicación larga: MongoDB vs PostgreSQL JSONB bajo contención de recursos

> Fuente: playbook "Medición de métricas en bases documentales" (IT2iD, Bases de Datos en la Nube, 2026), diapositivas de la sesión y apuntes de clase.
> Este documento explica el experimento completo. Lo que no está en el playbook se marca como **[supuesto]** o se lista en "Ambigüedades detectadas".

> **Nota de aplicación (importante).** El playbook describe el experimento con un dataset genérico de órdenes de e-commerce (`orders`, `items`, `payment`). Este documento es la **guía general** del experimento. El experimento real se aplica sobre el proyecto **Lethics** (plataforma de cursos sobre ética y leyes del desarrollo de software), con la colección `intentos` como equivalente de `orders`.
> Todo lo que aquí se dice sobre motores, perfiles, concurrencias, ciclo, KPIs, CSV y entregables **aplica sin cambios**. Solo cambia el contenido del dataset y de las queries: léanse `orders`, `items`, `price` y `payment.final_total` como sus campos equivalentes de Lethics (ver `03_requisitos_RF_RNF.md`, Anexo A).
> Las ambigüedades de la sección 8 ya tienen decisión tomada en `05_decisiones_y_supuestos.md`.

---

## 1. Objetivo y preguntas M1, M2, M3

**Objetivo.** Medir latencia, rendimiento (throughput) y huella de recursos al ejecutar agregaciones JSON anidadas sobre dos motores, con límites estrictos de CPU y memoria impuestos con Docker (cgroups v2):

- **MongoDB**: motor documental nativo (almacena BSON).
- **PostgreSQL**: motor relacional con una tabla que guarda documentos en una columna `JSONB`.

No es "probar si arranca": cada corrida debe producir **métricas numéricas** en un CSV homogéneo que luego alimenta un estudio y resiste las preguntas de un revisor.

| ID | Pregunta | Qué hay que mostrar con datos |
|----|----------|-------------------------------|
| **M1** | ¿Cómo cambian la latencia P95 y P99 de las agregaciones sobre documentos anidados cuando se limita de forma estricta CPU y memoria? | Latencias P95/P99 por perfil (A → B → C), por motor, query y concurrencia. |
| **M2** | ¿Qué motor usa de forma más eficiente los buffers de ordenamiento y agrupamiento antes de volcar a disco temporal (spill) o fallar por falta de memoria (OOM)? | En qué perfil/concurrencia aparece spill u OOM en cada motor, y qué pasa con el throughput cuando hay spill. |
| **M3** | ¿Cuál es la huella de CPU y memoria por cada 1 000 documentos procesados en el motor documental frente al motor con JSONB? | CPU consumida y RSS normalizados por cada 1 000 documentos. |

Para el equipo, estas preguntas guían qué celdas priorizar. Para el estudio, son las preguntas que un revisor pedirá justificar.

---

## 2. BSON vs JSONB y por qué importa

Es la comparativa principal del experimento (la historia que hay que contar en el reporte).

### BSON (MongoDB)
- Formato **binario** de MongoDB. Guarda cada documento con prefijos de longitud y tipos explícitos (fecha, entero, decimal, ObjectId, etc.).
- El motor de almacenamiento es **WiredTiger**. Los documentos viven en colecciones y se leen/escriben como unidades completas.
- Las agregaciones (`$unwind`, `$match`, `$group`, `$sort`) se ejecutan con el pipeline de agregación del propio motor, que ya "entiende" la estructura anidada.

### JSONB (PostgreSQL)
- Formato **binario descompuesto** de JSON dentro de una columna. Permite indexar y consultar sin reparsear texto.
- Los valores grandes se guardan comprimidos fuera de línea mediante **TOAST** **[supuesto: aplica cuando el documento supera ~2 KB, lo cual es probable con ítems anidados; confirmar con el tamaño real de los registros]**.
- Para extraer un campo hay que navegar el JSONB con operadores (`->`, `->>`) y **castear** el texto al tipo necesario (`::numeric`, `::timestamptz`). Cada fila ejecuta ese trabajo, lo cual cuesta CPU.
- Las agregaciones se expresan en SQL con `jsonb_array_elements` (equivalente al `$unwind`), `GROUP BY`, `ORDER BY`, etc.

### Por qué importa aquí
Ambos almacenan "JSON binario", pero el costo de **extraer, castear, desanidar, ordenar y agrupar** campos anidados cambia según el motor. Con CPU y RAM limitadas, esas diferencias se vuelven visibles en P95/P99, throttling, RSS y spill. La hipótesis a contrastar con datos: *¿el motor documental paga menos por operar sobre estructuras anidadas que el relacional con JSONB, y cómo cambia eso bajo contención?* Esto es una hipótesis de trabajo, no un resultado.

---

## 3. CPU, RAM y swap en cgroups v2

El experimento limita recursos del contenedor con **Docker + cgroups v2**.

### CPU: CFS throttling
- Con un límite de CPU (por ejemplo 1,0 CPUs), el planificador CFS le da al contenedor una cuota de tiempo por periodo. Cuando el contenedor la agota, **se detiene hasta el siguiente periodo**: eso es el *throttling*.
- Se observa con la métrica `container_cpu_cfs_throttled_seconds_total` (cAdvisor). A más throttling, más latencia de cola (P95/P99) y menos QPS.
- **Q1** (unwind + group) está pensada para **saturar CPU**: genera muchas filas intermedias y hace cálculos (`qty * price`, sumas, promedios) por cada una.

### RAM: buffers de ordenamiento y agrupamiento
- Las operaciones que **ordenan o agrupan** necesitan memoria de trabajo. Si no cabe, el motor tiene dos opciones: **volcar a disco temporal (spill)** o **fallar**. Si el contenedor excede su límite de memoria, el kernel puede matarlo (**OOM kill**).
- **Q2** (sort + Top-K sobre `payment.final_total`, sin índice en ese campo) está pensada para **estresar la RAM** (apunte del profe: la RAM se estresa cuando ordenamos y seleccionamos topes).
- Variantes de Q2 para controlar el comportamiento:
  - MongoDB: `allowDiskUse: false` (falla si no cabe) / `allowDiskUse: true` (puede volcar a disco).
  - PostgreSQL: `work_mem = '4MB'` / `work_mem = '64MB'` (con 4 MB es más probable el spill a archivos temporales).
- Métrica de memoria: `container_memory_rss_bytes` (RSS del contenedor).

### Swap
- El playbook fija `mem_swappiness = 0` en los tres perfiles. La intención es que el contenedor **no use disco como si fuera RAM** (swap), de modo que la presión de memoria aparezca como spill/OOM y no quede escondida por el swap.
- Pregunta de apunte: *¿cuándo se usa el disco como RAM?* Respuesta corta: cuando hay swap habilitado y presión de memoria; aquí se evita a propósito.
- **Nota técnica:** en cgroups v2 el control de swap del contenedor se hace normalmente con `memory.swap.max` (en Docker, `memswap_limit` igual a `mem_limit` equivale a "sin swap"). El parámetro `mem_swappiness` puede no tener efecto o dar error en cgroups v2. Ver "Ambigüedades detectadas".

---

## 4. Perfiles, concurrencias, ciclo de vida y matriz

### Perfiles de recursos (3)

| ID | Nombre | CPUs | Memoria | mem_swappiness |
|----|--------|------|---------|----------------|
| `PROFILE_A_BASELINE` | Sin contención (baseline) | 4,0 | 4096 m | 0 |
| `PROFILE_B_MEDIUM` | Contención media | 2,0 | 2048 m | 0 |
| `PROFILE_C_SEVERE` | Contención severa (throttling activo) | 1,0 | 1024 m | 0 |

Siempre se anota: `profile`, **límites Docker reales** (verificar con `docker inspect`), versión del motor, y si hubo spill/OOM. Sin eso la celda no sirve para el estudio.

### Concurrencia
**1, 10 y 50 clientes** simultáneos. Pregunta de análisis del apunte: *si limito la CPU, ¿las consultas se vuelven más lentas y cuánto?* Se responde comparando perfiles con la misma concurrencia. Se usan **entre 10 y 50 workers** para lanzar las consultas lo más simultáneamente posible.

### Dataset
- **500 000 registros** en JSON, **3 niveles de anidamiento**, ~3 ítems por registro.
- Atributos: `order_id` (UUID), `timestamp` (ISO-8601), `customer` (id, tier, segment, geo[country, state, city, zip, coordinates]), `items[]` (sku, category, brand, qty, price, tax_pct, discounts), `payment` (method, status, transaction_id, gateway_latency_ms, totals), `metadata` (channel, user_agent, session_id, flags).
- Se genera con un script Python (`synthetic_data_generator.py`).

### Modelo e indexación
- **MongoDB**: colección `orders`, sin sharding, WiredTiger, versión *latest-stable*. Índice simple en `timestamp` y `order_id`.
- **PostgreSQL**: tabla `orders (id UUID PRIMARY KEY, data JSONB)`, versión *latest-stable*. PK en `id` y B-Tree sobre el `timestamp` extraído del JSONB.
- Apunte del profe: la indexación se hace sobre el **nivel más alto**; indexar el nivel más bajo sería "muy fácil". Además, Q2 se ejecuta **sin índice previo sobre el total** (`payment.final_total`).

### Ciclo de vida de cada medición
1. **Flush de caché**: `sync; echo 3 > /proc/sys/vm/drop_caches` (no es automático, hay que hacerlo en cada ciclo; se ejecuta en el host Linux con privilegios).
2. **Warmup**: 60 s.
3. **Medición**: 300 s.
4. **Cooldown**: 60 s.

### Matriz
- 2 motores × 3 perfiles × 2 queries × 3 concurrencias = **36 celdas**, cada una con **3 repeticiones** → 108 repeticiones base.
- Cada repetición dura ~7 min (60 + 300 + 60 s), sin contar el flush ni la preparación: ~12,6 h solo la matriz base.
- Si las **variantes de Q2** (2 por motor) se ejecutan como celdas adicionales, la matriz crece a 54 celdas / 162 repeticiones (~18,9 h). El playbook dice "reportar ambas variantes", pero no aclara si cuentan dentro de las 36 celdas. Ver ambigüedades.
- Recomendación del profe: primero una **celda piloto** (1 motor × 1 query × 1 concurrencia) y validar el CSV antes de lanzar la matriz completa.

---

## 5. Telemetría y KPIs

### Stack de telemetría
- **cAdvisor** (:8080): métricas del contenedor (cgroups v2).
- **Node Exporter** (:9100): métricas del host (I/O, disco, swap).
- **Prometheus** (:9090): `scrape_interval: 1s`.

### KPIs del playbook

| KPI | Unidad | Tipo | Qué significa |
|-----|--------|------|---------------|
| `throughput_qps` | queries/s | Performance | Consultas completadas por segundo durante la ventana de medición. |
| `latency_p50_ms` | ms | Performance | Mediana: la mitad de las consultas tarda menos que esto. |
| `latency_p95_ms` | ms | Performance | El 95 % tarda menos que esto; muestra la cola de latencia. |
| `latency_p99_ms` | ms | Performance | El 99 % tarda menos; sensible a throttling y contención. |
| `container_cpu_cfs_throttled_seconds_total` | s | OS / Contención | Segundos que el contenedor estuvo detenido por agotar su cuota de CPU. |
| `container_memory_rss_bytes` | bytes | OS / Memoria | Memoria residente real del contenedor (se usa el máximo en la corrida). |
| `disk_spill_detected` | boolean | Motor / Interno | Si el motor volcó datos temporales a disco por falta de memoria de trabajo. |
| `oom_killed` | boolean | Estabilidad | Si el kernel mató el contenedor por superar su límite de memoria. |

> Dato del profe: para la entrega no es obligatorio saber qué significan las métricas, pero el equipo quiere entenderlas. Las **métricas adicionales no son una condición de diseño**: se pueden agregar como complemento, nunca en lugar de las obligatorias.

### Esquema del CSV (inmutable)

```
timestamp_epoch, engine, profile, query_id, concurrency, run_number,
throughput_qps, latency_p50_ms, latency_p95_ms, latency_p99_ms,
cpu_throttled_seconds, max_rss_mb, disk_spill, status
```

| Columna | Significado |
|---------|-------------|
| `timestamp_epoch` | Momento de la corrida (segundos desde epoch). |
| `engine` | `MongoDB` o `PostgreSQL`. |
| `profile` | `PROFILE_A_BASELINE`, `PROFILE_B_MEDIUM` o `PROFILE_C_SEVERE`. |
| `query_id` | `Q1` o `Q2` (y, si aplica, la variante; ver ambigüedades). |
| `concurrency` | 1, 10 o 50. |
| `run_number` | Repetición 1, 2 o 3. |
| `throughput_qps` | QPS en la ventana de medición. |
| `latency_p50_ms` / `p95` / `p99` | Percentiles de latencia en ms. |
| `cpu_throttled_seconds` | Throttling acumulado durante la corrida. |
| `max_rss_mb` | Pico de RSS en MB. |
| `disk_spill` | Si hubo volcado a disco. |
| `status` | `ok`, `spill`, `oom` o `error`. |

**No se inventan ni renombran columnas**: el estudio posterior concatena todos los CSV de todos los equipos.

---

## 6. Entregables exigidos

### Código (repositorio)
- `docker-compose.yml` con perfiles de recursos parametrizados.
- `synthetic_data_generator.py` (dataset de 500k).
- `benchmark_runner` (k6 o Python multiproceso).
- `queries/` (agregaciones MongoDB y SQL PostgreSQL).
- `run_benchmarks.sh` (automatiza la matriz).

Todo debe correr en **Docker sobre Linux**.

### Evidencia
- CSV con el esquema fijo.
- Capturas o logs de spill/OOM.
- Reporte de métricas con las **7 secciones**:
  1. Especificaciones del host y del entorno Docker.
  2. Método de medición y verificación del baseline.
  3. Resultados consolidados (throughput, P95/P99, tiempo de throttling).
  4. Análisis gráfico (P99 vs concurrencia, throttling vs QPS, curva RSS).
  5. Planes de ejecución (`explain executionStats` vs `EXPLAIN ANALYZE BUFFERS`).
  6. Interpretación: límites de memoria, volcado a disco y throttling de cgroups.
  7. Recomendaciones técnicas para despliegues documentales en la nube.
- Tablas y gráficas generadas **desde el CSV**, explicando las gráficas y contando la historia de JSON/BSON. Apunte del profe: una gráfica por métrica.
- Además, según el profe: explicación larga, explicación corta (`.md`) y un grafo de conocimiento sacado del playbook, guardados en la carpeta `context`.

**Criterio de utilidad:** si otro equipo no puede reejecutar, o un revisor no puede cuestionar P99/throttling con sus datos, la entrega está incompleta.

---

## 7. Qué preguntaría un revisor (y cómo responder)

| Pregunta del revisor | Con qué se responde |
|----------------------|---------------------|
| ¿El baseline es comparable (mismo dataset, mismas queries)? | Sección 2 del reporte; mismo dataset cargado en ambos motores, conteos verificados; perfil A. |
| ¿Las latencias son P50/P95/P99 o solo promedios? | Columnas `latency_p50/p95/p99_ms` del CSV. |
| ¿Hubo throttling CFS? ¿Cuántos segundos? | Columna `cpu_throttled_seconds`; gráfica throttling vs QPS. |
| ¿Spill a disco u OOM? ¿En qué perfil y concurrencia? | Columnas `disk_spill` y `status`; logs/capturas; ambas variantes de Q2. |
| ¿Cuántas repeticiones y cómo se resume (media / mediana)? | 3 repeticiones por celda; declarar el estadístico usado (se sugiere mediana, y mostrar los tres valores). **[supuesto]** |
| ¿El plan de ejecución respalda el cuello de botella? | Sección 5: `explain executionStats` y `EXPLAIN ANALYZE BUFFERS`. |

Regla: se contesta **con tablas, figuras, filas del CSV y planes de ejecución, no con opiniones**.

---

## 8. Ambigüedades detectadas

1. **`payment.final_total` vs `totals`.** Las queries usan `payment.final_total` y `payment.status`, pero la lista de atributos solo menciona `totals` dentro de `payment`. El generador debe incluir `final_total` y `status` (confirmar con el profe).
2. **Variantes de Q2 y tamaño de la matriz.** No queda claro si las variantes (`allowDiskUse`, `work_mem`) cuentan dentro de las 36 celdas o son celdas adicionales. Tampoco hay columna en el CSV para identificar la variante; **[supuesto]** codificarla en `query_id` (p. ej. `Q2_DISK_OFF`) o confirmar con el profe, porque el esquema es inmutable.
3. **`oom_killed` no es columna del CSV.** Está en los KPIs pero el CSV solo tiene `status`. **[supuesto]** reflejar OOM con `status = oom`.
4. **`mem_swappiness` en cgroups v2.** Puede no ser efectivo. Alternativa: igualar `memswap_limit` a `mem_limit` para impedir swap y verificar con `docker inspect`. Confirmar qué espera el profe.
5. **Huella por 1 000 documentos (M3).** Falta definir el denominador (documentos escaneados o resultados) y una métrica de CPU consumida (p. ej. `container_cpu_usage_seconds_total`) que no está en la lista de KPIs. **[supuesto]** usar documentos procesados por la query y registrar CPU usada como dato complementario.
6. **Tipo de `timestamp`.** En MongoDB el filtro compara contra una cadena ISO-8601; en PostgreSQL se castea a `timestamptz`. Si el dato se guarda como texto en Mongo la comparación es lexicográfica (funciona con ISO-8601 en UTC). Conviene decidir y documentar el tipo.
7. **Estadístico de resumen.** El playbook pregunta "media o mediana" sin imponer uno.
8. **Flush de caché dentro de Docker.** `drop_caches` requiere root en el host Linux; no se puede hacer desde un contenedor normal. Hay que ejecutarlo desde el script de orquestación en el host.
9. **Versiones.** Dice *latest-stable* sin número; hay que fijar y registrar versiones exactas (la diapositiva 5 lo exige).
10. **Corrida larga y reanudable.** El playbook no lo pide, pero dado el tiempo total conviene que la corrida pueda reanudarse sin repetir celdas ya presentes en el CSV.
