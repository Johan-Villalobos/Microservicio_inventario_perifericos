# Microservicio de stock (Supabase → Render → Django)

API en FastAPI que consulta directamente las tablas de Supabase creadas con
`supabase_migration.sql` (`perifericos_periferico`, `perifericos_monitor`,
`perifericos_equipo`) y las expone por HTTP para que el proyecto Django
`inventario_perifericos` las consuma desde su vista `stock_proveedor`.

```
Django (views.stock_proveedor) --HTTP GET--> este microservicio --SQL--> Supabase
```

## Endpoints

| Ruta | Descripción |
|---|---|
| `GET /` | Healthcheck |
| `GET /api/perifericos` | Mouse y teclados tal cual en la tabla `perifericos_periferico` |
| `GET /api/monitores` | Tabla `perifericos_monitor` |
| `GET /api/equipos` | Tabla `perifericos_equipo` |
| `GET /api/stock` | Combinación de las tres tablas, con la forma `{"categoria", "producto", "stock"}` — **este es el endpoint que debe usar `MICROSERVICIO_STOCK_URL`** |

## Probar en local

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edita .env con tu cadena real de Supabase

export $(cat .env | xargs)     # o usa python-dotenv / tu shell habitual
uvicorn main:app --reload
```

Luego visita `http://127.0.0.1:8000/api/stock`.

## Desplegar en Render

1. Sube esta carpeta (`microservicio_stock/`) a un repo de GitHub.
2. En Render: **New +** → **Web Service** → conecta el repo.
3. Render detecta el `Procfile`, pero confirma:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. En **Environment**, agrega la variable `DATABASE_URL` con la cadena de
   conexión de Supabase (usa el modo *Connection pooling*, puerto `6543`,
   para que Render no agote las conexiones directas de Supabase).
5. Deploy. Render te da una URL tipo `https://microservicio-stock.onrender.com`.

## Conectarlo con el proyecto Django adjunto

En `inventario_perifericos/inventario/settings.py`, cambia:

```python
MICROSERVICIO_STOCK_URL = "https://tu-microservicio.onrender.com/api/stock"
```

por la URL real que te dio Render, por ejemplo:

```python
MICROSERVICIO_STOCK_URL = "https://microservicio-stock.onrender.com/api/stock"
```

Con eso, al entrar a `/perifericos/stock-proveedor/` en el proyecto Django,
la vista `stock_proveedor` (en `perifericos/views.py`) le hará un `GET` a
este microservicio y renderizará la lista que devuelve `/api/stock` en
`stock_proveedor.html`, sin que Django toque SQLite ni Supabase directamente.

## Notas

- El microservicio es de **solo lectura** (solo `SELECT`). Si luego quieres
  registrar movimientos de stock desde Django hacia Supabase, se agregan
  endpoints `POST`/`PUT` aquí siguiendo el mismo patrón.
- CORS está abierto (`allow_origins=["*"]`) para simplificar las pruebas;
  en producción restringe `allow_origins` al dominio donde corra tu Django.
