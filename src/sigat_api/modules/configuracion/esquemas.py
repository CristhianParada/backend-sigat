"""Contrato HTTP de configuración: predios, lotes, trampas, programa, retícula y paquete de campo.

Los nombres de campo de ``Lote`` y ``Trampa`` son los de las vistas ``v_lote_app`` y
``v_trampa_app``: el móvil ya los lee así (``lotFromApi`` / ``trapFromApi``).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from sigat_api.compartido.esquemas import (
    ColeccionGeoJson,
    DecimalJson,
    Esquema,
    FeatureGeoJson,
    GeometriaGeoJson,
)


# ------------------------------------------------------------------ predio
class Predio(Esquema):
    pred_id: int
    pred_codigo: str | None
    pred_nombre: str
    muni_id: int
    municipio: str
    departamento: str
    pred_area: Decimal = Field(..., description="[ha] área declarada.")
    productor: str = Field(..., description="Nombre del productor dueño del predio.")
    pred_zona_horaria: str
    total_lotes: int
    tiene_geometria: bool
    responsable_tecnico: str | None = None


class ActualizacionPredio(Esquema):
    pred_nombre: str | None = Field(None, min_length=1, max_length=150)
    pred_codigo: str | None = Field(None, max_length=30)
    muni_id: int | None = None
    pred_area: Decimal | None = Field(None, gt=0)
    pred_zona_horaria: str | None = None


class EntradaGeometria(Esquema):
    geometria: GeometriaGeoJson = Field(..., description="Polygon o MultiPolygon WGS84 (lon, lat).")
    fuente: Literal["gps_dispositivo", "digitalizacion", "importacion"] = "digitalizacion"
    motivo: str = Field(..., min_length=5, max_length=300)
    vigente_desde: datetime


class MapaPredio(Esquema):
    """Capas para MapLibre (web y móvil). Todas en EPSG:4326."""

    predio: FeatureGeoJson
    lotes: ColeccionGeoJson
    celdas: ColeccionGeoJson
    trampas: ColeccionGeoJson


# ------------------------------------------------------------------ lote
class IndicadoresLote(Esquema):
    """Calculados en el servidor. Solo con ``?incluir=indicadores`` (pantalla de la web)."""

    escenario: str | None
    trampas_leidas_periodo: int
    ultima_visita: datetime | None
    ultima_sincronizacion: datetime | None
    tecnico_asignado: str | None
    registros_sin_verificar: int
    requiere_revision: bool
    cobertura: Literal["completo", "parcial", "sin_visitar"]
    codigos_trampa: list[str]


class Lote(Esquema):
    """Fila de ``v_lote_app``."""

    lote_id: int
    lote_codigo: str | None
    lote_descripcion: str
    lote_area: DecimalJson
    pred_id: int
    pred_nombre: str
    productor: str
    municipio: str
    cultivo: str | None
    variedad: str | None
    vigilancia_activa: bool
    trampas_vigentes: int
    indicadores: IndicadoresLote | None = None


class LoteDetalle(Lote):
    espc_id: int | None
    vari_id: int | None
    lote_fecha_plantacion: date | None
    lote_fecha_registro: date
    lote_fecha_baja: date | None
    geometria: GeometriaGeoJson | None = Field(None, description="Versión vigente de lote_geometria.")
    geometria_version: int | None


class NuevoLote(Esquema):
    lote_codigo: str = Field(..., min_length=1, max_length=30)
    lote_descripcion: str = Field(..., min_length=1, max_length=150)
    lote_area: Decimal = Field(..., gt=0)
    espc_id: int | None = None
    vari_id: int | None = None
    lote_fecha_plantacion: date | None = None
    lote_fecha_registro: date
    geometria: EntradaGeometria | None = None


class ActualizacionLote(Esquema):
    """El dueño NO se edita en el lote: sale del predio (BD). El área en ha > 0."""

    lote_descripcion: str | None = Field(None, min_length=1, max_length=150)
    lote_area: Decimal | None = Field(None, gt=0)
    espc_id: int | None = None
    vari_id: int | None = None
    lote_fecha_plantacion: date | None = None
    lote_fecha_baja: date | None = Field(None, description="Dar de baja el lote (no se borra).")


class VersionGeometriaLote(Esquema):
    lotg_id: int
    lotg_version: int
    geometria: GeometriaGeoJson
    lotg_area_m2: Decimal | None
    vigente_desde: datetime
    vigente_hasta: datetime | None
    fuente: str | None
    motivo: str | None
    registrado_en: datetime


# ------------------------------------------------------------------ trampa
class Trampa(Esquema):
    """Fila de ``v_trampa_app`` + atrayente y comprobación espacial."""

    tram_id: int
    tram_codigo: str = Field(..., description="Código oficial impreso (Divipola + ruta + número).")
    tipo: str = Field(..., description="Jackson (impar) / McPhail (par), RN-005.")
    lote_id: int | None
    pred_id: int
    longitud: DecimalJson
    latitud: DecimalJson
    celda: str | None
    estado: str
    atrayente: str | None = None
    ubic_id: int | None = None
    dentro_del_lote: bool | None = Field(None, description="v_trampa_lote_vigente (advertencia RF-012).")
    ultima_lectura: datetime | None
    ultima_lectura_especimenes: int | None


class BusquedaTrampa(Esquema):
    """Respuesta de búsqueda por código ICA (QR o digitado). Móvil ``TrapLookup``."""

    trampa: Trampa | None
    en_catalogo: bool
    pertenece_lote_activo: bool | None = Field(None, description="Nulo si no se envió lote_activo.")
    dentro_del_lote: bool | None = Field(None, description="Nulo si no se enviaron lat/lng.")
    advertencias: list[str] = Field(default_factory=list, description="No bloquean (RF-012).")


class NuevaUbicacion(Esquema):
    lote_id: int
    ubic_fecha: date = Field(..., description="Instalación (inclusive).")
    vigi_id: int
    tecn_id: int
    ruta_id: int | None = None
    retc_id: int | None = None
    loca_id: int | None = None
    arbo_id: int | None = None
    ubic_long: Decimal = Field(..., ge=-180, le=180, max_digits=8, decimal_places=5)
    ubic_lat: Decimal = Field(..., ge=-90, le=90, max_digits=7, decimal_places=5)
    ubic_alt: float | None = None
    ubic_referencia: str | None = Field(None, max_length=200)


class UbicacionTrampa(NuevaUbicacion):
    ubic_id: int
    tram_id: int
    pred_id: int
    ubic_fecha_fin: date | None
    ubic_origen: Literal["operacion", "legado"]
    ubic_registrado_en: datetime


class NuevaTrampa(Esquema):
    tram_codigo: str = Field(
        ...,
        pattern=r"^[0-9]{5}-[0-9A-Za-z]{1,10}-[0-9]{1,4}$",
        description="Divipola (5) - ruta - número, p. ej. 54518-602-001. Jackson impar, McPhail par (RN-005).",
    )
    tipt_id: int = Field(..., description="Tipo de trampa: decide la paridad del número.")
    atra_id: int
    ubicacion: NuevaUbicacion


class ActualizacionTrampa(Esquema):
    atra_id: int | None = None
    esta_id: int | None = Field(None, description="Activa/inactiva (estado_registro).")
    tecn_id_estado: int | None = Field(
        None, description="Técnico que cambia el estado (obligatorio si cambia esta_id)."
    )


# ------------------------------------------------------------------ programa de inspección
class EscenarioPrograma(Esquema):
    esce_id: int
    descripcion: str
    orden: int
    mtd_desde: Decimal
    mtd_hasta: Decimal | None


class NormaRef(Esquema):
    norm_id: int
    norm_codigo: str
    norm_titulo: str


class ProgramaInspeccion(Esquema):
    prog_id: int
    pred_id: int
    prog_version: int
    vigente_desde: date
    vigente_hasta: date | None
    ciclo_inicio: date | None
    ciclo_fin: date | None
    periodo_lectura_dias: int = Field(..., description="RN-007: 7 a 14 días.")
    distancia_min_trampas_m: int = Field(..., description="RN-004: 40 a 60 m.")
    reti_id: int | None
    resolucion_reticula_m: int | None
    proveedor_imagen: str | None
    umbral_exportacion_mtd: Decimal | None = Field(
        ..., description="NULO hasta que se defina oficialmente (UQQ-004). Los fronts muestran 'Sin definir'."
    )
    norma: NormaRef | None
    escenarios: list[EscenarioPrograma]
    criterios_bpa: list[int]
    motivo_cambio: str | None
    creado_por: str | None
    creado_en: datetime


class EscenarioEntrada(Esquema):
    esce_id: int
    mtd_desde: Decimal = Field(..., ge=0)
    mtd_hasta: Decimal | None = Field(None, ge=0)


class NuevaVersionPrograma(Esquema):
    """Nunca se edita una versión: se crea la siguiente con su vigencia (ADR-05, ADR-07)."""

    vigente_desde: date
    periodo_lectura_dias: int = Field(..., ge=1, le=60)
    distancia_min_trampas_m: int = Field(..., ge=1, le=500)
    reti_id: int | None = None
    ciclo_inicio: date | None = None
    ciclo_fin: date | None = None
    proveedor_imagen: str | None = None
    umbral_exportacion_mtd: Decimal | None = Field(None, ge=0)
    norm_id: int | None = None
    escenarios: list[EscenarioEntrada] = Field(default_factory=list)
    criterios_bpa: list[int] = Field(default_factory=list)
    motivo_cambio: str = Field(..., min_length=5, max_length=300)


# ------------------------------------------------------------------ retícula
class Reticula(Esquema):
    reti_id: int
    pred_id: int
    resolucion_m: int
    fecha_corte_imagen: date | None
    creada_en: datetime
    celdas: ColeccionGeoJson


class NuevaReticula(Esquema):
    resolucion_m: int = Field(..., gt=0, description="Debe superar la distancia mínima entre trampas (§5.3).")
    fecha_corte_imagen: date | None = None
    celdas: ColeccionGeoJson | None = Field(None, description="Nulo = el servidor la genera sobre el predio.")


# ------------------------------------------------------------------ paquete de campo (ADR-09)
class PaqueteCampoInfo(Esquema):
    paqu_id: UUID
    pred_id: int
    paqu_version: int
    prog_id: int
    paqu_hash: str = Field(..., description="SHA-256 del contenido. Sirve de ETag.")
    generado_en: datetime
    invalidado_en: datetime | None
    tamano_bytes: int | None


class FuenteMapaBase(Esquema):
    """Configuración del mapa base para MapLibre. La URL de teselas sale de config, nunca del código."""

    estilo_url: str | None
    plantillas_teselas: list[str] = Field(default_factory=list)
    atribucion: str | None
    permite_descarga: bool
    zoom_min: int | None
    zoom_max: int | None
    limites: list[float] | None = Field(None, description="[oeste, sur, este, norte] del predio + margen.")


class PaqueteCampoContenido(Esquema):
    """Lo que el dispositivo necesita para trabajar el predio SIN red."""

    paqu_version: int
    paqu_hash: str
    generado_en: datetime
    predio: Predio
    programa: ProgramaInspeccion
    mapa: MapaPredio
    catalogos: dict[str, list[dict[str, object]]] = Field(
        ...,
        description="condicion_trampa, atrayente, especie_mosca, producto_fitosanitario, unidad_medida, ...",
    )
    mapa_base: FuenteMapaBase
