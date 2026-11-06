"""Base de datos temporal para las pruebas de integración.

``SIGAT_DB_URL_PRUEBAS`` apunta a un servidor PostgreSQL/PostGIS con un usuario que pueda crear bases
(``CREATEDB``). Cada ejecución crea bases NUEVAS con nombre aleatorio, construye el esquema con
``alembic upgrade head`` (igual que un desarrollador después de clonar) y las borra al final.
Nunca toca la base indicada en la URL ni ninguna otra.

Las contraseñas se generan al azar en cada ejecución: no hay credenciales en el repositorio.
"""

import os
import secrets
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

URL_PRUEBAS = os.environ.get("SIGAT_DB_URL_PRUEBAS")
RAIZ = Path(__file__).resolve().parents[2]


def url_base(nombre: str) -> URL:
    assert URL_PRUEBAS
    return make_url(URL_PRUEBAS).set(database=nombre)


def _admin_sql(sql: str) -> None:
    """Ejecuta CREATE/DROP DATABASE en la base de mantenimiento ``postgres``."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    async def _correr() -> None:
        motor = create_async_engine(url_base("postgres"), isolation_level="AUTOCOMMIT")
        async with motor.connect() as con:
            await con.execute(text(sql))
        await motor.dispose()

    asyncio.run(_correr())


def crear_bd() -> str:
    nombre = f"sigat_prueba_{secrets.token_hex(4)}"
    _admin_sql(f'CREATE DATABASE "{nombre}"')
    return nombre


def borrar_bd(nombre: str) -> None:
    _admin_sql(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)')


def entorno(nombre: str, **extra: str) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        SIGAT_DB_URL=url_base(nombre).render_as_string(hide_password=False),
        SIGAT_JWT_SECRETO=env.get("SIGAT_JWT_SECRETO", "solo-pruebas-" + "x" * 40),
        SIGAT_ENTORNO="pruebas",
        PYTHONPATH=str(RAIZ / "src"),
        # El subproceso escribe en UTF-8 y aquí se lee en UTF-8 (en Windows, sin esto, cp1252).
        PYTHONIOENCODING="utf-8",
    )
    env.update(extra)
    return env


def alembic(nombre: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=RAIZ,
        env=entorno(nombre),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def psql(nombre: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Instalación por psql (la que usa el proyecto de base de datos). Requiere el cliente ``psql``."""
    ejecutable = shutil.which("psql")
    if ejecutable is None:
        pytest.skip("psql no está instalado")
    u = url_base(nombre)
    env = dict(os.environ)
    if u.password:
        env["PGPASSWORD"] = str(u.password)
    conexion = [
        "-h",
        str(u.query.get("host") or u.host or "localhost"),
        "-p",
        str(u.query.get("port") or u.port or 5432),
        "-U",
        str(u.username or "postgres"),
        "-d",
        nombre,
    ]
    return subprocess.run(
        [ejecutable, *conexion, "-X", "-q", "-v", "ON_ERROR_STOP=1", *args],
        cwd=RAIZ / "bd" / "sql",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def cli(nombre: str, *args: str, entrada: str = "", **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sigat_api.cli", *args],
        cwd=RAIZ,
        env=entorno(nombre, **extra),
        input=entrada,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def consulta(nombre: str, sql: str) -> list[tuple[object, ...]]:
    """Consulta de verificación con un motor síncrono propio (no interfiere con el de la app)."""
    import asyncio

    from sqlalchemy.ext.asyncio import create_async_engine

    async def _correr() -> list[tuple[object, ...]]:
        motor = create_async_engine(url_base(nombre))
        async with motor.connect() as con:
            filas = [tuple(f) for f in (await con.execute(text(sql))).all()]
        await motor.dispose()
        return filas

    return asyncio.run(_correr())


@pytest.fixture(scope="session")
def h() -> SimpleNamespace:
    """Herramientas para las pruebas (los módulos de prueba no pueden importarse entre sí)."""
    if not URL_PRUEBAS:
        pytest.skip("Defina SIGAT_DB_URL_PRUEBAS para probar contra PostgreSQL")
    return SimpleNamespace(
        alembic=alembic,
        psql=psql,
        cli=cli,
        consulta=consulta,
        crear_bd=crear_bd,
        borrar_bd=borrar_bd,
        url=lambda nombre: url_base(nombre).render_as_string(hide_password=False),
    )


@pytest.fixture(scope="module")
def bd_limpia() -> Iterator[str]:
    """Base recién creada con ``alembic upgrade head`` (sin ninguna cuenta)."""
    if not URL_PRUEBAS:
        pytest.skip("Defina SIGAT_DB_URL_PRUEBAS para probar contra PostgreSQL")
    nombre = crear_bd()
    try:
        r = alembic(nombre, "upgrade", "head")
        assert r.returncode == 0, r.stderr
        yield nombre
    finally:
        borrar_bd(nombre)
