Performance test
****************

# Postges configuration

## Create key and certificates

On the client, run:
hostname --fqdn

On the server, use the scripts to generate the certificates:

mk_server_cert.sh -> certificates for server
mk_client_cert.sh -> certificates for client
^Go with the default "performance".

On the client:

scp -r "root@qa.lan.checkmk.net:~/postgres/ssl_server_files/root.crt" ~/.postgresql/
scp -r "root@qa.lan.checkmk.net:~/postgres/ssl_client_files/postgresql/postgresql.crt" ~/.postgresql/
scp -r "root@qa.lan.checkmk.net:~/postgres/ssl_client_files/postgresql/postgresql.key" ~/.postgresql/
psql "host=qa.lan.checkmk.net dbname=performance user=performance sslmode=verify-full"

## postgresql.conf

ssl = on
ssl_ca_file = '/etc/postgresql/ssl/root.crt'
ssl_key_file = '/etc/postgresql/ssl/server.key'
ssl_cert_file = '/etc/postgresql/ssl/server.crt'
listen_addresses = '*'

## pg_hba.conf

hostssl performance     performance     0.0.0.0/0               cert

# Database creation

* sudo -u postgres psql --file=./createuser_performance.sql
* sudo -u postgres psql --file=./createdb_performance.sql
* sudo -u postgres psql --username=performance --dbname=performance --file=./initdb_performance.sql

# Database recreation

* sudo -u postgres psql --file=./dropdb_performance.sql
* sudo -u postgres psql --file=./createdb_performance.sql
* sudo -u postgres psql --username=performance --dbname=performance --file=./initdb_performance.sql

