"""Casos de uso de configuración."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sigat_api.compartido.errores import NoEncontrado, NoImplementado
from sigat_api.compartido.tipos import Actor
from sigat_api.infra.cola.cola import Cola
from sigat_api.modules.configuracion import esquemas as e
from sigat_api.modules.configuracion.repositorio import RepositorioConfiguracion

# Columnas auxiliares que trae la vista para saber por qué no se puede confirmar la posición.
# No forman parte del contrato HTTP: se quitan antes de construir el esquema de trampa.
_AUXILIARES_TRAMPA = frozenset({"lote_sin_geometria", "con_ubicacion_vigente"})


def _trampa(fila: dict[str, Any]) -> e.Trampa:
    """Construye el esquema de trampa a partir de una fila de la vista de la aplicación."""
    return e.Trampa(**{k: v for k, v in fila.items() if k not in _AUXILIARES_TRAMPA})


class ServicioPredios:
    def __init__(self, repo: RepositorioConfiguracion, cola: Cola) -> None:
        self._repo = repo
        self._cola = cola

    async def listar(self, actor: Actor) -> list[e.Predio]:
        raise NoImplementado("Predios")

    async def obtener(self, actor: Actor, pred_id: int) -> e.Predio:
        raise NoImplementado("Predio")

    async def actualizar(self, actor: Actor, pred_id: int, s: e.ActualizacionPredio) -> e.Predio:
        """Cartografía del admin (web ``updateFarm``). Invalida el paquete de campo."""
        raise NoImplementado("Actualizar predio")

    async def poner_geometria(self, actor: Actor, pred_id: int, s: e.EntradaGeometria) -> e.Predio:
        """Valida SRID 4326, ST_IsValid y que contenga a los lotes vigentes. Invalida el paquete."""
        raise NoImplementado("Geometría del predio")

    async def mapa(self, actor: Actor, pred_id: int, instante: datetime | None) -> e.MapaPredio:
        """``instante`` permite ver el contorno vigente en una fecha pasada (ADR-06)."""
        raise NoImplementado("Mapa del predio")


class ServicioLotes:
    def __init__(self, repo: RepositorioConfiguracion, cola: Cola) -> None:
        self._repo = repo
        self._cola = cola

    async def listar(self, actor: Actor, pred_id: int | None, incluir_indicadores: bool) -> list[e.Lote]:
        """Técnico: solo los lotes de sus actividades vigentes (v_asignacion_lote_tecnico) — lo
        resuelve fn_lotes_visibles. El estado de jornada (pendiente/en curso/visitado) NO viene del
        servidor: lo deriva el móvil de su visita local (CONCORDANCIA §4.1).

        ``incluir_indicadores`` es de la web (tarjetas del panel de administración). Los indicadores
        se calculan con las visitas, el programa y los periodos de trampeo, que son de otro sprint;
        mientras tanto el bloque va en ``null`` (lo admite el esquema) en vez de inventar cifras.
        """
        filas = await self._repo.lotes_visibles(actor.usua_id, pred_id)
        return [e.Lote(**fila) for fila in filas]

    async def obtener(self, actor: Actor, lote_id: int) -> e.LoteDetalle:
        """Detalle del lote. Si no es visible para el actor -> 404 (no 403: no se revela que el
        lote existe pero pertenece a otro usuario)."""
        if not await self._repo.lote_visible(actor.usua_id, lote_id):
            raise NoEncontrado("El lote no existe o no es visible para usted.", codigo="LOTE_NO_ENCONTRADO")
        fila = await self._repo.lote(lote_id)
        if fila is None:
            raise NoEncontrado("El lote no existe o no es visible para usted.", codigo="LOTE_NO_ENCONTRADO")
        return e.LoteDetalle(**fila)

    async def crear(self, actor: Actor, pred_id: int, s: e.NuevoLote) -> e.LoteDetalle:
        """(pred_id, lote_codigo) único. Si trae geometría, crea la versión 1."""
        raise NoImplementado("Alta de lote")

    async def actualizar(self, actor: Actor, lote_id: int, s: e.ActualizacionLote) -> e.LoteDetalle:
        """Web ``updateLot``: el 'propietario' no se edita aquí (es el productor del predio)."""
        raise NoImplementado("Actualizar lote")

    async def geometrias(self, actor: Actor, lote_id: int) -> list[e.VersionGeometriaLote]:
        raise NoImplementado("Versiones de geometría")

    async def nueva_geometria(
        self, actor: Actor, lote_id: int, s: e.EntradaGeometria
    ) -> e.VersionGeometriaLote:
        """ADR-06: genera evento de cambio de área (puede afectar la normalización del MTD) e invalida paquete."""
        raise NoImplementado("Nueva geometría de lote")


class ServicioTrampas:
    def __init__(self, repo: RepositorioConfiguracion, cola: Cola) -> None:
        self._repo = repo
        self._cola = cola

    async def listar(self, actor: Actor, lote_id: int | None, pred_id: int | None) -> list[e.Trampa]:
        """Trampas visibles para el actor. El permiso lo resuelve ``fn_trampa_app`` (a través de
        ``fn_lotes_visibles``); ``lote_id`` y ``pred_id`` solo acotan el resultado."""
        filas = await self._repo.trampas_visibles(actor.usua_id, lote_id, pred_id)
        return [_trampa(fila) for fila in filas]

    async def obtener(self, actor: Actor, tram_id: int) -> e.Trampa:
        """Detalle de la trampa. Si no es visible para el actor -> 404 (no 403)."""
        fila = await self._repo.trampa_por_id(actor.usua_id, tram_id)
        if fila is None:
            raise NoEncontrado(
                "La trampa no existe o no es visible para usted.", codigo="TRAMPA_NO_ENCONTRADA"
            )
        return _trampa(fila)

    async def buscar_por_codigo(
        self,
        actor: Actor,
        tram_codigo: str,
        lote_activo: int | None,
        lat: Decimal | None,
        lng: Decimal | None,
    ) -> e.BusquedaTrampa:
        """RF-012: compara trampa–lote–ubicación. ADVIERTE, no bloquea. Código inexistente ->
        200 con ``en_catalogo=false`` (no 404), para que el móvil muestre su pantalla de validación.

        La búsqueda es sobre todo el catálogo: el técnico tiene que poder validar la trampa que
        tiene delante aunque no sea la que tiene asignada (por eso las advertencias existen).
        """
        fila = await self._repo.trampa_por_codigo(tram_codigo)
        if fila is None:
            return e.BusquedaTrampa(
                trampa=None,
                en_catalogo=False,
                advertencias=[f"El código {tram_codigo} no está en el catálogo de trampas."],
            )
        if not fila.get("con_ubicacion_vigente"):
            return e.BusquedaTrampa(
                trampa=None,
                en_catalogo=True,
                advertencias=[f"La trampa {tram_codigo} no tiene ubicación vigente: no se puede validar."],
            )

        trampa = _trampa(fila)
        advertencias: list[str] = []

        pertenece = None if lote_activo is None else trampa.lote_id == lote_activo
        if pertenece is False:
            advertencias.append("La trampa no pertenece al lote que tiene abierto.")

        if fila.get("lote_sin_geometria"):
            advertencias.append(
                "El lote no tiene geometría registrada: no se puede comprobar la posición de la trampa."
            )
        elif fila.get("dentro_del_lote") is False:
            advertencias.append("La trampa está fuera del lote al que está asignada.")

        dentro_del_lote: bool | None = None
        if lat is not None and lng is not None:
            lote_del_punto = await self._repo.lote_que_contiene(float(lng), float(lat), datetime.now(UTC))
            if lote_activo is not None:
                dentro_del_lote = lote_del_punto == lote_activo
            else:
                dentro_del_lote = lote_del_punto is not None
            if not dentro_del_lote:
                advertencias.append("Su ubicación no está dentro del lote que tiene abierto.")

        return e.BusquedaTrampa(
            trampa=trampa,
            en_catalogo=True,
            pertenece_lote_activo=pertenece,
            dentro_del_lote=dentro_del_lote,
            advertencias=advertencias,
        )

    async def crear(self, actor: Actor, s: e.NuevaTrampa) -> e.Trampa:
        """Reglas: ``dominio.error_codigo_trampa`` (formato y paridad RN-005, mismos textos que
        ``sigat.fn_codigo_trampa_error``) -> 422 ``CODIGO_TRAMPA_INVALIDO``; código existente -> 409
        ``CODIGO_TRAMPA_DUPLICADO``; la ubicación debe caer en el lote (advertencia) y respetar la
        distancia mínima RN-004 con las vigentes."""
        raise NoImplementado("Alta de trampa")

    async def actualizar(self, actor: Actor, tram_id: int, s: e.ActualizacionTrampa) -> e.Trampa:
        raise NoImplementado("Actualizar trampa")

    async def ubicaciones(self, actor: Actor, tram_id: int) -> list[e.UbicacionTrampa]:
        raise NoImplementado("Ubicaciones")

    async def reubicar(self, actor: Actor, tram_id: int, s: e.NuevaUbicacion) -> e.UbicacionTrampa:
        """Sin solape (EXCLUDE ubicacion_trampa_sin_solape). Invalida el paquete de campo."""
        raise NoImplementado("Reubicar trampa")


class ServicioPrograma:
    def __init__(self, repo: RepositorioConfiguracion, cola: Cola) -> None:
        self._repo = repo
        self._cola = cola

    async def vigente(self, actor: Actor, pred_id: int, fecha: date | None) -> e.ProgramaInspeccion:
        """Sin fecha = hoy en la zona horaria del predio. Con fecha = el que regía ese día (RF-024)."""
        raise NoImplementado("Programa vigente")

    async def de_lote(self, actor: Actor, lote_id: int) -> e.ProgramaInspeccion:
        """Móvil ``getInspectionConfig``."""
        raise NoImplementado("Programa del lote")

    async def versiones(self, actor: Actor, pred_id: int) -> list[e.ProgramaInspeccion]:
        raise NoImplementado("Versiones del programa")

    async def nueva_version(
        self, actor: Actor, pred_id: int, s: e.NuevaVersionPrograma
    ) -> e.ProgramaInspeccion:
        """Web ``saveNewVersion``. Reglas (fn_programa_valida + §5.3): vigente_desde no anterior a la
        versión vigente; RN-007 y RN-004 en rango; escenarios sin solape. NO cambia el pasado:
        los periodos ya calculados conservan su umbral (ADR-05). Invalida el paquete de campo."""
        raise NoImplementado("Nueva versión del programa")


class ServicioReticula:
    def __init__(self, repo: RepositorioConfiguracion, cola: Cola) -> None:
        self._repo = repo
        self._cola = cola

    async def obtener(self, actor: Actor, pred_id: int) -> e.Reticula:
        raise NoImplementado("Retícula")

    async def crear(self, actor: Actor, pred_id: int, s: e.NuevaReticula) -> e.Reticula:
        """422 'La retícula es menor que la distancia mínima entre trampas' si no cumple §5.3."""
        raise NoImplementado("Alta de retícula")


class ServicioPaqueteCampo:
    def __init__(self, repo: RepositorioConfiguracion) -> None:
        self._repo = repo

    async def info(self, actor: Actor, pred_id: int) -> e.PaqueteCampoInfo:
        raise NoImplementado("Información del paquete")

    async def contenido(
        self, actor: Actor, pred_id: int, si_no_coincide: str | None
    ) -> e.PaqueteCampoContenido | None:
        """Devuelve None si ``If-None-Match`` coincide con el hash vigente (la ruta responde 304).
        RNF-020: tamaño acotado; el mapa base NO va aquí: el móvil lo descarga del proveedor
        según ``mapa_base.permite_descarga`` (licencia, UQQ-007)."""
        raise NoImplementado("Contenido del paquete")

    async def generar(self, pred_id: int, motivo: str) -> e.PaqueteCampoInfo:
        """Tarea de la cola ``generar_paquete_campo``: invalida el anterior y registra uno nuevo."""
        raise NoImplementado("Generar paquete")
