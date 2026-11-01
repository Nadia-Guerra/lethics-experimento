# Plan de Ejecución: Experimento Lethics

Este plan dicta el orden estricto de las tareas. El agente no debe avanzar al siguiente paso sin cumplir el criterio de salida del actual.

**Paso 0: Estructura y Dependencias**
- **Entrada:** Contexto actual.
- **Acción:** Crear la estructura de carpetas (`scripts`, `data`, `results/evidence`, `reports/plans`) y `requirements.txt`.
- **Salida:** Carpetas creadas y librerías instaladas.

**Paso 1: Entorno Docker (Usa Skill 1)**
- **Entrada:** `03_requisitos_RF_RNF.md`.
- **Acción:** Crear `docker-compose.yml` parametrizado (Mongo, Postgres, Prometheus, cAdvisor, Node Exporter).
- **Salida:** Contenedores UP.
- **Punto de Control (PC-1):** Detenerse. Mostrar al usuario el límite real de memoria/CPU aplicado a la BD. Esperar confirmación.

**Paso 2: Generador y Esquema (Usa Skill 1)**
- **Entrada:** `03_requisitos_RF_RNF.md` (Anexo A).
- **Acción:** Programar `synthetic_data_generator.py` para la colección `intentos`.
- **Salida:** Script de Python funcional.
- **Punto de Control (PC-2):** Detenerse. Generar solo 5 documentos, mostrarlos en consola y esperar aprobación del esquema.

**Paso 3: Carga y Verificación (Usa Skill 1)**
- **Entrada:** Generador validado.
- **Acción:** Generar los 500,000 registros, crear script de carga e índices, y ejecutar inserción masiva.
- **Salida:** Bases de datos pobladas.
- **Punto de Control (PC-3):** Detenerse. Mostrar conteo de ambas bases (debe ser 500,000). Esperar confirmación.

**Paso 4: Celda Piloto (Usa Skill 2)**
- **Entrada:** Datos cargados, scripts de consultas (Q1 y Q2).
- **Acción:** Programar `benchmark_runner.py` e inyectar 1 concurrencia en perfil A.
- **Salida:** `benchmark_results.csv` con su primera fila.
- **Punto de Control (PC-4):** Detenerse. Mostrar el CSV y validar que contiene exactamente las 14 columnas. Mostrar estimación de tiempo total. Esperar confirmación.

**Paso 5: Matriz Completa (Usa Skill 2)**
- **Entrada:** Runner validado.
- **Acción:** Ejecutar script bash/powershell que itere por las 54 celdas × 3 repeticiones limpiando caché.
- **Salida:** CSV final completo, logs de spill/OOM capturados.
- **Punto de Control (PC-5):** Notificar finalización de estrés de infraestructura.

**Paso 6: Reporte (Usa Skill 3)**
- **Entrada:** CSV y planes de ejecución extraídos.
- **Acción:** Generar gráficas y el markdown final con las 7 secciones.
- **Salida:** `reporte_final.md` listo para entregar.