"""Prueba de exportación a Excel y de la API REST sobre la base de la prueba de punta a punta."""

import base64
import datetime
import json
import sys
import threading
import time
import urllib.error
import urllib.request

from openpyxl import load_workbook

from ensayos.export.excel_exporter import export_to_excel

DB, OUT = sys.argv[1], sys.argv[2]

# ---------------------------------------------------------------- Excel
hoy = datetime.date.today()
ruta = export_to_excel(OUT, hoy, hoy, db_path=DB)
wb = load_workbook(ruta)
for ws in wb.worksheets:
    filas = list(ws.iter_rows(values_only=True))
    print(f"Excel hoja '{ws.title}': {len(filas) - 1} filas de datos | encabezado={filas[0] if filas else None}")
    if len(filas) > 1:
        print("   primera fila:", filas[1])

# ---------------------------------------------------------------- API
import uvicorn  # noqa: E402

from ensayos.api.app import create_app  # noqa: E402

app = create_app(db_path=DB)
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
for _ in range(50):
    if server.started:
        break
    time.sleep(0.1)


def get(path, user=None, pwd=None):
    req = urllib.request.Request(f"http://127.0.0.1:8765{path}")
    if user is not None:
        tok = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        req.add_header("Authorization", f"Basic {tok}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


s, b = get("/api/health")
print("API /api/health ->", s, b[:200])
s, b = get("/api/historial-fdl")
print("API /api/historial-fdl sin credenciales ->", s)
s, b = get("/api/historial-fdl", "admin", "incorrecta")
print("API /api/historial-fdl con clave incorrecta ->", s)
s, b = get("/api/historial-fdl", "admin", "admin")
datos = json.loads(b) if s == 200 else b
n = len(datos) if isinstance(datos, list) else (len(datos.get("data", datos)) if isinstance(datos, dict) else "?")
print("API /api/historial-fdl con admin/admin ->", s, "| registros:", n)
s, b = get("/api/historial-consumo", "admin", "admin")
print("API /api/historial-consumo ->", s, b[:120])
s, b = get("/app/")
print("API /app/ (frontend web) ->", s, b[:80].replace("\n", " "))
server.should_exit = True
time.sleep(0.5)
