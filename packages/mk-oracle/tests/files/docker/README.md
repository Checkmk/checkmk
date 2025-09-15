# Oracle Database with Docker Compose

This folder provides a simple way to run Oracle Database (Free or XE editions) using Docker Compose. It's configured for easy setup, persistent data, and straightforward customization.

NOTE: This is only for testing purposes.

## Prerequisites

Before you start, make sure you have the following installed:
* [Docker](https://docs.docker.com/get-docker/)
* [Docker Compose](https://docs.docker.com/compose/install/)

---

## Available Database Services

This `docker-compose.yml` file defines two separate Oracle database services. You should only run **one at a time** since they are both configured to use the same host port (`1521`), you can change port using `ORACLE_PORT` environment variable.

* `oracle-free`: Runs the **Oracle Database Free** edition. This is the latest developer-focused edition from Oracle.
* `oracle-xe`: Runs the older **Oracle Database Express Edition (XE)**.

---

## How to Run

You can run a specific database service directly from your terminal.

#### Oracle Free

To start the **Oracle Free** database, run:
```bash
docker compose -f <path_to_docker_compose_file> up oracle-free
```

Or you can specify a version, you can find all available versions on [Docker Hub](https://hub.docker.com/r/gvenzl/oracle-free):
```bash
ORACLE_FREE_VERSION=23.9 docker compose -f <path_to_docker_compose_file> up oracle-free
```

Available environment variables:
- `ORACLE_FREE_VERSION`
- `ORACLE_PASSWORD` - default `oracle`
- `ORACLE_PORT` - default `1521`

Default SID is `FREEPDB1` and it's not configurable.

#### Oracle XE

To start the **Oracle XE** database, run:
```bash
docker compose -f <path_to_docker_compose_file> up oracle-xe
```

Or you can specify a version, you can find all available versions on [Docker Hub](https://hub.docker.com/r/gvenzl/oracle-xe)(not all versions are working as expected, please refer to the link for more details):
```bash
ORACLE_XE_VERSION=11 docker compose -f <path_to_docker_compose_file> up oracle-xe
```

Available environment variables:
- `ORACLE_XE_VERSION`
- `ORACLE_PASSWORD` - default `oracle`
- `ORACLE_PORT` - default `1521`

Default SID is `FREEPDB1` and it's not configurable.

#### Oracle 12c

To start the **Oracle 12c** database, run:
```bash
docker compose -f <path_to_docker_compose_file> up oracle-12c
```

Available environment variables:
- `ORACLE_PASSWORD` - default `oracle`
- `ORACLE_PORT` - default `1521`

Default SID is `XE` and it's not configurable.

#### Oracle 19c

To start the **Oracle 12c** database, run:
```bash
docker compose -f <path_to_docker_compose_file> up oracle-12c
```

Available environment variables:
- `ORACLE_PASSWORD` - default `oracle`
- `ORACLE_PORT` - default `1521`
- `ORACLE_SID` - default `ORCLCDB`

## Configuration

You can customize the database configuration using environment variables in `docker-compose.yml` file, 
you can find the available options, for `oracle-free` [here](https://hub.docker.com/r/gvenzl/oracle-free#environment-variables)
and `oracle-xe` [here](https://hub.docker.com/r/gvenzl/oracle-xe#environment-variables).

Default values are provided for convenience, but you can override them as needed:
* `ORACLE_PASSWORD`: Sets the password for the `SYS`, `SYSTEM`, and `PDBADMIN` users. Default is `admin`.
