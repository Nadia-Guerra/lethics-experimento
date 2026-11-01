"""
Benchmark Runner - Experimento Lethics
Ejecuta mediciones bajo contención de CPU y memoria (cgroups v2)
Genera métricas en results/benchmark_results.csv con esquema inmutable de 14 columnas.
(EXP-RF-12, EXP-RF-14, EXP-RF-16, EXP-RF-19, EXP-RF-20, EXP-RF-21, D-06, D-07, D-15)
"""

import os
import sys
import time
import argparse
import subprocess
import urllib.request
import urllib.parse
import json
from concurrent.futures import ThreadPoolExecutor
import numpy as np

# Asegurar import de queries
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pymongo
import psycopg2
from queries.definitions import MONGO_Q1_PIPELINE, MONGO_Q2_FILTER, POSTGRES_Q1_SQL, POSTGRES_Q2_SQL

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'benchmark_results.csv')
CSV_COLUMNS = [
    "timestamp_epoch",
    "engine",
    "profile",
    "query_id",
    "concurrency",
    "run_number",
    "throughput_qps",
    "latency_p50_ms",
    "latency_p95_ms",
    "latency_p99_ms",
    "cpu_throttled_seconds",
    "max_rss_mb",
    "disk_spill",
    "status"
]

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = "lethics_bench"

PG_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
PG_DB = "lethics_bench"
PG_USER = "lethics_admin"
PG_PASS = "lethics_bench_2026"

def query_prometheus(query):
    try:
        url = f"http://localhost:9090/api/v1/query?query={urllib.parse.quote(query)}"
        req = urllib.request.urlopen(url, timeout=3)
        data = json.loads(req.read().decode('utf-8'))
        results = data.get('data', {}).get('result', [])
        if results:
            return float(results[0]['value'][1])
    except Exception:
        pass
    return None

def get_container_rss_mb(container_name):
    # Intentar vía Prometheus
    p_val = query_prometheus(f'container_memory_rss{{name="{container_name}"}}')
    if p_val is not None and p_val > 0:
        return round(p_val / (1024.0 * 1024.0), 2)
    
    # Fallback vía docker stats
    try:
        cmd = ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_name]
        out = subprocess.check_output(cmd, text=True, timeout=5).strip()
        usage_str = out.split('/')[0].strip()
        if 'GiB' in usage_str:
            return round(float(usage_str.replace('GiB', '').strip()) * 1024.0, 2)
        elif 'MiB' in usage_str:
            return round(float(usage_str.replace('MiB', '').strip()), 2)
        elif 'KiB' in usage_str:
            return round(float(usage_str.replace('KiB', '').strip()) / 1024.0, 2)
    except Exception:
        pass
    return 0.0

def get_cpu_throttled_seconds(container_name):
    val = query_prometheus(f'container_cpu_cfs_throttled_seconds_total{{name="{container_name}"}}')
    return val if val is not None else 0.0

def get_postgres_temp_bytes():
    try:
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)
        cur = conn.cursor()
        cur.execute("SELECT temp_bytes FROM pg_stat_database WHERE datname = %s;", (PG_DB,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        return res[0] if res else 0
    except Exception:
        return 0

def execute_single_query(engine, query_id):
    t0 = time.perf_counter()
    if engine == "mongo":
        client = pymongo.MongoClient(MONGO_URI)
        col = client[MONGO_DB]["intentos"]
        if query_id == "Q1":
            list(col.aggregate(MONGO_Q1_PIPELINE))
        elif query_id == "Q2_DISK_OFF":
            list(col.find(MONGO_Q2_FILTER, {"resultado.puntaje_final": 1, "intento_id": 1, "_id": 0})
                 .sort("resultado.puntaje_final", -1)
                 .limit(1000))
        elif query_id == "Q2_DISK_ON":
            list(col.find(MONGO_Q2_FILTER, {"resultado.puntaje_final": 1, "intento_id": 1, "_id": 0})
                 .sort("resultado.puntaje_final", -1)
                 .allow_disk_use(True)
                 .limit(1000))
        else:
            raise ValueError(f"Query {query_id} desconocida para MongoDB")
        client.close()
    elif engine == "postgres":
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASS)
        cur = conn.cursor()
        if query_id == "Q1":
            cur.execute(POSTGRES_Q1_SQL)
            cur.fetchall()
        elif query_id == "Q2_WM4MB":
            cur.execute("SET work_mem = '4MB';")
            cur.execute(POSTGRES_Q2_SQL)
            cur.fetchall()
        elif query_id == "Q2_WM64MB":
            cur.execute("SET work_mem = '64MB';")
            cur.execute(POSTGRES_Q2_SQL)
            cur.fetchall()
        else:
            raise ValueError(f"Query {query_id} desconocida para PostgreSQL")
        cur.close()
        conn.close()
    else:
        raise ValueError(f"Engine {engine} desconocido")
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0  # Latencia en ms

def run_benchmark(engine, profile, query_id, concurrency, run_number, warmup_sec, measure_sec, is_pilot=False):
    container_name = f"lethics-{engine}"
    print(f"\n=======================================================")
    print(f"Iniciando Corrida: {engine} | Perfil {profile} | Query {query_id}")
    print(f"Concurrencia: {concurrency} | Repetición: {run_number} | Piloto: {is_pilot}")
    print(f"Ventana: Warmup={warmup_sec}s, Medición={measure_sec}s")
    print(f"=======================================================")

    epoch_start = int(time.time())
    
    # Métricas iniciales de telemetría
    initial_throttled = get_cpu_throttled_seconds(container_name)
    initial_temp_bytes = get_postgres_temp_bytes() if engine == "postgres" else 0
    max_rss = get_container_rss_mb(container_name)

    # 1. Warmup
    if warmup_sec > 0:
        print(f"[*] Fase de Warmup ({warmup_sec}s)...")
        w_end = time.time() + warmup_sec
        while time.time() < w_end:
            execute_single_query(engine, query_id)
            if is_pilot:
                break

    # 2. Medición
    print(f"[*] Fase de Medición ({measure_sec}s)...")
    latencies_ms = []
    m_end = time.time() + measure_sec
    
    # Closed-loop execution
    def worker_loop():
        local_latencies = []
        while time.time() < m_end or len(local_latencies) == 0:
            try:
                lat = execute_single_query(engine, query_id)
                local_latencies.append(lat)
            except Exception as ex:
                print(f"[!] Error ejecutando consulta: {ex}")
                break
            if is_pilot and len(local_latencies) >= 1:
                break
        return local_latencies

    start_meas = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker_loop) for _ in range(concurrency)]
        for f in futures:
            latencies_ms.extend(f.result())
            # Actualizar max_rss durante la medición
            current_rss = get_container_rss_mb(container_name)
            if current_rss > max_rss:
                max_rss = current_rss
    actual_meas_duration = time.perf_counter() - start_meas

    # Métricas finales de telemetría
    final_throttled = get_cpu_throttled_seconds(container_name)
    cpu_throttled = max(0.0, round(final_throttled - initial_throttled, 4))
    final_rss = get_container_rss_mb(container_name)
    if final_rss > max_rss:
        max_rss = final_rss

    # Detección de spill
    disk_spill = False
    if engine == "postgres":
        final_temp_bytes = get_postgres_temp_bytes()
        if final_temp_bytes > initial_temp_bytes:
            disk_spill = True
    elif engine == "mongo":
        if "DISK_ON" in query_id:
            disk_spill = False  # Verificable con plan de ejecución

    status = "ok"
    if disk_spill:
        status = "spill"

    # Cálculo de KPIs (EXP-RF-19)
    total_queries = len(latencies_ms)
    throughput_qps = round(total_queries / max(actual_meas_duration, 0.001), 2)
    p50 = round(float(np.percentile(latencies_ms, 50)), 2) if latencies_ms else 0.0
    p95 = round(float(np.percentile(latencies_ms, 95)), 2) if latencies_ms else 0.0
    p99 = round(float(np.percentile(latencies_ms, 99)), 2) if latencies_ms else 0.0

    print(f"\n--- Resultados de la corrida ---")
    print(f"Total consultas : {total_queries}")
    print(f"Throughput      : {throughput_qps} QPS")
    print(f"Latencias (ms)  : P50={p50} | P95={p95} | P99={p99}")
    print(f"CPU Throttled   : {cpu_throttled} s")
    print(f"Max RSS         : {max_rss} MB")
    print(f"Disk Spill      : {disk_spill}")
    print(f"Status          : {status}")

    # Guardar en CSV inmutable (EXP-RF-21)
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    file_exists = os.path.exists(CSV_PATH)
    
    row = [
        str(epoch_start),
        engine,
        profile,
        query_id,
        str(concurrency),
        str(run_number),
        str(throughput_qps),
        str(p50),
        str(p95),
        str(p99),
        str(cpu_throttled),
        str(max_rss),
        str(disk_spill),
        status
    ]

    with open(CSV_PATH, 'a', encoding='utf-8') as f:
        if not file_exists or os.path.getsize(CSV_PATH) == 0:
            f.write(",".join(CSV_COLUMNS) + "\n")
        f.write(",".join(row) + "\n")
    
    print(f"\n[+] Fila registrada exitosamente en {CSV_PATH}")
    return row

def main():
    parser = argparse.ArgumentParser(description="Lethics Benchmark Runner")
    parser.add_argument("--engine", choices=["mongo", "postgres"], default="mongo")
    parser.add_argument("--profile", choices=["A", "B", "C"], default="A")
    parser.add_argument("--query", choices=["Q1", "Q2_DISK_OFF", "Q2_DISK_ON", "Q2_WM4MB", "Q2_WM64MB"], default="Q1")
    parser.add_argument("--concurrency", type=int, choices=[1, 10, 50], default=1)
    parser.add_argument("--run-number", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--pilot", action="store_true", help="Ejecutar celda piloto de prueba rápida")

    args = parser.parse_args()

    warmup_sec = args.warmup
    measure_sec = args.duration
    if args.pilot:
        warmup_sec = 0
        measure_sec = 10  # En modo piloto se lanza al menos 1 iteración para validar

    run_benchmark(
        engine=args.engine,
        profile=args.profile,
        query_id=args.query,
        concurrency=args.concurrency,
        run_number=args.run_number,
        warmup_sec=warmup_sec,
        measure_sec=measure_sec,
        is_pilot=args.pilot
    )

if __name__ == "__main__":
    main()

