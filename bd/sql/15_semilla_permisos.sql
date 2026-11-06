-- =====================================================================
-- SIGAT v9.1 - Semilla de permiso y rol_permiso (RNF-015)
--
-- Qué cambia: SOLO AGREGA filas a permiso (25) y rol_permiso (54) cuando las dos tablas están
-- vacías. No crea ni modifica tablas, columnas, restricciones ni otros datos.
-- Fuente: la matriz que la API aplica hoy (src/sigat_api/modules/identidad/permisos.py, usada por
-- requiere(...)). Mismos códigos, con punto (area.accion, CHECK permiso_codigo_formato), y mismas
-- asignaciones por rol. Decisión del responsable del proyecto (2026-11-04): no se siembran los
-- códigos alternativos de la documentación ni se duplican capacidades.
-- tests/unit/test_semilla_permisos_migracion.py falla si esta lista y permisos.py dejan de coincidir.
-- Los roles se buscan por rol_codigo (02_catalogos_basicos.sql), nunca por id.
--
-- Comportamiento ante datos existentes (nunca completa, modifica ni borra filas):
--   * permiso y rol_permiso vacías                -> inserta la matriz completa;
--   * contienen exactamente esta matriz           -> no hace nada (idempotente);
--   * cualquier otro contenido (parcial, distinto
--     o con otras descripciones)                  -> se DETIENE con un error que enumera las
--                                                    diferencias. Lo resuelve el responsable de la BD.
-- Cada par insertado queda en bitacora_auditoria (trg_aud_rol_permiso) sin usuario: no hay actor.
-- Lo aplica la migración Alembic 0006 y, en una instalación nueva, 00_instalar_todo.sql.
-- =====================================================================

DO $$
DECLARE
  v_existentes integer;
  v_falta_rol text;
  v_diferencias text;
BEGIN
  CREATE TEMP TABLE IF NOT EXISTS permiso_esperado (
    codigo varchar, descripcion varchar, roles text[]
  ) ON COMMIT DROP;
  TRUNCATE pg_temp.permiso_esperado;
  -- (perm_codigo, perm_descripcion, roles). Mismo orden que permisos.py.
  INSERT INTO pg_temp.permiso_esperado (codigo, descripcion, roles) VALUES
    -- identidad
    ('usuarios.administrar', 'Administrar usuarios', ARRAY['ADMINISTRADOR']),
    ('auditoria.consultar', 'Consultar la bitácora de auditoría', ARRAY['ADMINISTRADOR']),
    -- catálogos y configuración
    ('catalogos.consultar', 'Consultar catálogos', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    ('catalogos.editar', 'Editar catálogos', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR']),
    ('predios.consultar', 'Consultar predios', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    ('predios.editar', 'Editar predios', ARRAY['ADMINISTRADOR']),
    ('lotes.editar', 'Editar lotes', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR']),
    ('trampas.editar', 'Editar trampas', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR']),
    ('programa.consultar', 'Consultar el programa de inspección', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    ('programa.versionar', 'Crear versiones del programa de inspección', ARRAY['AGRONOMO_SUPERVISOR']),
    ('reticula.crear', 'Crear retículas', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR']),
    ('paquete_campo.descargar', 'Descargar el paquete de campo', ARRAY['AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    -- registro
    ('visitas.consultar', 'Consultar visitas', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','TECNICO']),
    ('lecturas.consultar', 'Consultar lecturas de trampa', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    ('lecturas.corregir', 'Corregir lecturas de trampa', ARRAY['AGRONOMO_SUPERVISOR']),
    ('revisiones.resolver', 'Resolver revisiones de visitas', ARRAY['AGRONOMO_SUPERVISOR']),
    ('autorreporte.registrar', 'Registrar autorreportes', ARRAY['PRODUCTOR']),
    ('autorreporte.consultar', 'Consultar autorreportes', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','PRODUCTOR']),
    -- sincronización
    ('sincronizacion.enviar', 'Enviar operaciones de sincronización', ARRAY['TECNICO','PRODUCTOR']),
    -- concepto
    ('concepto.consultar', 'Consultar conceptos de aptitud', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    -- planificación
    ('planificacion.crear', 'Crear planificaciones', ARRAY['AGRONOMO_SUPERVISOR']),
    ('planificacion.responder', 'Responder planificaciones', ARRAY['PRODUCTOR']),
    ('planificacion.resultado_lote', 'Registrar el resultado de una actividad en un lote', ARRAY['TECNICO']),
    ('planificacion.consultar', 'Consultar planificaciones', ARRAY['AGRONOMO_SUPERVISOR','TECNICO','PRODUCTOR']),
    ('actividades_tecnico.consultar', 'Consultar actividades de técnicos', ARRAY['ADMINISTRADOR','AGRONOMO_SUPERVISOR']);

  -- Los cuatro roles deben existir (los siembra 02_catalogos_basicos.sql).
  SELECT string_agg(DISTINCT x.rol, ', ') INTO v_falta_rol
    FROM (SELECT unnest(roles) AS rol FROM pg_temp.permiso_esperado) x
   WHERE NOT EXISTS (SELECT 1 FROM sigat.rol r WHERE r.rol_codigo = x.rol);
  IF v_falta_rol IS NOT NULL THEN
    RAISE EXCEPTION USING ERRCODE = 'foreign_key_violation',
      MESSAGE = 'Faltan roles en sigat.rol: ' || v_falta_rol || ' (los siembra 02_catalogos_basicos.sql).';
  END IF;

  SELECT (SELECT count(*) FROM sigat.permiso) + (SELECT count(*) FROM sigat.rol_permiso) INTO v_existentes;

  IF v_existentes = 0 THEN
    INSERT INTO sigat.permiso (perm_codigo, perm_descripcion)
    SELECT codigo, descripcion FROM pg_temp.permiso_esperado;
    INSERT INTO sigat.rol_permiso (rol_id, perm_id)
    SELECT r.rol_id, p.perm_id
      FROM pg_temp.permiso_esperado e
      CROSS JOIN LATERAL unnest(e.roles) AS x(rol)
      JOIN sigat.rol r ON r.rol_codigo = x.rol
      JOIN sigat.permiso p ON p.perm_codigo = e.codigo;
    RETURN;
  END IF;

  -- Ya hay datos: comparar códigos, descripciones y pares rol-permiso (por código, nunca por id).
  SELECT string_agg(linea, E'\n  - ' ORDER BY linea) INTO v_diferencias FROM (
    SELECT format('permiso no esperado: %s (%s)', a.perm_codigo, a.perm_descripcion) AS linea
      FROM (SELECT perm_codigo, perm_descripcion FROM sigat.permiso
            EXCEPT SELECT codigo, descripcion FROM pg_temp.permiso_esperado) a
    UNION ALL
    SELECT format('falta el permiso: %s (%s)', b.codigo, b.descripcion)
      FROM (SELECT codigo, descripcion FROM pg_temp.permiso_esperado
            EXCEPT SELECT perm_codigo, perm_descripcion FROM sigat.permiso) b
    UNION ALL
    SELECT format('par no esperado: %s -> %s', c.perm_codigo, c.rol_codigo)
      FROM (SELECT p.perm_codigo, r.rol_codigo FROM sigat.rol_permiso rp
              JOIN sigat.permiso p ON p.perm_id = rp.perm_id JOIN sigat.rol r ON r.rol_id = rp.rol_id
            EXCEPT SELECT e.codigo, x.rol FROM pg_temp.permiso_esperado e CROSS JOIN LATERAL unnest(e.roles) AS x(rol)) c
    UNION ALL
    SELECT format('falta el par: %s -> %s', d.codigo, d.rol)
      FROM (SELECT e.codigo, x.rol FROM pg_temp.permiso_esperado e CROSS JOIN LATERAL unnest(e.roles) AS x(rol)
            EXCEPT SELECT p.perm_codigo, r.rol_codigo FROM sigat.rol_permiso rp
              JOIN sigat.permiso p ON p.perm_id = rp.perm_id JOIN sigat.rol r ON r.rol_id = rp.rol_id) d
  ) t;

  IF v_diferencias IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = 'integrity_constraint_violation',
      MESSAGE = 'permiso / rol_permiso ya tienen datos y NO coinciden con la matriz de permisos.py. '
                || E'No se modificó nada. Diferencias:\n  - ' || v_diferencias,
      HINT = 'Resuelva la carga con el responsable de la BD y vuelva a ejecutar.';
  END IF;
  -- Coinciden exactamente: no se inserta nada.
END $$;
