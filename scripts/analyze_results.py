import pandas as pd
import matplotlib.pyplot as plt
import os

# 1. Configurar directorios
CSV_PATH = 'results/benchmark_results.csv'
OUTPUT_DIR = 'results/graphs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Cargando resultados desde {CSV_PATH}...")
df = pd.read_csv(CSV_PATH)

# Promediar las repeticiones (run_number) para suavizar la varianza
df_agg = df.groupby(['engine', 'profile', 'query_id', 'concurrency']).mean(numeric_only=True).reset_index()

plt.style.use('ggplot')

# --- GRÁFICA 1: Throughput (QPS) Comparativo ---
print("Generando Gráfica 1: Throughput...")
plt.figure(figsize=(10, 6))
# Filtramos consulta de lectura (Q1) a máxima concurrencia (50)
q1_data = df_agg[(df_agg['query_id'] == 'Q1') & (df_agg['concurrency'] == 50)]
if not q1_data.empty:
    q1_pivot = q1_data.pivot(index='profile', columns='engine', values='throughput_qps')
    q1_pivot.plot(kind='bar', color=['#4CAF50', '#2196F3'], ax=plt.gca())
    plt.title('Throughput Máximo (QPS) - Consulta Q1 (50 Clientes)')
    plt.ylabel('Consultas por Segundo (QPS)')
    plt.xlabel('Perfil de Contención (A=Base, B=Medio, C=Severo)')
    plt.xticks(rotation=0)
    plt.legend(title='Motor')
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/01_throughput_comparativo.png')
plt.close()

# --- GRÁFICA 2: Degradación de Latencia P95 ---
print("Generando Gráfica 2: Latencia P95...")
plt.figure(figsize=(10, 6))
# Analizamos la consulta de agregación (Q2_DISK_ON) en el perfil más restrictivo (C)
q2_data = df_agg[(df_agg['query_id'] == 'Q2_DISK_ON') & (df_agg['profile'] == 'C')]
if not q2_data.empty:
    for engine in ['mongo', 'postgres']:
        subset = q2_data[q2_data['engine'] == engine].sort_values('concurrency')
        plt.plot(subset['concurrency'], subset['latency_p95_ms'], marker='o', linewidth=2, label=engine.capitalize())
    
    plt.title('Degradación de Latencia P95 vs Concurrencia (Agregaciones en Perfil C)')
    plt.ylabel('Latencia P95 (ms)')
    plt.xlabel('Concurrencia (Clientes Simultáneos)')
    plt.legend(title='Motor')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/02_latencia_p95_stress.png')
plt.close()

# --- GRÁFICA 3: Impacto del Disk Spill ---
print("Generando Gráfica 3: Impacto de Volcado a Disco...")
plt.figure(figsize=(10, 6))
# Comparamos ejecuciones donde hubo vs no hubo volcado a disco
q2_raw = df[df['query_id'].str.contains('Q2')].copy()
spill_agg = q2_raw.groupby(['engine', 'disk_spill'])['latency_p95_ms'].mean().unstack()

if not spill_agg.empty:
    spill_agg.plot(kind='bar', color=['#9E9E9E', '#F44336'], ax=plt.gca())
    plt.title('Penalización de Latencia por Vuelco a Disco (Spill)')
    plt.ylabel('Latencia Media P95 (ms)')
    plt.xlabel('Motor de Base de Datos')
    plt.legend(title='Disk Spill (Volcado)', labels=['Sin volcado (RAM)', 'Con volcado (Disco)'])
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/03_impacto_disk_spill.png')
plt.close()

print(f"¡Análisis completo! Revisa la carpeta '{OUTPUT_DIR}' para ver las gráficas generadas.")