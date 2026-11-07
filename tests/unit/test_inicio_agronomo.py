"""Pruebas unitarias para el endpoint GET /api/v1/yo/inicio con rol AGRONOMO_SUPERVISOR."""

import os
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pydantic import SecretStr

from sigat_api.api.fabricas import (
    servicio_lotes,
    servicio_notificaciones,
    servicio_planificacion,
    servicio_revision,
)
from sigat_api.compartido.tipos import Cliente, RolCodigo
from sigat_api.config import Configuracion
from sigat_api.infra.seguridad.tokens import ServicioTokens


def _generar_token(rol: RolCodigo, usua_id: int = 1) -> str:
    """Genera un token JWT firmado válido para las pruebas unitarias."""
    cfg = Configuracion(jwt_secreto=SecretStr(os.environ["SIGAT_JWT_SECRETO"]))
    token, _ = ServicioTokens(cfg).emitir_acceso(usua_id, rol, None, Cliente.WEB)
    return token


def test_inicio_agronomo_devuelve_indicadores(cliente: TestClient) -> None:
    mock_notis = AsyncMock()
    mock_notis.conteo.return_value.no_leidas = 2

    mock_revision = AsyncMock()
    mock_revision.contar_por_revisar.return_value = 5

    mock_planif = AsyncMock()
    mock_planif.contar_pendientes.return_value = 3
    mock_planif.contar_en_curso.return_value = 1

    mock_lotes = AsyncMock()
    mock_lotes.contar_sobre_umbral.return_value = 4

    cliente.app.dependency_overrides[servicio_notificaciones] = lambda: mock_notis
    cliente.app.dependency_overrides[servicio_revision] = lambda: mock_revision
    cliente.app.dependency_overrides[servicio_planificacion] = lambda: mock_planif
    cliente.app.dependency_overrides[servicio_lotes] = lambda: mock_lotes

    token = _generar_token(RolCodigo.AGRONOMO_SUPERVISOR, usua_id=10)

    respuesta = cliente.get("/api/v1/yo/inicio", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    datos = respuesta.json()

    assert datos["rol"] == "AGRONOMO_SUPERVISOR"
    assert datos["notificaciones_no_leidas"] == 2
    assert datos["agronomo"] == {
        "registros_por_revisar": 5,
        "planificaciones_pendientes": 3,
        "actividades_en_curso": 1,
        "lotes_sobre_umbral": 4,
    }
    assert datos["tecnico"] is None
    assert datos["productor"] is None


def test_inicio_otro_rol_no_incluye_bloque_agronomo(cliente: TestClient) -> None:
    mock_notis = AsyncMock()
    mock_notis.conteo.return_value.no_leidas = 0

    mock_revision = AsyncMock()
    mock_planif = AsyncMock()
    mock_lotes = AsyncMock()

    cliente.app.dependency_overrides[servicio_notificaciones] = lambda: mock_notis
    cliente.app.dependency_overrides[servicio_revision] = lambda: mock_revision
    cliente.app.dependency_overrides[servicio_planificacion] = lambda: mock_planif
    cliente.app.dependency_overrides[servicio_lotes] = lambda: mock_lotes

    token = _generar_token(RolCodigo.ADMINISTRADOR, usua_id=1)

    respuesta = cliente.get("/api/v1/yo/inicio", headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["rol"] == "ADMINISTRADOR"
    assert datos["agronomo"] is None

    # Verificamos que al no ser agronomo, nunca consulto sus metodos
    mock_revision.contar_por_revisar.assert_not_called()
    mock_planif.contar_pendientes.assert_not_called()
    mock_planif.contar_en_curso.assert_not_called()
    mock_lotes.contar_sobre_umbral.assert_not_called()


def test_inicio_sin_token_da_401(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/v1/yo/inicio")
    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"].startswith("application/problem+json")
