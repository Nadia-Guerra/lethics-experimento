"""
Definición de consultas Q1 y Q2 para MongoDB y PostgreSQL
Experimento Lethics (EXP-RF-09, EXP-RF-10, D-03, D-10)
"""

# ==============================================================================
# Q1 (Satura CPU):
# Unwind respuestas, filtro tiempo_respuesta_seg > 50,
# subtotal = peso * tiempo_respuesta_seg,
# agrupar por usuario.geo.pais y respuestas.tema
# ==============================================================================

MONGO_Q1_PIPELINE = [
    { "$unwind": "$respuestas" },
    { "$match": { "respuestas.tiempo_respuesta_seg": { "$gt": 50 } } },
    {
        "$project": {
            "pais": "$usuario.geo.pais",
            "tema": "$respuestas.tema",
            "subtotal": { "$multiply": ["$respuestas.peso", "$respuestas.tiempo_respuesta_seg"] }
        }
    },
    {
        "$group": {
            "_id": { "pais": "$pais", "tema": "$tema" },
            "suma_subtotal": { "$sum": "$subtotal" },
            "promedio_subtotal": { "$avg": "$subtotal" },
            "conteo": { "$sum": 1 }
        }
    }
]

POSTGRES_Q1_SQL = """
SELECT 
    data->'usuario'->'geo'->>'pais' AS pais,
    r->>'tema' AS tema,
    SUM((r->>'peso')::numeric * (r->>'tiempo_respuesta_seg')::numeric) AS suma_subtotal,
    AVG((r->>'peso')::numeric * (r->>'tiempo_respuesta_seg')::numeric) AS promedio_subtotal,
    COUNT(*) AS conteo
FROM intentos,
     jsonb_array_elements(data->'respuestas') AS r
WHERE (r->>'tiempo_respuesta_seg')::numeric > 50
GROUP BY data->'usuario'->'geo'->>'pais', r->>'tema';
"""

# ==============================================================================
# Q2 (Estresa RAM):
# Filtro estado = "aprobado" y fecha >= "2026-01-01",
# ordenar desc por resultado.puntaje_final, Top 1000
# ==============================================================================

MONGO_Q2_FILTER = {
    "resultado.estado": "aprobado",
    "fecha": { "$gte": "2026-01-01T00:00:00Z" }
}

POSTGRES_Q2_SQL = """
SELECT 
    id, 
    (data->'resultado'->>'puntaje_final')::numeric AS puntaje_final
FROM intentos
WHERE data->'resultado'->>'estado' = 'aprobado'
  AND get_fecha(data) >= '2026-01-01T00:00:00Z'
ORDER BY (data->'resultado'->>'puntaje_final')::numeric DESC
LIMIT 1000;
"""

