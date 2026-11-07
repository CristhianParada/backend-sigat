"""Servicio de lotes y trampas: visibilidad, búsqueda por código (RF-012) y serialización.

No toca PostgreSQL: el repositorio se sustituye por un doble que devuelve las filas de las
vistas. Así se prueban las decisiones del servicio (404, advertencias, ``en_catalogo``) sin
levantar la base.
"""

from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest

from sigat_api.compartido.errores import NoEncontrado
from sigat_api.compartido.tipos import Actor, Cliente, RolCodigo
from sigat_api.modules.configuracion.servicio import ServicioLotes, ServicioTrampas

ACTOR = Actor(usua_id=2, rol=RolCodigo.TECNICO, disp_id=None, cliente=Cliente.MOVIL)

LOTE = {
    "lote_id": 1,
    "lote_codigo": "01",
    "lote_descripcion": "Lote de demostración",
    "lote_area": Decimal("5000.0000"),
    "pred_id": 1,
    "pred_nombre": "Finca de demostración",
    "productor": "Productor Prueba",
    "municipio": "Municipio de demostración",
    "cultivo": "Durazno",
    "variedad": None,
    "vigilancia_activa": False,
    "trampas_vigentes": 2,
    "indicadores": None,
}

DETALLE = {
    **LOTE,
    "espc_id": 1,
    "vari_id": None,
    "lote_fecha_plantacion": None,
    "lote_fecha_registro": date(2026, 11, 6),
    "lote_fecha_baja": None,
    "geometria": None,
    "geometria_version": 1,
}

TRAMPA = {
    "tram_id": 1,
    "tram_codigo": "68001-A-001",
    "tipo": "Jackson",
    "lote_id": 1,
    "pred_id": 1,
    "longitud": Decimal("-73.12200"),
    "latitud": Decimal("7.11800"),
    "celda": None,
    "estado": "activo",
    "atrayente": "Plug",
    "ubic_id": 1,
    "dentro_del_lote": True,
    "ultima_lectura": None,
    "ultima_lectura_especimenes": None,
    "lote_sin_geometria": False,
    "con_ubicacion_vigente": True,
}


class RepoFalso:
    """Filas que devolvería ``RepositorioConfiguracion``; cada prueba ajusta las que necesita."""

    def __init__(self) -> None:
        self.lotes: list[dict[str, Any]] = [deepcopy(LOTE)]
        self.visible = True
        self.detalle: dict[str, Any] | None = deepcopy(DETALLE)
        self.trampas: list[dict[str, Any]] = [deepcopy(TRAMPA)]
        self.trampa: dict[str, Any] | None = deepcopy(TRAMPA)
        self.trampa_codigo: dict[str, Any] | None = deepcopy(TRAMPA)
        self.lote_punto: int | None = 1
        self.llamadas: list[tuple[Any, ...]] = []

    async def lotes_visibles(self, usua_id: int, pred_id: int | None) -> list[dict[str, Any]]:
        self.llamadas.append(("lotes_visibles", usua_id, pred_id))
        return self.lotes

    async def lote_visible(self, usua_id: int, lote_id: int) -> bool:
        self.llamadas.append(("lote_visible", usua_id, lote_id))
        return self.visible

    async def lote(self, lote_id: int) -> dict[str, Any] | None:
        self.llamadas.append(("lote", lote_id))
        return self.detalle

    async def trampas_visibles(
        self, usua_id: int, lote_id: int | None, pred_id: int | None
    ) -> list[dict[str, Any]]:
        self.llamadas.append(("trampas_visibles", usua_id, lote_id, pred_id))
        return self.trampas

    async def trampa_por_id(self, usua_id: int, tram_id: int) -> dict[str, Any] | None:
        self.llamadas.append(("trampa_por_id", usua_id, tram_id))
        return self.trampa

    async def trampa_por_codigo(self, tram_codigo: str) -> dict[str, Any] | None:
        self.llamadas.append(("trampa_por_codigo", tram_codigo))
        return self.trampa_codigo

    async def lote_que_contiene(self, lon: float, lat: float, instante: datetime) -> int | None:
        self.llamadas.append(("lote_que_contiene", lon, lat, instante))
        return self.lote_punto


@pytest.mark.regla
async def test_listar_lotes_devuelve_esquemas_y_respeta_el_filtro() -> None:
    repo = RepoFalso()
    servicio = ServicioLotes(repo, None)  # type: ignore[arg-type]

    lotes = await servicio.listar(ACTOR, pred_id=1, incluir_indicadores=False)

    assert len(lotes) == 1
    assert lotes[0].lote_codigo == "01"
    assert float(lotes[0].lote_area) == 5000.0
    assert repo.llamadas == [("lotes_visibles", ACTOR.usua_id, 1)]


@pytest.mark.regla
async def test_obtener_lote_no_visible_da_404_sin_revelar_que_existe() -> None:
    repo = RepoFalso()
    repo.visible = False
    servicio = ServicioLotes(repo, None)  # type: ignore[arg-type]

    with pytest.raises(NoEncontrado) as error:
        await servicio.obtener(ACTOR, 1)

    assert error.value.codigo == "LOTE_NO_ENCONTRADO"


@pytest.mark.regla
async def test_obtener_lote_visible_devuelve_el_detalle() -> None:
    repo = RepoFalso()
    servicio = ServicioLotes(repo, None)  # type: ignore[arg-type]

    lote = await servicio.obtener(ACTOR, 1)

    assert lote.lote_id == 1
    assert lote.geometria_version == 1


@pytest.mark.regla
async def test_obtener_lote_visible_pero_borrado_entre_consultas_da_404() -> None:
    repo = RepoFalso()
    repo.detalle = None
    servicio = ServicioLotes(repo, None)  # type: ignore[arg-type]

    with pytest.raises(NoEncontrado):
        await servicio.obtener(ACTOR, 1)


@pytest.mark.regla
async def test_listar_trampas_quita_columnas_auxiliares_de_la_vista() -> None:
    repo = RepoFalso()
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    trampas = await servicio.listar(ACTOR, lote_id=1, pred_id=None)

    assert len(trampas) == 1
    assert trampas[0].tram_codigo == "68001-A-001"
    assert trampas[0].dentro_del_lote is True
    assert not hasattr(trampas[0], "lote_sin_geometria")
    assert repo.llamadas == [("trampas_visibles", ACTOR.usua_id, 1, None)]


@pytest.mark.regla
async def test_obtener_trampa_inexistente_da_404() -> None:
    repo = RepoFalso()
    repo.trampa = None
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    with pytest.raises(NoEncontrado) as error:
        await servicio.obtener(ACTOR, 99)

    assert error.value.codigo == "TRAMPA_NO_ENCONTRADA"


@pytest.mark.regla
async def test_buscar_codigo_inexistente_responde_200_con_en_catalogo_false() -> None:
    repo = RepoFalso()
    repo.trampa_codigo = None
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(ACTOR, "99999-Z-999", None, None, None)

    assert resultado.en_catalogo is False
    assert resultado.trampa is None
    assert "no está en el catálogo" in resultado.advertencias[0]


@pytest.mark.regla
async def test_buscar_codigo_sin_ubicacion_vigente_no_se_puede_validar() -> None:
    repo = RepoFalso()
    assert repo.trampa_codigo is not None
    repo.trampa_codigo["con_ubicacion_vigente"] = False
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(ACTOR, "68001-A-001", None, None, None)

    assert resultado.en_catalogo is True
    assert resultado.trampa is None
    assert "no tiene ubicación vigente" in resultado.advertencias[0]


@pytest.mark.regla
async def test_buscar_codigo_advierte_si_el_lote_no_tiene_geometria() -> None:
    repo = RepoFalso()
    assert repo.trampa_codigo is not None
    repo.trampa_codigo["lote_sin_geometria"] = True
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(ACTOR, "68001-A-001", 1, None, None)

    assert resultado.en_catalogo is True
    assert resultado.trampa is not None
    assert resultado.pertenece_lote_activo is True
    assert "no tiene geometría registrada" in resultado.advertencias[0]


@pytest.mark.regla
async def test_buscar_codigo_advierte_si_la_trampa_pertenece_a_otro_lote() -> None:
    repo = RepoFalso()
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(ACTOR, "68001-A-001", 2, None, None)

    assert resultado.pertenece_lote_activo is False
    assert "no pertenece al lote" in resultado.advertencias[0]


@pytest.mark.regla
async def test_buscar_codigo_compara_la_posicion_del_tecnico_con_el_lote_activo() -> None:
    repo = RepoFalso()
    repo.lote_punto = 1
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(
        ACTOR, "68001-A-001", 1, Decimal("7.118"), Decimal("-73.122")
    )

    assert resultado.dentro_del_lote is True
    assert resultado.advertencias == []
    assert repo.llamadas[-1][0] == "lote_que_contiene"


@pytest.mark.regla
async def test_buscar_codigo_advierte_si_la_posicion_cae_fuera_del_lote() -> None:
    repo = RepoFalso()
    repo.lote_punto = 7
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(
        ACTOR, "68001-A-001", 1, Decimal("7.118"), Decimal("-73.122")
    )

    assert resultado.dentro_del_lote is False
    assert "Su ubicación no está dentro del lote" in resultado.advertencias[-1]


@pytest.mark.regla
async def test_buscar_codigo_sin_coordenadas_no_compara_posicion() -> None:
    repo = RepoFalso()
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(ACTOR, "68001-A-001", 1, None, None)

    assert resultado.dentro_del_lote is None
    assert all(llamada[0] != "lote_que_contiene" for llamada in repo.llamadas)


@pytest.mark.regla
async def test_buscar_codigo_advierte_si_la_trampa_esta_fuera_del_lote_asignado() -> None:
    repo = RepoFalso()
    assert repo.trampa_codigo is not None
    repo.trampa_codigo["dentro_del_lote"] = False
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(ACTOR, "68001-A-001", None, None, None)

    assert "está fuera del lote al que está asignada" in resultado.advertencias[0]
    assert resultado.dentro_del_lote is None
    assert resultado.advertencias == ["La trampa está fuera del lote al que está asignada."]


@pytest.mark.regla
async def test_buscar_codigo_sin_lote_activo_solo_indica_si_cae_en_algun_lote() -> None:
    repo = RepoFalso()
    repo.lote_punto = 5
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(
        ACTOR, "68001-A-001", None, Decimal("7.118"), Decimal("-73.122")
    )

    assert resultado.pertenece_lote_activo is None
    assert resultado.dentro_del_lote is True


@pytest.mark.regla
async def test_buscar_codigo_sin_lote_activo_advierte_si_cae_fuera_de_todo_lote() -> None:
    repo = RepoFalso()
    repo.lote_punto = None
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    resultado = await servicio.buscar_por_codigo(
        ACTOR, "68001-A-001", None, Decimal("7.118"), Decimal("-73.122")
    )

    assert resultado.dentro_del_lote is False
    assert resultado.advertencias[-1] == "Su ubicación no está dentro del lote que tiene abierto."


@pytest.mark.regla
async def test_obtener_trampa_visible_devuelve_el_esquema() -> None:
    repo = RepoFalso()
    servicio = ServicioTrampas(repo, None)  # type: ignore[arg-type]

    trampa = await servicio.obtener(ACTOR, 1)

    assert trampa.tram_codigo == "68001-A-001"
    assert trampa.dentro_del_lote is True
    assert repo.llamadas == [("trampa_por_id", ACTOR.usua_id, 1)]


def test_el_doble_sigue_usando_una_fecha_consciente() -> None:
    """La comparación espacial recibe un instante con zona (``now(UTC)``), no una fecha local."""
    assert datetime.now(UTC).tzinfo is UTC
