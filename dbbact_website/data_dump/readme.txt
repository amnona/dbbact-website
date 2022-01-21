Files here are dbBact complete database dumps
Files are in PostgreSQL 9.5.10 binary format

To populate a postgres database with this dump, use the postgres command:
pg_restore -U postgres -d postgres --clean --create database/dbbact-export.psql


For instuctions on locally installing the dbBact rest-api server, see documentation at https://github.com/amnona/dbbact-server
