"""Casos de uso del núcleo de registro."""

from datetime import datetime
from uuid import UUID

from sigat_api.compartido.contratos import OperacionCampo, ResultadoAplicacion
from sigat_api.compartido.errores import NoImplementado
from sigat_api.compartido.esquemas import Pagina
from sigat_api.compartido.tipos import Actor, EstadoRevision
from sigat_api.infra.reloj import Reloj
from sigat_api.modules.registro import esquemas as e
from sigat_api.modules.registro.puertos import PuertoOperaciones
from sigat_api.modules.registro.repositorio import RepositorioRegistro
from sigat_api.modules.registro.validador import ValidadorInvariantes


class ServicioRegistro:
    """Escritura. Implementa estructuralmente ``sincronizacion.puertos.PuertoRegistro``."""

    def __init__(
        self,
        repo: RepositorioRegistro,
        validador: ValidadorInvariantes,
        operaciones: PuertoOperaciones,
        reloj: Reloj,
    ) -> None:
        self._repo = repo
        self._validador = validador
        self._operaciones = operaciones
        self._reloj = reloj

    async def aplicar(self, actor: Actor, op: OperacionCampo) -> ResultadoAplicacion:
        """Aplica UNA operación dentro de la transacción del lote de sincronización.

        1. ``validador.validar`` -> si hay motivo: ``rechazada`` (no toca el histórico).
        2. ``repo.estado_previo`` + ``dominio.clasificar``.
        3. ``revisar`` -> NO inserta en la tabla de dominio (queda solo en operacion_sync con payload).
        4. alta/corrección -> ``repo.insertar_version`` (o ``insertar_visita``) ligado a ``op.oper_id``.
        5. Si es lectura oficial (o su corrección/anulación): devolver ``periodos_afectados`` para
           que Sincronización encole el reproceso de MTD y concepto (RF-054, ADR-13).
        """
        raise NoImplementado("Aplicar operación de campo")

    # --- escrituras en línea de la web (pasan por el mismo camino) ---------------------------
    async def registrar_aplicacion(self, actor: Actor, s: e.NuevaAplicacion) -> e.Aplicacion:
        """Productor desde la web (``registerApplication``). Construye una ``OperacionCampo`` con
        ``PuertoOperaciones.registrar_operacion_en_linea`` y llama a ``aplicar``. Linaje autorreporte."""
        raise NoImplementado("Registrar aplicación")

    async def registrar_cosecha(self, actor: Actor, s: e.NuevaCosecha) -> e.Cosecha:
        """Web ``saveHarvest``: si ya existe la cosecha del lote, el front usa ``nueva_version_cosecha``."""
        raise NoImplementado("Registrar cosecha")

    async def nueva_version_aplicacion(
        self, actor: Actor, registro_id: UUID, s: e.NuevaVersionAutorreporte
    ) -> e.Aplicacion:
        """Solo el autor. ``version_esperada`` != vigente -> 412."""
        raise NoImplementado("Corregir aplicación")

    async def nueva_version_cosecha(
        self, actor: Actor, registro_id: UUID, s: e.NuevaVersionAutorreporte
    ) -> e.Cosecha:
        raise NoImplementado("Corregir cosecha")

    async def corregir_lectura(self, actor: Actor, registro_id: UUID, s: e.CorreccionLectura) -> e.Lectura:
        """Agrónomo (web 'corregir', motivo obligatorio). Versión n+1 con mismo t_observacion y
        ``lect_motivo_correccion`` (BD v9); su operación es 'corregir' con el dispositivo web de la sesión.
        Dispara el reproceso del periodo. El estado pasa a 'corregido' en v_lectura_revision."""
        raise NoImplementado("Corregir lectura")

    async def anular_lectura(self, actor: Actor, registro_id: UUID, s: e.AnulacionRegistro) -> e.Lectura:
        """Agrónomo (web 'rechazar'). Versión n+1 anulada; sale del MTD; dispara reproceso."""
        raise NoImplementado("Anular lectura")


class ServicioRevision:
    """Revisión del agrónomo/supervisor SOBRE LA VISITA (BD: visi_estado_revision).

    Web y móvil deben revisar lo mismo (CONCORDANCIA §4.2): la web muestra lecturas,
    pero la decisión 'aceptar' es de la visita; corregir/rechazar una lectura es una
    versión nueva de esa lectura (``ServicioRegistro``).
    """

    def __init__(self, repo: RepositorioRegistro, reloj: Reloj) -> None:
        self._repo = repo
        self._reloj = reloj

    async def listar(
        self, actor: Actor, estado: EstadoRevision | None, cursor: str | None
    ) -> Pagina[e.RegistroRevision]:
        raise NoImplementado("Registros por revisar")

    async def obtener(self, actor: Actor, visi_id: UUID) -> e.RevisionDetalle:
        raise NoImplementado("Detalle de revisión")

    async def aceptar(self, actor: Actor, visi_id: UUID) -> e.RevisionDetalle:
        """pendiente|en_revision -> aceptado (UPDATE de las columnas de revisión de la visita).
        Las lecturas sin corrección ni anulación pasan a 'confirmado' en v_lectura_revision (la web
        'Confirmar' llama aquí). Ya aceptada -> 409 ``REVISION_YA_RESUELTA``."""
        raise NoImplementado("Aceptar registro")

    async def marcar_en_revision(
        self, actor: Actor, visi_id: UUID, s: e.ObservacionRevision
    ) -> e.RevisionDetalle:
        """pendiente -> en_revision con motivo (notifica al técnico)."""
        raise NoImplementado("Marcar en revisión")

    async def contar_por_revisar(self, actor: Actor) -> int:
        """Total de visitas pendientes de revisar en los predios del agronomo."""
        return await self._repo.contar_por_revisar(actor.usua_id)


class ServicioConsultaRegistro:
    """Lecturas para pantallas. Siempre filtradas por fn_lotes_visibles."""

    def __init__(self, repo: RepositorioRegistro) -> None:
        self._repo = repo

    async def visitas(
        self,
        actor: Actor,
        pred_id: int | None,
        desde: datetime | None,
        hasta: datetime | None,
        cursor: str | None,
    ) -> Pagina[e.Visita]:
        """Técnico: solo las suyas. Móvil ``HistoryRepository.getVisits``."""
        raise NoImplementado("Visitas")

    async def visita(self, actor: Actor, visi_id: UUID) -> e.VisitaDetalle:
        raise NoImplementado("Visita")

    async def lecturas(
        self,
        actor: Actor,
        lote_id: int | None,
        tram_id: int | None,
        desde: datetime | None,
        cursor: str | None,
    ) -> Pagina[e.Lectura]:
        raise NoImplementado("Lecturas")

    async def versiones_lectura(self, actor: Actor, registro_id: UUID) -> e.HistorialVersiones:
        raise NoImplementado("Versiones de lectura")

    async def aplicaciones(
        self, actor: Actor, lote_id: int | None, cursor: str | None
    ) -> Pagina[e.Aplicacion]:
        raise NoImplementado("Aplicaciones")

    async def cosechas(self, actor: Actor, lote_id: int | None, cursor: str | None) -> Pagina[e.Cosecha]:
        raise NoImplementado("Cosechas")

    async def actividad(
        self,
        actor: Actor,
        lote_id: int | None,
        tipo: str | None,
        linaje: str | None,
        desde: datetime | None,
        hasta: datetime | None,
        cursor: str | None,
    ) -> Pagina[e.EntradaActividad]:
        """Historial unificado: web History/ProducerHistory/timeline, móvil getActivity/getLotHistory.
        Orden: t_observacion DESC (R-T1 invertido para pantalla)."""
        raise NoImplementado("Actividad")

    async def actividad_reciente(self, actor: Actor, lote_id: int) -> list[e.ActividadReciente]:
        raise NoImplementado("Actividad reciente")
