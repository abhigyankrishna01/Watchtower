import psutil

def get_metrics():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent

    return {
        "cpu_usage": cpu,
        "memory_usage": memory
    }
