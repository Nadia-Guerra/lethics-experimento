import urllib.request
import urllib.parse
import json
import subprocess

def query_prometheus(query):
    try:
        url = f"http://localhost:9090/api/v1/query?query={urllib.parse.quote(query)}"
        req = urllib.request.urlopen(url, timeout=3)
        data = json.loads(req.read().decode('utf-8'))
        return data.get('data', {}).get('result', [])
    except Exception as e:
        print(f"Error consultando Prometheus ({query}): {e}")
        return []

def get_container_stats_docker(container_name):
    try:
        cmd = ["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container_name]
        out = subprocess.check_output(cmd, text=True, timeout=5).strip()
        # Ejemplo: "1.23GiB / 4GiB" -> 1.23 * 1024 MB
        usage_str = out.split('/')[0].strip()
        if 'GiB' in usage_str:
            mb = float(usage_str.replace('GiB', '').strip()) * 1024.0
        elif 'MiB' in usage_str:
            mb = float(usage_str.replace('MiB', '').strip())
        elif 'KiB' in usage_str:
            mb = float(usage_str.replace('KiB', '').strip()) / 1024.0
        elif 'B' in usage_str:
            mb = float(usage_str.replace('B', '').strip()) / (1024.0 * 1024.0)
        else:
            mb = 0.0
        return round(mb, 2)
    except Exception as e:
        print(f"Error docker stats: {e}")
        return 0.0

if __name__ == "__main__":
    print("--- Test Prometheus ---")
    rss = query_prometheus('container_memory_rss')
    print(f"Series de RSS encontradas: {len(rss)}")
    
    print("\n--- Test Docker Stats ---")
    m_mem = get_container_stats_docker("lethics-mongo")
    p_mem = get_container_stats_docker("lethics-postgres")
    print(f"MongoDB RSS (Docker Stats): {m_mem} MB")
    print(f"PostgreSQL RSS (Docker Stats): {p_mem} MB")

