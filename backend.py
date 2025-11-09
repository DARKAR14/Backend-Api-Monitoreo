from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import pandas as pd
import numpy as np
import random
from datetime import datetime
from typing import Optional

app = FastAPI(title="API Monitoring Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "api_monitoring.db"

ENDPOINTS_LIST = [
    '/api/usuarios/login',
    '/api/usuarios/registro',
    '/api/productos/listar',
    '/api/productos/buscar',
    '/api/pedidos/crear',
    '/api/pedidos/consultar',
    '/api/pagos/procesar',
    '/api/inventario/actualizar',
    '/api/reportes/generar',
    '/api/dashboard/estadisticas'
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generar_datos_aleatorios(endpoint: Optional[str] = None):
    """Genera un request aleatorio con datos realistas"""
    if endpoint is None:
        endpoint = random.choice(ENDPOINTS_LIST)
    
    # Códigos HTTP con probabilidades
    codigos = {200: 0.70, 201: 0.10, 400: 0.05, 404: 0.05, 500: 0.05, 503: 0.05}
    codigo_http = random.choices(list(codigos.keys()), weights=list(codigos.values()))[0]
    
    # Hora actual
    ahora = datetime.now()
    hora_dia = ahora.hour
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_semana = dias[ahora.weekday()]
    es_hora_pico = 1 if (9 <= hora_dia <= 12 or 14 <= hora_dia <= 17) else 0
    
    # Generar tiempo de respuesta realista
    if codigo_http in [200, 201]:
        tiempo_base = np.random.normal(150, 50)
    elif codigo_http in [400, 404]:
        tiempo_base = np.random.normal(80, 30)
    else:
        tiempo_base = np.random.normal(800, 300)
    
    if es_hora_pico:
        tiempo_base *= random.uniform(1.2, 1.5)
    
    tiempo_respuesta = max(10, round(tiempo_base, 2))
    
    return {
        'fecha_hora': ahora.strftime('%Y-%m-%d %H:%M:%S'),
        'endpoint': endpoint,
        'tiempo_respuesta_ms': tiempo_respuesta,
        'codigo_http': codigo_http,
        'hora_dia': hora_dia,
        'dia_semana': dia_semana,
        'es_hora_pico': es_hora_pico
    }

@app.get("/")
def root():
    return {
        "message": "API Monitoring Dashboard Backend - EN VIVO",
        "version": "2.0.0",
        "features": ["Stats en tiempo real", "Ping endpoints", "Datos aleatorios"],
        "endpoints": {
            "ping": "/api/ping (POST o GET con ?endpoint=...)",
            "stats": "/api/stats",
            "data": "/api/data",
            "frequencies": "/api/frequencies/*",
            "probabilities": "/api/probabilities",
            "charts": "/api/chart-data/*"
        }
    }

@app.post("/api/ping")
@app.get("/api/ping")
def ping_endpoint(endpoint: Optional[str] = None):
    """Simula un ping a un endpoint y guarda el resultado en la DB"""
    from fastapi.responses import JSONResponse
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Generar datos aleatorios
    data = generar_datos_aleatorios(endpoint)
    
    # Insertar en la base de datos
    cursor.execute('''
        INSERT INTO requests 
        (fecha_hora, endpoint, tiempo_respuesta_ms, codigo_http, hora_dia, dia_semana, es_hora_pico)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['fecha_hora'],
        data['endpoint'],
        data['tiempo_respuesta_ms'],
        data['codigo_http'],
        data['hora_dia'],
        data['dia_semana'],
        data['es_hora_pico']
    ))
    
    conn.commit()
    conn.close()
    
    # Mensajes según el código HTTP
    messages = {
        200: "OK - Request procesado exitosamente",
        201: "Created - Recurso creado exitosamente",
        400: "Bad Request - Solicitud incorrecta",
        404: "Not Found - Endpoint no encontrado",
        500: "Internal Server Error - Error interno del servidor",
        503: "Service Unavailable - Servicio no disponible"
    }
    
    response_data = {
        "status": "success" if data['codigo_http'] < 400 else "error",
        "message": messages.get(data['codigo_http'], "Unknown status"),
        "endpoint": data['endpoint'],
        "data": data,
        "response_time_ms": data['tiempo_respuesta_ms'],
        "http_code": data['codigo_http']
    }
    
    # Log en consola con colores
    status_emoji = "" if data['codigo_http'] < 400 else ""
    print(f"\n{status_emoji} PING SIMULADO:")
    print(f"   └─ Endpoint: {data['endpoint']}")
    print(f"   └─ HTTP {data['codigo_http']}: {messages.get(data['codigo_http'], 'Unknown')}")
    print(f"   └─ Tiempo: {data['tiempo_respuesta_ms']} ms")
    print(f"   └─ Hora: {data['fecha_hora']}\n")
    
    # Retornar con el código HTTP simulado
    return JSONResponse(
        status_code=data['codigo_http'],
        content=response_data
    )

@app.get("/api/endpoints-list")
def get_endpoints_list():
    """Lista de endpoints disponibles para hacer ping"""
    return {
        "endpoints": ENDPOINTS_LIST,
        "total": len(ENDPOINTS_LIST)
    }

@app.get("/api/stats")
def get_statistics():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return {"error": "No hay datos disponibles"}
    
    tiempos = df['tiempo_respuesta_ms']
    
    return {
        "total_requests": len(df),
        "tendencia_central": {
            "media": round(tiempos.mean(), 2),
            "mediana": round(tiempos.median(), 2),
            "moda": round(tiempos.mode()[0], 2) if len(tiempos.mode()) > 0 else None
        },
        "dispersion": {
            "desviacion_estandar": round(tiempos.std(), 2),
            "varianza": round(tiempos.var(), 2),
            "rango": round(tiempos.max() - tiempos.min(), 2),
            "coef_variacion": round((tiempos.std() / tiempos.mean()) * 100, 2)
        },
        "posicion": {
            "minimo": round(tiempos.min(), 2),
            "q1": round(tiempos.quantile(0.25), 2),
            "q2": round(tiempos.quantile(0.50), 2),
            "q3": round(tiempos.quantile(0.75), 2),
            "maximo": round(tiempos.max(), 2),
            "p90": round(tiempos.quantile(0.90), 2),
            "p95": round(tiempos.quantile(0.95), 2),
            "p99": round(tiempos.quantile(0.99), 2)
        },
        "errores": {
            "total_errores": int(df[df['codigo_http'] >= 400].shape[0]),
            "porcentaje_errores": round((df[df['codigo_http'] >= 400].shape[0] / len(df)) * 100, 2),
            "total_exitos": int(df[df['codigo_http'] < 400].shape[0]),
            "porcentaje_exitos": round((df[df['codigo_http'] < 400].shape[0] / len(df)) * 100, 2)
        }
    }

@app.get("/api/data")
def get_all_data(limit: int = 50):
    conn = get_db()
    query = f"SELECT * FROM requests ORDER BY id DESC LIMIT {limit}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.to_dict(orient='records')

@app.get("/api/frequencies/codigo-http")
def get_codigo_http_frequencies():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return []
    
    freq = df['codigo_http'].value_counts().sort_index()
    total = len(df)
    
    result = []
    acum = 0
    for codigo, cantidad in freq.items():
        acum += cantidad
        result.append({
            "codigo": int(codigo),
            "frecuencia_absoluta": int(cantidad),
            "frecuencia_relativa": round(cantidad / total, 4),
            "frecuencia_porcentual": round((cantidad / total) * 100, 2),
            "frecuencia_acumulada": int(acum)
        })
    
    return result

@app.get("/api/frequencies/endpoints")
def get_endpoint_frequencies():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return []
    
    freq = df['endpoint'].value_counts()
    total = len(df)
    
    result = []
    for endpoint, cantidad in freq.items():
        result.append({
            "endpoint": endpoint,
            "frecuencia": int(cantidad),
            "porcentaje": round((cantidad / total) * 100, 2)
        })
    
    return result

@app.get("/api/chart-data/codigo-http")
def get_codigo_http_chart():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return {"labels": [], "values": []}
    
    freq = df['codigo_http'].value_counts().sort_index()
    
    return {
        "labels": [str(x) for x in freq.index.tolist()],
        "values": freq.values.tolist()
    }

@app.get("/api/chart-data/endpoints")
def get_endpoints_chart():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return {"labels": [], "values": []}
    
    freq = df['endpoint'].value_counts().head(10)
    
    return {
        "labels": [x.split('/')[-1] for x in freq.index.tolist()],
        "values": freq.values.tolist()
    }

@app.get("/api/chart-data/histograma")
def get_histograma_chart():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return {"labels": [], "values": []}
    
    tiempos = df['tiempo_respuesta_ms']
    n = len(tiempos)
    k = int(1 + 3.322 * np.log10(n))
    k = min(max(k, 5), 10)
    
    intervalos = pd.cut(tiempos, bins=k, precision=0)
    freq = intervalos.value_counts().sort_index()
    
    return {
        "labels": [f"{int(i.left)}-{int(i.right)}" for i in freq.index],
        "values": freq.values.tolist()
    }

@app.get("/api/chart-data/tiempo-real")
def get_tiempo_real_chart():
    """Últimos 20 requests para gráfico de línea en tiempo real"""
    conn = get_db()
    query = "SELECT fecha_hora, tiempo_respuesta_ms FROM requests ORDER BY id DESC LIMIT 20"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) == 0:
        return {"labels": [], "values": []}
    
    df = df.iloc[::-1]  # Invertir para orden cronológico
    
    return {
        "labels": [f"#{i+1}" for i in range(len(df))],
        "values": df['tiempo_respuesta_ms'].tolist()
    }

@app.get("/api/probabilities")
def get_probabilities():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM requests", conn)
    conn.close()
    
    if len(df) == 0:
        return {"simples": {}, "condicionales": {}}
    
    total = len(df)
    errores = df[df['codigo_http'] >= 400]
    hora_pico = df[df['es_hora_pico'] == 1]
    hora_normal = df[df['es_hora_pico'] == 0]
    
    return {
        "simples": {
            "p_error": round(len(errores) / total, 4),
            "p_exito": round(len(df[df['codigo_http'] < 400]) / total, 4),
            "p_tiempo_mayor_300": round(len(df[df['tiempo_respuesta_ms'] > 300]) / total, 4),
            "p_tiempo_mayor_500": round(len(df[df['tiempo_respuesta_ms'] > 500]) / total, 4)
        },
        "condicionales": {
            "p_error_dado_hora_pico": round(
                len(errores[errores['es_hora_pico'] == 1]) / len(hora_pico), 4
            ) if len(hora_pico) > 0 else 0,
            "p_error_dado_hora_normal": round(
                len(errores[errores['es_hora_pico'] == 0]) / len(hora_normal), 4
            ) if len(hora_normal) > 0 else 0
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print(" BACKEND API MONITORING - EN VIVO")
    print("="*60)
    print("\n Servidor: http://localhost:8000")
    print(" Docs: http://localhost:8000/docs")
    print(" Ping endpoint: http://localhost:8000/api/ping")
    print("\nListo para conectar con el frontend React!\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)