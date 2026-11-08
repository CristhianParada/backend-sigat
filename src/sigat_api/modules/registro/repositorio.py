"""Acceso a datos del núcleo de registro. SOLO INSERT en tablas versionadas (ADR-03)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from sigat_api.compartido.errores import NoImplementado
from sigat_api.modules.registro.dominio import EstadoPrevio


class RepositorioRegistro:
    def __init__(self, con: AsyncConnection) -> None:
        self._con = con

    async def estado_previo(
        self,
        entidad: str,
        registro_id: UUID,
        lote_id: int | None,
        tram_id: int | None,
        t_observacion: datetime,
    ) -> EstadoPrevio:
        """Versión vigente del registro lógico + última t_observacion de la serie + solapamiento (R-T5)."""
        raise NoImplementado("Estado previo del registro")

    async def insertar_version(self, entidad: str, fila: dict[str, Any]) -> UUID:
        """INSERT en la tabla de la entidad. La BD valida versión n+1 y t_observacion inmutable
        (fn_registro_version_valida) y fija t_sincronizacion."""
        raise NoImplementado("Insertar versión")

    async def insertar_visita(self, fila: dict[str, Any], lote_ids: list[int]) -> None:
        """visita + visita_lote (todas del mismo predio: FK compuesta)."""
        raise NoImplementado("Insertar visita")

    async def actualizar_revision_visita(
        self, visi_id: UUID, estado: str, motivo: str | None, usua_id: int
    ) -> None:
        """Único UPDATE permitido sobre visita (fn_visita_integridad)."""
        raise NoImplementado("Revisión de visita")

    async def visitas(self, usua_id: int, filtros: dict[str, Any], cursor: str | None) -> Any:
        raise NoImplementado("Visitas")

    async def lecturas(self, usua_id: int, filtros: dict[str, Any], cursor: str | None) -> Any:
        """v_lectura_vigente por defecto; ``incluir_versiones`` lee lectura_trampa completa."""
        raise NoImplementado("Lecturas")

    async def versiones(self, entidad: str, registro_id: UUID) -> list[dict[str, Any]]:
        raise NoImplementado("Versiones")

    async def registros_por_revisar(self, usua_id: int, estado: str | None, cursor: str | None) -> Any:
        """v_registro_campo filtrado por predios visibles del agrónomo."""
        raise NoImplementado("Registros por revisar")

    async def actividad(self, usua_id: int, filtros: dict[str, Any], cursor: str | None) -> Any:
        """fn_actividad_lote(:usua) + hallazgos y etapas."""
        raise NoImplementado("Actividad")

    async def autorreportes(self, entidad: str, usua_id: int, lote_id: int | None, cursor: str | None) -> Any:
        raise NoImplementado("Autorreportes")

    async def contar_por_revisar(self, usua_id: int) -> int:
        sql = """
        SELECT count(*)::int
         FROM sigat.v_registro_campo vrc
         JOIN sigat.v_acceso_predio vap ON vap.pred_id = vrc.pred_id
        WHERE vap.usua_id = :u
        """
        resultado = await self._con.scalar(text(sql), {"u": usua_id})
        return int(resultado or 0)
