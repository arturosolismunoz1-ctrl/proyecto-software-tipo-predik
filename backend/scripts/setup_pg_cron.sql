-- ── pg_cron: Programar ETLs nocturnos ─────────────────────────────────────────
-- Ejecutar esto en el Editor SQL de Supabase (una sola vez).
--
-- Requisitos:
--   1. La extensión pg_cron debe estar habilitada en tu proyecto Supabase
--      (Settings → Database → Extensions → habilitar pg_cron)
--   2. La extensión pg_net debe estar habilitada para poder llamar HTTP endpoints
--      (Settings → Database → Extensions → habilitar pg_net)
--   3. Reemplaza TU_CRON_SECRET por un token aleatorio que configures como
--      variable CRON_SECRET en el backend de Render.
--   4. Reemplaza BACKEND_URL por la URL real de tu backend en Render.

-- ── 1. Programar ETL DENUE (diario a las 8:00 UTC = 2:00 AM CDMX) ─────────────
SELECT cron.schedule(
    'etl-denue-diario',
    '0 8 * * *',
    $$SELECT net.http_post(
        url:='BACKEND_URL/api/v1/admin/etl/denue/run',
        headers:=jsonb_build_object(
            'Authorization', 'Bearer TU_CRON_SECRET',
            'Content-Type', 'application/json'
        ),
        body:=jsonb_build_object(
            'max_records', 5000,
            'h3_resolution', 9
        )
    )$$
);

-- ── 2. Programar ETL Población (diario a las 8:15 UTC) ────────────────────────
SELECT cron.schedule(
    'etl-poblacion-diario',
    '15 8 * * *',
    $$SELECT net.http_post(
        url:='BACKEND_URL/api/v1/admin/etl/poblacion/run',
        headers:=jsonb_build_object(
            'Authorization', 'Bearer TU_CRON_SECRET',
            'Content-Type', 'application/json'
        )
    )$$
);

-- ── 3. Ver trabajos programados ───────────────────────────────────────────────
-- SELECT * FROM cron.job;
--
-- ── 4. Eliminar un trabajo (si es necesario) ──────────────────────────────────
-- SELECT cron.unschedule('etl-denue-diario');

-- ── 5. Nota sobre seguridad ───────────────────────────────────────────────────
-- El CRON_SECRET debe coincidir con el valor de CRON_SECRET en las variables
-- de entorno del backend en Render. El backend verificará este token en lugar
-- del JWT normal cuando el request provenga de pg_cron.
