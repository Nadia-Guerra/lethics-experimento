"""
Orquestador de la Matriz Completa del Experimento Lethics
Ejecuta las 54 celdas x 3 repeticiones (162 ejecuciones)
Soporta reanudacion automatica (EXP-RF-17, D-14) y apagado del motor inactivo (D-15).
"""

import os
import sys
import subprocess
import time

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'results', 'benchmark_results.csv')

PROFILES = {
    "A": {"cpus": "4.0", "mem": "4096m"},
    "B": {"cpus": "2.0", "mem": "2048m"},
    "C": {"cpus": "1.0", "mem": "1024m"}
}

MATRIX = [
    # Mongo
    {"engine": "mongo", "queries": ["Q1", "Q2_DISK_OFF", "Q2_DISK_ON"]},
    # Postgres
    {"engine": "postgres", "queries": ["Q1", "Q2_WM4MB", "Q2_WM64MB"]}
]

CONCURRENCIES = [1, 10, 50]
RUNS = [1, 2, 3]

def get_completed_runs():
    completed = set()
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 6:
                    # engine, profile, query_id, concurrency, run_number
                    key = (parts[1], parts[2], parts[3], int(parts[4]), int(parts[5]))
                    completed.add(key)
    return completed

def apply_docker_profile(profile):
    conf = PROFILES[profile]
    print(f"\n[Docker] Aplicando Perfil {profile} (CPUs: {conf['cpus']}, Mem: {conf['mem']})...")
    env = os.environ.copy()
    env["BENCHMARK_CPUS"] = conf["cpus"]
    env["BENCHMARK_MEMORY"] = conf["mem"]
    env["BENCHMARK_MEM_SWAP"] = conf["mem"]
    
    # Actualizar límites de contenedores
    subprocess.run(["docker", "compose", "up", "-d"], env=env, check=False)
    time.sleep(5)

def manage_engines(active_engine):
    # D-15: Solo un motor a la vez durante las mediciones
    inactive_engine = "postgres" if active_engine == "mongo" else "mongo"
    subprocess.run(["docker", "stop", f"lethics-{inactive_engine}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "start", f"lethics-{active_engine}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

def run():
    print("=================================================================")
    print("  EXPERIMENTO LETHICS: INICIANDO MATRIZ COMPLETA (54 CELDAS x 3) ")
    print("=================================================================")
    
    completed = get_completed_runs()
    print(f"Corridas ya completadas anteriormente: {len(completed)} de 162")

    current_profile = None

    for profile in ["A", "B", "C"]:
        for item in MATRIX:
            engine = item["engine"]
            queries = item["queries"]

            for query in queries:
                for concurrency in CONCURRENCIES:
                    for run_number in RUNS:
                        key = (engine, profile, query, concurrency, run_number)
                        if key in completed:
                            print(f"[Omitida] Celda ya completada: {key}")
                            continue

                        # Cambiar perfil si cambia
                        if current_profile != profile:
                            apply_docker_profile(profile)
                            current_profile = profile

                        # Asegurar que solo el motor activo esté encendido
                        manage_engines(engine)

                        # Ejecutar benchmark runner
                        cmd = [
                            sys.executable,
                            os.path.join(os.path.dirname(__file__), "benchmark_runner.py"),
                            "--engine", engine,
                            "--profile", profile,
                            "--query", query,
                            "--concurrency", str(concurrency),
                            "--run-number", str(run_number),
                            "--warmup", "60",
                            "--duration", "300"
                        ]

                        print(f"\n[Ejecutando] {engine} | {profile} | {query} | c={concurrency} | rep={run_number}")
                        res = subprocess.run(cmd)
                        
                        if res.returncode == 0:
                            completed.add(key)
                        else:
                            print(f"[!] Corrida falló con código {res.returncode}. Continuando...")
                        
                        # Cooldown 60s (EXP-RF-12)
                        print("[*] Cooldown de 60 segundos...")
                        time.sleep(60)

    print("\n=================================================================")
    print("  MATRIZ COMPLETA FINALIZADA CON ÉXITO")
    print(f"  Resultados consolidados en: {CSV_PATH}")
    print("=================================================================")

if __name__ == "__main__":
    run()

