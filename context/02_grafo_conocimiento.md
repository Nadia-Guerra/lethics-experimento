# Grafo de conocimiento del playbook

> **Aplicación:** el grafo representa el playbook general. En este experimento el nodo "Dataset 500k órdenes" corresponde a la colección `intentos` del proyecto **Lethics** (ver `03_requisitos_RF_RNF.md`, Anexo A). El resto de relaciones aplica sin cambios.

## Diagrama (Mermaid)

```mermaid
graph LR
    EXP["Experimento: contención CPU y memoria en agregaciones JSON"]

    subgraph Motores
        MONGO["MongoDB (BSON, WiredTiger)"]
        PG["PostgreSQL (JSONB)"]
    end

    subgraph Perfiles
        PA["PROFILE_A 4 CPU / 4096m"]
        PB["PROFILE_B 2 CPU / 2048m"]
        PC["PROFILE_C 1 CPU / 1024m"]
    end

    subgraph Queries
        Q1["Q1 Unwind + Group"]
        Q2["Q2 Sort + Top-1000"]
        Q2M["allowDiskUse false/true"]
        Q2P["work_mem 4MB/64MB"]
    end

    subgraph Concurrencia
        C1["1 cliente"]
        C10["10 clientes"]
        C50["50 clientes"]
    end

    subgraph Recursos
        CPU["CPU / CFS throttling"]
        RAM["RAM / buffers sort-group"]
        SWAP["Swap (swappiness 0)"]
        DISK["Spill a disco / OOM"]
    end

    subgraph Telemetria
        CADV["cAdvisor"]
        NODE["Node Exporter"]
        PROM["Prometheus 1s"]
    end

    subgraph KPIs
        QPS["throughput_qps"]
        LAT["latency P50/P95/P99"]
        THR["cpu_throttled_seconds"]
        RSS["max_rss_mb"]
        SPILL["disk_spill"]
        OOM["oom_killed / status"]
    end

    subgraph Preguntas
        M1["M1 Latencia bajo limites"]
        M2["M2 Buffers antes de spill/OOM"]
        M3["M3 Huella por 1000 docs"]
    end

    subgraph Entregables
        CODE["Repo: compose, generador, runner, queries, run_benchmarks.sh"]
        CSV["CSV esquema inmutable"]
        REP["Reporte 7 secciones + graficas"]
        CTX["context: explicacion larga, corta, grafo"]
    end

    DATA["Dataset 500k ordenes, 3 niveles"]
    CICLO["Ciclo: flush cache, warmup 60s, medicion 300s, cooldown 60s"]
    MATRIZ["Matriz 36 celdas x 3 repeticiones"]
    DOCKER["Docker sobre Linux, cgroups v2"]

    EXP -->|compara| MONGO
    EXP -->|compara| PG
    EXP -->|responde| M1
    EXP -->|responde| M2
    EXP -->|responde| M3
    EXP -->|corre en| DOCKER

    DATA -->|se carga en| MONGO
    DATA -->|se carga en| PG
    DOCKER -->|aplica| PA
    DOCKER -->|aplica| PB
    DOCKER -->|aplica| PC

    PC -->|provoca| CPU
    PC -->|presiona| RAM
    Q1 -->|satura| CPU
    Q2 -->|estresa| RAM
    Q2 -->|variante en| Q2M
    Q2 -->|variante en| Q2P
    Q2M -->|aplica a| MONGO
    Q2P -->|aplica a| PG
    SWAP -->|se evita para exponer| DISK
    RAM -->|si no cabe causa| DISK

    CPU -->|aumenta| THR
    THR -->|empeora| LAT
    THR -->|reduce| QPS
    RAM -->|determina| RSS
    DISK -->|se registra como| SPILL
    DISK -->|se registra como| OOM
    SPILL -->|reduce| QPS

    CADV -->|mide| THR
    CADV -->|mide| RSS
    NODE -->|mide| DISK
    PROM -->|recolecta de| CADV
    PROM -->|recolecta de| NODE

    MATRIZ -->|combina| MONGO
    MATRIZ -->|combina| PG
    MATRIZ -->|combina| PA
    MATRIZ -->|combina| PB
    MATRIZ -->|combina| PC
    MATRIZ -->|combina| Q1
    MATRIZ -->|combina| Q2
    MATRIZ -->|combina| C1
    MATRIZ -->|combina| C10
    MATRIZ -->|combina| C50
    CICLO -->|define cada celda de| MATRIZ

    MATRIZ -->|produce filas en| CSV
    QPS -->|columna de| CSV
    LAT -->|columna de| CSV
    THR -->|columna de| CSV
    RSS -->|columna de| CSV
    SPILL -->|columna de| CSV
    OOM -->|columna status de| CSV
    CSV -->|alimenta| REP
    CODE -->|genera| CSV
    CTX -->|guia al agente en| CODE

    LAT -->|responde| M1
    SPILL -->|responde| M2
    OOM -->|responde| M2
    RSS -->|responde| M3
    THR -->|responde| M3
```

## Triples (sujeto, relación, objeto)

| # | Sujeto | Relación | Objeto |
|---|--------|----------|--------|
| 1 | Experimento | compara | MongoDB |
| 2 | Experimento | compara | PostgreSQL JSONB |
| 3 | Experimento | responde | M1, M2, M3 |
| 4 | Experimento | corre en | Docker sobre Linux (cgroups v2) |
| 5 | Dataset 500k | se carga en | MongoDB y PostgreSQL |
| 6 | Docker | aplica | Perfiles A, B, C |
| 7 | Perfil C | provoca | CFS throttling |
| 8 | Perfil C | presiona | RAM |
| 9 | Q1 | satura | CPU |
| 10 | Q2 | estresa | RAM (buffer de ordenamiento) |
| 11 | Q2 | tiene variante | allowDiskUse false/true (Mongo) |
| 12 | Q2 | tiene variante | work_mem 4MB/64MB (Postgres) |
| 13 | Swap (swappiness 0) | se evita para exponer | Spill / OOM |
| 14 | RAM insuficiente | causa | Spill a disco u OOM |
| 15 | CPU limitada | aumenta | cpu_throttled_seconds |
| 16 | Throttling | empeora | Latencia P95/P99 |
| 17 | Throttling | reduce | throughput_qps |
| 18 | Spill | reduce | throughput_qps |
| 19 | RAM | determina | max_rss_mb |
| 20 | cAdvisor | mide | Throttling y RSS |
| 21 | Node Exporter | mide | I/O, disco y swap del host |
| 22 | Prometheus (1 s) | recolecta de | cAdvisor y Node Exporter |
| 23 | Matriz | combina | 2 motores × 3 perfiles × 2 queries × 3 concurrencias |
| 24 | Ciclo (flush, warmup 60 s, medición 300 s, cooldown 60 s) | define cada celda de | Matriz |
| 25 | Matriz | produce filas en | CSV de esquema inmutable |
| 26 | CSV | alimenta | Reporte de 7 secciones y gráficas |
| 27 | Latencias P95/P99 | responden | M1 |
| 28 | Spill y OOM | responden | M2 |
| 29 | RSS y CPU por 1 000 docs | responden | M3 |
| 30 | Carpeta context | guía al agente en | Código del repositorio |

> Revisa que cada relación coincida con el playbook antes de usar este grafo como contexto del agente. Las relaciones 13 y 29 combinan lo que dice el playbook con interpretación razonable (ver ambigüedades en `00_explicacion_larga.md`).
