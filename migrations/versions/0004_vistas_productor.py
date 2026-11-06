"""Vistas del productor: ``v_actividad_lote_detalle`` (F1), ``v_cosecha_lote_vigente`` (F2) y ``v_aplicacion_ultima_lote`` (F3).

Qué hace: ejecuta ``bd/sql/13_vistas_productor.sql``, que SOLO AGREGA tres vistas y sus funciones
filtradas por usuario (``fn_actividad_lote_detalle``, ``fn_cosecha_lote_vigente``,
``fn_aplicacion_ultima_lote``, sobre ``fn_lotes_visibles``). No crea ni modifica tablas, columnas, restricciones, índices ni datos, y no
reemplaza vistas existentes. Es idempotente (``CREATE OR REPLACE``): una base instalada con
``00_instalar_todo.sql``, que ya incluye el archivo, queda igual.

Por qué en un archivo nuevo y no en ``03_vistas.sql``: la revisión 0001 ejecuta ``03_vistas.sql``
al instalar desde cero; editarlo cambiaría retroactivamente lo que hace 0001. Mismo patrón que
0003 / ``12_ajustes_v9_1.sql``.

``downgrade`` elimina SOLO los seis objetos que crea esta revisión (primero las funciones, que
dependen del tipo de fila de las vistas). No toca ``v_actividad_lote`` ni ninguna otra vista.

Revisión: 0004
"""

from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

ARCHIVO = Path(__file__).resolve().parents[2] / "bd" / "sql" / "13_vistas_productor.sql"


def upgrade() -> None:
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(ARCHIVO.read_text(encoding="utf-8")))  # type: ignore[union-attr]


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS sigat.fn_aplicacion_ultima_lote(integer)")
    op.execute("DROP FUNCTION IF EXISTS sigat.fn_cosecha_lote_vigente(integer)")
    op.execute("DROP FUNCTION IF EXISTS sigat.fn_actividad_lote_detalle(integer)")
    op.execute("DROP VIEW IF EXISTS sigat.v_aplicacion_ultima_lote")
    op.execute("DROP VIEW IF EXISTS sigat.v_cosecha_lote_vigente")
    op.execute("DROP VIEW IF EXISTS sigat.v_actividad_lote_detalle")
