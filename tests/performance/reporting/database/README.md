# Performance database

The PostgreSQL databases the performance tests upload to. How tests end up in them is described
in the [performance test guide](../../README.md#what-ends-up-in-the-database).

- `initdb_performance.sql`: the schema (`jobs`, `scenarios`, `tests`, `benchmarks`, `metrics`)
- [`graphs/`](graphs/README.md): the SQL of the Metabase dashboards

---

# PostgreSQL configuration

## Create key and certificates

On the client, run:

```bash
hostname --fqdn
```

On the server, use the scripts to generate the certificates:

- `mk_server_cert.sh`: certificates for the server
- `mk_client_cert.sh`: certificates for the client; go with the default "performance"

On the client:

```bash
scp -r "root@qa.lan.checkmk.net:~/postgres/ssl_server_files/root.crt" ~/.postgresql/
scp -r "root@qa.lan.checkmk.net:~/postgres/ssl_client_files/postgresql/postgresql.crt" ~/.postgresql/
scp -r "root@qa.lan.checkmk.net:~/postgres/ssl_client_files/postgresql/postgresql.key" ~/.postgresql/
psql "host=qa.lan.checkmk.net dbname=performance user=performance sslmode=verify-full"
```

## postgresql.conf

```
ssl = on
ssl_ca_file = '/etc/postgresql/ssl/root.crt'
ssl_key_file = '/etc/postgresql/ssl/server.key'
ssl_cert_file = '/etc/postgresql/ssl/server.crt'
listen_addresses = '*'
```

## pg_hba.conf

```
hostssl performance performance 0.0.0.0/0 cert
```

# Database creation

```bash
sudo -u postgres psql --file=./createuser_performance.sql
sudo -u postgres psql --file=./createdb_performance.sql
sudo -u postgres psql --username=performance --dbname=performance --file=./initdb_performance.sql
```

# Database recreation

```bash
sudo -u postgres psql --file=./dropdb_performance.sql
sudo -u postgres psql --file=./createdb_performance.sql
sudo -u postgres psql --username=performance --dbname=performance --file=./initdb_performance.sql
```

# Further databases

The site suite uploads into `performance`. The component suites upload into databases of their
own (see `database()` in `perftest_run.py`): `performance_data_backend` for the data backend,
`performance_component` for every other suite. Create each one like `performance`, with its own
name, e.g.:

```bash
sudo -u postgres psql --command="CREATE DATABASE performance_component OWNER performance;"
sudo -u postgres psql --username=performance --dbname=performance_component --file=./initdb_performance.sql
```

and allow it in `pg_hba.conf`:

```
hostssl performance_component performance 0.0.0.0/0 cert
hostssl performance_data_backend performance 0.0.0.0/0 cert
```

Run `initdb_performance.sql` as the `performance` user, as above: the tables have to belong to
it. Tables created by `postgres` make every upload fail with "permission denied for table jobs".
To repair such a database, hand its tables over:

```sql
ALTER TABLE jobs OWNER TO performance;
ALTER TABLE scenarios OWNER TO performance;
ALTER TABLE tests OWNER TO performance;
ALTER TABLE benchmarks OWNER TO performance;
ALTER TABLE metrics OWNER TO performance;
```
