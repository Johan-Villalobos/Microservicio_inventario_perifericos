"""Microservicio de solo lectura del inventario de equipos y periféricos.

Django --HTTP + X-API-Key--> este servicio (Render) --SQL--> Supabase (PostgreSQL)

Variables de entorno obligatorias:
  DATABASE_URL  cadena de conexión de Supabase (usar el pooler)
  API_KEY       clave que Django debe enviar en la cabecera X-API-Key
"""
import os
import secrets
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Estado = Literal["EN_USO", "EN_BODEGA", "EN_REPARACION", "DADO_DE_BAJA"]
PLACA = Path(pattern=r"^\d{5}$", description="Placa de 5 dígitos")


def _env(nombre: str) -> str:
    valor = os.environ.get(nombre)
    if not valor:
        raise RuntimeError(f"Falta la variable de entorno {nombre}")
    return valor


def _solo_lectura(conn) -> None:
    # Cada transacción se abre como READ ONLY: esta API nunca escribe.
    conn.read_only = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.api_key = _env("API_KEY")
    app.state.pool = ConnectionPool(
        _env("DATABASE_URL"),
        min_size=1,
        max_size=5,
        timeout=10,
        open=False,
        configure=_solo_lectura,
        # prepare_threshold=None: compatible con el pooler en modo transacción
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
    )
    app.state.pool.open(wait=True, timeout=30)
    yield
    app.state.pool.close()


app = FastAPI(title="API Inventario", version="1.0.0", lifespan=lifespan)


@app.exception_handler(OperationalError)
async def base_de_datos_no_disponible(request: Request, exc: OperationalError):
    return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible"})


def require_api_key(request: Request, x_api_key: Optional[str] = Header(default=None)) -> None:
    esperada = request.app.state.api_key
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), esperada.encode()):
        raise HTTPException(status_code=401, detail="API key inválida o ausente")


def consultar(request: Request, sql: str, params: tuple = ()) -> list[dict]:
    with request.app.state.pool.connection() as conn:
        return conn.execute(sql, params).fetchall()


def uno_o_404(filas: list[dict], mensaje: str) -> dict:
    if not filas:
        raise HTTPException(status_code=404, detail=mensaje)
    return filas[0]


@app.get("/health", tags=["sistema"])
def health(request: Request):
    consultar(request, "select 1")
    return {"status": "ok"}


router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@router.get("/resumen", tags=["inventario"])
def resumen(request: Request):
    """Conteos generales (equivale a la vista index de Django)."""
    return uno_o_404(
        consultar(
            request,
            """
            select
              (select count(*) from public.perifericos)                  as total_perifericos,
              (select coalesce(sum(cantidad), 0) from public.perifericos) as unidades_perifericos,
              (select count(*) from public.monitores)                    as total_monitores,
              (select count(*) from public.equipos)                      as total_equipos
            """,
        ),
        "Sin datos",
    )


@router.get("/stock", tags=["inventario"])
def stock(request: Request, categoria: Optional[Literal["PERIFERICO", "EQUIPO", "MONITOR"]] = None):
    """Resumen total / asignados / disponibles por categoría (endpoint de stock_proveedor)."""
    return consultar(
        request,
        """
        select * from public.v_stock_resumen
        where (%s::text is null or categoria = %s)
        order by categoria, tipo, detalle, marca
        """,
        (categoria, categoria),
    )


@router.get("/equipos", tags=["equipos"])
def listar_equipos(
    request: Request,
    tipo: Optional[Literal["PORTATIL", "ESCRITORIO"]] = None,
    estado: Optional[Estado] = None,
):
    return consultar(
        request,
        """
        select * from public.v_equipos
        where (%s::text is null or tipo = %s)
          and (%s::text is null or estado = %s)
        order by placa
        """,
        (tipo, tipo, estado, estado),
    )


@router.get("/equipos/{placa}", tags=["equipos"])
def detalle_equipo(request: Request, placa: str = PLACA):
    filas = consultar(request, "select * from public.v_equipos where placa = %s", (placa,))
    return uno_o_404(filas, f"No existe un equipo con placa {placa}")


@router.get("/monitores", tags=["monitores"])
def listar_monitores(request: Request, estado: Optional[Estado] = None):
    return consultar(
        request,
        """
        select * from public.v_monitores
        where (%s::text is null or estado = %s)
        order by placa
        """,
        (estado, estado),
    )


@router.get("/monitores/{placa}", tags=["monitores"])
def detalle_monitor(request: Request, placa: str = PLACA):
    filas = consultar(request, "select * from public.v_monitores where placa = %s", (placa,))
    return uno_o_404(filas, f"No existe un monitor con placa {placa}")


@router.get("/perifericos", tags=["perifericos"])
def listar_perifericos(request: Request):
    return consultar(
        request,
        "select * from public.v_stock_perifericos order by tipo, conexion, marca",
    )


@router.get("/perifericos/{periferico_id}", tags=["perifericos"])
def detalle_periferico(request: Request, periferico_id: int):
    filas = consultar(
        request,
        "select * from public.v_stock_perifericos where periferico_id = %s",
        (periferico_id,),
    )
    return uno_o_404(filas, f"No existe el periférico {periferico_id}")


app.include_router(router)
