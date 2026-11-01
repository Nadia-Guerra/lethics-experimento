import json
import uuid
import random
from datetime import datetime, timedelta

def generate_lethics_dataset(filename, num_records):
    temas = ["Etica", "Propiedad Intelectual", "Privacidad", "Seguridad", "Leyes Laborales"]
    estados = ["aprobado", "reprobado"]
    tipos_usuario = ["estudiante", "profesional", "casual"]
    
    start_date = datetime(2025, 1, 1)
    
    with open(filename, 'w', encoding='utf-8') as f:
        for i in range(num_records):
            record_date = start_date + timedelta(days=random.randint(0, 600))
            is_aprobado = random.choice(estados)
            puntaje = round(random.uniform(70, 100), 4) if is_aprobado == "aprobado" else round(random.uniform(0, 69.9), 4)
            
            respuestas = []
            for _ in range(random.randint(2, 4)): # ~3 respuestas por intento
                respuestas.append({
                    "id_pregunta": str(uuid.uuid4()),
                    "tema": random.choice(temas),
                    "modulo": random.randint(1, 5),
                    "peso": random.randint(1, 5),
                    "tiempo_respuesta_seg": round(random.uniform(10, 120), 2),
                    "penalizacion_pct": round(random.uniform(0, 10), 2),
                    "bonificacion": {"tipo": "racha", "pct": round(random.uniform(0, 5), 2)},
                    "id_opcion_elegida": random.choice(["a", "b", "c", "d"]),
                    "es_correcta": random.choice([True, False])
                })
            
            doc = {
                "intento_id": str(uuid.uuid4()),
                "fecha": record_date.isoformat() + "Z",
                "usuario": {
                    "id": str(uuid.uuid4()),
                    "tipo_usuario": random.choice(tipos_usuario),
                    "segmento": "universitario",
                    "geo": {
                        "pais": random.choice(["Mexico", "Colombia", "España", "Argentina", "Chile"]),
                        "estado": "Chiapas",
                        "ciudad": "Tuxtla Gutierrez",
                        "cp": "29000",
                        "coordenadas": {"lat": 16.75, "lon": -93.11}
                    }
                },
                "respuestas": respuestas,
                "resultado": {
                    "modalidad": random.choice(["cuestionario", "examen_final"]),
                    "estado": is_aprobado,
                    "id_calificacion": str(uuid.uuid4()),
                    "latencia_calificacion_ms": random.randint(100, 500),
                    "totales": {
                        "aciertos": random.randint(5, 15),
                        "total_preguntas": 15,
                        "porcentaje": float(puntaje)
                    },
                    "puntaje_final": float(puntaje)
                },
                "metadata": {
                    "canal": "web",
                    "user_agent": "Mozilla/5.0",
                    "id_sesion": str(uuid.uuid4()),
                    "banderas": ["first_attempt"]
                }
            }
            f.write(json.dumps(doc) + '\n')

if __name__ == "__main__":
    import os
    os.makedirs('./data', exist_ok=True)
    print("Generando 500,000 registros de intentos. Esto puede tardar unos minutos...")
    generate_lethics_dataset('./data/dataset_intentos.json', 500000)
    print("Dataset generado exitosamente en ./data/dataset_intentos.json")