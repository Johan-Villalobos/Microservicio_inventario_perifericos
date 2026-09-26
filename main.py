"""
Microservicio de stock - inventario_perifericos
================================================

Se conecta a la base de datos en Supabase (tablas perifericos_periferico,
perifericos_monitor, perifericos_equipo) y expone esos datos por HTTP.

Encaja en el flujo del proyecto Django adjunto:

    Django (views.py) --HTTP--> este microservicio --SQL--> Supabase

Para conectarlo con el proyecto Django:
1. Despliega este microservicio en Render (ver README.md).
2. En inventario/settings.py del proyecto Django, cambia:
       MICROSERVICIO_STOCK_URL = "https://tu-servicio.onrender.com/api/stock"
   por la URL real que te da Render.
3. Las vistas de listado/creación/edición/eliminación de Django ya están
   listas para consumir/enviar el JSON de estos endpoints.

Endpoints por recurso (perifericos, monitores, equipos):
    GET    /api/<recurso>            -> listar todos
    POST   /api/<recurso>            -> crear uno nuevo
    PUT    /api/<recurso>/{id|placa} -> actualizar uno existente
    DELETE /api/<recurso>/{id|placa} -> eliminar uno existente
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import errors as pg_errors
from pydantic import BaseModel

from database import filas_a_diccionarios, get_connection

app = FastAPI(title="Microservicio de Stock - Inventario Periféricos")

# En producción, reemplaza "*" por el dominio real donde corre tu Django
# (ej. https://mi-django-app.onrender.com) para no exponer la API a cualquiera.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Esquemas de entrada (lo que Django envía en POST/PUT)
# ---------------------------------------------------------------------

class PerifericoEntrada(BaseModel):
    tipo: str
    conexion: str
    marca: str
    cantidad: int = 0


class MonitorCrear(BaseModel):
    placa: str
    marca: str
    pulgadas: int = 24


class MonitorActualizar(BaseModel):
    marca: str
    pulgadas: int = 24


class EquipoCrear(BaseModel):
    placa: str
    tipo: str
    marca: str
    usuario_asignado: str = ""


class EquipoActualizar(BaseModel):
    tipo: str
    marca: str
    usuario_asignado: str = ""


@app.get("/")
def raiz():
    return {"status": "ok", "servicio": "microservicio-stock", "supabase": True}


# ---------------------------------------------------------------------
# Mouse y teclados (tabla perifericos_periferico) — id autonumérico
# ---------------------------------------------------------------------

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


@app.post("/api/perifericos", status_code=201)
def crear_periferico(datos: PerifericoEntrada):
    query = """
        insert into perifericos_periferico (tipo, conexion, marca, cantidad)
        values (%s, %s, %s, %s)
        returning id, tipo, conexion, marca, cantidad
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (datos.tipo, datos.conexion, datos.marca, datos.cantidad))
            return filas_a_diccionarios(cur)[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error insertando en Supabase: {exc}")


@app.put("/api/perifericos/{periferico_id}")
def actualizar_periferico(periferico_id: int, datos: PerifericoEntrada):
    query = """
        update perifericos_periferico
        set tipo = %s, conexion = %s, marca = %s, cantidad = %s
        where id = %s
        returning id, tipo, conexion, marca, cantidad
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (datos.tipo, datos.conexion, datos.marca, datos.cantidad, periferico_id))
            fila = filas_a_diccionarios(cur)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error actualizando en Supabase: {exc}")
    if not fila:
        raise HTTPException(status_code=404, detail="Periférico no encontrado")
    return fila[0]


@app.delete("/api/perifericos/{periferico_id}")
def eliminar_periferico(periferico_id: int):
    query = "delete from perifericos_periferico where id = %s"
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (periferico_id,))
            eliminado = cur.rowcount > 0
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error eliminando en Supabase: {exc}")
    if not eliminado:
        raise HTTPException(status_code=404, detail="Periférico no encontrado")
    return {"eliminado": True, "id": periferico_id}


# ---------------------------------------------------------------------
# Monitores (tabla perifericos_monitor) — clave: placa
# ---------------------------------------------------------------------

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


@app.post("/api/monitores", status_code=201)
def crear_monitor(datos: MonitorCrear):
    query = """
        insert into perifericos_monitor (placa, marca, pulgadas)
        values (%s, %s, %s)
        returning id, placa, marca, pulgadas
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (datos.placa, datos.marca, datos.pulgadas))
            return filas_a_diccionarios(cur)[0]
    except pg_errors.UniqueViolation:
        raise HTTPException(status_code=409, detail=f"Ya existe un monitor con la placa {datos.placa}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error insertando en Supabase: {exc}")


@app.put("/api/monitores/{placa}")
def actualizar_monitor(placa: str, datos: MonitorActualizar):
    query = """
        update perifericos_monitor
        set marca = %s, pulgadas = %s
        where placa = %s
        returning id, placa, marca, pulgadas
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (datos.marca, datos.pulgadas, placa))
            fila = filas_a_diccionarios(cur)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error actualizando en Supabase: {exc}")
    if not fila:
        raise HTTPException(status_code=404, detail="Monitor no encontrado")
    return fila[0]


@app.delete("/api/monitores/{placa}")
def eliminar_monitor(placa: str):
    query = "delete from perifericos_monitor where placa = %s"
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (placa,))
            eliminado = cur.rowcount > 0
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error eliminando en Supabase: {exc}")
    if not eliminado:
        raise HTTPException(status_code=404, detail="Monitor no encontrado")
    return {"eliminado": True, "placa": placa}


# ---------------------------------------------------------------------
# Equipos (tabla perifericos_equipo) — clave: placa
# ---------------------------------------------------------------------

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


@app.post("/api/equipos", status_code=201)
def crear_equipo(datos: EquipoCrear):
    query = """
        insert into perifericos_equipo (placa, tipo, marca, usuario_asignado)
        values (%s, %s, %s, %s)
        returning id, placa, tipo, marca, usuario_asignado
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (datos.placa, datos.tipo, datos.marca, datos.usuario_asignado))
            return filas_a_diccionarios(cur)[0]
    except pg_errors.UniqueViolation:
        raise HTTPException(status_code=409, detail=f"Ya existe un equipo con la placa {datos.placa}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error insertando en Supabase: {exc}")


@app.put("/api/equipos/{placa}")
def actualizar_equipo(placa: str, datos: EquipoActualizar):
    query = """
        update perifericos_equipo
        set tipo = %s, marca = %s, usuario_asignado = %s
        where placa = %s
        returning id, placa, tipo, marca, usuario_asignado
    """
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (datos.tipo, datos.marca, datos.usuario_asignado, placa))
            fila = filas_a_diccionarios(cur)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error actualizando en Supabase: {exc}")
    if not fila:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return fila[0]


@app.delete("/api/equipos/{placa}")
def eliminar_equipo(placa: str):
    query = "delete from perifericos_equipo where placa = %s"
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (placa,))
            eliminado = cur.rowcount > 0
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error eliminando en Supabase: {exc}")
    if not eliminado:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return {"eliminado": True, "placa": placa}


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
