# Oracle Database with Docker Compose

This folder provides a simple way to run Oracle Database (Free or XE editions) using Docker Compose. It's configured for easy setup, persistent data, and straightforward customization.

NOTE: This is only for testing purposes.

## Prerequisites

Before you start, make sure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Available Database Services

This `docker-compose.yml` file defines several Oracle database services. You should only run **one at a time** since they are configured to use the same host port (`1521`) by default.

- `oracle-free` (Version 23): Runs the **Oracle Database Free** edition.
- `oracle-xe` (Version 11): Runs the **Oracle Database Express Edition (XE)**.
- `oracle-12c` (Version 12): Runs **Oracle Database 12c**.
- `oracle-19c` (Version 19): Runs **Oracle Database 19c**.

---

## How to Run

You can easily start any of the supported database versions using the `run-db.sh` helper script. This script handles starting the container and waiting for the database to be fully ready and healthy.

### Usage

```bash
./run-db.sh -v <version> [-P <port>]
```

### Options

- `-v, --version`: **Required**. The Oracle version to run.
  - Available versions: `23`, `11`, `12`, `19`.
- `-P, --port`: **Optional**. The host port to bind the database listener to.
  - Default: `1521`.

### Examples

Start Oracle 23 (Free) on default port 1521:

```bash
./run-db.sh -v 23
```

Start Oracle 19c on port 1521:

```bash
./run-db.sh -v 19 -P 1521
```

The script will output the connection details (Host, Port, SID, Password) once the database is ready to accept connections.

### Default Credentials

- **Password**: `oracle` (for all versions)
- **SIDs**:
  - Version 23: `FREE`
  - Version 19: `ORCLCDB`
  - Version 12: `XE`
  - Version 11: `XE`
