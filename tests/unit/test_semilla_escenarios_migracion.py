"""Migración 0005 (semilla provisional de escenarios): coherencia sin base de datos."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

RAIZ = Path(__file__).resolve().parents[2]
SQL = RAIZ / "bd" / "sql"
ARCHIVO_SQL = SQL / "14_semilla_escenarios_provisionales.sql"
MIGRACION = RAIZ / "migrations" / "versions" / "0005_semilla_escenarios_provisionales.py"


def _cargar(ruta: Path, nombre: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_cadena_de_revisiones() -> None:
    m = _cargar(MIGRACION, "migracion_0005")
    assert (m.revision, m.down_revision) == ("0005", "0004")
    assert m.ARCHIVO == ARCHIVO_SQL


def test_no_es_destructiva_y_esta_registrada() -> None:
    """Mismo chequeo que la CI (scripts/revisar_migraciones.py)."""
    revisor = _cargar(RAIZ / "scripts" / "revisar_migraciones.py", "revisar_migraciones")
    destructivas, problemas = revisor.revisar(
        [
            "migrations/versions/0005_semilla_escenarios_provisionales.py",
            "bd/sql/14_semilla_escenarios_provisionales.sql",
        ]
    )
    assert destructivas == []
    assert problemas == []


def test_instalacion_por_psql_incluye_la_semilla_despues_de_las_vistas() -> None:
    lineas = [x.strip() for x in (SQL / "00_instalar_todo.sql").read_text(encoding="utf-8").splitlines()]
    assert lineas.index(r"\ir 14_semilla_escenarios_provisionales.sql") == (
        lineas.index(r"\ir 13_vistas_productor.sql") + 1
    )


def test_la_semilla_queda_marcada_como_provisional_y_no_borra_ni_modifica() -> None:
    texto = ARCHIVO_SQL.read_text(encoding="utf-8")
    assert "'PROVISIONAL: RN-002, Tabla 1 OIEA 2005" in texto
    assert "(P-02)" in texto
    # «ON COMMIT DROP» solo descarta la tabla temporal de comparación al terminar la transacción.
    sin_comentarios = re.sub(r"--.*", "", texto).replace("ON COMMIT DROP", "")
    # Solo inserta en el catálogo; el TRUNCATE es de la tabla temporal de comparación (pg_temp).
    assert not re.search(r"\b(DELETE|UPDATE|ALTER|DROP)\b", sin_comentarios)
    assert re.findall(r"\bTRUNCATE\s+([\w.]+)", sin_comentarios) == ["pg_temp.escenario_esperado"]
    assert re.findall(r"\bINSERT\s+INTO\s+([\w.]+)", sin_comentarios) == [
        "pg_temp.escenario_esperado",
        "sigat.escenario_trampeo",
    ]
