import os
import sys
import time

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
import pymongo
from queries.definitions import MONGO_Q1_PIPELINE, MONGO_Q2_FILTER, POSTGRES_Q1_SQL, POSTGRES_Q2_SQL

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "lethics_bench"
PG_PORT = 5433

def test_queries():
    print("=== Probando Conexiones y Consultas ===")
    
    # 1. Mongo
    m_client = pymongo.MongoClient(MONGO_URI)
    m_col = m_client[DB_NAME]["intentos"]
    
    print("\n--- MongoDB Q1 ---")
    t0 = time.time()
    m_res_q1 = list(m_col.aggregate(MONGO_Q1_PIPELINE))
    t1 = time.time()
    print(f"MongoDB Q1 retorno {len(m_res_q1)} grupos en {t1 - t0:.2f}s")
    if m_res_q1:
        print("Ejemplo grupo Q1:", m_res_q1[0])
        
    print("\n--- MongoDB Q2 (allowDiskUse=False) ---")
    t0 = time.time()
    m_res_q2 = list(m_col.find(MONGO_Q2_FILTER, {"resultado.puntaje_final": 1, "intento_id": 1, "_id": 0})
                    .sort("resultado.puntaje_final", -1)
                    .limit(1000))
    t1 = time.time()
    print(f"MongoDB Q2 retorno {len(m_res_q2)} registros en {t1 - t0:.2f}s")
    if m_res_q2:
        print("Top 1 puntaje:", m_res_q2[0]["resultado"]["puntaje_final"])

    # 2. Postgres
    p_conn = psycopg2.connect(
        host="127.0.0.1",
        port=PG_PORT,
        dbname="lethics_bench",
        user="lethics_admin",
        password="lethics_bench_2026"
    )
    p_cur = p_conn.cursor()
    
    print("\n--- PostgreSQL Q1 ---")
    t0 = time.time()
    p_cur.execute(POSTGRES_Q1_SQL)
    p_res_q1 = p_cur.fetchall()
    t1 = time.time()
    print(f"PostgreSQL Q1 retorno {len(p_res_q1)} grupos en {t1 - t0:.2f}s")
    if p_res_q1:
        print("Ejemplo grupo Q1:", p_res_q1[0])

    print("\n--- PostgreSQL Q2 ---")
    t0 = time.time()
    p_cur.execute(POSTGRES_Q2_SQL)
    p_res_q2 = p_cur.fetchall()
    t1 = time.time()
    print(f"PostgreSQL Q2 retorno {len(p_res_q2)} registros en {t1 - t0:.2f}s")
    if p_res_q2:
        print("Top 1 puntaje:", p_res_q2[0][1])

    p_cur.close()
    p_conn.close()
    print("\n=== Todas las consultas ejecutaron exitosamente ===")

if __name__ == "__main__":
    test_queries()
