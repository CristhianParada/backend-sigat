"""Pruebas unitarias de ``ServicioLotes.actualizar``."""

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from sigat_api.compartido.errores import NoEncontrado
from sigat_api.modules.configuracion.servicio import ServicioLotes


class RepoFalsoActualizar:
    """Doble de prueba para simular el repositorio en actualizar."""

    def __init__(self):
        self.lotes_visibles_ids = {10, 20}  # El actor solo puede ver estos
        self.actualizado = False
        self.cambios_recibidos = {}

    async def lote_visible(self, usua_id: int, lote_id: int) -> bool:
        return lote_id in self.lotes_visibles_ids and usua_id == 7

    async def actualizar_lote(self, lote_id: int, cambios: dict) -> None:
        self.actualizado = True
        self.cambios_recibidos = cambios

    # CORRECCIÓN CLAVE: Devolver un diccionario completo que cumpla con el esquema LoteDetalle
    async def lote(self, lote_id: int) -> dict | None:
        if lote_id in self.lotes_visibles_ids:
            return {
                "lote_id": lote_id,
                "lote_codigo": "L10",
                "lote_descripcion": "Actualizado",
                "lote_area": 5.0,
                "pred_id": 1,
                "pred_nombre": "Predio Test",
                "productor": "Productor Test",
                "municipio": "Municipio Test",
                "cultivo": None,
                "variedad": None,
                "vigilancia_activa": True,
                "trampas_vigentes": 0,
                "espc_id": None,
                "vari_id": None,
                "lote_fecha_plantacion": None,
                "lote_fecha_registro": date(2023, 1, 1),
                "lote_fecha_baja": None,
                "geometria": None,
                "geometria_version": None,
            }
        return None


def _servicio_actualizar():
    repo = RepoFalsoActualizar()
    return ServicioLotes(repo, cola=None), repo


ACTOR = SimpleNamespace(usua_id=7)


def test_actualizar_lote_exitoso():
    svc, repo = _servicio_actualizar()

    # Simulamos el esquema de Pydantic con solo algunos campos
    class FakeSchema:
        def model_dump(self, exclude_unset=True):
            return {"lote_descripcion": "Nuevo nombre", "lote_area": 5.0}

    resultado = asyncio.run(svc.actualizar(ACTOR, 10, FakeSchema()))

    assert repo.actualizado is True

    # Verificamos que los campos de auditoría SE INYECTARON en el diccionario
    assert "lote_descripcion" in repo.cambios_recibidos
    assert "lote_area" in repo.cambios_recibidos
    assert repo.cambios_recibidos["lote_tecnico_actualizacion_id"] == 7
    assert "lote_fecha_actualizacion" in repo.cambios_recibidos

    # Verificamos que el servicio devolvió el objeto correctamente
    assert resultado.lote_id == 10
    assert resultado.lote_descripcion == "Actualizado"  # Viene del mock de `lote`


def test_actualizar_lote_no_visible_devuelve_404():
    svc, repo = _servicio_actualizar()

    class FakeSchema:
        def model_dump(self, exclude_unset=True):
            return {"lote_descripcion": "Hack"}

    with pytest.raises(NoEncontrado) as exc:
        asyncio.run(svc.actualizar(ACTOR, 999, FakeSchema()))  # 999 no está en lotes_visibles_ids

    assert "no es visible" in str(exc.value)
    assert repo.actualizado is False  # Nunca llegó a la BD
