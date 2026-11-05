"""Semilla de ``permiso`` (25) y ``rol_permiso`` (54) con la matriz de ``permisos.py`` (RNF-015).

Qué hace: ejecuta ``bd/sql/15_semilla_permisos.sql``. Si las dos tablas están vacías, inserta los
mismos códigos (``area.accion``) y las mismas asignaciones por rol que la API aplica hoy con
``requiere(...)``. Si ya contienen exactamente esa matriz, no hace nada. Si contienen otra cosa
(carga parcial o distinta), se DETIENE con un error que enumera las diferencias, sin tocar filas.

``permisos.py`` sigue siendo la fuente de verdad del backend; la BD queda como reflejo exacto
(decisión del responsable del proyecto, 2026-11-04). Una prueba unitaria impide que diverjan.

``downgrade`` NO borra filas: no se distinguen con seguridad de una carga institucional idéntica.
Volver a aplicar ``upgrade`` después es seguro (encuentra la misma matriz y continúa).

Revisión: 0006
"""

from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

ARCHIVO = Path(__file__).resolve().parents[2] / "bd" / "sql" / "15_semilla_permisos.sql"


def upgrade() -> None:
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(ARCHIVO.read_text(encoding="utf-8")))  # type: ignore[union-attr]


def downgrade() -> None:
    """Sin cambios: la matriz sembrada no se distingue de una carga institucional idéntica."""
