# Reglas del Agente de IA

- **Contexto Base:** Antes de iniciar cualquier tarea o responder, lee silenciosamente `context/01_explicacion_corta.md` y `context/04_plan_de_ejecucion.md`.
- **Ámbito:** Trabaja SOLO dentro del directorio de este experimento.
- **Infraestructura:** Asume que todo corre bajo Docker sobre Linux (cgroups v2).
- **Inmutabilidad:** El esquema CSV del playbook es inmutable: no renombres, alteres ni agregues nuevas columnas bajo ninguna circunstancia.
- **Secuencialidad:** Sigue `04_plan_de_ejecucion.md` estrictamente. No avances al siguiente paso sin que el actual haya cumplido su criterio de terminado.
- **Puntos de Control:** Cuando llegues a una tarea marcada como Punto de Control (PC-1 a PC-5), detén la ejecución, muestra la salida solicitada y pide confirmación explícita al usuario para continuar.
- **Validación Temprana:** Antes de ejecutar la matriz completa, es obligatorio ejecutar la Celda Piloto y validar la escritura del CSV.
- **Gestión de Dudas:** Si algún requisito técnico entra en conflicto o es ambiguo, documéntalo en `context/05_decisiones_y_supuestos.md` y pregunta al usuario antes de inventar un comportamiento.
- **Cierre de Tarea:** Después de completar cada paso de ejecución, entrega un resumen conciso de lo logrado y del estado actual.