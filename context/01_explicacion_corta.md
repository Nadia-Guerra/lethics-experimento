# Explicación corta: MongoDB vs PostgreSQL JSONB bajo contención

> **Aplicación:** este resumen es la guía general del playbook. El experimento se ejecuta sobre el proyecto **Lethics** (colección `intentos` en lugar de `orders`; `respuestas` en lugar de `items`). Todo lo demás (perfiles, queries, ciclo, KPIs, CSV, entregables) aplica igual. Equivalencia de campos: `03_requisitos_RF_RNF.md`, Anexo A. Decisiones: `05_decisiones_y_supuestos.md`.

**Objetivo:** comparar MongoDB (BSON) y PostgreSQL JSONB ejecutando agregaciones JSON anidadas con límites estrictos de CPU y memoria (Docker, cgroups v2, Linux). Cada corrida produce métricas numéricas en un CSV homogéneo.

## Preguntas
- **M1:** ¿Cómo cambian P95/P99 al limitar CPU y memoria?
- **M2:** ¿Qué motor gestiona mejor los buffers antes de spill a disco u OOM?
- **M3:** ¿Cuál es la huella de CPU/memoria por cada 1 000 documentos?

## Dataset y motores
- 500 000 órdenes JSON, 3 niveles de anidamiento, ~3 ítems por orden. Generador en Python.
- MongoDB: colección `orders`, WiredTiger, índices simples en `timestamp` y `order_id`.
- PostgreSQL: `orders (id UUID PK, data JSONB)`, B-Tree sobre el `timestamp` extraído.
- Un solo motor por tabla/colección; indexación solo en el nivel más alto.

## Queries
- **Q1 (satura CPU):** unwind de `items`, filtro `price > 50`, subtotal `qty*price`, agrupar por país y categoría.
- **Q2 (estresa RAM):** órdenes `completed` desde 2026-01-01, ordenar por `payment.final_total` desc, Top-1000, sin índice en el total.
  - Variantes: Mongo `allowDiskUse` false/true; Postgres `work_mem` 4MB/64MB. Se reportan ambas.

## Perfiles (mem_swappiness = 0)
| Perfil | CPUs | Memoria |
|---|---|---|
| A baseline | 4,0 | 4096 m |
| B media | 2,0 | 2048 m |
| C severa | 1,0 | 1024 m |

## Protocolo
- Concurrencia: 1, 10, 50 (10-50 workers simultáneos).
- Ciclo: flush de caché (`sync; echo 3 > /proc/sys/vm/drop_caches`) → warmup 60 s → medición 300 s → cooldown 60 s.
- Matriz: 2 motores × 3 perfiles × 2 queries × 3 concurrencias = 36 celdas × 3 repeticiones (~7 min c/u).
- Primero una celda piloto y validar el CSV.

## Telemetría
cAdvisor (:8080), Node Exporter (:9100), Prometheus (:9090, scrape 1 s).

## KPIs
`throughput_qps`, `latency_p50/p95/p99_ms`, `container_cpu_cfs_throttled_seconds_total`, `container_memory_rss_bytes`, `disk_spill_detected`, `oom_killed`.

## CSV (esquema inmutable, sin columnas nuevas ni renombradas)
`timestamp_epoch, engine, profile, query_id, concurrency, run_number, throughput_qps, latency_p50_ms, latency_p95_ms, latency_p99_ms, cpu_throttled_seconds, max_rss_mb, disk_spill, status` (status: ok/spill/oom/error)

## Entregables
- Código: `docker-compose.yml` parametrizado, `synthetic_data_generator.py`, benchmark runner (k6 o Python), `queries/`, `run_benchmarks.sh`.
- Evidencia: CSV, logs/capturas de spill/OOM, reporte de 7 secciones (host/Docker, método y baseline, resultados, gráficas, planes de ejecución, interpretación, recomendaciones), con una gráfica por métrica contando la historia BSON vs JSONB.
- Además: explicación larga y corta (`.md`) y grafo de conocimiento en `context/`.

## Reglas de oro
- Todo corre en Docker sobre Linux; limpiar caché en cada ciclo (no es automático).
- Anotar siempre: perfil, límites Docker reales, versión del motor, spill/OOM.
- Responder al revisor con datos y planes (`explain executionStats` / `EXPLAIN ANALYZE BUFFERS`), no con opiniones.
- Métricas extra son complemento, no condición de diseño.

## Ambigüedades abiertas
`payment.final_total` no aparece en la lista de atributos; las variantes de Q2 no tienen columna en el CSV; `mem_swappiness` puede no aplicar en cgroups v2; definir el denominador de M3. Detalle en `00_explicacion_larga.md`.
