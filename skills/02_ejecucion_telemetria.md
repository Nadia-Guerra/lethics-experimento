---
name: ejecucion-telemetria
description: Procedimientos para ejecutar el ciclo de vida del benchmark (flush, warmup, medición), inyectar carga concurrente y registrar telemetría en el CSV inmutable.
---

# Skill 2: Ejecución y Telemetría

## 1. Ciclo de Vida de Celda (Flush y Ejecución)
Antes de cada medición, el host debe limpiar cachés.
```bash
# Requiere permisos en el host/VM Linux
sync; echo 3 > /proc/sys/vm/drop_caches