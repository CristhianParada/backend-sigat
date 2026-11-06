"""Migración 0004 (vistas del productor): coherencia sin base de datos."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
SQL = RAIZ / "bd" / "sql"
MIGRACION = RAIZ / "migrations" / "versions" / "0004_vistas_productor.py"
VISTAS = ("v_actividad_lote_detalle", "v_aplicacion_ultima_lote", "v_cosecha_lote_vigente")


def _cargar(ruta: Path, nombre: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_cadena_de_revisiones() -> None:
    m = _cargar(MIGRACION, "migracion_0004")
    assert (m.revision, m.down_revision) == ("0004", "0003")
    assert m.ARCHIVO == SQL / "13_vistas_productor.sql"


def test_no_es_destructiva_y_esta_registrada() -> None:
    """Mismo chequeo que la CI (scripts/revisar_migraciones.py)."""
    revisor = _cargar(RAIZ / "scripts" / "revisar_migraciones.py", "revisar_migraciones")
    destructivas, problemas = revisor.revisar(
        ["migrations/versions/0004_vistas_productor.py", "bd/sql/13_vistas_productor.sql"]
    )
    assert destructivas == []
    assert problemas == []


def test_instalacion_por_psql_incluye_el_archivo_despues_de_v9_1() -> None:
    """Sin esto, Alembic y psql dejarían esquemas distintos (tests/integracion/test_migraciones.py)."""
    lineas = [x.strip() for x in (SQL / "00_instalar_todo.sql").read_text(encoding="utf-8").splitlines()]
    assert lineas.index(r"\ir 13_vistas_productor.sql") == lineas.index(r"\ir 12_ajustes_v9_1.sql") + 1


def test_el_sql_solo_agrega_objetos() -> None:
    texto = (SQL / "13_vistas_productor.sql").read_text(encoding="utf-8")
    sentencias = re.findall(r"^\s*(CREATE OR REPLACE (?:VIEW|FUNCTION)|COMMENT ON)\b", texto, re.M)
    assert sentencias
    assert not re.search(r"\b(DROP|ALTER|INSERT|UPDATE|DELETE|TRUNCATE)\b", re.sub(r"--.*", "", texto))


def test_el_backend_nunca_lee_las_vistas_sin_filtrar() -> None:
    """Las vistas devuelven todos los lotes. El código debe usar fn_actividad_lote_detalle /
    fn_aplicacion_ultima_lote con el usuario del token, nunca la vista directamente."""
    usos = []
    for archivo in (RAIZ / "src").rglob("*.py"):
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            for vista in VISTAS:
                if vista in linea.replace("fn_" + vista.removeprefix("v_"), ""):
                    usos.append(f"{archivo.relative_to(RAIZ)}:{numero}")
    assert usos == []
