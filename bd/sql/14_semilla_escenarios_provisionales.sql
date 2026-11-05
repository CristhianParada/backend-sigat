-- =====================================================================
-- SIGAT v9.1 - Semilla PROVISIONAL del catálogo escenario_trampeo (RN-002)
--
-- Qué cambia: SOLO AGREGA las 4 filas del catálogo cuando la tabla está vacía. No crea ni
-- modifica tablas, columnas, restricciones ni otros datos.
-- Valores: informe de consumo de datos (CD §10.1; RN-002, Tabla 1 OIEA 2005).
-- Estado: PROVISIONALES (decisión del responsable del proyecto, 2026-11-04, pendiente P-02).
--   * Oficial: escenario validado y aprobado por el responsable institucional.
--   * Provisional: registro inicial para desarrollar y probar mientras llega esa validación.
-- esce_fuente lo deja escrito en cada fila para que nadie lo confunda con un valor oficial.
--
-- Comportamiento ante datos existentes (nunca completa, modifica ni borra filas):
--   * tabla vacía                                   -> inserta los 4 escenarios;
--   * tabla con exactamente estos 4 escenarios       -> no hace nada (idempotente);
--   * cualquier otro contenido (parcial o distinto,
--     incluida una carga oficial con otra fuente)    -> se DETIENE con un error que enumera
--                                                      las diferencias. Lo resuelve el
--                                                      responsable de la BD.
-- Lo aplica la migración Alembic 0005 y, en una instalación nueva, 00_instalar_todo.sql.
-- =====================================================================

DO $$
DECLARE
  v_fuente constant text :=
    'PROVISIONAL: RN-002, Tabla 1 OIEA 2005 (informe de consumo de datos §10.1). '
    'Pendiente de validación institucional ICA/Agronomía (P-02).';
  v_existentes integer;
  v_diferencias text;
BEGIN
  CREATE TEMP TABLE IF NOT EXISTS pg_temp.escenario_esperado (
    descripcion varchar, orden smallint, desde numeric(10,4), hasta numeric(10,4), fuente varchar
  ) ON COMMIT DROP;
  TRUNCATE pg_temp.escenario_esperado;
  INSERT INTO pg_temp.escenario_esperado VALUES
    ('Área infestada', 1, 1.0000, NULL,   v_fuente),
    ('Supresión',      2, 0.1000, 1.0000, v_fuente),
    ('Erradicación',   3, 0.0000, 0.1000, v_fuente),
    ('Exclusión',      4, 0.0000, 0.0000, v_fuente);

  SELECT count(*) INTO v_existentes FROM sigat.escenario_trampeo;

  IF v_existentes = 0 THEN
    INSERT INTO sigat.escenario_trampeo
      (esce_descripcion, esce_orden, esce_mtd_desde_defecto, esce_mtd_hasta_defecto, esce_fuente)
    SELECT descripcion, orden, desde, hasta, fuente FROM pg_temp.escenario_esperado ORDER BY orden;
    RETURN;
  END IF;

  SELECT string_agg(linea, E'\n  - ' ORDER BY linea) INTO v_diferencias FROM (
    SELECT format('no esperado: %s (orden %s, %s-%s, fuente %s)', e.esce_descripcion, e.esce_orden,
                  e.esce_mtd_desde_defecto, coalesce(e.esce_mtd_hasta_defecto::text, 'sin límite'),
                  coalesce(e.esce_fuente, 'nula')) AS linea
      FROM (SELECT esce_descripcion, esce_orden, esce_mtd_desde_defecto, esce_mtd_hasta_defecto, esce_fuente
              FROM sigat.escenario_trampeo
            EXCEPT
            SELECT descripcion, orden, desde, hasta, fuente FROM pg_temp.escenario_esperado) e
    UNION ALL
    SELECT format('falta: %s (orden %s, %s-%s)', x.descripcion, x.orden, x.desde,
                  coalesce(x.hasta::text, 'sin límite'))
      FROM (SELECT descripcion, orden, desde, hasta, fuente FROM pg_temp.escenario_esperado
            EXCEPT
            SELECT esce_descripcion, esce_orden, esce_mtd_desde_defecto, esce_mtd_hasta_defecto, esce_fuente
              FROM sigat.escenario_trampeo) x
  ) d;

  IF v_diferencias IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = 'integrity_constraint_violation',
      MESSAGE = 'escenario_trampeo ya tiene datos y NO coinciden con la semilla provisional. '
                || E'No se modificó nada. Diferencias:\n  - ' || v_diferencias,
      HINT = 'Resuelva el catálogo con el responsable de la BD (ICA/Agronomía) y vuelva a ejecutar.';
  END IF;
  -- Coinciden exactamente: no se inserta nada.
END $$;
