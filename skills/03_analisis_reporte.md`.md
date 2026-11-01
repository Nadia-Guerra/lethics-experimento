---
name: analisis-reporte
description: Extracción de planes de ejecución, consolidación del CSV en tablas y gráficas automatizadas para las 7 secciones del reporte.
---

# Skill 3: Análisis y Reporte

## 1. Planes de Ejecución
Extraer el comportamiento interno de los motores para Q1 y variantes de Q2.
```bash
python scripts/extract_query_plans.py --output ./reports/plans/