"""Acceso a datos de configuración. Fuentes: v_lote_app, v_trampa_app, v_trampa_lote_vigente,
fn_lote_app(usua), fn_trampa_app(usua), fn_lote_que_contiene(punto, instante)."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado


class RepositorioConfiguracion:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    # predios
    async def predios_visibles(self, usua_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Predios visibles")

    async def predio(self, pred_id: int) -> dict[str, Any] | None:
        raise NoImplementado("Predio")

    async def actualizar_predio(self, pred_id: int, cambios: dict[str, Any]) -> None:
        """Fija pred_fecha_actualizacion y pred_tecnico_actualizacion_id según la BD."""
        raise NoImplementado("Actualizar predio")

    async def mapa_predio(self, pred_id: int, instante: datetime) -> dict[str, Any]:
        """ST_AsGeoJSON de predio, lote_geometria vigente en ``instante``, reticula_celda y ubicacion_trampa."""
        raise NoImplementado("Mapa del predio")

    # lotes
    async def lotes_visibles(self, usua_id: int, pred_id: int | None) -> list[dict[str, Any]]:
        """``SELECT * FROM fn_lote_app(:usua)`` (ya filtrado por fn_lotes_visibles)."""
        raise NoImplementado("Lotes visibles")

    async def lote(self, lote_id: int) -> dict[str, Any] | None:
        raise NoImplementado("Lote")

    async def insertar_lote(self, pred_id: int, datos: dict[str, Any]) -> int:
        raise NoImplementado("Alta de lote")

    async def actualizar_lote(self, lote_id: int, cambios: dict[str, Any]) -> None:
        raise NoImplementado("Actualizar lote")

    async def versiones_geometria(self, lote_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Versiones de geometría")

    async def nueva_version_geometria(
        self, lote_id: int, geojson: str, desde: datetime, fuente: str, motivo: str
    ) -> int:
        """En una transacción: cierra la vigente (lotg_vigente_hasta = desde) e inserta la nueva.
        La BD valida geometría (fn_lote_geometria_valida) y no solape (EXCLUDE)."""
        raise NoImplementado("Nueva versión de geometría")

    # trampas
    async def trampas_visibles(
        self, usua_id: int, lote_id: int | None, pred_id: int | None
    ) -> list[dict[str, Any]]:
        """``fn_trampa_app(:usua)`` + v_trampa_lote_vigente."""
        raise NoImplementado("Trampas visibles")

    async def trampa_por_codigo(self, tram_codigo: str) -> dict[str, Any] | None:
        raise NoImplementado("Trampa por código")

    async def lote_que_contiene(self, lon: float, lat: float, instante: datetime) -> int | None:
        """``fn_lote_que_contiene(ST_SetSRID(ST_MakePoint(lon, lat), 4326), instante)``."""
        raise NoImplementado("Lote que contiene el punto")

    async def insertar_trampa(self, datos: dict[str, Any], ubicacion: dict[str, Any]) -> int:
        """trampa + ubicacion_trampa en una transacción (fn_trampa_valida, fn_ubicacion_trampa_valida)."""
        raise NoImplementado("Alta de trampa")

    async def actualizar_trampa(self, tram_id: int, cambios: dict[str, Any]) -> None:
        raise NoImplementado("Actualizar trampa")

    async def ubicaciones(self, tram_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Historial de ubicaciones")

    async def reubicar(self, tram_id: int, nueva: dict[str, Any]) -> int:
        """Cierra la vigente (ubic_fecha_fin = nueva.ubic_fecha) e inserta la nueva."""
        raise NoImplementado("Reubicación")

    # programa / retícula / paquete
    async def programa_vigente(self, pred_id: int, fecha: date) -> dict[str, Any] | None:
        """Vigencia [desde, hasta): ``prog_vigente_desde <= fecha AND (hasta IS NULL OR hasta > fecha)``."""
        raise NoImplementado("Programa vigente")

    async def versiones_programa(self, pred_id: int) -> list[dict[str, Any]]:
        raise NoImplementado("Versiones del programa")

    async def nueva_version_programa(self, pred_id: int, datos: dict[str, Any], creado_por: int) -> int:
        """Cierra la vigente y crea la siguiente + programa_umbral + programa_criterio_bpa."""
        raise NoImplementado("Nueva versión del programa")

    async def reticula(self, pred_id: int) -> dict[str, Any] | None:
        raise NoImplementado("Retícula")

    async def insertar_reticula(
        self, pred_id: int, resolucion_m: int, corte: date | None, celdas: list[dict[str, Any]]
    ) -> int:
        """La retícula es inmutable (fn_reticula_inmutable): una nueva resolución = nueva retícula."""
        raise NoImplementado("Alta de retícula")

    async def paquete_vigente(self, pred_id: int) -> dict[str, Any] | None:
        raise NoImplementado("Paquete vigente")

    async def registrar_paquete(self, pred_id: int, prog_id: int, hash_hex: str) -> UUID:
        raise NoImplementado("Registrar paquete")

    async def invalidar_paquetes(self, pred_id: int, motivo: str) -> None:
        raise NoImplementado("Invalidar paquetes")

    async def contar_lotes_sobre_umbral(self, usua_id: int) -> int:
        """Cuenta lotes visibles del agronomo cuyo MTD supera el umbral fitosanitario."""
        sql = """
        SELECT count(*)::int
          FROM sigat.v_lote_resumen_app vlra
          JOIN sigat.fn_lotes_visibles(:u) lv ON lv.lote_id = vlra.lote_id
        WHERE vlra.contraste = 'igual_o_superior_umbral'
          OR vlra.escenario IN ('Supresión', 'Área infestada')
        """
        resultado = await self._con.scalar(text(sql), {"u": usua_id})
        return int(resultado or 0)
