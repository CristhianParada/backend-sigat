"""Esquemas comunes del contrato HTTP: paginación, problema RFC 9457 y GeoJSON."""

from decimal import Decimal
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

T = TypeVar("T")

# Pydantic v2 serializa ``Decimal`` como TEXTO JSON ("1.2500"). Los clientes (Flutter) leen estos
# campos como número (``(j['lote_area'] as num).toDouble()``) y fallan al recibir una cadena.
# ``DecimalJson`` mantiene la precisión decimal en Python y la entrega como número en el JSON.
DecimalJson = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class Esquema(BaseModel):
    """Base de todos los esquemas: rechaza campos desconocidos en las entradas."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, from_attributes=True)


class Pagina(Esquema, Generic[T]):
    """Lista paginada por cursor opaco. ``siguiente`` = None cuando no hay más."""

    items: list[T]
    siguiente: str | None = Field(None, description="Cursor opaco para pedir la página siguiente.")


class ErrorCampo(Esquema):
    campo: str
    mensaje: str


class Problema(Esquema):
    """``application/problem+json`` (RFC 9457) con extensiones del proyecto."""

    model_config = ConfigDict(extra="allow")

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    codigo: str = Field(..., description="Código estable para la lógica de los fronts.")
    errores: list[ErrorCampo] = Field(default_factory=list)
    traza_id: str | None = None


# --------------------------------------------------------------------- GeoJSON (RFC 7946, WGS84)
class GeometriaGeoJson(Esquema):
    """Geometría GeoJSON en EPSG:4326 (lon, lat). Se valida en el servidor con PostGIS."""

    model_config = ConfigDict(extra="allow")

    type: Literal["Point", "Polygon", "MultiPolygon", "LineString"]
    coordinates: Any


class FeatureGeoJson(Esquema):
    model_config = ConfigDict(extra="allow")

    type: Literal["Feature"] = "Feature"
    id: str | int | None = None
    geometry: GeometriaGeoJson | None
    properties: dict[str, Any] = Field(default_factory=dict)


class ColeccionGeoJson(Esquema):
    model_config = ConfigDict(extra="allow")

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[FeatureGeoJson] = Field(default_factory=list)


class Aceptado(Esquema):
    """Respuesta 202 genérica (operaciones que no revelan información)."""

    mensaje: str
