Descripción de la Consulta Principal - Proyecto LETHICS

Este documento define el comportamiento y los patrones de acceso de la consulta principal seleccionada para el experimento de rendimiento (PostgreSQL/JSONB vs MongoDB/BSON). Esta descripción sirve como contexto para los agentes de IA encargados de la generación de scripts y ejecución de pruebas.

¿Qué hace la consulta a grandes rasgos?

A nivel de negocio, la consulta realiza un historial de promedios de calificaciones o incidencias agrupadas por módulo. En otras palabras, toma el universo de registros, filtra la información relevante por periodos o estados, y procesa los datos para obtener una vista consolidada que muestra el comportamiento histórico y el promedio de rendimiento o reportes de cada módulo del sistema LETHICS.

Desglose de Patrones de Acceso

La consulta está diseñada intencionalmente para disparar patrones de acceso específicos que pongan a prueba los recursos del sistema:

1. Patrón de Búsqueda y Filtrado Selectivo (Lectura y Escaneo)

Acción: La consulta inicia filtrando los registros basándose en múltiples condiciones (por ejemplo, un rango de fechas, estado activo y coincidencia con identificadores de módulos específicos dentro de la estructura JSON/BSON).

Impacto esperado: Evaluará el uso de índices de alto nivel. Si el motor no utiliza el índice correctamente, forzará un escaneo secuencial penalizando fuertemente los tiempos de lectura.

2. Patrón de Agregación y Transformación (Carga intensiva en CPU)

Acción: Una vez filtrados los datos por módulo, la consulta agrupa los registros y calcula operaciones matemáticas de resumen (el promedio histórico de las métricas o puntajes registrados en cada módulo).

Impacto esperado: Este es el núcleo del estrés para el CPU. Los motores de bases de datos deberán procesar y cruzar los datos filtrados en memoria para generar las nuevas métricas calculadas al vuelo.

3. Patrón de Ordenamiento (Sorting) y Límite (Carga intensiva en RAM)

Acción: Los promedios obtenidos por cada módulo se ordenan de manera descendente (del promedio más alto al más bajo) y se aplica un límite para extraer únicamente el "Top" de módulos con mejor o peor desempeño histórico.

Impacto esperado: Este patrón estresará directamente la memoria RAM al requerir un ordenamiento en memoria (in-memory sort) de los resultados calculados antes de entregar el tope solicitado.

4. Patrón de Proyección de Datos (Extracción JSON/BSON)

Acción: La consulta extrae y mapea campos específicos anidados dentro del documento JSON/BSON (como el nombre del módulo y sus calificaciones o valores de reporte) para estructurar la respuesta final del promedio.

Impacto esperado: Evalúa la eficiencia del motor para parsear fragmentos específicos de documentos complejos sin deserializar información innecesaria.