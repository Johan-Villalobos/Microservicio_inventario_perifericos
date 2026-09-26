# Microservicio de stock (Supabase → Render → Django)

API en FastAPI que consulta directamente las tablas de Supabase creadas con
`supabase_migration.sql` (`perifericos_periferico`, `perifericos_monitor`,
`perifericos_equipo`) y las expone por HTTP para que el proyecto Django
`inventario_perifericos` las consuma desde su vista `stock_proveedor`.

```
Django (views.stock_proveedor) --HTTP GET--> este microservicio --SQL--> Supabase
```

## Endpoints

| Ruta | Método | Descripción |
|---|---|---|
| `GET /` | GET | Healthcheck |
| `GET /api/perifericos` | GET | Mouse y teclados tal cual en la tabla `perifericos_periferico` |
| `POST /api/perifericos` | POST | Crea un mouse/teclado. Body: `{tipo, conexion, marca, cantidad}` |
| `PUT /api/perifericos/{id}` | PUT | Actualiza un mouse/teclado por `id`. Mismo body que crear |
| `DELETE /api/perifericos/{id}` | DELETE | Elimina un mouse/teclado por `id` |
| `GET /api/monitores` | GET | Tabla `perifericos_monitor` |
| `POST /api/monitores` | POST | Crea un monitor. Body: `{placa, marca, pulgadas}` |
| `PUT /api/monitores/{placa}` | PUT | Actualiza un monitor por `placa`. Body: `{marca, pulgadas}` |
| `DELETE /api/monitores/{placa}` | DELETE | Elimina un monitor por `placa` |
| `GET /api/equipos` | GET | Tabla `perifericos_equipo` |
| `POST /api/equipos` | POST | Crea un equipo. Body: `{placa, tipo, marca, usuario_asignado}` |
| `PUT /api/equipos/{placa}` | PUT | Actualiza un equipo por `placa`. Body: `{tipo, marca, usuario_asignado}` |
| `DELETE /api/equipos/{placa}` | DELETE | Elimina un equipo por `placa` |
| `GET /api/stock` | GET | Combinación de las tres tablas, con la forma `{"categoria", "producto", "stock"}` — **este es el endpoint que debe usar `MICROSERVICIO_STOCK_URL`** |

Los endpoints `POST`/`PUT` en `/api/monitores` y `/api/equipos` devuelven **409**
si la `placa` ya existe (viola la restricción `unique` de Supabase). Los `PUT`/`DELETE`
sobre un registro que no existe devuelven **404**.

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

- El microservicio ahora soporta operaciones de escritura (`POST`/`PUT`/`DELETE`)
  además de las de solo lectura, para las tres tablas (periféricos, monitores,
  equipos), siguiendo el mismo patrón de conexión a Supabase.
- CORS está abierto (`allow_origins=["*"]`, y ahora también permite los métodos
  `POST`, `PUT`, `DELETE`) para simplificar las pruebas; en producción restringe
  `allow_origins` al dominio donde corra tu Django.
