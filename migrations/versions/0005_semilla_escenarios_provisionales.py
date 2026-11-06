"""Semilla PROVISIONAL del catálogo ``escenario_trampeo`` (RN-002, pendiente P-02).

Qué hace: ejecuta ``bd/sql/14_semilla_escenarios_provisionales.sql``, que inserta los 4 escenarios
(Área infestada, Supresión, Erradicación y Exclusión; valores del informe de consumo §10.1) SOLO si la
tabla está vacía. Si ya tiene exactamente esos 4, no hace nada. Si tiene otra cosa (carga parcial,
distinta u oficial), se DETIENE con un error que enumera las diferencias, sin tocar ninguna fila.

Provisionales por decisión del responsable del proyecto (2026-11-04): permiten desarrollar y probar
mientras ICA/Agronomía los valida; ``esce_fuente`` lo indica en cada fila.

``downgrade`` NO borra filas: los escenarios pueden quedar referenciados por ``programa_umbral`` e
``indice_mtd``, y no se distinguen con seguridad de una carga institucional idéntica. Volver a aplicar
``upgrade`` después es seguro (encuentra los mismos 4 y continúa).

Revisión: 0005
"""

from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

ARCHIVO = Path(__file__).resolve().parents[2] / "bd" / "sql" / "14_semilla_escenarios_provisionales.sql"


def upgrade() -> None:
    crudo = op.get_bind().connection.driver_connection
    await_only(crudo.execute(ARCHIVO.read_text(encoding="utf-8")))  # type: ignore[union-attr]


def downgrade() -> None:
    """Sin cambios: los escenarios pueden estar referenciados y no se distinguen de una carga oficial."""
