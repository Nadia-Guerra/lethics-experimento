import os
import json
import time
import pymongo
import psycopg2
from psycopg2.extras import execute_values

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "lethics_bench")

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5433")
PG_DB = os.getenv("POSTGRES_DB", "lethics_bench")
PG_USER = os.getenv("POSTGRES_USER", "lethics_admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lethics_bench_2026")

def load_mongo(filepath):
    print(f"\n[MongoDB] Conectando a {MONGO_URI} (db: {DB_NAME})...")
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["intentos"]
    
    collection.drop()
    print("[MongoDB] Colección 'intentos' reiniciada.")

    batch = []
    total = 0
    start_time = time.time()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            batch.append(json.loads(line))
            if len(batch) >= 10000:
                collection.insert_many(batch, ordered=False)
                total += len(batch)
                batch = []
                if total % 100000 == 0:
                    print(f"[MongoDB] Insertados {total:,} registros ({time.time() - start_time:.1f}s)...")
        if batch:
            collection.insert_many(batch, ordered=False)
            total += len(batch)
    
    elapsed = time.time() - start_time
    count = collection.count_documents({})
    print(f"[MongoDB] Carga terminada: {count:,} documentos en {elapsed:.2f}s.")
    return count

def load_postgres(filepath):
    print(f"\n[PostgreSQL] Conectando a {PG_HOST}:{PG_PORT} (db: {PG_DB}, user: {PG_USER})...")
    conn = psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS intentos;")
    cur.execute("CREATE TABLE intentos (id UUID PRIMARY KEY, data JSONB);")
    conn.commit()
    print("[PostgreSQL] Tabla 'intentos' (id UUID PK, data JSONB) recreada.")

    batch = []
    total = 0
    start_time = time.time()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            doc = json.loads(line)
            batch.append((doc['intento_id'], json.dumps(doc)))
            if len(batch) >= 10000:
                execute_values(cur, "INSERT INTO intentos (id, data) VALUES %s", batch, page_size=10000)
                conn.commit()
                total += len(batch)
                batch = []
                if total % 100000 == 0:
                    print(f"[PostgreSQL] Insertados {total:,} registros ({time.time() - start_time:.1f}s)...")
        if batch:
            execute_values(cur, "INSERT INTO intentos (id, data) VALUES %s", batch, page_size=10000)
            conn.commit()
            total += len(batch)
    
    cur.execute("SELECT count(*) FROM intentos;")
    count = cur.fetchone()[0]
    elapsed = time.time() - start_time
    print(f"[PostgreSQL] Carga terminada: {count:,} registros en {elapsed:.2f}s.")
    cur.close()
    conn.close()
    return count

if __name__ == "__main__":
    filepath = './data/dataset_intentos.json'
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No se encontró el dataset en {filepath}")
    
    print("=== Iniciando Carga Masiva (EXP-RF-07) ===")
    m_count = load_mongo(filepath)
    p_count = load_postgres(filepath)
    print("\n=== Resumen de Carga ===")
    print(f"MongoDB    : {m_count:,} documentos")
    print(f"PostgreSQL : {p_count:,} registros")
