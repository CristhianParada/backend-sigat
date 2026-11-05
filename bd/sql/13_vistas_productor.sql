-- =====================================================================
-- SIGAT v9.1 - Vistas de consulta del PRODUCTOR (F1, F2 y F3 del informe de consumo)
--
-- Qué cambia: SOLO AGREGA tres vistas y tres funciones de lectura. No crea ni modifica
-- tablas, columnas, restricciones, índices ni datos; no reemplaza ninguna vista existente.
--   * v_actividad_lote_detalle  (F1): historial por lote con responsable, rol, conteo de
--     trampas de la visita, producto de la aplicación y fecha esperada de la cosecha.
--   * v_cosecha_lote_vigente    (F2): por cada lote, su cosecha vigente (la abierta, por la
--     regla P-04 «una sola cosecha abierta por lote», o si no la más reciente).
--   * v_aplicacion_ultima_lote  (F3): por cada lote, su última aplicación fitosanitaria
--     vigente (o nulos si no tiene ninguna) y los días transcurridos.
--   * fn_actividad_lote_detalle / fn_cosecha_lote_vigente / fn_aplicacion_ultima_lote(usua):
--     las mismas vistas filtradas por fn_lotes_visibles, igual que fn_actividad_lote.
--
-- Las vistas NO son un mecanismo de autorización: devuelven todos los lotes. El backend
-- debe leer SIEMPRE las funciones fn_* con el usuario del token (RNF-015).
--
-- Idempotente (CREATE OR REPLACE): se puede ejecutar varias veces. En una base existente lo
-- aplica la migración Alembic 0004; en una instalación nueva, 00_instalar_todo.sql.
-- Decisiones y limitaciones: docs/VISTAS_PRODUCTOR.md.
-- =====================================================================

-- ---------------------------------------------------------------------------------------
-- F1. Historial detallado por lote
-- ---------------------------------------------------------------------------------------
-- Una fila por fila de v_actividad_lote (vigilancia por cada lote de la visita, aplicación y
-- cosecha vigentes). Ningún JOIN multiplica filas: lote, predio, usuario, persona y rol son
-- 1:1; las tres subconsultas LATERAL devuelven como máximo una fila.
--
-- Conteo de trampas de una vigilancia, SOLO del lote de la fila:
--   * trampas_en_lote: ubicaciones de trampa del lote vigentes el día de la visita
--     ([ubic_fecha, ubic_fecha_fin), día = visi_t_inicio_obs en la zona del predio, el mismo
--     criterio que fn_lectura_valida). La restricción EXCLUDE ubicacion_trampa_sin_solape
--     garantiza una sola ubicación por trampa y día, así que count(*) cuenta trampas.
--   * trampas_revisadas / trampas_leidas: trampas DISTINTAS con lectura vigente (última versión,
--     no anulada, como v_lectura_vigente) en esa visita cuya ubicación de ese día es del lote.
--     Se cuentan trampas y no filas: dos lecturas distintas de la misma trampa en la misma
--     visita son una sola trampa revisada; las versiones (correcciones) no suman.
-- Fecha de la cosecha: formato fijo «DD mmm AAAA» con meses en español escritos aquí; no
-- depende de lc_time (to_char con 'DD' y 'YYYY' no usa el idioma del servidor).
-- Linaje: el de la versión vigente para aplicación y cosecha. La tabla visita NO tiene
-- columna de linaje, así que para vigilancia linaje y es_inspeccion_oficial son NULL
-- (desconocido) en vez de deducirlos del tipo.
CREATE OR REPLACE VIEW sigat.v_actividad_lote_detalle AS
SELECT a.lote_id,
       l.pred_id,
       l.lote_codigo,
       l.lote_descripcion,
       a.tipo,
       a.registro_id,
       a.t_observacion,
       (a.t_observacion AT TIME ZONE p.pred_zona_horaria)::date AS fecha_observacion_local,
       a.usua_id,
       pe.pers_nombre || ' ' || pe.pers_apellido AS responsable,
       r.rol_codigo AS rol_codigo_responsable,
       r.rol_descripcion AS rol_responsable,
       CASE a.tipo
         WHEN 'vigilancia' THEN 'Visita de vigilancia'
         WHEN 'aplicacion' THEN 'Aplicación fitosanitaria'
         WHEN 'cosecha' THEN 'Cosecha'
       END AS titulo,
       vt.trampas_en_lote,
       lv.trampas_revisadas,
       lv.trampas_leidas,
       ap.producto,
       co.cose_fecha_esperada,
       CASE a.tipo
         WHEN 'vigilancia' THEN
           lv.trampas_revisadas::text || ' de ' || vt.trampas_en_lote::text || ' trampas revisadas'
         WHEN 'aplicacion' THEN ap.producto::text
         WHEN 'cosecha' THEN
           'Cosecha esperada · ' || to_char(co.cose_fecha_esperada, 'DD') || ' '
           || (ARRAY['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'])
                [EXTRACT(MONTH FROM co.cose_fecha_esperada)::integer]
           || ' ' || to_char(co.cose_fecha_esperada, 'YYYY')
       END AS detalle,
       (CASE a.tipo WHEN 'aplicacion' THEN ap.linaje WHEN 'cosecha' THEN co.linaje END)::sigat.d_linaje
         AS linaje,
       (CASE a.tipo WHEN 'aplicacion' THEN ap.linaje WHEN 'cosecha' THEN co.linaje END)
         = 'inspeccion_oficial' AS es_inspeccion_oficial
FROM sigat.v_actividad_lote a
JOIN sigat.lote l ON l.lote_id = a.lote_id
JOIN sigat.predio p ON p.pred_id = l.pred_id
JOIN sigat.usuario u ON u.usua_id = a.usua_id
JOIN sigat.persona pe ON pe.pers_cc = u.pers_cc
JOIN sigat.rol r ON r.rol_id = u.rol_id
-- Trampas del lote el día de la visita (solo vigilancia).
LEFT JOIN LATERAL (
  SELECT count(*) AS trampas_en_lote
  FROM sigat.ubicacion_trampa ut
  WHERE a.tipo = 'vigilancia'
    AND ut.lote_id = a.lote_id
    AND ut.ubic_fecha <= (a.t_observacion AT TIME ZONE p.pred_zona_horaria)::date
    AND (ut.ubic_fecha_fin IS NULL
         OR ut.ubic_fecha_fin > (a.t_observacion AT TIME ZONE p.pred_zona_horaria)::date)
) vt ON a.tipo = 'vigilancia'
-- Trampas del lote con lectura vigente en esta visita (solo vigilancia).
LEFT JOIN LATERAL (
  SELECT count(DISTINCT lt.tram_id) AS trampas_revisadas,
         count(DISTINCT lt.tram_id) FILTER (WHERE lt.lect_leida) AS trampas_leidas
  FROM sigat.lectura_trampa lt
  WHERE a.tipo = 'vigilancia'
    AND lt.visi_id = a.registro_id
    AND NOT lt.lect_anulada
    AND NOT EXISTS (SELECT 1 FROM sigat.lectura_trampa n
                     WHERE n.lect_registro_id = lt.lect_registro_id
                       AND n.lect_version > lt.lect_version)
    AND EXISTS (SELECT 1 FROM sigat.ubicacion_trampa ut
                 WHERE ut.tram_id = lt.tram_id
                   AND ut.lote_id = a.lote_id
                   AND ut.ubic_fecha <= (a.t_observacion AT TIME ZONE p.pred_zona_horaria)::date
                   AND (ut.ubic_fecha_fin IS NULL
                        OR ut.ubic_fecha_fin > (a.t_observacion AT TIME ZONE p.pred_zona_horaria)::date))
) lv ON a.tipo = 'vigilancia'
-- Versión vigente de la aplicación (la misma que eligió v_actividad_lote).
LEFT JOIN LATERAL (
  SELECT COALESCE(pf.prof_nombre, x.apli_producto_texto) AS producto, x.apli_linaje AS linaje
  FROM sigat.aplicacion_fitosanitaria x
  LEFT JOIN sigat.producto_fitosanitario pf ON pf.prof_id = x.prof_id
  WHERE a.tipo = 'aplicacion'
    AND x.apli_registro_id = a.registro_id
  ORDER BY x.apli_version DESC
  LIMIT 1
) ap ON a.tipo = 'aplicacion'
-- Versión vigente de la cosecha (la misma que eligió v_actividad_lote).
LEFT JOIN LATERAL (
  SELECT x.cose_fecha_esperada, x.cose_linaje AS linaje
  FROM sigat.cosecha x
  WHERE a.tipo = 'cosecha'
    AND x.cose_registro_id = a.registro_id
  ORDER BY x.cose_version DESC
  LIMIT 1
) co ON a.tipo = 'cosecha';

COMMENT ON VIEW sigat.v_actividad_lote_detalle IS
  'F1: v_actividad_lote con lote, responsable, rol, título y detalle por tipo. Conteo de trampas solo del lote de la fila y del día de la visita, con lecturas vigentes y trampas distintas. linaje y es_inspeccion_oficial son NULL en vigilancia (visita no tiene linaje). No filtra por usuario: usar fn_actividad_lote_detalle.';
COMMENT ON COLUMN sigat.v_actividad_lote_detalle.trampas_en_lote IS 'Solo vigilancia: trampas ubicadas en el lote el día de la visita (zona del predio).';
COMMENT ON COLUMN sigat.v_actividad_lote_detalle.trampas_revisadas IS 'Solo vigilancia: trampas distintas del lote con lectura vigente en la visita (leída o no).';
COMMENT ON COLUMN sigat.v_actividad_lote_detalle.trampas_leidas IS 'Solo vigilancia: trampas distintas del lote con lectura vigente y lect_leida = true.';
COMMENT ON COLUMN sigat.v_actividad_lote_detalle.linaje IS 'Linaje de la versión vigente (aplicación, cosecha). NULL en vigilancia: la visita no registra linaje.';
COMMENT ON COLUMN sigat.v_actividad_lote_detalle.detalle IS 'Texto determinista (no depende del idioma del servidor). Los datos tipados están en las columnas trampas_*, producto y cose_fecha_esperada.';

CREATE OR REPLACE FUNCTION sigat.fn_actividad_lote_detalle(p_usua integer DEFAULT sigat.fn_usuario_actual())
RETURNS SETOF sigat.v_actividad_lote_detalle LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM sigat.v_actividad_lote_detalle v
   WHERE v.lote_id IN (SELECT lote_id FROM sigat.fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION sigat.fn_actividad_lote_detalle(integer) IS 'v_actividad_lote_detalle filtrada a los lotes que el usuario puede ver (fn_lotes_visibles).';

-- ---------------------------------------------------------------------------------------
-- F3. Última aplicación fitosanitaria por lote
-- ---------------------------------------------------------------------------------------
-- Una fila por lote (también los lotes sin aplicaciones: columnas de la aplicación en NULL).
-- Aplicación vigente = última versión de su registro y no anulada (si la última versión
-- está anulada, el registro no cuenta). «Última» = mayor apli_t_observacion; desempate por
-- apli_t_captura y apli_registro_id (orden canónico R-T1). Días transcurridos: fechas en la
-- zona horaria del predio (REGLAS_NEGOCIO §4.1).
CREATE OR REPLACE VIEW sigat.v_aplicacion_ultima_lote AS
SELECT l.lote_id,
       l.pred_id,
       l.lote_codigo,
       l.lote_descripcion,
       x.apli_registro_id,
       x.apli_version,
       x.apli_t_observacion,
       (x.apli_t_observacion AT TIME ZONE p.pred_zona_horaria)::date AS apli_fecha_local,
       (now() AT TIME ZONE p.pred_zona_horaria)::date
         - (x.apli_t_observacion AT TIME ZONE p.pred_zona_horaria)::date AS dias_desde_aplicacion,
       x.prof_id,
       COALESCE(pf.prof_nombre, x.apli_producto_texto) AS producto,
       x.apli_dosis,
       x.apli_dosis_uni_id,
       ud.unid_simbolo AS dosis_unidad,
       x.apli_area_tratada,
       x.apli_area_uni_id,
       ua.unid_simbolo AS area_unidad,
       x.pers_cc_responsable,
       COALESCE(pr.pers_nombre || ' ' || pr.pers_apellido, x.apli_responsable_nombre) AS responsable,
       x.apli_linaje
FROM sigat.lote l
JOIN sigat.predio p ON p.pred_id = l.pred_id
LEFT JOIN LATERAL (
  SELECT f.*
  FROM sigat.aplicacion_fitosanitaria f
  WHERE f.lote_id = l.lote_id
    AND NOT f.apli_anulada
    AND NOT EXISTS (SELECT 1 FROM sigat.aplicacion_fitosanitaria n
                     WHERE n.apli_registro_id = f.apli_registro_id
                       AND n.apli_version > f.apli_version)
  ORDER BY f.apli_t_observacion DESC, f.apli_t_captura DESC, f.apli_registro_id DESC
  LIMIT 1
) x ON true
LEFT JOIN sigat.producto_fitosanitario pf ON pf.prof_id = x.prof_id
LEFT JOIN sigat.unidad_medida ud ON ud.unid_id = x.apli_dosis_uni_id
LEFT JOIN sigat.unidad_medida ua ON ua.unid_id = x.apli_area_uni_id
LEFT JOIN sigat.persona pr ON pr.pers_cc = x.pers_cc_responsable;

COMMENT ON VIEW sigat.v_aplicacion_ultima_lote IS
  'F3 / RF-041: última aplicación vigente (no anulada, última versión) de cada lote y días transcurridos en la zona del predio. Incluye lotes sin aplicaciones (NULL). No filtra por usuario: usar fn_aplicacion_ultima_lote.';
COMMENT ON COLUMN sigat.v_aplicacion_ultima_lote.dias_desde_aplicacion IS 'Días entre la fecha de la aplicación y hoy, ambas en la zona horaria del predio.';

CREATE OR REPLACE FUNCTION sigat.fn_aplicacion_ultima_lote(p_usua integer DEFAULT sigat.fn_usuario_actual())
RETURNS SETOF sigat.v_aplicacion_ultima_lote LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM sigat.v_aplicacion_ultima_lote v
   WHERE v.lote_id IN (SELECT lote_id FROM sigat.fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION sigat.fn_aplicacion_ultima_lote(integer) IS 'v_aplicacion_ultima_lote filtrada a los lotes que el usuario puede ver (fn_lotes_visibles).';

-- ---------------------------------------------------------------------------------------
-- F2. Cosecha vigente por lote (esperada + real)
-- ---------------------------------------------------------------------------------------
-- Regla de negocio (P-04, decisión del responsable 2026-11-05): UNA SOLA cosecha abierta por lote
-- (abierta = versión vigente sin cose_fecha_real).
-- Una fila por lote (también los lotes sin cosechas: columnas de la cosecha en NULL).
-- Cosecha vigente = última versión de su registro y no anulada (como F3; si la última versión
-- está anulada, el registro no cuenta). Por lote se elige:
--   1. la cosecha ABIERTA (por P-04 debería haber como mucho una);
--   2. si no hay abierta, la más reciente: mayor cose_t_observacion, luego cose_t_captura y
--      cose_registro_id (orden canónico R-T1).
-- cosechas_abiertas cuenta las abiertas del lote: > 1 indica datos que violan P-04 (esta vista
-- no las oculta ni elige en silencio; la regla todavía no está impuesta en la BD).
CREATE OR REPLACE VIEW sigat.v_cosecha_lote_vigente AS
SELECT l.lote_id,
       l.pred_id,
       l.lote_codigo,
       l.lote_descripcion,
       x.cose_registro_id,
       x.cose_version,
       x.cose_t_observacion,
       x.cose_fecha_esperada,
       x.cose_volumen_esperado,
       x.cose_fecha_real,
       x.cose_volumen_real,
       x.cose_volumen_uni_id,
       um.unid_simbolo AS volumen_unidad,
       CASE WHEN x.cose_registro_id IS NOT NULL THEN x.cose_fecha_real IS NULL END AS abierta,
       ab.cosechas_abiertas,
       x.cose_linaje
FROM sigat.lote l
LEFT JOIN LATERAL (
  SELECT c.*
  FROM sigat.cosecha c
  WHERE c.lote_id = l.lote_id
    AND NOT c.cose_anulada
    AND NOT EXISTS (SELECT 1 FROM sigat.cosecha n
                     WHERE n.cose_registro_id = c.cose_registro_id
                       AND n.cose_version > c.cose_version)
  ORDER BY (c.cose_fecha_real IS NULL) DESC, c.cose_t_observacion DESC, c.cose_t_captura DESC,
           c.cose_registro_id DESC
  LIMIT 1
) x ON true
LEFT JOIN sigat.unidad_medida um ON um.unid_id = x.cose_volumen_uni_id
CROSS JOIN LATERAL (
  SELECT count(*) AS cosechas_abiertas
  FROM sigat.cosecha c
  WHERE c.lote_id = l.lote_id
    AND c.cose_fecha_real IS NULL
    AND NOT c.cose_anulada
    AND NOT EXISTS (SELECT 1 FROM sigat.cosecha n
                     WHERE n.cose_registro_id = c.cose_registro_id
                       AND n.cose_version > c.cose_version)
) ab;

COMMENT ON VIEW sigat.v_cosecha_lote_vigente IS
  'F2 / RF-042: cosecha vigente de cada lote (esperada + real). Prefiere la abierta (P-04: una sola por lote); si no hay, la más reciente. Incluye lotes sin cosechas (NULL). No filtra por usuario: usar fn_cosecha_lote_vigente.';
COMMENT ON COLUMN sigat.v_cosecha_lote_vigente.abierta IS 'true si la cosecha elegida no tiene fecha real (sigue abierta); NULL si el lote no tiene cosechas.';
COMMENT ON COLUMN sigat.v_cosecha_lote_vigente.cosechas_abiertas IS 'Cosechas abiertas vigentes del lote. Más de 1 viola la regla P-04 (una sola abierta por lote).';

CREATE OR REPLACE FUNCTION sigat.fn_cosecha_lote_vigente(p_usua integer DEFAULT sigat.fn_usuario_actual())
RETURNS SETOF sigat.v_cosecha_lote_vigente LANGUAGE sql STABLE SET search_path = sigat, public AS $$
  SELECT v.* FROM sigat.v_cosecha_lote_vigente v
   WHERE v.lote_id IN (SELECT lote_id FROM sigat.fn_lotes_visibles(p_usua)) $$;
COMMENT ON FUNCTION sigat.fn_cosecha_lote_vigente(integer) IS 'v_cosecha_lote_vigente filtrada a los lotes que el usuario puede ver (fn_lotes_visibles).';
