# Cambios de la base de datos

Este documento establece las convenciones para administrar y mantener la estructura de la base de datos de SIGAT.

Su objetivo es mantener la trazabilidad de los cambios, facilitar el mantenimiento y garantizar que las modificaciones sean consistentes entre los diferentes entornos del sistema.

## Gestión de la estructura

La estructura de la base de datos se administra mediante scripts SQL y migraciones de Alembic.

Este mecanismo permite:

- Crear la estructura de la base de datos.
- Incorporar nuevas tablas, relaciones y restricciones.
- Actualizar índices, vistas y funciones.
- Mantener los catálogos y datos de referencia.
- Aplicar modificaciones de forma controlada.
- Conservar la consistencia entre los entornos de ejecución.

Las migraciones deben ejecutarse siguiendo el orden establecido por el proyecto.

Para aplicar las migraciones:

```bash
alembic upgrade head
```

Para consultar el historial:

```bash
alembic history
```

Para consultar la revisión actual:

```bash
alembic current
```

## Organización de los cambios

Los cambios de estructura se gestionan mediante dos mecanismos:

| Mecanismo | Responsabilidad |
|---|---|
| Scripts SQL | Definición y mantenimiento de los elementos de la base de datos |
| Alembic | Control de versiones y ejecución ordenada de migraciones |

Los archivos SQL se organizan en el directorio `bd/sql/`, mientras que las migraciones se almacenan en `migrations/`.

Cada modificación debe estar documentada y asociada con su correspondiente cambio en el proyecto.

## Principios para modificar la base de datos

Las modificaciones deben seguir estas buenas prácticas:

1. **Conservar el historial:** no modificar migraciones que ya hayan sido aplicadas en otros entornos. Los cambios nuevos deben incorporarse mediante nuevas revisiones.
2. **Priorizar cambios compatibles:** procurar que las modificaciones no afecten innecesariamente la información existente.
3. **Mantener la integridad:** conservar las relaciones, restricciones y reglas de validación de los datos.
4. **Documentar los cambios:** describir el propósito y el alcance de cada modificación.
5. **Verificar las migraciones:** comprobar que los cambios puedan aplicarse correctamente.
6. **Evitar pérdidas de información:** evaluar cuidadosamente cualquier modificación que pueda alterar o eliminar datos existentes.

## Procedimiento para incorporar cambios

Cuando sea necesario modificar la estructura de la base de datos, se recomienda seguir este procedimiento:

### 1. Identificar la modificación

Determinar qué elemento necesita cambiarse y cuál es el propósito de la modificación.

### 2. Crear una nueva migración

Generar una revisión mediante Alembic:

```bash
alembic revision -m "descripcion_del_cambio"
```

### 3. Implementar el cambio

Incorporar las operaciones necesarias en la migración, procurando mantener la compatibilidad con la estructura existente.

### 4. Documentar la modificación

Registrar qué cambia, cuál es su propósito y qué consideraciones deben tenerse en cuenta al aplicarlo.

### 5. Ejecutar las verificaciones

Aplicar las migraciones:

```bash
alembic upgrade head
```

Ejecutar las pruebas de integración:

```bash
pytest -m integracion
```

### 6. Revisar y compartir

Comprobar los resultados, revisar los cambios y seguir el flujo de contribución establecido en el repositorio.

## Integridad y protección de los datos

La administración de la base de datos debe considerar las siguientes medidas:

- Mantener las relaciones y restricciones de integridad referencial.
- Evitar modificaciones que comprometan información existente.
- Evaluar los cambios antes de aplicarlos en entornos compartidos.
- Realizar respaldos cuando las operaciones puedan afectar información almacenada.
- No incorporar credenciales, contraseñas, tokens ni información sensible en los scripts SQL.
- No almacenar volcados de bases de datos ni información personal real dentro del repositorio.

## Convenciones de desarrollo

Para mantener una estructura organizada y consistente:

- Utilizar nombres descriptivos para las migraciones.
- Mantener un orden lógico de ejecución.
- Evitar duplicar definiciones existentes.
- Documentar las modificaciones relevantes.
- Mantener sincronizados los scripts SQL y las migraciones correspondientes.
- Verificar los cambios antes de integrarlos a la rama principal.

## Historial de migraciones

### Revisión `0001` — Esquema institucional SIGAT v9

Establece la línea base de la base de datos SIGAT v9. Cuando el esquema está vacío, ejecuta los scripts SQL institucionales en el orden definido. Si la estructura v9 ya existe, registra la revisión sin reconstruirla. Si encuentra una versión incompatible, detiene el proceso para evitar modificaciones no controladas.

### Revisión `0002` — Esquema técnico de sesiones API

Crea el esquema `api` y las tablas técnicas necesarias para gestionar sesiones de actualización de tokens e intentos de inicio de sesión. Incluye relaciones con usuarios y dispositivos, restricciones de validación e índices para las consultas.

### Revisión `0003` — Categoría de solicitudes de cuenta

Incorpora la categoría `solicitudes_cuenta` al catálogo de notificaciones. Permite identificar los avisos relacionados con solicitudes de recuperación de acceso. La operación es idempotente y no elimina categorías ni notificaciones existentes.

### Revisión `0004` — Vistas de consulta del productor

Ejecuta `bd/sql/13_vistas_productor.sql`, que **solo agrega** tres vistas y tres funciones de lectura; no crea ni modifica tablas, columnas, restricciones, índices ni datos, y no reemplaza vistas existentes. El archivo también se incluye en `00_instalar_todo.sql`, así que una instalación por psql y una por Alembic quedan iguales. Es idempotente (`CREATE OR REPLACE`).

- `v_actividad_lote_detalle` (F1 del informe de consumo): historial por lote con responsable, rol, título y detalle. Cuenta las trampas solo del lote de cada fila y del día de la visita, con lecturas vigentes y trampas distintas. El texto de fecha no depende del idioma del servidor. `linaje` y `es_inspeccion_oficial` son nulos en las vigilancias porque `visita` no registra linaje.
- `v_aplicacion_ultima_lote` (F3 / RF-041): última aplicación vigente de cada lote, incluidos los lotes sin aplicaciones, y los días transcurridos en la zona horaria del predio.
- `v_cosecha_lote_vigente` (F2 / RF-042): cosecha vigente de cada lote (esperada + real), incluidos los lotes sin cosechas. Aplica la regla **P-04, una sola cosecha abierta por lote** (decisión del responsable del proyecto, 2026-11-05): elige la abierta y, si no hay ninguna, la más reciente. `cosechas_abiertas` muestra si un lote incumple la regla, que todavía no se impone en la base de datos.
- `fn_actividad_lote_detalle(usua)`, `fn_cosecha_lote_vigente(usua)` y `fn_aplicacion_ultima_lote(usua)`: las mismas vistas filtradas con `fn_lotes_visibles`. Las vistas no son un mecanismo de autorización; el backend debe consultar las funciones.
- No se edita `03_vistas.sql`, porque la revisión 0001 lo ejecuta al instalar desde cero.
- `downgrade` elimina solo estos seis objetos.

Detalle, decisiones y limitaciones: `docs/VISTAS_PRODUCTOR.md`.

### Consideraciones de revisión

Las modificaciones de restricciones de `operacion_sync` en los ajustes v8 y v9 amplían los valores permitidos para incorporar nuevas entidades sincronizables. Como utilizan `DROP CONSTRAINT` seguido de `ADD CONSTRAINT`, deben contar con revisión técnica y aprobación del responsable de la base de datos antes de integrarse.
---

**SIGAT — Sistema de Información para la Gestión y Análisis de la Vigilancia Fitosanitaria.**