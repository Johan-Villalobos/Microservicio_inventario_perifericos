# API Inventario (FastAPI + Supabase)

Microservicio **de solo lectura** que expone el inventario de equipos, monitores y
periféricos guardado en Supabase. Lo consume la app Django.

```
Django --HTTP + X-API-Key--> Render (este servicio) --SQL--> Supabase
```

## Endpoints

Todos (menos `/health`) requieren la cabecera `X-API-Key`.

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/health` | Estado del servicio y de la conexión a la BD (sin API key) |
| GET | `/api/resumen` | Conteos generales (equivale al `index` de Django) |
| GET | `/api/stock?categoria=` | Total / asignados / disponibles (`PERIFERICO`, `EQUIPO`, `MONITOR`). Es la ruta para `stock_proveedor` |
| GET | `/api/equipos?tipo=&estado=` | Lista de equipos |
| GET | `/api/equipos/{placa}` | Detalle por placa de 5 dígitos |
| GET | `/api/monitores?estado=` | Lista de monitores |
| GET | `/api/monitores/{placa}` | Detalle por placa de 5 dígitos |
| GET | `/api/perifericos` | Mouse y teclados con total, asignados y disponibles |
| GET | `/api/perifericos/{id}` | Detalle de un periférico |

Documentación interactiva en `/docs`.

## Prueba local

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL="postgresql://..."   # Windows PowerShell: $env:DATABASE_URL="..."
export API_KEY="una-clave-de-prueba"

uvicorn main:app --reload
curl -H "X-API-Key: una-clave-de-prueba" http://127.0.0.1:8000/api/stock
```

## Despliegue en Render

1. Sube esta carpeta a un repositorio de GitHub.
2. En Render: **New > Blueprint** (usa `render.yaml`) o **New > Web Service** con:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
3. En **Environment** define `DATABASE_URL` y `API_KEY`.
4. Con la URL pública, en Django: `MICROSERVICIO_STOCK_URL = "https://<tu-servicio>.onrender.com/api/stock"`
   y enviar la cabecera `X-API-Key` en el `requests.get(...)`.

## Notas

- Usa la cadena del **Session pooler** de Supabase (soporta IPv4). La conexión directa
  de Supabase es solo IPv6 y puede fallar desde Render.
- Cada transacción se abre en modo `READ ONLY`: aunque alguien llegue a la API,
  esta no puede modificar datos.
- En el plan gratuito de Render el servicio se duerme tras inactividad y la primera
  petición puede tardar de 30 a 60 segundos.
