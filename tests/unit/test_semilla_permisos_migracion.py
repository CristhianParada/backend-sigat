"""Migración 0006 (semilla de permisos): la matriz del SQL es EXACTAMENTE la de permisos.py. Sin BD."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

from sigat_api.compartido.tipos import RolCodigo
from sigat_api.modules.identidad.permisos import PERMISOS

RAIZ = Path(__file__).resolve().parents[2]
SQL = RAIZ / "bd" / "sql"
ARCHIVO_SQL = SQL / "15_semilla_permisos.sql"
MIGRACION = RAIZ / "migrations" / "versions" / "0006_semilla_permisos.py"

FILA = re.compile(r"\('([^']+)',\s*'([^']+)',\s*ARRAY\[([^\]]*)\]\)")


def _cargar(ruta: Path, nombre: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _semilla() -> list[tuple[str, str, list[str]]]:
    """Filas (código, descripción, roles) del VALUES de 15_semilla_permisos.sql."""
    texto = re.sub(r"--.*", "", ARCHIVO_SQL.read_text(encoding="utf-8"))
    return [(c, d, re.findall(r"'([A-Z_]+)'", roles)) for c, d, roles in FILA.findall(texto)]


def test_cadena_de_revisiones() -> None:
    m = _cargar(MIGRACION, "migracion_0006")
    assert (m.revision, m.down_revision) == ("0006", "0005")
    assert m.ARCHIVO == ARCHIVO_SQL


def test_no_es_destructiva_y_esta_registrada() -> None:
    """Mismo chequeo que la CI (scripts/revisar_migraciones.py)."""
    revisor = _cargar(RAIZ / "scripts" / "revisar_migraciones.py", "revisar_migraciones")
    destructivas, problemas = revisor.revisar(
        ["migrations/versions/0006_semilla_permisos.py", "bd/sql/15_semilla_permisos.sql"]
    )
    assert destructivas == []
    assert problemas == []


def test_instalacion_por_psql_incluye_la_semilla_despues_de_los_escenarios() -> None:
    lineas = [x.strip() for x in (SQL / "00_instalar_todo.sql").read_text(encoding="utf-8").splitlines()]
    assert lineas.index(r"\ir 15_semilla_permisos.sql") == (
        lineas.index(r"\ir 14_semilla_escenarios_provisionales.sql") + 1
    )


def test_la_semilla_es_exactamente_la_matriz_de_permisos_py() -> None:
    """Mismos códigos y mismas asignaciones por rol: ni uno más, ni uno menos."""
    semilla = {codigo: frozenset(RolCodigo(r) for r in roles) for codigo, _, roles in _semilla()}
    assert semilla == PERMISOS


def test_25_permisos_54_pares_sin_repetidos_y_mismo_orden() -> None:
    filas = _semilla()
    assert len(filas) == 25
    assert len({c for c, _, _ in filas}) == 25
    assert sum(len(r) for _, _, r in filas) == 54
    assert all(len(set(r)) == len(r) for _, _, r in filas)
    assert [c for c, _, _ in filas] == list(PERMISOS)


def test_cumple_las_restricciones_de_la_bd() -> None:
    """CHECK permiso_codigo_formato (con punto, sin «:») y permiso_descripcion_no_vacia; roles existentes."""
    roles_validos = {r.value for r in RolCodigo}
    for codigo, descripcion, roles in _semilla():
        assert re.fullmatch(r"[a-z_]+\.[a-z_]+", codigo), codigo
        assert ":" not in codigo
        assert descripcion.strip(), codigo
        assert set(roles) <= roles_validos, codigo


def test_no_incluye_los_codigos_alternativos_de_la_documentacion() -> None:
    codigos = {c for c, _, _ in _semilla()}
    alternativos = {"predio.leer", "aplicacion.crear", "cosecha.crear", "notificacion.leer", "perfil.editar"}
    assert codigos.isdisjoint(alternativos)


def test_el_productor_no_recibe_visitas_consultar() -> None:
    """Decisión vigente: el productor ve sus visitas por la actividad unificada."""
    roles = {c: r for c, _, r in _semilla()}
    assert "PRODUCTOR" not in roles["visitas.consultar"]


def test_todo_permiso_que_exige_una_ruta_esta_en_la_semilla() -> None:
    """Si una ruta pidiera un código que no está en la BD, el día que la API lea la tabla nadie entraría."""
    usados = set()
    for archivo in (RAIZ / "src").rglob("*.py"):
        usados |= set(re.findall(r"requiere\(\s*\"([^\"]+)\"\s*\)", archivo.read_text(encoding="utf-8")))
    assert usados
    assert usados <= {c for c, _, _ in _semilla()}
