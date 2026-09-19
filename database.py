"""
Conexión a la base de datos de Supabase (PostgreSQL).

La cadena de conexión se toma de la variable de entorno DATABASE_URL.
En Supabase la obtienes en: Project Settings -> Database -> Connection string
(usa la variante "Connection pooling" / puerto 6543 si desplegarás en Render,
ya que Render abre/cierra muchas conexiones y el pooler de Supabase lo maneja
mejor que la conexión directa al puerto 5432).

Ejemplo de valor para DATABASE_URL:
postgresql://postgres.xxxxxxxxxxxx:TU_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
"""

import contextlib
import os

import psycopg2
import psycopg2.pool

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta la variable de entorno DATABASE_URL con la cadena de conexión de Supabase."
    )

# Pool pequeño: suficiente para un microservicio de solo lectura en Render (plan free).
_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=DATABASE_URL)


@contextlib.contextmanager
def get_connection():
    """Entrega una conexión del pool y la devuelve al terminar."""
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def filas_a_diccionarios(cur):
    columnas = [c.name for c in cur.description]
    return [dict(zip(columnas, fila)) for fila in cur.fetchall()]
