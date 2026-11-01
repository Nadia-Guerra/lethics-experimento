# Requisitos funcionales y no funcionales del experimento

> **Experimento:** MongoDB vs PostgreSQL JSONB bajo contención de CPU y memoria (Docker, cgroups v2), aplicado al proyecto **Lethics** (plataforma de cursos sobre ética y leyes del desarrollo de software).
> **Fuentes:** playbook (§ = sección del playbook), diapositivas de la sesión, apuntes de clase, `skill.md` de la compañera y el documento de patrones de acceso de Lethics.
> **IDs:** llevan el prefijo `EXP-` para no chocar con los RF/RN del proyecto Lethics (p. ej. RF 7.1, RN-03).
> **Decisiones:** las referencias `D-xx` apuntan a `05_decisiones_y_supuestos.md`, donde se explica por qué se tomó cada una.

---

## 0. Cómo se aplica el playbook a Lethics

El playbook describe el experimento con un dataset genérico de órdenes de e-commerce. Aquí se **conserva todo lo técnico** (motores, perfiles, concurrencias, ciclo, queries, KPIs, CSV, entregables) y se **cambia el dominio** de los datos a Lethics:

| Playbook | Lethics (este experimento) |
|---|---|
| Colección/tabla `orders` | Colección/tabla `intentos` (intentos de cuestionarios y examen final) |
| `items[]` (≈3 por orden) | `respuestas[]` (≈3 por intento) |
| `payment.final_total`, `payment.status` | `resultado.puntaje_final`, `resultado.estado` |
| `customer.geo.country` | `usuario.geo.pais` |

La equivalencia completa campo por campo está en el **Anexo A**. Cuando los documentos de `context/` mencionen `orders`, `items` o `price`, se leen como sus equivalentes de Lethics.

---

## 1. Requisitos funcionales (RF)

### A. Entorno e infraestructura

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-01 | **Docker sobre Linux.** Todos los servicios y cargas corren en contenedores Docker sobre Linux (nativo o VM Linux como WSL2, declarado). | `docker version` y `uname -a` quedan en `results/run_metadata.json` y en la sección 1 del reporte. | Apuntes; §8 |
| EXP-RF-02 | **Perfiles parametrizados.** Un solo `docker-compose.yml` cambia de perfil únicamente con variables de entorno (`BENCHMARK_CPUS`, `BENCHMARK_MEMORY`, `BENCHMARK_MEM_SWAP`). | Al levantar A, B y C, `docker inspect` del contenedor del motor muestra CPUs, memoria y swap iguales a la tabla de §3 (D-08). | §3, §8.1; skill.md |
| EXP-RF-03 | **Servicios y versiones fijas.** MongoDB :27017, PostgreSQL :5432, Prometheus :9090, cAdvisor :8080, Node Exporter :9100. Imágenes con versión exacta, no `latest` (D-13). | Todos healthy/UP; versiones exactas registradas en `run_metadata.json`. | §2, §7 |
| EXP-RF-04 | **Un motor a la vez.** Durante una celda solo corre el motor medido; el otro permanece detenido (D-15). | El log de cada celda muestra el estado de ambos contenedores. | Derivado de §6 |

### B. Datos

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-05 | **Generador reproducible.** `synthetic_data_generator.py` produce 500 000 documentos JSON en streaming (sin cargar todo en memoria) con semilla fija. | Misma semilla produce el mismo hash de archivo; el archivo tiene 500 000 documentos. | §4, §8.1 |
| EXP-RF-06 | **Estructura del documento.** Documentos de `intentos` según el Anexo A: 3 niveles de anidamiento, ≈3 `respuestas` por documento, campos de Q1/Q2 siempre presentes y con el tipo correcto (D-02, D-05). | Validador sobre el archivo: profundidad máxima = 3; media de `respuestas` entre 2,9 y 3,1; 0 nulos en campos usados por Q1/Q2; el filtro de Q2 selecciona entre 40 % y 60 % de los documentos. | §4 |
| EXP-RF-07 | **Carga idéntica.** El mismo archivo se carga en MongoDB (`intentos`) y en PostgreSQL (`intentos (id UUID PRIMARY KEY, data JSONB)`). | Conteo = 500 000 en ambos; muestra de 1 000 ids con contenido idéntico. | §2, §4 |
| EXP-RF-08 | **Índices del playbook, solo en el nivel más alto.** MongoDB: índices simples en `fecha` e `intento_id`. PostgreSQL: PK en `id` y B-Tree sobre la fecha extraída del JSONB (D-10). Sin índice sobre `resultado.puntaje_final` ni sobre campos de `respuestas`. | `getIndexes()` y `\d+ intentos` guardados en `results/evidence/`. | §2, §5.2; apuntes |

### C. Consultas

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-09 | **Q1 (satura CPU).** Desanidar `respuestas`, filtrar `tiempo_respuesta_seg > 50`, calcular subtotal `peso × tiempo_respuesta_seg` y agrupar suma, promedio y conteo por país y tema. Pipeline en MongoDB y SQL con `jsonb_array_elements` en PostgreSQL, en `queries/` (D-03). | Mismos grupos y mismos totales en ambos motores (tolerancia de redondeo) sobre el dataset completo. | §5.1 |
| EXP-RF-10 | **Q2 (estresa RAM) y variantes.** Filtrar `resultado.estado = "aprobado"` y `fecha >= 2026-01-01`, ordenar desc por `resultado.puntaje_final`, Top-1000 y proyectar. Variantes: MongoDB `allowDiskUse` false/true; PostgreSQL `work_mem` 4MB/64MB. | Cada variante se ejecuta con su ajuste verificado (`SHOW work_mem`; bandera presente en el comando de Mongo). Los 1 000 valores de `puntaje_final` coinciden entre motores. | §5.2 |
| EXP-RF-11 | **Bandera de disco documentada.** Investigar y documentar, para la versión instalada de MongoDB, cómo permitir o prohibir disco y cuál es su valor por defecto. | Nota con enlace a la documentación de esa versión en `context/`. | Apuntes ([MCP]) |

### D. Ejecución

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-12 | **Ciclo por repetición.** Flush de caché → warmup 60 s → medición 300 s → cooldown 60 s. | Log con marcas de tiempo; los KPIs se calculan solo con la ventana de medición. | §6 |
| EXP-RF-13 | **Flush real de caché.** Ejecutar `sync; echo 3 > /proc/sys/vm/drop_caches` en el kernel donde corre el daemon de Docker antes de cada repetición (D-12). | Código de salida 0 registrado por repetición; si falla, la repetición queda como `error`. | §6; apuntes |
| EXP-RF-14 | **Concurrencia.** 1, 10 y 50 clientes; en los niveles altos se usan entre 10 y 50 workers simultáneos, en lazo cerrado (cada worker lanza la siguiente consulta al terminar la anterior) (D-15). | Durante la medición hay N conexiones activas; el log lo confirma. | §6; apuntes |
| EXP-RF-15 | **Matriz completa.** 2 motores × 3 perfiles × (Q1 + 2 variantes de Q2) × 3 concurrencias = **54 celdas** × 3 repeticiones = **162 filas** (D-06). | El CSV final tiene 162 filas; ninguna combinación falta (o consta como `error`). | §6 |
| EXP-RF-16 | **Celda piloto.** Antes de la matriz, ejecutar 1 motor × 1 query × 1 concurrencia (modo `--pilot`). | El CSV del piloto pasa el validador (EXP-RF-21) y se revisa a mano. | Diap. 13; skill.md |
| EXP-RF-17 | **Reanudable y tolerante a fallos.** El orquestador omite celdas ya registradas y, si una celda falla o muere por OOM, escribe su fila con el estado y continúa (D-14). | Detener el proceso a mitad y relanzar continúa sin duplicar filas; un OOM provocado no detiene la matriz. | Apuntes; derivado |

### E. Medición y datos de salida

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-18 | **Telemetría.** cAdvisor, Node Exporter y Prometheus con `scrape_interval: 1s`. | En Prometheus los targets están UP y hay series de los KPIs con resolución de 1 s durante una corrida. | §7 |
| EXP-RF-19 | **Cálculo de KPIs.** Latencias y QPS salen de los tiempos medidos por el runner (reloj monotónico). `cpu_throttled_seconds` es la **diferencia** del contador CFS entre inicio y fin de la medición. `max_rss_mb` es el máximo de RSS en la ventana. | Prueba unitaria de percentiles con una distribución conocida; el throttling reportado no es el valor acumulado del contador. | §7 |
| EXP-RF-20 | **Detección de spill y OOM.** Spill: indicador de uso de disco de MongoDB de la versión instalada y aumento de `temp_files`/`temp_bytes` en `pg_stat_database` de PostgreSQL. OOM: bandera `OOMKilled` del contenedor. | Se prueba la detección con una consulta de control que sí necesita disco (p. ej. ordenar todo sin `LIMIT`) y con un límite de memoria mínimo para forzar OOM. | §7 |
| EXP-RF-21 | **CSV con esquema fijo.** `results/benchmark_results.csv` con exactamente las 14 columnas del playbook y su orden; una fila por repetición; `status` ∈ {ok, spill, oom, error}; `query_id` ∈ {Q1, Q2_DISK_OFF, Q2_DISK_ON, Q2_WM4MB, Q2_WM64MB} (D-06, D-07). | Validador automático de columnas, tipos, rangos y duplicados (motor, perfil, query, concurrencia, repetición). Lo no medible queda vacío. | §8.2 |
| EXP-RF-22 | **Metadatos de corrida.** Guardar host (CPU, RAM, SO, Docker), límites reales por perfil, versiones y configuración efectiva de los motores (p. ej. `shared_buffers`, caché de WiredTiger) (D-13). | `results/run_metadata.json`; alimenta las secciones 1 y 2 del reporte. | §8.3; Diap. 5 |

### F. Evidencia y reporte

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-23 | **Planes de ejecución.** Guardar `explain("executionStats")` (Mongo) y `EXPLAIN (ANALYZE, BUFFERS)` (PostgreSQL) de Q1 y de cada variante de Q2, en perfiles A y C. | Archivos en `reports/plans/`; el plan de PostgreSQL muestra método de ordenamiento y memoria usada. | §8.3 (5) |
| EXP-RF-24 | **Evidencia de spill/OOM.** Guardar logs o capturas de cada celda con spill u OOM. | Carpeta `results/evidence/` con archivos nombrados por celda. | Diap. 10 |
| EXP-RF-25 | **Reporte automatizado.** Un script genera tablas y gráficas desde el CSV, sin edición manual. | Un comando regenera todo; el mismo CSV produce las mismas salidas. | Apuntes; §8.3 |
| EXP-RF-26 | **Gráficas.** Una gráfica por métrica (g1 = RAM, g2 = CPU, etc.) más las del playbook: P99 vs concurrencia, throttling vs QPS, curva de RSS. | Lista cerrada en el plan de ejecución; cada gráfica con título, ejes con unidades, motor identificable y la pregunta M1–M3 que responde (Anexo B). | Apuntes; §8.3 (4) |
| EXP-RF-27 | **Reporte de 7 secciones.** Las 7 secciones del playbook, con la historia BSON vs JSONB conectada a evidencia. | Checklist de secciones; cada afirmación de la interpretación señala una fila del CSV o un plan. | §8.3; apuntes |

### G. Trabajo con el agente de IA

| ID | Requisito | Criterio de aceptación | Fuente |
|---|---|---|---|
| EXP-RF-28 | **Contexto para el agente.** `context/` con los md 00–05, 3 skills en `skills/` y un `AGENTS.md`. | El agente, leyendo solo `context/`, resume correctamente el experimento. | Apuntes |
| EXP-RF-29 | **Puntos de control.** El agente se detiene y pide confirmación en: **PC-1** límites de perfiles verificados; **PC-2** esquema aprobado con una muestra de 5 documentos, antes de generar 500k; **PC-3** conteos y checksums tras la carga; **PC-4** CSV del piloto; **PC-5** estimación de tiempo y alcance antes de la matriz. | Cada punto deja un resumen breve en el log del proyecto. | Derivado |
| EXP-RF-30 | **Entregables de código.** `docker-compose.yml`, generador, runner (k6 o Python multiproceso), `queries/`, `run_benchmarks.sh` (y `.ps1` opcional). | Un tercero reejecuta el experimento siguiendo el README. | §8.1 |

---

## 2. Requisitos no funcionales (RNF)

| ID | Requisito | Criterio de aceptación |
|---|---|---|
| EXP-RNF-01 | **Reproducibilidad.** Semilla fija, versiones fijas, comandos documentados. | Otro equipo reejecuta y obtiene resultados comparables (criterio de utilidad del playbook). |
| EXP-RNF-02 | **Comparabilidad.** Mismo dataset, mismas queries, mismo ciclo y mismo perfil en ambos motores; solo cambia el motor. Configuración por defecto salvo lo que fija el playbook (D-13). | Tabla de configuración efectiva de ambos motores en el reporte. |
| EXP-RNF-03 | **Esquema CSV inmutable.** No se renombran ni agregan columnas. Métricas adicionales van en archivos aparte (D-09). | El validador rechaza cualquier cambio de columnas. |
| EXP-RNF-04 | **Trazabilidad.** Cada fila del CSV es rastreable a su perfil, límites reales, versión del motor y estado. | `run_metadata.json` presente por corrida. |
| EXP-RNF-05 | **Validez de la medición.** El runner corre fuera de los límites del perfil y no debe ser el cuello de botella (con 50 workers, usar multiproceso o k6, no hilos de Python). | Uso de CPU del runner monitoreado y reportado; muy por debajo de saturación. |
| EXP-RNF-06 | **Aislamiento del host.** Sin otras cargas pesadas durante las mediciones (IDE, navegador, actualizaciones). En laptop: conectada a corriente, sin suspensión, plan de energía de alto rendimiento. | Carga de fondo del host (Node Exporter) registrada y baja en el baseline. |
| EXP-RNF-07 | **Recursos del host o VM.** Al menos los 4 CPUs y 4 GB del perfil A **más** margen para runner y telemetría, y disco libre para dataset, índices y logs de ambos motores. Si es Docker Desktop con WSL2, ajustar el límite de la VM (`.wslconfig`). | `nproc`, memoria y espacio libre registrados antes de empezar. |
| EXP-RNF-08 | **Duración planificable.** Matriz base: 108 repeticiones × 7 min ≈ 12,6 h. Con variantes de Q2: 162 × 7 min ≈ 18,9 h, más flush y preparación. Debe poder ejecutarse por sesiones. | Estimación mostrada en PC-5; ejecución reanudable (EXP-RF-17). |
| EXP-RNF-09 | **Robustez.** Un fallo de celda no detiene la matriz; logs persistentes por celda. | Logs en `results/logs/` con marcas de tiempo. |
| EXP-RNF-10 | **Datos sintéticos y seguridad.** Ningún dato real de usuarios de Lethics; credenciales de bases de datos en `.env` fuera del control de versiones. | Revisión del repo: sin secretos ni datos reales. |
| EXP-RNF-11 | **Explicabilidad.** Código comentado y metodología documentada, porque en la entrega hay que explicar scripts, métricas y gráficas. | El README explica cada métrica del CSV y cada script. |
| EXP-RNF-12 | **Portabilidad de scripts.** Orquestación principal en Bash; PowerShell opcional. Los comandos exclusivos de Linux se ejecutan dentro de la VM o host Linux que corre Docker. | Instrucciones separadas para Linux nativo y para Windows con WSL2. |

---

## 3. Riesgos

| ID | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R1 | **Q2 podría no producir spill.** Con `LIMIT` 1000 los motores suelen usar ordenamiento Top-N que solo retiene 1 000 filas, así que `work_mem` y `allowDiskUse` quizá no cambien nada. | M2 se quedaría sin contraste visible. | No modificar la query. Reportar "sin spill" como resultado válido y respaldarlo con el plan (p. ej. `Sort Method` en PostgreSQL). Usar la consulta de control de EXP-RF-20 solo para validar la detección. |
| R2 | **Índice de fecha en PostgreSQL.** El cast de texto a `timestamptz` normalmente no es IMMUTABLE, por lo que `CREATE INDEX` sobre esa expresión suele fallar. | El índice del playbook no se crearía o no se usaría. | Función envoltorio IMMUTABLE y usar la misma expresión en Q2; documentarlo (D-10). Verificar con `EXPLAIN`. |
| R3 | **Windows con Docker Desktop/WSL2.** `drop_caches`, cgroups v2 y cAdvisor se comportan distinto dentro de la VM. | Flush de caché o telemetría incompletos. | Ejecutar el flush dentro de la VM, verificar con `docker inspect` y registrar el entorno real (EXP-RF-22). Si cAdvisor no ve algo, documentarlo. |
| R4 | **Throttling térmico o de energía del laptop.** | Contamina los resultados de CPU y las latencias. | Corriente, ventilación, plan de alto rendimiento; comparar con el baseline. |
| R5 | **El runner es el cuello de botella** (50 workers). | La latencia medida sería la del cliente. | Runner multiproceso o k6, monitoreo de su CPU (EXP-RNF-05). |
| R6 | **P99 con pocas muestras** (concurrencia 1 con queries lentas). | El P99 se acerca al máximo. | Reportar cuántas consultas se completaron por corrida (`QPS × 300`). |
| R7 | **Datos sintéticos poco representativos de Lethics** (país, tiempos de respuesta, puntaje). | Conclusiones difíciles de extrapolar. | Declarar en el reporte qué campos son reales y cuáles sintéticos (Anexo A). |
| R8 | **Variabilidad con solo 3 repeticiones.** | Diferencias pequeñas podrían ser ruido. | Mediana más rango min–max (D-11); no afirmar diferencias que caigan dentro del rango. |
| R9 | **Las cachés de los motores cambian con el límite de memoria** (p. ej. caché de WiredTiger, `shared_buffers`). | Parte de la diferencia entre perfiles vendría de la autoconfiguración. | Dejar configuración por defecto y registrar la configuración efectiva por perfil (D-13). |

---

## Anexo A. Equivalencia playbook → Lethics

Colección `intentos` de Lethics (historial de intentos; P14, P17, P19). **Real** = campo que ya existe en el modelo de `intentos`; **sintético** = se agrega solo para el experimento. Esta es una propuesta que se confirma en **PC-2** con una muestra de 5 documentos.

| Playbook | Lethics (experimento) | Origen y nota |
|---|---|---|
| `orders` | `intentos` | Colección y tabla (`id UUID PK`, `data JSONB`). |
| `order_id` (UUID) | `intento_id` (UUID) | Sintético: en producción es ObjectId; se usa UUID para igualar el `id UUID` de PostgreSQL. Indexado. |
| `timestamp` (ISO-8601) | `fecha` | Real. Cadena ISO-8601 en UTC en ambos motores (D-10). Indexado. |
| `customer` | `usuario` | Snapshot desnormalizado; real solo `id_usuario`. |
| `customer.id` | `usuario.id` | Real (`id_usuario`), como UUID. |
| `customer.tier` | `usuario.tipo_usuario` | Real: estudiante, profesional o casual. |
| `customer.segment` | `usuario.segmento` | Sintético (p. ej. autodidacta, universitario, empresa). |
| `customer.geo{country, state, city, zip, coordinates}` | `usuario.geo{pais, estado, ciudad, cp, coordenadas{lat, lon}}` | Sintético: Lethics solo guarda `zona_horaria`. Aporta el tercer nivel de anidamiento y el agrupamiento por país. |
| `items[]` | `respuestas[]` | Real (arreglo), con ≈3 por intento en lugar de 10 para respetar el playbook (D-02). |
| `items[].sku` | `respuestas[].id_pregunta` | Real. |
| `items[].category` | `respuestas[].tema` | Sintético (5 a 8 temas del curso). |
| `items[].brand` | `respuestas[].modulo` | Derivado de `id_modulo` (1 a 5). |
| `items[].qty` | `respuestas[].peso` | Sintético (1 a 5). |
| `items[].price` | `respuestas[].tiempo_respuesta_seg` | Sintético (decimal, 1 a 120). Q1 filtra `> 50`. |
| `items[].tax_pct` | `respuestas[].penalizacion_pct` | Sintético. |
| `items[].discounts` | `respuestas[].bonificacion{tipo, pct}` | Sintético. |
| (sin equivalente) | `respuestas[].id_opcion_elegida`, `respuestas[].es_correcta` | Real; se conservan, no los usan Q1 ni Q2. |
| `payment` | `resultado` | Agrupa el resultado del intento. |
| `payment.method` | `resultado.modalidad` | Real (`tipo`): cuestionario o examen_final. |
| `payment.status` (`completed`) | `resultado.estado` | Derivado de `aprobado`: "aprobado" o "reprobado". Q2 filtra "aprobado". |
| `payment.transaction_id` | `resultado.id_calificacion` | Sintético (UUID). |
| `payment.gateway_latency_ms` | `resultado.latencia_calificacion_ms` | Sintético. |
| `payment.totals` | `resultado.totales{aciertos, total_preguntas, porcentaje}` | Real. |
| `payment.final_total` | `resultado.puntaje_final` | Sintético: decimal de alta cardinalidad para evitar empates en el Top-1000 (el `porcentaje` real tiene pocos valores distintos) (D-05). |
| `metadata{channel, user_agent, session_id, flags}` | `metadata{canal, user_agent, id_sesion, banderas}` | `user_agent` real (de `sesiones`); el resto sintético. |

**Q1 en términos de Lethics:** esfuerzo ponderado (`peso × tiempo_respuesta_seg`) de las respuestas lentas (> 50 s), agrupado por país y tema.
**Q2 en términos de Lethics:** los 1 000 intentos aprobados desde el 2026-01-01 con mayor `puntaje_final`.

---

## Anexo B. Qué ver y dónde (pregunta → columnas → gráficas)

| Pregunta | Columnas del CSV | Dónde se ve |
|---|---|---|
| **M1** Latencia bajo límites | `latency_p95_ms`, `latency_p99_ms`; apoyo: `throughput_qps`, `cpu_throttled_seconds` | P99 vs concurrencia (por perfil y motor, Q1 y Q2); throttling vs QPS |
| **M2** Buffers antes de spill/OOM | `disk_spill`, `status`, `max_rss_mb` en las variantes de Q2 | Tabla de spill/OOM por perfil × concurrencia × variante; curva de RSS; QPS con y sin spill |
| **M3** Huella por 1 000 documentos | `max_rss_mb`; extra: CPU consumida y documentos examinados (`results/extra_metrics.csv`) | Tabla M3 a concurrencia 1 (D-09) |

---

## Pendientes que conviene confirmar con el profe (opcionales)

Si hay oportunidad, agrupar en preguntas de sí/no:
1. ¿Las variantes de Q2 cuentan como celdas aparte (54 en total) y pueden codificarse en `query_id`?
2. ¿Se aceptan campos sintéticos (país, tiempos, puntaje) para el dataset de Lethics?
3. ¿Es válido ejecutar sobre Docker en una VM Linux (WSL2)?

Si no hay respuesta, se procede con las decisiones de `05_decisiones_y_supuestos.md`.
