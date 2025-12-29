-- Script de inicialización para APG BI Dashboard
-- Este script se ejecuta automáticamente cuando se crea el contenedor de PostgreSQL

-- Crear extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Crear usuario específico para la aplicación (opcional)
-- DO $$ 
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'apg_bi_user') THEN
--         CREATE ROLE apg_bi_user WITH LOGIN PASSWORD 'secure_password_here';
--     END IF;
-- END
-- $$;

-- Otorgar permisos al usuario de la aplicación
-- GRANT CONNECT ON DATABASE apg_bi TO apg_bi_user;
-- GRANT USAGE ON SCHEMA public TO apg_bi_user;
-- GRANT CREATE ON SCHEMA public TO apg_bi_user;

-- Configurar parámetros específicos para la base de datos
ALTER DATABASE apg_bi SET timezone TO 'UTC';
ALTER DATABASE apg_bi SET log_statement TO 'all';
ALTER DATABASE apg_bi SET log_min_duration_statement TO 1000;

-- Crear índices útiles que se usarán frecuentemente
-- (Estos se crearán automáticamente por SQLAlchemy, pero se pueden pre-crear aquí)

-- Función para logging de cambios (audit trail)
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log(table_name, operation, user_id, old_values, new_values, timestamp)
        VALUES (TG_TABLE_NAME, 'INSERT', current_setting('app.current_user_id', true)::integer, NULL, row_to_json(NEW), NOW());
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log(table_name, operation, user_id, old_values, new_values, timestamp)
        VALUES (TG_TABLE_NAME, 'UPDATE', current_setting('app.current_user_id', true)::integer, row_to_json(OLD), row_to_json(NEW), NOW());
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log(table_name, operation, user_id, old_values, new_values, timestamp)
        VALUES (TG_TABLE_NAME, 'DELETE', current_setting('app.current_user_id', true)::integer, row_to_json(OLD), NULL, NOW());
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Crear tabla de audit log (opcional)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL,
    user_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crear índices para la tabla de audit
CREATE INDEX IF NOT EXISTS idx_audit_log_table_name ON audit_log(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);

-- Función para limpiar logs antiguos
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_log WHERE timestamp < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Programar limpieza automática (requiere pg_cron extension)
-- SELECT cron.schedule('cleanup-audit-logs', '0 2 * * *', 'SELECT cleanup_old_audit_logs();');

-- Crear función para obtener estadísticas de la aplicación
CREATE OR REPLACE FUNCTION get_app_stats()
RETURNS TABLE(
    total_users INTEGER,
    active_users INTEGER,
    total_companies INTEGER,
    active_sessions INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*)::INTEGER FROM users) as total_users,
        (SELECT COUNT(*)::INTEGER FROM users WHERE is_active = true) as active_users,
        (SELECT COUNT(*)::INTEGER FROM companies) as total_companies,
        (SELECT COUNT(*)::INTEGER FROM user_sessions WHERE is_active = true AND expires_at > NOW()) as active_sessions;
END;
$$ LANGUAGE plpgsql;

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE 'Base de datos APG BI Dashboard inicializada correctamente';
    RAISE NOTICE 'Extensiones creadas: uuid-ossp, pg_stat_statements, pg_trgm';
    RAISE NOTICE 'Funciones de utilidad creadas';
    RAISE NOTICE 'Tabla de audit log creada';
END
$$;
