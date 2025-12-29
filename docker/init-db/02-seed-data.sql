-- Script de datos iniciales para APG BI Dashboard
-- Este script crea datos de ejemplo y configuración inicial

-- Esperar a que las tablas sean creadas por SQLAlchemy
-- Este script se ejecutará después de que la aplicación cree las tablas

-- Función para insertar datos iniciales de manera segura
CREATE OR REPLACE FUNCTION insert_initial_data()
RETURNS void AS $$
DECLARE
    company_id INTEGER;
    admin_user_id INTEGER;
    contador_user_id INTEGER;
    invitado_user_id INTEGER;
    permission_id INTEGER;
BEGIN
    -- Verificar si ya existen datos
    IF EXISTS (SELECT 1 FROM companies LIMIT 1) THEN
        RAISE NOTICE 'Los datos iniciales ya existen, saltando inserción';
        RETURN;
    END IF;

    RAISE NOTICE 'Insertando datos iniciales...';

    -- Insertar empresa de ejemplo
    INSERT INTO companies (name, description, email, phone, address, website, created_at, updated_at, is_active)
    VALUES ('APG Empresa Demo', 'Empresa de demostración para el sistema APG BI', 'admin@apg-demo.com', '+1234567890', 'Dirección de ejemplo', 'https://apg-demo.com', NOW(), NOW(), true)
    RETURNING id INTO company_id;

    RAISE NOTICE 'Empresa creada con ID: %', company_id;

    -- Insertar permisos básicos
    -- Permisos para módulo de costos
    INSERT INTO permissions (name, description, module, action, created_at) VALUES
    ('costos.read', 'Ver datos de costos', 'costos', 'read', NOW()),
    ('costos.write', 'Editar datos de costos', 'costos', 'write', NOW()),
    ('costos.delete', 'Eliminar datos de costos', 'costos', 'delete', NOW()),
    ('costos.admin', 'Administrar módulo de costos', 'costos', 'admin', NOW());

    -- Permisos para módulo de producción
    INSERT INTO permissions (name, description, module, action, created_at) VALUES
    ('produccion.read', 'Ver datos de producción', 'produccion', 'read', NOW()),
    ('produccion.write', 'Editar datos de producción', 'produccion', 'write', NOW()),
    ('produccion.delete', 'Eliminar datos de producción', 'produccion', 'delete', NOW()),
    ('produccion.admin', 'Administrar módulo de producción', 'produccion', 'admin', NOW());

    -- Permisos para módulo de ventas
    INSERT INTO permissions (name, description, module, action, created_at) VALUES
    ('ventas.read', 'Ver datos de ventas', 'ventas', 'read', NOW()),
    ('ventas.write', 'Editar datos de ventas', 'ventas', 'write', NOW()),
    ('ventas.delete', 'Eliminar datos de ventas', 'ventas', 'delete', NOW()),
    ('ventas.admin', 'Administrar módulo de ventas', 'ventas', 'admin', NOW());

    -- Permisos para administración del sistema
    INSERT INTO permissions (name, description, module, action, created_at) VALUES
    ('sistema.read', 'Ver configuración del sistema', 'sistema', 'read', NOW()),
    ('sistema.write', 'Editar configuración del sistema', 'sistema', 'write', NOW()),
    ('sistema.admin', 'Administrar sistema completo', 'sistema', 'admin', NOW()),
    ('usuarios.read', 'Ver usuarios', 'usuarios', 'read', NOW()),
    ('usuarios.write', 'Gestionar usuarios', 'usuarios', 'write', NOW()),
    ('usuarios.admin', 'Administrar usuarios', 'usuarios', 'admin', NOW());

    RAISE NOTICE 'Permisos básicos creados';

    -- Asignar permisos a roles
    -- Permisos para ADMIN (todos los permisos)
    INSERT INTO role_permissions (role, permission_id, company_id, created_at)
    SELECT 'admin', id, NULL, NOW() FROM permissions;

    -- Permisos para CONTADOR (costos, producción, ventas - read/write)
    INSERT INTO role_permissions (role, permission_id, company_id, created_at)
    SELECT 'contador', id, company_id, NOW() 
    FROM permissions 
    WHERE (module IN ('costos', 'produccion', 'ventas') AND action IN ('read', 'write'))
       OR (module = 'usuarios' AND action = 'read');

    -- Permisos para EMPRESA (todos los módulos - read/write, sin admin)
    INSERT INTO role_permissions (role, permission_id, company_id, created_at)
    SELECT 'empresa', id, company_id, NOW() 
    FROM permissions 
    WHERE action IN ('read', 'write');

    -- Permisos para INVITADO (solo lectura)
    INSERT INTO role_permissions (role, permission_id, company_id, created_at)
    SELECT 'invitado', id, company_id, NOW() 
    FROM permissions 
    WHERE action = 'read' AND module IN ('costos', 'produccion', 'ventas');

    RAISE NOTICE 'Permisos asignados a roles';

    -- Insertar usuarios de ejemplo
    -- Usuario Administrador
    INSERT INTO users (username, email, password_hash, is_active, is_admin, role, created_at, updated_at, company_id)
    VALUES ('admin', 'admin@apg-demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8/2KyPgXJ2', true, true, 'admin', NOW(), NOW(), company_id)
    RETURNING id INTO admin_user_id;
    
    INSERT INTO user_profiles (first_name, last_name, phone, position, department, created_at, updated_at, user_id)
    VALUES ('Admin', 'Sistema', '+1234567890', 'Administrador del Sistema', 'TI', NOW(), NOW(), admin_user_id);

    -- Usuario Contador
    INSERT INTO users (username, email, password_hash, is_active, is_admin, role, created_at, updated_at, company_id)
    VALUES ('contador', 'contador@apg-demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8/2KyPgXJ2', true, false, 'contador', NOW(), NOW(), company_id)
    RETURNING id INTO contador_user_id;
    
    INSERT INTO user_profiles (first_name, last_name, phone, position, department, created_at, updated_at, user_id)
    VALUES ('Juan', 'Pérez', '+1234567891', 'Contador Principal', 'Contabilidad', NOW(), NOW(), contador_user_id);

    -- Usuario Invitado
    INSERT INTO users (username, email, password_hash, is_active, is_admin, role, created_at, updated_at, company_id)
    VALUES ('invitado', 'invitado@apg-demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8/2KyPgXJ2', true, false, 'invitado', NOW(), NOW(), company_id)
    RETURNING id INTO invitado_user_id;
    
    INSERT INTO user_profiles (first_name, last_name, phone, position, department, created_at, updated_at, user_id)
    VALUES ('María', 'García', '+1234567892', 'Consultor Externo', 'Consultoría', NOW(), NOW(), invitado_user_id);

    RAISE NOTICE 'Usuarios de ejemplo creados:';
    RAISE NOTICE 'Admin ID: %, Contador ID: %, Invitado ID: %', admin_user_id, contador_user_id, invitado_user_id;
    RAISE NOTICE 'Contraseña para todos los usuarios de ejemplo: "password123"';

    -- Insertar configuraciones iniciales de la aplicación (opcional)
    CREATE TABLE IF NOT EXISTS app_settings (
        id SERIAL PRIMARY KEY,
        key VARCHAR(100) UNIQUE NOT NULL,
        value TEXT,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    INSERT INTO app_settings (key, value, description) VALUES
    ('app.name', 'APG BI Dashboard', 'Nombre de la aplicación'),
    ('app.version', '1.0.0', 'Versión de la aplicación'),
    ('session.timeout', '28800', 'Timeout de sesión en segundos (8 horas)'),
    ('cache.default_ttl', '3600', 'TTL por defecto del cache en segundos (1 hora)'),
    ('audit.enabled', 'true', 'Habilitar auditoría de cambios'),
    ('maintenance.mode', 'false', 'Modo de mantenimiento');

    RAISE NOTICE 'Configuraciones iniciales de la aplicación creadas';
    RAISE NOTICE 'Datos iniciales insertados correctamente';

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error insertando datos iniciales: %', SQLERRM;
        RAISE;
END;
$$ LANGUAGE plpgsql;

-- Ejecutar la función de inserción de datos iniciales
-- Nota: Esta función se ejecutará cuando las tablas estén disponibles
-- Si las tablas no existen aún, la función simplemente no hará nada

-- Programar la ejecución de datos iniciales para después
-- (esto se puede hacer desde la aplicación Python también)
DO $$
BEGIN
    -- Intentar insertar datos iniciales
    -- Si falla porque las tablas no existen, simplemente continuar
    BEGIN
        PERFORM insert_initial_data();
    EXCEPTION
        WHEN undefined_table THEN
            RAISE NOTICE 'Las tablas aún no existen, los datos iniciales se insertarán más tarde';
        WHEN OTHERS THEN
            RAISE NOTICE 'Error al insertar datos iniciales: %', SQLERRM;
    END;
END;
$$;
