import os
import time
import pymongo
import psycopg2

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "lethics_bench")

PG_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
PG_PORT = os.getenv("POSTGRES_PORT", "5433")
PG_DB = os.getenv("POSTGRES_DB", "lethics_bench")
PG_USER = os.getenv("POSTGRES_USER", "lethics_admin")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "lethics_bench_2026")

def index_mongo():
    print(f"\n[MongoDB] Creando índices en colección 'intentos'...")
    start_time = time.time()
    client = pymongo.MongoClient(MONGO_URI)
    collection = client[DB_NAME]["intentos"]
    
    # EXP-RF-08: MongoDB: índices simples en fecha e intento_id
    idx_fecha = collection.create_index("fecha")
    idx_id = collection.create_index("intento_id")
    
    elapsed = time.time() - start_time
    indexes = collection.index_information()
    print(f"[MongoDB] Índices creados en {elapsed:.2f}s: {list(indexes.keys())}")

def index_postgres():
    print(f"\n[PostgreSQL] Creando función IMMUTABLE e índice B-Tree (EXP-RF-08, D-10)...")
    start_time = time.time()
    conn = psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT
    )
    cur = conn.cursor()
    
    # EXP-RF-08, D-10: Función envoltorio IMMUTABLE e índice B-Tree sobre get_fecha(data)
    cur.execute("""
        CREATE OR REPLACE FUNCTION get_fecha(data jsonb) RETURNS timestamptz AS $$
            SELECT (data->>'fecha')::timestamptz;
        $$ LANGUAGE SQL IMMUTABLE;
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_intentos_fecha ON intentos USING btree (get_fecha(data));")
    conn.commit()
    
    elapsed = time.time() - start_time
    cur.execute("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'intentos';
    """)
    indexes = cur.fetchall()
    print(f"[PostgreSQL] Índices creados en {elapsed:.2f}s:")
    for name, definition in indexes:
        print(f"  - {name}: {definition}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("=== Creación de Índices (EXP-RF-08, D-10) ===")
    index_mongo()
    index_postgres()
    print("\n=== Índices creados exitosamente ===")
