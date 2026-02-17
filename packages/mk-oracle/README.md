# Oracle SQL check

## Table of Contents

- [Oracle instant client download and installation](#oracle-instant-client-download-and-installation)
  - [Linux](#linux)
  - [Windows](#windows)
- [YAML Configuration](#yaml-configuration)
  - [Configuration Structure](#configuration-structure)
  - [Authentication](#authentication)
  - [Connection](#connection)
  - [Instances](#instances)
  - [Discovery](#discovery)
  - [Options](#options)
  - [Sections](#sections)
  - [Complete Configuration Example](#complete-configuration-example)
- [Oracle Wallet Authentication](#oracle-wallet-authentication)
  - [Default Configuration](#default-configuration)
  - [Enabling Wallet Authentication](#enabling-wallet-authentication)
  - [Workflow 1: Using Default Configuration](#workflow-1-using-default-configuration-no-explicit-tns_admin)
  - [Workflow 2: Using Custom tns_admin Location](#workflow-2-using-custom-tns_admin-location)

## Oracle instant client download and installation

### Linux

Please, download and unzip Oracle Instant Client _zipped_ installation for your Linux.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

We recommend to use version 21.

For unzipping, use command like this:
assuming that you are using `instantclient-basiclite-linux.x64-21.20.0.0.0dbru.zip`
Choose one of the following options:

1. Global Installation

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /opt/checkmk/oracle-instant-client
```

2. In Agent installation(recommended)

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /path/to/agent/plugins/packages/mk-oracle
```

For default _legacy deployment_ plugins path for Checkmk agent on Linux is `/usr/lib/check_mk_agent/plugins/`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /usr/lib/check_mk_agent/plugins/packages/mk-oracle/
```

For default _single directory deployment_ plugins path for Checkmk agent on Linux is `/opt/checkmk/agent/default/package/plugins`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /opt/checkmk/agent/default/package/plugins/packages/mk-oracle/
```

you may determine the path to the agent installation by running command:

```
sudo check_mk_agent | grep "^pluginsdir " | head -1
```

Please install oracle instant client to be write-accessible only by admin user.

After the Instant Client libraries are installed you may use WATO to configure type of deployment

_Ubuntu Linux_ may require linking libaio

```
ln -sf "/lib/x86_64-linux-gnu/libaio.so.1t64" "/lib/x86_64-linux-gnu/libaio.so.1"
```

### Windows

Download and unzip Oracle Windows installation guide to configure your Oracle Instant Client in folder of your choice.
Find it on Oracle’s download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

Choose one of the following options:

1. Global Installation
   PATH must contain the path to the folder where dlls are stored.
   For example: `C:\oracle\instantclient_21_3`
2. In Agent Installation(recommended)
   you unzip \*.dll files to `PROGRAMDATA%/checkmk/agent/plugins/packages/mk-oracle` folder.

## YAML Configuration

The mk-oracle plugin is configured via a YAML file. The configuration file is placed in the agent's configuration directory (`MK_CONFDIR`). The file defines how the plugin connects to Oracle databases, which instances to monitor, and what data to collect.

### Configuration Structure

The top-level structure consists of two root sections:

```yaml
system: # optional, global plugin settings
oracle: # Oracle monitoring configuration
```

#### System Section

Controls plugin-wide logging behavior.

```yaml
system:
  logging:
    level: 'warn' # optional, default: "info"
    max_size: 1000000 # max log file size in bytes
    max_count: 5 # number of rotated log files to keep
```

#### Oracle Section

All Oracle-specific configuration lives under `oracle.main`. It contains the following subsections:

| Subsection       | Required    | Description                                                                    |
| ---------------- | ----------- | ------------------------------------------------------------------------------ |
| `authentication` | Yes         | Credentials and authentication method                                          |
| `connection`     | No          | Hostname, port, timeouts, and TNS configuration                                |
| `instances`      | Conditional | Explicit list of databases to monitor (required if `discovery` is not enabled) |
| `discovery`      | No          | Automatic instance detection                                                   |
| `options`        | No          | Connection pool limits and OCI client behavior                                 |
| `sections`       | No          | Which monitoring sections to collect and their settings                        |
| `cache_age`      | No          | Cache lifetime for async sections (default: `600` seconds)                     |
| `piggyback_host` | No          | Piggyback hostname for forwarding data to another host                         |

### Authentication

Defines how the plugin authenticates to the database.

```yaml
authentication:
  username: 'checkmk' # mandatory for standard auth
  password: 'secret' # mandatory for standard auth
  role: 'sysdba' # optional, e.g. sysdba, sysasm
  type: 'standard' # optional, default: "standard", values: standard, wallet
```

Set `type: wallet` to use Oracle Wallet authentication instead of username/password (see [Oracle Wallet Authentication](#oracle-wallet-authentication) below).

### Connection

Defines the network-level connection parameters shared by all instances unless overridden.

```yaml
connection:
  hostname: 'localhost' # optional, default: "localhost"
  port: 1521 # optional, default: 1521
  timeout: 5 # optional, default: 5 (seconds)
  tns_admin: '/path/to/oracle/config/files/' # optional, default: MK_CONFDIR
  oracle_local_registry: '/etc/oracle/olr.loc' # optional, path to Oracle Local Registry
```

- `tns_admin` points to the directory containing `sqlnet.ora` and `tnsnames.ora`.
- `oracle_local_registry` points to the Oracle Local Registry file used for instance discovery via `oratab`.

### Instances

The `instances` list defines which databases to monitor. Each entry specifies a connection identifier using one or more of the following fields:

| Field           | Description                                   |
| --------------- | --------------------------------------------- |
| `sid`           | Oracle System Identifier (SID)                |
| `service_name`  | Oracle service name                           |
| `instance_name` | Oracle instance name (RAC environments)       |
| `alias`         | TNS alias (must be defined in `tnsnames.ora`) |

Each instance can also override the top-level `authentication` and `connection` settings.

The plugin builds an Oracle connection string (connect descriptor) from these fields. The following examples show how different field combinations produce different connection strings.

#### Connect by SID

```yaml
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: system
      password: pass
    instances:
      - sid: SID
```

Generated connection string:

```
(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
  (CONNECT_DATA = (SID = SID)))
```

#### Connect by Service Name

```yaml
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: system
      password: pass
    instances:
      - service_name: MYSERVICE
```

Generated connection string:

```
(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
  (CONNECT_DATA = (SERVICE_NAME = MYSERVICE)))
```

#### Connect by Service Name and Instance Name

Useful in Oracle RAC environments where you need to target a specific instance of a service.

```yaml
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: system
      password: pass
    instances:
      - service_name: MYSERVICE
        instance_name: MYINSTANCE
```

Generated connection string:

```
(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
  (CONNECT_DATA = (SERVICE_NAME = MYSERVICE)(INSTANCE_NAME = MYINSTANCE)))
```

#### Connect by SID, Service Name, and Instance Name

All three identifiers can be combined into a single connect descriptor.

```yaml
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: system
      password: pass
    instances:
      - service_name: MYSERVICE
        sid: MYSID
        instance_name: MYINSTANCE
```

Generated connection string:

```
(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
  (CONNECT_DATA = (SERVICE_NAME = MYSERVICE)(INSTANCE_NAME = MYINSTANCE)(SID = MYSID)))
```

#### Connect by TNS Alias

When using a TNS alias, the plugin uses the alias directly as the connection identifier instead of building a connect descriptor. The alias must be defined in your `tnsnames.ora` file (located in `tns_admin`, which defaults to `MK_CONFDIR`).

```yaml
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: system
      password: pass
    instances:
      - alias: TNS_ALIAS
```

Generated connection string:

```
TNS_ALIAS
```

You can also set a custom `tns_admin` path to point to a directory containing your `tnsnames.ora`:

```yaml
connection:
  tns_admin: /custom/path/to/tns_admin
```

#### Monitoring Multiple Databases

You can define multiple instances to monitor several databases with a single plugin configuration. Each instance can use a different connection method.

```yaml
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: system
      password: pass
    instances:
      - service_name: MYSERVICE
      - sid: MYSID
```

Generated connection strings:

```
(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
  (CONNECT_DATA = (SERVICE_NAME = MYSERVICE)))

(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521))
  (CONNECT_DATA = (SID = MYSID)))
```

#### Per-Instance Authentication and Connection Overrides

Each instance can override the top-level `authentication` and `connection` settings. This is useful when different databases require different credentials or are hosted on different servers.

```yaml
oracle:
  main:
    connection:
      hostname: db-primary
      port: 1521
    authentication:
      username: checkmk
      password: default_pass
    instances:
      - service_name: PRODDB
      - service_name: REMOTEDB
        authentication:
          username: user
          password: pass
        connection:
          hostname: db-secondary
          port: 1522
```

### Discovery

As an alternative to listing instances explicitly, the plugin can automatically detect Oracle instances running on the host using the Oracle Local Registry (`oratab`).

```yaml
discovery:
  detect: yes # enable automatic instance detection
  include: ['PROD', 'DEV'] # optional, only monitor these instances
  exclude: ['TEST'] # optional, skip these instances
```

- When `detect: yes` is set, the plugin reads the local Oracle configuration to discover running instances.
- Use `include` to restrict monitoring to a specific set of instance names.
- Use `exclude` to skip specific instances.
- If both `include` and `exclude` are specified, `exclude` takes precedence.
- `instances` is required when `discovery` is not enabled. When discovery is enabled, `instances` can still be specified to add additional databases that are not discoverable locally.

### Options

Fine-tunes plugin runtime behavior.

```yaml
options:
  max_connections: 6 # optional, default: 6, max parallel database connections
  max_queries: 16 # optional, reserved for future use
  use_host_client: never # optional, default: "auto"
  IGNORE_DB_NAME: 0 # optional, default: 0
```

- `use_host_client` controls whether the plugin uses the OCI library installed on the host or the one bundled with the plugin. Values: `auto`, `never`, `always`, or a path to a specific OCI library.
- `IGNORE_DB_NAME`: when set to `1`, the plugin will not verify that the database name matches the instance name.

### Sections

Defines which monitoring sections to collect. If omitted, all default sections are enabled.

Each section can optionally specify:

- `affinity`: determines which database types the section applies to (`"db"`, `"asm"`, or `"all"`).
- `is_async`: when `yes`, the section runs asynchronously and its results are cached (controlled by `cache_age`).

```yaml
sections:
  - instance:
      affinity: 'db'
  - asm_instance:
      affinity: 'asm'
  - dataguard_stats:
  - locks:
  - logswitches:
  - longactivesessions:
  - performance:
  - processes:
      affinity: 'all'
  - recovery_area:
  - recovery_status:
  - sessions:
  - systemparameter:
  - undostat:
  - asm_diskgroup:
      is_async: yes
      affinity: 'asm'
  - iostats:
      is_async: yes
  - jobs:
      is_async: yes
  - resumable:
      is_async: yes
  - rman:
      is_async: yes
  - tablespaces:
      is_async: yes
```

### Complete Configuration Example

Below is a full configuration example demonstrating all available fields:

```yaml
system:
  logging:
    level: 'warn'
    max_size: 1000000
    max_count: 5

oracle:
  main:
    options:
      max_connections: 6
      use_host_client: never
      IGNORE_DB_NAME: 0
    connection:
      hostname: 'localhost'
      port: 1521
      timeout: 5
      tns_admin: '/etc/check_mk'
    authentication:
      username: 'checkmk'
      password: 'secret'
      role: 'sysdba'
      type: 'standard'
    discovery:
      detect: yes
      include: ['PROD', 'DEV']
      exclude: ['TEST']
    instances:
      - service_name: 'ORCL'
        sid: 'ORCL'
      - alias: 'REMOTE_DB'
    sections:
      - instance:
          affinity: 'db'
      - tablespaces:
          is_async: yes
      - performance:
      - sessions:
    cache_age: 600
    piggyback_host: 'mypiggybackhost'
```

## Oracle Wallet Authentication

Oracle Wallet provides a secure way to authenticate to Oracle databases without storing passwords in plain text configuration files.
The plugin supports Oracle Wallet authentication with the following behavior:

### Default Configuration

- **TNS_ADMIN**: By default, the `TNS_ADMIN` environment variable is set to `MK_CONFDIR` (typically `/etc/check_mk` on Linux).
- **Wallet Location**: The default wallet location is `MK_CONFDIR/oracle_wallet` (e.g., `/etc/check_mk/oracle_wallet`).

### Enabling Wallet Authentication

To enable Oracle Wallet authentication, set the authentication type to `wallet` in your YAML configuration file:

```yaml
oracle:
  main:
    connection:
      hostname: 127.0.0.1
      port: 1521
      service_name: FREE
    authentication:
      type: wallet # auth type is set to wallet
```

### Workflow 1: Using Default Configuration (No explicit tns_admin)

When the authentication type is set to `wallet` and no `tns_admin` is explicitly configured:

1. The plugin sets `TNS_ADMIN` to `MK_CONFDIR`.
2. A `sqlnet.ora` file is created in `MK_CONFDIR` (if it doesn't already exist) with the wallet location pointing to `MK_CONFDIR/oracle_wallet`.
3. You need to place your Oracle Wallet files in `MK_CONFDIR/oracle_wallet`.

**Note:** You can also pre-create `sqlnet.ora`, `tnsnames.ora`, and the `oracle_wallet` directory with wallet files in `MK_CONFDIR` before running the plugin.

#### Creating the Oracle Wallet

Assuming `MK_CONFDIR` is `/etc/check_mk` and this is your config file:

```yaml
oracle:
  main:
    connection:
      hostname: 127.0.0.1
      port: 1521
      service_name: FREE
    authentication:
      type: wallet
```

Use the following commands to create and configure the wallet:

1. Create the wallet directory and initialize it:

```bash
mkstore -wrl /etc/check_mk/oracle_wallet -create
```

2. Add credentials to the wallet (replace with your actual connection details):

```bash
mkstore -wrl /etc/check_mk/oracle_wallet -createCredential 127.0.0.1:1521/FREE/FREE checkmk myPassword
```

#### Example sqlnet.ora File

```
LOG_DIRECTORY_CLIENT = /var/log/check_mk/oracle_client
DIAG_ADR_ENABLED = OFF

SQLNET.WALLET_OVERRIDE = TRUE
WALLET_LOCATION =
 (SOURCE=
   (METHOD = FILE)
   (METHOD_DATA = (DIRECTORY=/etc/check_mk/oracle_wallet))
 )
```

### Workflow 2: Using Custom tns_admin Location

When the authentication type is set to `wallet` and `tns_admin` is explicitly set in the configuration:

```yaml
oracle:
  main:
    connection:
      hostname: 127.0.0.1
      port: 1521
      tns_admin: /custom/path/to/tns_admin
    authentication:
      type: wallet
```

In this case:

1. The plugin sets `TNS_ADMIN` to the value specified in `tns_admin`.
2. The plugin does **not** create any configuration files automatically.
3. You are responsible for managing all configuration files in your custom `TNS_ADMIN` directory, including:
   - `sqlnet.ora` (with wallet location configuration)
   - `tnsnames.ora` (if using TNS aliases)
   - Oracle Wallet files in the location specified in your `sqlnet.ora`

This workflow is useful when you have an existing Oracle configuration setup that you want to reuse.
