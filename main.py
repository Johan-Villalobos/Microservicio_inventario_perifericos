"""
Microservicio de stock - inventario_perifericos
================================================

Se conecta a la base de datos en Supabase (tablas perifericos_periferico,
perifericos_monitor, perifericos_equipo) y expone esos datos por HTTP.

Encaja en el flujo del proyecto Django adjunto:

    Django (views.stock_proveedor) --HTTP GET--> este microservicio --SQL--> Supabase

Para conectarlo con el proyecto Django:
1. Despliega este microservicio en Render (ver README.md).
2. En inventario/settings.py del proyecto Django, cambia:
       MICROSERVICIO_STOCK_URL = "https://tu-servicio.onrender.com/api/stock"
   por la URL real que te da Render.
3. La vista `stock_proveedor` y su template ya están listos para consumir
   el JSON que devuelve /api/stock (ver más abajo).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import filas_a_diccionarios, get_connection

app = FastAPI(title="Microservicio de Stock - Inventario Periféricos")

# En producción, reemplaza "*" por el dominio real donde corre tu Django
# (ej. https://mi-django-app.onrender.com) para no exponer la API a cualquiera.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def raiz():
    return {"status": "ok", "servicio": "microservicio-stock", "supabase": True}


@app.get("/api/perifericos")
def listar_perifericos():
    """Mouse y teclados: tabla perifericos_periferico."""
    query = """
        select id, tipo, conexion, marca, cantidad
        from perifericos_periferico
        order by tipo, conexion
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query)
            return filas_a_diccionarios(cur)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {exc}")


@app.get("/api/monitores")
def listar_monitores():
    """Tabla perifericos_monitor."""
    query = """
        select id, placa, marca, pulgadas
        from perifericos_monitor
        order by placa
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query)
            return filas_a_diccionarios(cur)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {exc}")


@app.get("/api/equipos")
def listar_equipos():
    """Tabla perifericos_equipo."""
    query = """
        select id, placa, tipo, marca, usuario_asignado
        from perifericos_equipo
        order by placa
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query)
            return filas_a_diccionarios(cur)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {exc}")


@app.get("/api/stock")
def stock_general():
    """
    Endpoint que consume directamente la vista `stock_proveedor` de Django
    (MICROSERVICIO_STOCK_URL). Combina las tres tablas en una sola lista,
    describiendo cada ítem y su cantidad en stock.
    """
    items = []
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select tipo, conexion, marca, cantidad
                from perifericos_periferico
                order by tipo, conexion
                """
            )
            for tipo, conexion, marca, cantidad in cur.fetchall():
                items.append(
                    {
                        "categoria": "periferico",
                        "producto": f"{tipo.title()} {conexion.title()} - {marca}",
                        "stock": cantidad,
                    }
                )

            cur.execute(
                """
                select placa, marca, pulgadas
                from perifericos_monitor
                order by placa
                """
            )
            for placa, marca, pulgadas in cur.fetchall():
                items.append(
                    {
                        "categoria": "monitor",
                        "producto": f"Monitor {placa} - {marca} ({pulgadas}\")",
                        "stock": 1,
                    }
                )

            cur.execute(
                """
                select placa, tipo, marca, usuario_asignado
                from perifericos_equipo
                order by placa
                """
            )
            for placa, tipo, marca, usuario in cur.fetchall():
                asignado = f" - {usuario}" if usuario else " - sin asignar"
                items.append(
                    {
                        "categoria": "equipo",
                        "producto": f"{tipo.title()} {placa} - {marca}{asignado}",
                        "stock": 1,
                    }
                )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error consultando Supabase: {exc}")

    return items
