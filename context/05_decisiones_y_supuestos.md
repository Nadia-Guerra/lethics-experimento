# Decisiones y supuestos del experimento

> Registro de cada decisión tomada ante una ambigüedad del playbook o al aplicarlo a Lethics.
> Regla general: (1) lectura más literal del playbook, (2) lo que no altere el CSV ni la comparabilidad, (3) lo más barato de cambiar después.
> El agente debe **agregar** aquí cualquier decisión nueva con el formato de la última sección.

---

## Decisiones

| ID | Tema | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|---|
| D-01 | Base del experimento | El experimento se hace sobre **Lethics** (no es un supuesto: así lo definió la estudiante). Colección de trabajo: `intentos`. | Es la colección de mayor volumen (usuarios × evaluaciones × intentos), la más leída en historial (P19) y tiene un arreglo anidado (`respuestas`), fecha, estado y valores numéricos. | `progreso_usuario` (un documento por usuario-curso, arreglo de ~30 lecciones), `usuarios` (sin arreglo anidado), `cursos` y `lecciones` (catálogo pequeño). |
| D-02 | Forma del dataset | Se respeta la forma del playbook: 3 niveles de anidamiento y ≈3 `respuestas` por intento. | Cuenta como condición del experimento y mantiene la carga comparable con el resto de equipos y con el CSV compartido. | Usar 10 respuestas por intento (más realista para Lethics): triplicaría las filas de Q1 y alejaría el experimento del playbook. Se declara la diferencia en el reporte. |
| D-03 | Queries | Se mantienen **Q1 y Q2 del playbook**, adaptadas a Lethics (Anexo A de `03`). El documento de patrones de acceso de la consulta se usa como descripción conceptual. | Los apuntes piden dos tipos de consulta (CPU y RAM) y el playbook las define por separado. El documento de patrones describe una sola consulta que combina filtro, agrupación, orden y Top N. | Ejecutar esa consulta única: cambiaría la matriz de 36 celdas y la lectura de M1 y M2. |
| D-04 | Nombres de campos | Se usan los nombres en español de Lethics (`fecha`, `respuestas`, `usuario`, etc.). | El experimento se basa en el proyecto y los nombres no afectan al CSV. La **forma** de las queries se conserva. | Mantener nombres en inglés del playbook (`items`, `price`). |
| D-05 | Campos sintéticos | Se agregan campos que Lethics no tiene (país, tema, peso, tiempo de respuesta, `puntaje_final`) y se marcan como sintéticos. `puntaje_final` tiene alta cardinalidad. Las fechas se distribuyen para que el filtro de Q2 seleccione entre 40 % y 60 % de los documentos. | Q1 necesita campos numéricos y geográficos, y Q2 un valor para ordenar. El `porcentaje` real tiene pocos valores distintos y produciría empates masivos en el Top-1000. Una selectividad fija hace comparable la carga. | Usar solo campos reales: Q1 y Q2 no tendrían cálculo ni orden significativos. |
| D-06 | Variantes de Q2 | Son **celdas adicionales**: 54 celdas, 162 repeticiones, ≈19 h. En `query_id`: `Q2_DISK_OFF`, `Q2_DISK_ON` (MongoDB), `Q2_WM4MB`, `Q2_WM64MB` (PostgreSQL). | El playbook exige reportar ambas variantes (M2). Sin identificarlas en el CSV no se podrían distinguir sus filas. | Una sola variante por motor: deja M2 sin contraste. Codificar la variante en otra columna: rompe el esquema inmutable. |
| D-07 | `oom_killed` | Se refleja como `status = oom`. | El CSV no tiene columna `oom_killed`; el esquema no se puede cambiar. | Agregar columna: viola el esquema. |
| D-08 | Swap | `memswap_limit` igual a `mem_limit` (sin swap), verificado con `docker inspect`. `mem_swappiness: 0` se declara pero no se depende de él. | En cgroups v2 el control efectivo del swap es otro y `mem_swappiness` puede no aplicar. La intención del playbook es que no haya swap. | Confiar solo en `mem_swappiness`. |
| D-09 | M3 (huella por 1 000 documentos) | Se calcula a **concurrencia 1**: RSS máximo y CPU consumida entre documentos examinados (en miles). La CPU consumida y los documentos examinados van en `results/extra_metrics.csv`. | El playbook no define el denominador ni una métrica de CPU consumida. A concurrencia 1 la atribución es limpia. Las métricas adicionales no son condición de diseño y no tocan el CSV. | Calcularlo con todas las concurrencias: mezcla efectos de contención. |
| D-10 | Tipo de `fecha` | Cadena ISO-8601 en UTC en ambos motores. En PostgreSQL, índice B-Tree sobre una función envoltorio IMMUTABLE que castea a `timestamptz`, y Q2 usa la misma expresión. | Los filtros del playbook comparan contra una cadena ISO. El cast directo de texto a `timestamptz` normalmente no es IMMUTABLE y no se puede indexar. | Guardar `Date` en Mongo y texto en PostgreSQL: semánticas distintas. |
| D-11 | Resumen de repeticiones | Mediana de las 3 repeticiones, más rango min–max. | El playbook pregunta "media o mediana" sin imponer una; con 3 datos la mediana resiste un valor atípico. | Media: se distorsiona con un valor extremo. |
| D-12 | Flush de caché | `drop_caches` se ejecuta en el kernel donde corre el daemon de Docker (host Linux o VM WSL2), antes de cada repetición, desde el script de orquestación. | Requiere privilegios y afecta al kernel, no a un contenedor normal. | Ejecutarlo dentro del contenedor: no limpia la caché del host. |
| D-13 | Versiones y configuración | Versiones exactas fijadas (sin `latest`) y registradas. Configuración de motores por defecto salvo lo que fija el playbook (`work_mem`, `allowDiskUse`); la configuración efectiva se registra por perfil. | "Latest-stable" cambia con el tiempo y rompe la reproducibilidad. Afinar un motor y no el otro sesgaría la comparación. | Afinar cachés por perfil: no lo pide el playbook. |
| D-14 | Corrida larga | El orquestador omite celdas ya registradas y escribe filas con `error` u `oom` cuando falla. | La matriz dura horas y puede interrumpirse (apunte: "si mi lap explota, que quede trabajando"). | Reiniciar desde cero ante cada fallo. |
| D-15 | Ejecución de la carga | Un motor a la vez; el runner corre fuera del límite del perfil, es multiproceso (o k6) y trabaja en lazo cerrado. | Evita que el motor inactivo compita por recursos y que el cliente sea el cuello de botella. El lazo cerrado mantiene N consultas simultáneas. | Mantener ambos motores encendidos; hilos de Python con 50 workers. |
| D-16 | IDs de requisitos | Prefijo `EXP-` (`EXP-RF-xx`, `EXP-RNF-xx`). | Lethics ya usa RF/RN en su documento de requerimientos. | Reutilizar numeración RF/RN. |

---

## Observaciones técnicas que pueden afectar los resultados

- **Q2 puede no producir spill** aunque se reduzca `work_mem` o se desactive `allowDiskUse`, porque con `LIMIT` 1000 los motores suelen usar un ordenamiento Top-N que retiene pocas filas. Si pasa, es un resultado válido de M2 y se respalda con el plan de ejecución. No se modifica la query para forzar spill.
- **Hay que registrar las cachés efectivas** de cada motor por perfil, porque pueden autoajustarse al límite de memoria del contenedor.

---

## Formato para decisiones nuevas

```
| D-xx | Tema | Decisión | Por qué | Alternativa descartada |
```

Cuando una decisión cambie un requisito de `03_requisitos_RF_RNF.md`, anotar también qué requisito afecta.
