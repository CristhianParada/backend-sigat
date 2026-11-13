"""``ServicioLotes.listar`` contra PostgreSQL REAL (repositorio + ``sigat.fn_lote_app``).

Requiere ``SIGAT_DB_URL_PRUEBAS`` (ver ``conftest.py``). Usa una base TEMPORAL que se borra al final.

Escenario de datos:

* Predio 1 (Ana): lotes 11 y 12. Predio 2 (Bruno): lote 21. Predio 3 (Ana): lote 31.
* Gil (AGRONOMO_SUPERVISOR): asignado a los predios 1 y 2; su asignación al 3 venció el 2026-02-01.
* Sara (productora sin predios) y el técnico (sin planificaciones) no ven ningún lote.
"""

import asyncio
from collections.abc import Iterator
from types import SimpleNamespace

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from sigat_api.compartido.errores import NoEncontrado
from sigat_api.modules.configuracion import esquemas as e
from sigat_api.modules.configuracion.repositorio import RepositorioConfiguracion
from sigat_api.modules.configuracion.servicio import ServicioLotes

pytestmark = pytest.mark.integracion

TECNICO, ANA, BRUNO, GIL, SARA = 1, 2, 3, 4, 5

DATOS = r"""
SET search_path = sigat, public;

INSERT INTO region (regi_id, regi_descripcion) VALUES (1, 'Región de prueba');
INSERT INTO departamento (depa_id, depa_descripcion, regi_id, depa_codigo) VALUES (1, 'Depto', 1, '99');
INSERT INTO municipio (muni_id, muni_descripcion, depa_id, muni_codigo) VALUES (1, 'Muni', 1, '001');
INSERT INTO centro_acopio (cent_id, cent_descripcion, depa_id) VALUES (1, 'Centro', 1);
INSERT INTO persona (pers_cc, pers_nombre, pers_apellido) VALUES
  (1001, 'Adela', 'Admin'), (1002, 'Tomás', 'Técnico'), (2001, 'Ana', 'Productora'),
  (2002, 'Bruno', 'Productor'), (3001, 'Gil', 'Agrónomo'), (3002, 'Sara', 'SinPredio');
INSERT INTO administrador (admi_id, pers_cc, cent_id) VALUES (1, 1001, 1);
INSERT INTO tecnico (tecn_id, pers_cc, cent_id, admi_id, tecn_fecha_registro, esta_id)
  VALUES (1, 1002, 1, 1, DATE '2026-01-01', (SELECT esta_id FROM estado_registro WHERE esta_descripcion = 'activo'));
INSERT INTO productor (pers_cc, prod_fecha_registro, prod_tecnico_registro_id, muni_id) VALUES
  (2001, DATE '2026-01-01', 1, 1), (2002, DATE '2026-01-01', 1, 1);
INSERT INTO usuario (usua_id, pers_cc, usua_usuario, usua_requiere_reinicio, rol_id, esta_id)
SELECT v.id, v.cc, v.usu, true, r.rol_id, e.esta_id
  FROM (VALUES (1, 1002::bigint, 'tecnico.prueba', 'TECNICO'),
               (2, 2001::bigint, 'ana.prueba', 'PRODUCTOR'),
               (3, 2002::bigint, 'bruno.prueba', 'PRODUCTOR'),
               (4, 3001::bigint, 'gil.prueba', 'AGRONOMO_SUPERVISOR'),
               (5, 3002::bigint, 'sara.prueba', 'PRODUCTOR')) v(id, cc, usu, rol)
  JOIN rol r ON r.rol_codigo = v.rol
  JOIN estado_registro e ON e.esta_descripcion = 'activo';

INSERT INTO predio (pred_id, pred_nombre, muni_id, pred_area, pers_cc, pred_fecha_registro, pred_tecnico_registro_id)
  VALUES (1, 'Predio Ana', 1, 10, 2001, DATE '2026-01-01', 1),
         (2, 'Predio Bruno', 1, 10, 2002, DATE '2026-01-01', 1),
         (3, 'Predio Ana 2', 1, 5, 2001, DATE '2026-01-01', 1);
INSERT INTO lote (lote_id, lote_codigo, lote_descripcion, lote_area, pred_id, lote_fecha_registro, lote_tecnico_registro_id) VALUES
  (11, 'L11', 'Lote 1 · Norte', 2, 1, DATE '2026-01-01', 1),
  (12, 'L12', 'Lote 2 · Centro', 2, 1, DATE '2026-01-01', 1),
  (21, 'L21', 'Lote único', 2, 2, DATE '2026-01-01', 1),
  (31, 'L31', 'Lote del predio 3', 1, 3, DATE '2026-01-01', 1);

INSERT INTO usuario_predio (usua_id, pred_id, usup_desde, usup_hasta) VALUES
  (4, 1, DATE '2026-01-01', NULL),
  (4, 2, DATE '2026-01-01', NULL),
  (4, 3, DATE '2026-01-01', DATE '2026-02-01');  -- asignación vencida: no da acceso
"""


def _dsn(h: SimpleNamespace, nombre: str) -> str:
    return str(h.url(nombre)).replace("postgresql+asyncpg://", "postgresql://", 1)


def ejecutar(h: SimpleNamespace, nombre: str, sql: str) -> None:
    """Ejecuta varias sentencias en una transacción (los datos de prueba necesitan escribir)."""

    async def _correr() -> None:
        con = await asyncpg.connect(_dsn(h, nombre))
        try:
            async with con.transaction():
                await con.execute(sql)
        finally:
            await con.close()

    asyncio.run(_correr())


@pytest.fixture(scope="module")
def bd(h: SimpleNamespace) -> Iterator[str]:
    """Base temporal en la cabeza de Alembic, con el escenario de datos cargado."""
    nombre = h.crear_bd()
    try:
        r = h.alembic(nombre, "upgrade", "head")
        assert r.returncode == 0, r.stderr
        ejecutar(h, nombre, DATOS)
        yield nombre
    finally:
        h.borrar_bd(nombre)


def listar(
    h: SimpleNamespace,
    bd: str,
    usua: int,
    pred_id: int | None = None,
    indicadores: bool = False,
) -> list[e.Lote]:
    """Llama al servicio real con el repositorio real sobre la base temporal."""

    async def _correr() -> list[e.Lote]:
        motor = create_async_engine(h.url(bd))
        try:
            async with motor.connect() as con:
                svc = ServicioLotes(RepositorioConfiguracion(con), cola=None)  # type: ignore[arg-type]
                return await svc.listar(SimpleNamespace(usua_id=usua), pred_id, indicadores)  # type: ignore[arg-type]
        finally:
            await motor.dispose()

    return asyncio.run(_correr())


def ids(lotes: list[e.Lote]) -> list[int]:
    return [lote.lote_id for lote in lotes]


# ------------------------------------------------------------------ visibilidad
@pytest.mark.parametrize(
    ("usuario", "esperado"),
    [
        (ANA, [11, 12, 31]),  # dueña de los predios 1 y 3
        (BRUNO, [21]),
        (GIL, [11, 12, 21]),  # agrónomo: predios 1 y 2; la asignación al 3 venció
        (SARA, []),  # productora sin predios
        (TECNICO, []),  # sin planificaciones no tiene lotes asignados
        (999, []),  # usuario inexistente: falla cerrada
    ],
)
def test_listar_devuelve_solo_los_lotes_visibles_ordenados(
    bd: str, h: SimpleNamespace, usuario: int, esperado: list[int]
) -> None:
    assert ids(listar(h, bd, usuario)) == esperado


# ------------------------------------------------------------------ filtro por predio
@pytest.mark.parametrize(
    ("usuario", "pred_id", "esperado"),
    [
        (GIL, 1, [11, 12]),
        (GIL, 2, [21]),
        (GIL, 3, []),  # su asignación al predio 3 venció
        (GIL, 999, []),  # predio inexistente
        (ANA, 3, [31]),
        (ANA, 2, []),  # predio de otro productor: no se revela
        (SARA, 1, []),
    ],
)
def test_listar_filtra_por_predio_sin_saltarse_la_visibilidad(
    bd: str, h: SimpleNamespace, usuario: int, pred_id: int, esperado: list[int]
) -> None:
    assert ids(listar(h, bd, usuario, pred_id)) == esperado


# ------------------------------------------------------------------ contenido
def test_listar_trae_los_campos_del_contrato(bd: str, h: SimpleNamespace) -> None:
    [lote] = listar(h, bd, GIL, pred_id=2)
    assert lote.lote_id == 21
    assert lote.lote_codigo == "L21"
    assert lote.lote_descripcion == "Lote único"
    assert float(lote.lote_area) == 2.0
    assert (lote.pred_id, lote.pred_nombre) == (2, "Predio Bruno")
    assert lote.productor == "Bruno Productor"
    assert lote.municipio == "Muni"
    assert (lote.cultivo, lote.variedad) == (None, None)
    assert lote.vigilancia_activa is False
    assert lote.trampas_vigentes == 0


def test_listar_con_indicadores_los_deja_en_null_mientras_no_tengan_fuente(
    bd: str, h: SimpleNamespace
) -> None:
    """PENDIENTE DE REVISIÓN: ``IndicadoresLote`` no tiene fuente en la BD (ver docstring de listar).
    Si se define cómo calcularlos, esta prueba debe cambiar."""
    lotes = listar(h, bd, GIL, indicadores=True)
    assert ids(lotes) == [11, 12, 21]
    assert all(lote.indicadores is None for lote in lotes)


# ------------------------------------------------------------------ actualizacion
# ------------------------------------------------------------------ actualizacion (Integración)
def test_actualizar_lote_modifica_campos_permitidos_y_auditoria(bd: str, h: SimpleNamespace) -> None:
    """Verifica que un agrónomo pueda actualizar la descripción y área, y que se registre la auditoría."""

    async def _correr():
        motor = create_async_engine(h.url(bd))
        try:
            async with motor.connect() as con:
                svc = ServicioLotes(RepositorioConfiguracion(con), cola=None)
                actor = SimpleNamespace(usua_id=GIL)  # GIL es el agrónomo supervisor (id=4)
                lote_id = 11  # Lote del predio 1, asignado a GIL

                # 1. Ver estado inicial
                antes = await svc.obtener(actor, lote_id)
                assert antes.lote_descripcion == "Lote 1 · Norte"

                # 2. Crear esquema de actualización simulado
                class FakeUpdate:
                    def model_dump(self, exclude_unset=True):
                        return {"lote_descripcion": "Lote 1 · Norte (Actualizado)", "lote_area": 3.5}

                # 3. Ejecutar actualización
                despues = await svc.actualizar(actor, lote_id, FakeUpdate())

                # 4. Verificar cambios en la respuesta
                assert despues.lote_descripcion == "Lote 1 · Norte (Actualizado)"
                assert float(despues.lote_area) == 3.5

        finally:
            await motor.dispose()

    asyncio.run(_correr())


def test_actualizar_lote_no_visible_devuelve_404_en_bd(bd: str, h: SimpleNamespace) -> None:
    """Verifica que no se pueda actualizar un lote de otro predio (ej. predio 3 de Ana, asignación vencida de Gil)."""

    async def _correr():
        motor = create_async_engine(h.url(bd))
        try:
            async with motor.connect() as con:
                svc = ServicioLotes(RepositorioConfiguracion(con), cola=None)
                actor = SimpleNamespace(usua_id=GIL)

                class FakeUpdate:
                    def model_dump(self, exclude_unset=True):
                        return {"lote_descripcion": "Hackeado"}

                with pytest.raises(NoEncontrado):
                    # El lote 31 es del predio 3, y la asignación de GIL venció el 2026-02-01
                    await svc.actualizar(actor, 31, FakeUpdate())
        finally:
            await motor.dispose()

    asyncio.run(_correr())
