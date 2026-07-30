\set ON_ERROR_STOP on

\prompt 'Password for role haydar_app: ' app_password
\prompt 'Password for role haydar_migrator: ' migrator_password

SELECT format('CREATE ROLE haydar_app LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'haydar_app')
\gexec

SELECT format('ALTER ROLE haydar_app LOGIN PASSWORD %L', :'app_password')
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'haydar_app')
\gexec

SELECT format('CREATE ROLE haydar_migrator LOGIN PASSWORD %L', :'migrator_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'haydar_migrator')
\gexec

SELECT format('ALTER ROLE haydar_migrator LOGIN PASSWORD %L', :'migrator_password')
WHERE EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'haydar_migrator')
\gexec

SELECT 'CREATE DATABASE haydar_dev OWNER haydar_migrator'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'haydar_dev')
\gexec

SELECT 'CREATE DATABASE haydar_test OWNER haydar_migrator'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'haydar_test')
\gexec

\connect haydar_dev
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE haydar_dev TO haydar_app;
GRANT USAGE ON SCHEMA public TO haydar_app;
ALTER DEFAULT PRIVILEGES FOR ROLE haydar_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO haydar_app;
ALTER DEFAULT PRIVILEGES FOR ROLE haydar_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO haydar_app;

\connect haydar_test
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE haydar_test TO haydar_app;
GRANT USAGE ON SCHEMA public TO haydar_app;
ALTER DEFAULT PRIVILEGES FOR ROLE haydar_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO haydar_app;
ALTER DEFAULT PRIVILEGES FOR ROLE haydar_migrator IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO haydar_app;

\unset app_password
\unset migrator_password

SELECT current_setting('server_version') AS server_version;
