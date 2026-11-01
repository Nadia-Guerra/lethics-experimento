---
name: preparacion-entorno
description: Procedimientos para configurar Docker con perfiles de contención, generar 500k registros sintéticos basados en Lethics y cargar los datos en MongoDB y PostgreSQL.
---

# Skill 1: Preparación del Entorno y Datos

## 1. Configuración de Perfiles Docker
Levantar la infraestructura parametrizada limitando CPU y Memoria (cgroups v2).
```bash
# Ejemplo: Perfil B (Medio)
export BENCHMARK_CPUS=2.0
export BENCHMARK_MEMORY=2048m
export BENCHMARK_MEM_SWAP=2048m
docker compose up -d