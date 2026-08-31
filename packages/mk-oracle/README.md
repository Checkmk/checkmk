# Oracle SQL Check

## Table of Contents

- [Supported Oracle Releases](#supported-oracle-releases)
- [Oracle Instant Client Download and Installation](#oracle-instant-client-download-and-installation)
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
  - [Custom SQL Metrics](#custom-sql-metrics)
  - [Targeting Pluggable Databases (PDBs)](#targeting-pluggable-databases-pdbs)
  - [User Configuration File](#user-configuration-file)
- [Complete Configuration Example](#complete-configuration-example)
- [Oracle Wallet Authentication](#oracle-wallet-authentication)
  - [Default Configuration](#default-configuration)
  - [Enabling Wallet Authentication](#enabling-wallet-authentication)
  - [Workflow 1: Using Default Configuration](#workflow-1-using-default-configuration-no-explicit-tns_admin)
  - [Workflow 2: Using Custom tns_admin Location](#workflow-2-using-custom-tns_admin-location)
- [Migration from the Legacy mk_oracle Plugin](#migration-from-the-legacy-mk_oracle-plugin)
  - [Running the Migration](#running-the-migration)
  - [Migration Output](#migration-output)
  - [What Is Migrated](#what-is-migrated)
  - [What Is Not Migrated](#what-is-not-migrated)
  - [Adapting Custom SQL Files](#adapting-custom-sql-files)

## Supported Oracle Releases

The minimum supported release is **Oracle 12.1.0.2**.

Older releases are not supported and are not accommodated. The queries name
`V$DATABASE.CDB` and `V$INSTANCE.CON_ID`, which arrived with 12.1, and
`V$PDBS.RECOVERY_STATUS`, which arrived with 12.1.0.2. An older instance
therefore fails with `ORA-00904` while its version is being established, and
reports that error in the `oracle_instance` section instead of being monitored.

## Oracle Instant Client Download and Installation

The plugin requires Oracle Instant Client libraries to connect to Oracle databases.
You can:

- Use the OCI libraries downloaded and deployed with the agent.
- Use the Oracle Instant Client deployed with an already installed Oracle Database.
- Install the Oracle Instant Client on the host.

### Linux

Please download and unzip the Oracle Instant Client _zipped_ installation for your Linux.
Find it on Oracle's download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

We recommend using version 21.

For unzipping, use a command like the one below,
assuming that you are using `instantclient-basiclite-linux.x64-21.20.0.0.0dbru.zip`.
Choose one of the following options:

1. Global Installation

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /opt/checkmk/oracle-instant-client
```

2. In Agent Installation (recommended)

```
    sudo unzip -j instantclient-basiclite-linux.x64-21.19.0.0.0dbru.zip -d /path/to/agent/plugins/packages/mk-oracle
```

The default _legacy deployment_ plugins path for the Checkmk agent on Linux is `/usr/lib/check_mk_agent/plugins/`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /usr/lib/check_mk_agent/plugins/packages/mk-oracle/
```

The default _single directory deployment_ plugins path for the Checkmk agent on Linux is `/opt/checkmk/agent/default/package/plugins`

```
sudo unzip -j /home/$USER/Downloads/instantclient-basic-linux.x64-21.20.0.0.0dbru.zip -d /opt/checkmk/agent/default/package/plugins/packages/mk-oracle/
```

You may determine the path to the agent installation by running the following command:

```
sudo check_mk_agent | grep "^pluginsdir " | head -1
```

Please install Oracle Instant Client to be write-accessible only by the admin user.

After the Instant Client libraries are installed, you may use WATO to configure the type of deployment.

_Ubuntu Linux_ may require linking `libaio`.

```
ln -sf "/lib/x86_64-linux-gnu/libaio.so.1t64" "/lib/x86_64-linux-gnu/libaio.so.1"
```

### Windows

Download and unzip the Oracle Instant Client for Windows into a folder of your choice.
Find it on Oracle's download page:
https://www.oracle.com/ch-de/database/technologies/instant-client/downloads.html

Choose one of the following options:

1. Global Installation
   `PATH` must contain the path to the folder where DLLs are stored.
   For example: `C:\oracle\instantclient_21_3`
2. In Agent Installation (recommended)
   Unzip \*.dll files to the `%PROGRAMDATA%/checkmk/agent/plugins/packages/mk-oracle` folder.

### Other Options

- If Oracle Instant Client is already installed on the host (e.g., via `yum`, `alien` or `winget`), you can use
  it instead by setting `use_host_client: always` (see [Options](#options)). Verify the installation
  with `ldconfig -p | grep libclntsh` and check `/etc/ld.so.conf.d/` for the registered path.

- You may use the `ORACLE_HOME` environment variable to point to the location of your Oracle Instant Client installation.
  Typically, you would set it to the database location like this:
  `export ORACLE_HOME=/opt/oracle23/u01/app/oracle/dbhome1`
  or using the corresponding Windows environment variable configuration.
  In this case, the Oracle plugin will use the `"$ORACLE_HOME/lib"` location to find Oracle Instant Client libraries.

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

| Subsection          | Required    | Description                                                                    |
| ------------------- | ----------- | ------------------------------------------------------------------------------ |
| `authentication`    | Yes         | Credentials and authentication method                                          |
| `connection`        | No          | Hostname, port, timeouts, and TNS configuration                                |
| `instances`         | Conditional | Explicit list of databases to monitor (required if `discovery` is not enabled) |
| `discovery`         | No          | Automatic instance detection                                                   |
| `options`           | No          | Connection pool limits and OCI client behavior                                 |
| `sections`          | No          | Which monitoring sections to collect and their settings                        |
| `excluded_sections` | No          | Sections that individual targets do not collect                                |
| `cache_age`         | No          | Cache lifetime for async sections (default: `600` seconds)                     |
| `piggyback_host`    | No          | Piggyback hostname for forwarding data to another host                         |

### Authentication

Defines how the plugin authenticates to the database.

```yaml
authentication:
  username: 'checkmk' # mandatory for standard auth
  password: 'secret' # mandatory for standard auth
  role: 'sysdba' # optional, e.g. sysdba, sysasm
  type: 'standard' # optional, default: "standard", values: standard, wallet
  asm_username: 'asm_user' # optional, only used for ASM instances
  asm_password: 'asm_pass' # optional, only used for ASM instances
  asm_role: 'sysasm' # optional, only used for ASM instances
  asm_type: 'standard' # optional, only used for ASM instances
```

Set `type: wallet` to use Oracle Wallet authentication instead of username/password (see [Oracle Wallet Authentication](#oracle-wallet-authentication) below).

#### ASM Authentication

ASM instances (a SID or instance name starting with `+`, e.g. `+ASM`) are usually
reached with different credentials than a normal database. The `asm_*` fields
hold those credentials and replace their regular counterparts whenever the plugin
connects to an ASM instance; normal database connections ignore them. This
mirrors `ASMUSER` of the legacy `mk_oracle` plugin.

Each field falls back to its regular counterpart when it is not set:

| Field          | Replaces   | Fallback when unset                                                                     |
| -------------- | ---------- | --------------------------------------------------------------------------------------- |
| `asm_username` | `username` | `username`                                                                              |
| `asm_password` | `password` | `password` (only when `asm_username` is unset, so an ASM user never reuses a DB secret) |
| `asm_role`     | `role`     | `role`                                                                                  |
| `asm_type`     | `type`     | derived from `asm_username`/`asm_password`, see below                                   |

When `asm_type` is omitted it is derived: `asm_username: '/'` or an
`asm_username` without `asm_password` means external authentication (`wallet`),
an ASM user with a password means `standard`, and without any `asm_username` the
regular `type` applies.

Set `asm_role` (typically `sysasm`, `sysdba` also works) — an ASM instance has no
data dictionary reachable from an unprivileged session.

```yaml
oracle:
  main:
    authentication:
      username: 'checkmk'
      password: 'secret'
      role: 'sysdba'
      asm_username: 'asm_user'
      asm_password: 'asm_pass'
      asm_role: 'sysasm'
    instances:
      - sid: 'ORCL' # connects as checkmk/secret as sysdba
      - sid: '+ASM' # connects as asm_user/asm_pass as sysasm
```

### Connection

Defines the network-level connection parameters shared by all instances unless overridden.

```yaml
connection:
  hostname: 'localhost' # optional, default: "localhost"
  port: 1521 # optional, default: 1521
  timeout: 5 # optional, default: 5 (seconds)
  tns_admin: '/path/to/oracle/config/files/' # optional, default: MK_CONFDIR
  oracle_local_registry: '/etc/oracle/olr.loc' # optional, default: /etc/oracle/olr.loc, /var/opt/oracle/olr.loc
```

- `tns_admin` points to the directory containing `sqlnet.ora` and `tnsnames.ora`.
- `oracle_local_registry` points to the `olr.loc` pointer file of Oracle Grid
  Infrastructure, which covers both Oracle Clusterware and Oracle Restart. When
  the setting is absent, `/etc/oracle/olr.loc` and `/var/opt/oracle/olr.loc` are
  probed in that order.

Two things change once the Grid home named in that file is found. The default
`hostname` becomes the name of this node instead of `localhost`, because a
listener under Grid Infrastructure binds the node address. And the Grid home
becomes the last candidate for `ORACLE_HOME`, which matters because Grid
Infrastructure stops maintaining `oratab` from version 12.2 on.

Pointing `oracle_local_registry` at a path that does not exist switches this
handling off, which is what legacy `mk_oracle` documents for `OLRLOC`.

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

As an alternative to listing instances explicitly, the plugin can automatically detect Oracle instances running on the host. On Unix it scans the process table for PMON processes, so only a running instance is found. On Windows there are no per-instance processes, so it reads the instance registry under `HKLM\SOFTWARE\Oracle` instead, which lists installed instances rather than running ones.

```yaml
discovery:
  detect: yes # enable automatic instance detection
  include: ['PROD', 'DEV'] # optional, only monitor these instances
  exclude: ['TEST'] # optional, skip these instances
```

- When `detect: yes` is set, the plugin discovers instances as described above.
- Use `include` to restrict monitoring to a specific set of instance names.
- Use `exclude` to skip specific instances.
- If both `include` and `exclude` are specified, `include` takes precedence and
  `exclude` is ignored. This matches the legacy `ONLY_SIDS` and `SKIP_SIDS`
  priorities.
- `instances` is required when `discovery` is not enabled. When discovery is enabled, `instances` can still be specified to add additional databases that are not discoverable locally.

### Options

Fine-tunes plugin runtime behavior.

```yaml
options:
  max_queries: 16 # optional, reserved for future use
  use_host_client: never # optional, default: "auto"
  IGNORE_DB_NAME: 0 # optional, default: 0
  threads: 1 # optional, default: 1, parallel worker threads (range 1–8)
  permissions_check: yes # optional, default: yes
  permissions_safe_entries: [] # optional, default: none
```

- `use_host_client` controls whether the plugin uses the OCI library installed on the host or the one bundled with the plugin. Values: `auto`, `never`, `always`, or a path to the directory containing the OCI library. When that path is the `lib` directory of a full Oracle installation (an `oracore` directory exists next to it), the plugin also derives `ORACLE_HOME` from its parent and exports it, so that OCI finds its message and timezone files (prevents `ORA-01804`). An Oracle Instant Client directory is used as is; it needs no `ORACLE_HOME`.
- `IGNORE_DB_NAME`: when set to `1`, the plugin will not verify that the database name matches the instance name.
- `threads`: number of worker threads used to process instances in parallel. Default is `1`, meaning sequential execution. The supported range is `1` to `8`. Higher values are clamped down to `8`.
- `permissions_check` controls whether the permissions of the OCI runtime are validated before its library is loaded. Loading a library as a privileged user executes whoever may write it with those privileges, so the runtime is refused when it can be modified from outside the Oracle installation. The validation only ever applies to a privileged run: as an unprivileged user the library runs with the privileges the user already has, and the check is skipped. Set to `no` to load the runtime regardless — the last resort when the permissions cannot be corrected.

  On Unix, when running as root, the runtime directory, the entries in it and its parent directories must be writable only by `root` or by the conventional Oracle owner — the user `oracle` and the group `oinstall`. That single exception is what lets a standard installation work unchanged, including the group-writable `$ORACLE_BASE` directories the Oracle installer creates. Anything world-writable, or owned by any other user, is refused — including a runtime owned consistently by some other account, which needs `permissions_safe_entries` or `permissions_check: no`. Subdirectories of the runtime directory are not descended into. On Windows, when running elevated, the DACL of the runtime must grant write access only to privileged SIDs (`SYSTEM`, the local `Administrators` group, `Domain Admins`, `Enterprise Admins`).

- `permissions_safe_entries` lists users and groups that are accepted as writers in addition to the above, for installations that keep their Oracle software under a different account or group. On Unix an entry is a user name, a group name or a numeric ID; on Windows an account name. Example: `permissions_safe_entries: ["ora19", "dba"]`.

### Sections

Defines which monitoring sections to collect. If omitted, all default sections are enabled.

Each section can optionally specify:

- `affinity`: determines which database types the section applies to (`"db"`, `"asm"`, or `"all"`).
- `is_async`: when `yes`, the section runs asynchronously and its results are cached (controlled by `cache_age`).
- `path`: load the SQL body from an external file instead of the bundled query. See [External SQL files (`path:`)](#external-sql-files-path) under custom metrics — the same rules apply to predefined sections.

```yaml
sections:
  - instance:
      affinity: 'db'
  - asm_instance:
      affinity: 'asm'
  - dataguard_stats:
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
  - locks:
      is_async: yes
  - resumable:
      is_async: yes
  - rman:
      is_async: yes
  - tablespaces:
      is_async: yes
```

#### Excluding sections for single targets

`sections` enables or disables a section for **all** monitored instances. To skip
sections for individual instances only, list them under `excluded_sections`, next
to `sections` in `oracle.main`. Each entry names one target and the sections that
target does not query:

```yaml
oracle:
  main:
    excluded_sections:
      - target_id:
          sid: FREE
        sections: [instance, recovery_status]
      - target_id:
          service_name: prod_service
          instance_name: PROD
        sections: [jobs]
```

- A target is identified by `sid`, `service_name` or `alias`, exactly as in an
  `instances:` entry. `instance_name` only refines a `service_name` target, it
  cannot name one on its own.
- A target matches an instance only when both name it with the **same keys**: an
  entry with `service_name: SRV` alone does not match an instance that also sets
  `instance_name`. Copy the identifying keys of the `instances:` entry.
- The whole target is matched case-insensitively - `sid`, `service_name`,
  `instance_name` and `alias` alike. A target without an entry keeps every section.
- A `target_id` that matches no monitored instance is simply never used.
- The names are **section** names, the same ones used under `sections`. A
  `custom_metrics` entry is addressed by its section name `sql`, so excluding
  `sql` skips every custom metric of that target.
- Exclusion is applied last: a section excluded here is dropped even when the
  instance defines it under its own `custom_metrics`.
- Names that match no section are ignored.
- A target listed twice keeps its last list.
- Only the queries are skipped. The signalling headers the plugin emits for cached
  sections are global and stay as they are.

### Custom SQL Metrics

Use `custom_metrics` to define ad-hoc SQL queries whose output is emitted under the legacy `oracle_sql` agent section. Each entry is keyed by the **item name** that becomes the service item on the Checkmk site (the `<item>` in `[[[SID|item]]]`).

```yaml
oracle:
  main:
    connection:
      hostname: localhost
    authentication:
      username: system
      password: oracle
      type: standard
    custom_metrics:
      - product_price: # item name -> service "<SID> SQL product_price"
          sql: "SELECT 'details:Price OK' FROM dual"
    instances:
      - service_name: FREE
        custom_metrics:
          - last_sessions: # runs only against this instance
              sql: "SELECT 'details:per-instance' FROM dual"
```

Resulting agent output:

```
<<<oracle_sql:sep(58)>>>
[[[FREE|product_price]]]
details:Price OK
<<<oracle_sql:sep(58)>>>
[[[FREE|last_sessions]]]
details:per-instance
```

#### Placement and merge rules

- `custom_metrics` may appear at the **global** level (under `oracle.main`) or under any **per-instance** entry (`oracle.main.instances[*]`).
- A given instance executes the union of global and its own per-instance metrics.
- If a global and a per-instance entry share the same item name, the per-instance one wins.

#### External SQL files (`path:`)

Instead of embedding SQL inline via `sql:`, an entry can point at an external `.sql` file via `path:`. This applies both to `custom_metrics` entries and to predefined `sections` (where it overrides the bundled query for that section).

```yaml
custom_metrics:
  # 1. Absolute path to a file.
  - heavy_query:
      path: '/opt/checkmk/sql/heavy_query.sql'

  # 2. Relative file path — searched in MK_LIBDIR/plugins/packages/mk-oracle/orasql/ first,
  #    then in MK_CONFDIR/orasql/.
  - product_price:
      path: 'queries/product_price.sql'

  # 3. Directory path — the file name is derived from the item name
  #    ("sessions_stats.sql" in this case).
  - sessions_stats:
      path: 'queries/'

  # 4. File with inline fallback. If the file cannot be resolved, the
  #    inline `sql:` is used instead.
  - last_resort:
      path: 'queries/last_resort.sql'
      sql: "SELECT 'details:fallback' FROM dual"
```

Resolution rules:

- **Absolute vs. relative.** Absolute paths are used as-is. Relative paths are searched first in **`MK_LIBDIR/plugins/packages/mk-oracle/orasql/`** and then in **`MK_CONFDIR/orasql/`**. When the same relative path resolves in both, the **`MK_LIBDIR/plugins/packages/mk-oracle/orasql/`** copy wins.
- **File vs. directory.** A `path:` may point at a file (with or without the `.sql` extension) or at a directory. In the directory case the file name is derived from the **item name** for `custom_metrics`, or from the **section name** for predefined `sections`.
- **Version variants.** Alongside the base `<stem>.sql`, you may provide Oracle-version-specific variants named `<stem>@<min_version>.sql` (e.g. `sessions@19000000.sql`). The plugin picks the file with the highest `min_version` that is still less than or equal to the connected instance's version. The version is the 8-digit numeric form `MMmmRRSSSS` (major / minor / release / patch), e.g. `12.1.0.2` → `12010002`.
- **Fallback chain.** Resolution order for a section is: `path:` → inline `sql:` → bundled (for predefined sections only). If `path:` is set but no file matches the instance version and no inline `sql:` is provided, the section yields no output.

Example layout on Linux:

```
$MK_CONFDIR/orasql/
├── product_price.sql
├── product_price@19000000.sql       # picked for Oracle >= 19.0.0.0
└── product_price@23000000.sql       # picked for Oracle >= 23.0.0.0

$MK_LIBDIR/plugins/packages/mk-oracle/orasql/
└── product_price.sql                    # overrides the MK_CONFDIR copy
```

#### SQL parameters (`sql_params`)

An entry can declare named parameters that are substituted into the SQL body before execution. Each `${<name>}` placeholder is replaced **textually** by the configured value. This works for inline `sql:` and for files resolved via `path:`.

```yaml
custom_metrics:
  - test:
      sql: 'SELECT ${parameter_1} FROM dual; SELECT ${parameter_2} FROM dual'
      sql_params:
        parameter_1: 'value_1'
        parameter_2: '${ENV_VAR_1}' # resolved from the environment
```

- **Textual substitution, not bind variables.** Values are pasted verbatim into the statement, so they may name columns or tables — but quoting/escaping is the user's responsibility.
- **Environment references.** A value may reference environment variables as `$VAR` or `${VAR}`; they are resolved when the config is read. If a referenced variable is not set, the parameter is skipped with a warning and its `${<name>}` placeholder stays in the SQL (the query then fails visibly instead of running with an empty value).
- **Unused parameters are ignored**; placeholders without a matching parameter are left untouched.

#### SQL contract

Each SQL must produce rows with a single string column whose value starts with one of the recognised prefixes:

| Prefix      | Purpose                                                |
| ----------- | ------------------------------------------------------ |
| `details:`  | First line of the service summary                      |
| `perfdata:` | `NAME=VALUE;WARN;CRIT;MAX` performance metric          |
| `long:`     | Additional lines in the long service output            |
| `exit:`     | Service state: `0=OK`, `1=WARN`, `2=CRIT`, `3=UNKNOWN` |

The plugin emits the section header (`<<<oracle_sql:sep(58)>>>`) and the subsection header (`[[[<SID>|<item>]]]`) itself; the SQL only provides the body rows.

Each row returned by the SQL is emitted **as-is**: the plugin does not reinterpret, reorder, or join columns. In practice this means custom-metric SQL should `SELECT` a single string column whose value is already a complete line (e.g. `'details:OK'`), and emit one such row per output line.

#### Own section header (`header_name`, `header_sep`)

By default a custom metric is emitted under `<<<oracle_sql:sep(58)>>>` and is processed by the built-in `oracle_sql` check plugin. An entry that is meant for a check plugin of your own can name its own agent section instead:

```yaml
custom_metrics:
  - myscn:
      path: 'queries/myscn.sql'
      header_name: my_section # emitted as <<<my_section:sep(124)>>>
      header_sep: 124 # optional, ASCII code of the separator: 124 = '|'
```

- **Both keys belong to a `custom_metrics` entry.** On a `sections:` entry they are ignored with a warning: a built-in section is processed by a check plugin that ships with Checkmk, and renaming its header would only take its data away from that plugin.
- **The name is used verbatim.** Unlike the built-in sections, `header_name` is _not_ prefixed with `oracle_` — write the complete section name your check plugin registers.
- **Only ASCII letters, digits and `_` are allowed in the name.** This is the rule of the Checkmk site: a section whose name contains anything else is discarded on arrival, together with all its data. An entry with such a name therefore keeps the default header and logs an error instead.
- **`header_sep` is the field separator announced in the header** (`:sep(<ASCII code>)`), i.e. how the Checkmk site splits the lines of the section. It does not change the rows themselves: as everywhere in `custom_metrics`, each row is emitted as-is, so the SQL has to produce the separators it declares. Without `header_sep` the header is emitted bare (`<<<my_section>>>`) and the site splits on whitespace.
- **`header_sep` is a number, the ASCII code of the separator** — `124`, not `'|'` — exactly as the legacy `SQLS_SECTION_SEP` had it, and exactly what the header announces. A value that is not an ASCII code (a literal character such as `'|'`, or a number above 127) is ignored with an error, and the header is emitted bare.
- **`header_sep` alone has no effect** and is ignored with a warning: the default `oracle_sql` header is always `sep(58)`.
- **No item subsection.** A section of your own gets no `[[[<SID>|<item>]]]` line — that line is part of the `oracle_sql` format. The YAML key stays the entry's name (used for merging and for a directory `path:`), but it no longer appears in the output, so a query that has to distinguish instances must select the identification itself.
- **Cache marker.** For a cached (async) metric the `cached(<since>,<age>)` marker then rides on the section header (`<<<my_section:cached(...):sep(124)>>>`), since there is no subsection to carry it.

This mirrors the legacy `SQLS_SECTION_NAME` / `SQLS_SECTION_SEP` variables, and the [migration](#custom-sql-sections-sqls_) produces these keys.

#### Differences from the legacy `mk_oracle` bash plugin

Custom SQL metrics in this plugin replace the legacy `SQLS_*` configuration variables and `SQLS_SECTIONS` shell-function-based sections. Key differences:

- **No SQL\*Plus directives.** Statements run through the Oracle OCI driver, not `sqlplus`, so `PROMPT`, `SET …`, `SPOOL`, `WHENEVER SQLERROR`, and similar `SQL*Plus`-only commands are not available. Use plain SQL.
- **Inline SQL or external `.sql` file.** Define the query inline via `sql: "..."` or load it from an external file via `path:` (see [External SQL files](#external-sql-files-path)). The legacy `SQLS_DIR` / `SQLS_SQL` lookup semantics are replaced by the rules under `path:`.
- **Item name is the YAML key.** Equivalent to the legacy `SQLS_ITEM_NAME` (replaces `SQLS_SECTIONS` shell functions).
- **Cache marker location.** For cached (async) sections, the legacy `cached(<since>,<age>)` marker is emitted on the **subsection** header `[[[<SID>|<item>|cached(...)]]]`, not on the section header. The section header is always plain `<<<oracle_sql:sep(58)>>>`. With an [own section header](#own-section-header-header_name-header_sep) there is no subsection, and the marker sits on the section header as it did in the legacy plugin.
- **Separator is fixed at `:` (ASCII 58).** Unless the entry names its [own section header](#own-section-header-header_name-header_sep), the output is emitted under `oracle_sql:sep(58)` so the existing server-side `oracle_sql` check plugin processes it unchanged.

#### Targeting Pluggable Databases (PDBs)

A `custom_metrics` entry can target one or more Pluggable Databases inside a Container Database by adding a `pdbs` list. Each entry is a case-insensitive regular expression matched against the full PDB name. The plugin connects to the CDB root and issues `ALTER SESSION SET CONTAINER = <PDB>` before each query, then resets the session back to `CDB$ROOT` afterwards.

```yaml
custom_metrics:
  - product_price:
      path: 'queries/product_price.sql'
      pdbs: ['TESTPDB1', 'TESTPDB2'] # exact names
  - object_count:
      path: 'queries/object_count.sql'
      pdbs: ['TEST.*'] # regex — matches any PDB starting with TEST
```

Resulting agent output (instance SID is `FREE`):

```
<<<oracle_sql:sep(58)>>>
[[[FREE_TESTPDB1|product_price]]]
details:...
<<<oracle_sql:sep(58)>>>
[[[FREE_TESTPDB2|product_price]]]
details:...
```

- If `pdbs` is **omitted or empty**, the query runs against the CDB root — existing behaviour, unchanged.
- Patterns are anchored (`^pattern$`) and case-insensitive. A bare `PDB1` matches only `PDB1`, not `PDB10`. Use `PDB1.*` or `(PDB1|PDB10)` for broader matching.
- PDB names are discovered at runtime via `V$PDBS`. A pattern that matches no discovered PDB is logged as a warning and skipped; other patterns still execute.
- The same PDB is only queried once even if multiple patterns match it.
- The monitoring user must hold the `SET CONTAINER` privilege: `GRANT SET CONTAINER TO <user> CONTAINER = ALL`.
- The connection must target the **CDB root service** (e.g. `service_name: FREE`), not a PDB service name. Connecting directly to a PDB service bypasses the container-switching mechanism.

### User Configuration File

The plugin merges configuration from **two** files:

| File          | Path                                                       |
| ------------- | ---------------------------------------------------------- |
| Bakery config | `$MK_CONFDIR/mk-oracle.yml`                                |
| User config   | `$MK_LIBDIR/plugins/packages/mk-oracle/mk-oracle.user.yml` |

The user file lets an user extend or override the configuration without
editing the bakery file, and conversely lets the bakery redeploy
its file without clobbering the user's changes.
The path is the same on Linux and Windows.

Custom SQL files referenced by a relative `path:` are likewise searched in both
`$MK_LIBDIR/plugins/packages/mk-oracle/orasql/` (user, searched first) and
`$MK_CONFDIR/orasql/` (bakery), so user SQL wins on a name collision.

The user file is **fully optional** and uses the **same syntax** as the bakery
file — every key is optional. The plugin loads the bakery file first, then
merges the user file on top:

| Element                                                                    | Merge rule                                                                                   |
| -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Scalars (`cache_age`, `connection.hostname`, `authentication.username`, …) | the user value overrides the bakery value when set                                           |
| `connection`, `authentication`, `options`, `discovery`, `system.logging`   | merged field by field; unset fields are inherited from the bakery file                       |
| `instances`, `configs`, `excluded_sections`                                | **not** merged — if present in the user file, the whole list replaces the bakery list        |
| `custom_metrics`, `sections` (global)                                      | merged by item/section name; the user entry wins on a name collision, new names are appended |

- If the user file is missing or empty, the bakery file is used as-is.
- If both files are missing, the plugin behaves as before (no monitoring configured).
- A broken (unparseable) user file is ignored with a warning, so an operator
  typo never breaks bakery-configured monitoring.
- Every bakery value that the user file overrides is written to the plugin log.

#### Examples

Override the connection host and a credential, inheriting everything else:

```yaml
# mk-oracle.user.yml
oracle:
  main:
    connection:
      hostname: db-prod.example.com # overrides bakery hostname; port etc. inherited
    authentication:
      password: 'operator-secret' # overrides only the password
```

Enable an extra section without redefining the others (merged by name):

```yaml
# mk-oracle.user.yml
oracle:
  main:
    sections:
      - rman: # overrides the bakery `rman` entry (or adds it)
          is_async: yes
```

Add a custom metric (merged into the global `custom_metrics` by item name):

```yaml
# mk-oracle.user.yml
oracle:
  main:
    custom_metrics:
      - my_metric:
          sql: "select 'details:hello' from dual"
```

Replace the whole instance list (the user list wins entirely):

```yaml
# mk-oracle.user.yml
oracle:
  main:
    instances:
      - sid: PROD1
      - sid: PROD2
        connection:
          hostname: another-host
```

Raise the log level for debugging without touching the bakery file:

```yaml
# mk-oracle.user.yml
system:
  logging:
    level: 'debug'
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
    excluded_sections:
      - target_id: # same keys as the ORCL instance above, so it matches
          service_name: 'ORCL'
          sid: 'ORCL'
        sections: [tablespaces]
    cache_age: 600
    custom_metrics_cache_age: 600
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

## Migration from the Legacy `mk_oracle` Plugin

`mk-oracle` replaces the shell-based `mk_oracle` agent plugin (Linux/AIX) and the
PowerShell `mk_oracle.ps1` plugin (Windows). The binary contains a built-in migration
command that converts a legacy configuration file into the
[YAML configuration](#yaml-configuration) described above.

### Running the Migration

```
mk-oracle --migrate-config <legacy-config> [--migrate-output <file>]
```

| Option                          | Description                                                                                                    |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `-M`, `--migrate-config <path>` | Path to the legacy configuration file to convert                                                               |
| `--migrate-output <path>`       | Write the result to this file (overwritten if it exists). Without this option the result is printed to stdout. |

Typical invocations:

```bash
# Linux/AIX: convert and review on stdout first
mk-oracle --migrate-config /etc/check_mk/mk_oracle.cfg

# then write the new configuration file
mk-oracle --migrate-config /etc/check_mk/mk_oracle.cfg --migrate-output /etc/check_mk/mk-oracle.yml
```

```powershell
# Windows
mk-oracle.exe --migrate-config C:\ProgramData\checkmk\agent\config\mk_oracle_cfg.ps1 --migrate-output C:\ProgramData\checkmk\agent\config\mk-oracle.yml
```

The command exits with code `0` on success and `1` on failure (the legacy file cannot
be read, `DBUSER` is not defined, or the output file cannot be written).

**The legacy config is executed.** To resolve variable values, the migration sources
the legacy file in its native shell — `bash` on Linux, `ksh` on AIX, PowerShell on
Windows. Run the migration on the host where the legacy plugin is deployed, so that
shell logic in the config (environment variables, conditionals) resolves the same way
it does for the legacy plugin.

### Migration Output

The generated file is a single YAML document consisting of:

1. A header with the source path and the conversion timestamp.
2. The recognized legacy variables with their resolved values, as comments
   (credentials are masked); `REMOTE_INSTANCE_*` entries that could not be parsed
   are marked `# INVALID`.
3. `# WARNING:` comments for everything that needs manual attention, also printed
   to the terminal: custom SQL files that cannot be executed as they are (see
   [Adapting Custom SQL Files](#adapting-custom-sql-files)) and custom SQL sections
   whose target instances could not be determined (see
   [Custom SQL Sections](#custom-sql-sections-sqls_)).
4. The converted configuration below the `# --- Unified Config ---` marker.

The legacy file itself is not copied into the output — keep it until you have
verified the migrated configuration.

### What Is Migrated

| Legacy variable                            | Migrated to                                                                                       |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `DBUSER` (required)                        | Top-level `connection:` (hostname, port) and `authentication:`, plus the first `instances:` entry |
| `DBUSER_<SID>`                             | An `instances:` entry with per-instance `connection:` and `authentication:`                       |
| `ASMUSER`                                  | `asm_username`, `asm_password`, `asm_role`, `asm_type` under `authentication:`                    |
| `REMOTE_INSTANCE_<ID>`                     | An `instances:` entry including `piggyback_host:` (Linux/AIX only)                                |
| `SYNC_SECTIONS` / `ASYNC_SECTIONS`         | `sections:` entries with `is_async: false` / `true`                                               |
| `SYNC_ASM_SECTIONS` / `ASYNC_ASM_SECTIONS` | `sections:` entries with `affinity: "asm"` (`"all"` if the section is also a normal section)      |
| `CACHE_MAXAGE`                             | `cache_age:`                                                                                      |
| `SQLS_MAX_CACHE_AGE`                       | `custom_metrics_cache_age:`                                                                       |
| `MAX_TASKS`                                | `options.threads:` (only for values ≥ 2, capped at 8)                                             |
| `ONLY_SIDS`                                | `discovery.include:` (with `detect: true`)                                                        |
| `SKIP_SIDS`, `EXCLUDE_<SID>="ALL"`         | `discovery.exclude:` (with `detect: true`)                                                        |
| `TNS_ADMIN`                                | `connection.tns_admin:`                                                                           |
| `OLRLOC`                                   | `connection.oracle_local_registry:`                                                               |
| `SQLS_SECTIONS` + per-section `SQLS_*`     | `custom_metrics:` entries (see below)                                                             |

Notes:

- The fields of `DBUSER`-style variables are `USERNAME:PASSWORD:ROLE:HOST:PORT:TNSALIAS`.
  An empty host becomes `localhost`; a `/` username (OS authentication) becomes an
  empty username.
- A `DBUSER` without the TNS-alias field produces an instance entry with the literal
  placeholder `$ORACLE_SID`. Replace it with the actual SID, or remove the entry and
  enable `discovery:` instead.
- `REMOTE_INSTANCE_<ID>` fields are `USER:PASSWORD:ROLE:HOST:PORT:PIGGYBACKHOST:SID:VERSION`;
  the version is ignored (detected at runtime). Entries missing mandatory fields are
  skipped and recorded as `# INVALID` comments.

#### Custom SQL Sections (`SQLS_*`)

Each function listed in `SQLS_SECTIONS` becomes one `custom_metrics:` entry:

| Legacy variable                      | Migrated to                                                    |
| ------------------------------------ | -------------------------------------------------------------- |
| Function name in `SQLS_SECTIONS`     | The item name (YAML key) of the entry                          |
| `SQLS_ITEM_NAME`                     | Overrides the item name                                        |
| `SQLS_DIR` + `SQLS_SQL`              | `path:`                                                        |
| `SQLS_SIDS` (literal list)           | Places the entry under the matching `instances:` entries       |
| `SQLS_SIDS` (shell expression)       | The instances it expands to, or nothing (see below)            |
| `SQLS_TNSALIAS`                      | Places the entry under the instance with that `alias:`         |
| `SQLS_SIDS` + `SQLS_TNSALIAS`        | One entry carrying both, the alias identifies it (see below)   |
| `SQLS_SECTION_NAME` (≠ `oracle_sql`) | `header_name:`                                                 |
| `SQLS_SECTION_SEP` (ASCII code)      | `header_sep:`, the same code (kept only with a `header_name:`) |

A migrated `header_name:` keeps the legacy output shape: the section is emitted under
that name verbatim and without an item subsection, see
[Own section header](#own-section-header-header_name-header_sep).

Placement rules:

- A section restricted to specific SIDs or to a TNS alias is attached to the
  corresponding `instances:` entries; new entries are created for SIDs and aliases
  that have no `DBUSER_*` counterpart.
- A section without any `SQLS_SIDS` or `SQLS_TNSALIAS` becomes a global custom metric
  and runs on every instance.
- A section whose `SQLS_SIDS` names a `REMOTE_INSTANCE_*` variable is attached to the
  instance that variable defines. References that resolve to nothing are dropped with
  a warning, and a section left without any instance is skipped.
- A section setting both `SQLS_SIDS` and `SQLS_TNSALIAS` keeps both values (see below).
- A section without `SQLS_SQL` is skipped with a warning.

##### Dynamic `SQLS_SIDS` values

The legacy plugin allows `SQLS_SIDS` to be built by a shell expression, evaluated
every time the plugin runs and typically derived from the SIDs the plugin has just
discovered:

```bash
SQLS_SIDS="$(echo "$SIDS" | tr ' ' '\n' | awk '$0 !~ /^\+ASM([0-9]*)?$/' | paste -sd,)"
```

**Such a value cannot be represented in the new configuration**, which lists instances
statically. The migration therefore keeps the SIDs the expression expands to while it
sources the legacy config, and warns about every affected section:

```
# WARNING: mycustomsection1: SQLS_SIDS is built by a shell expression, which cannot be migrated reliably; using the SIDs it expanded to: PROD1, PROD2
```

Review those sections: the expansion is a snapshot taken on the migration host, and
variables the legacy plugin only defines at runtime (`$SIDS`, `$ORACLE_SID`, `$AWK`,
`$GREP`, …) are not set while the config is sourced. Expressions that depend on them
expand to nothing, and the section is skipped instead of migrated:

```
# WARNING: mycustomsection1: SQLS_SIDS is built by a shell expression that expanded to no SID, skipping custom SQL section; assign the intended instances manually
```

Such a section is deliberately not migrated as a global custom metric: it would then
run on every instance of the new configuration — including explicitly configured and
remote ones that the legacy expression never selected — creating unexpected services
and failing wherever the queried objects do not exist. Add the section back manually
under the `instances:` entries it is meant to run on (or, if it really applies to all
of them, as a global `custom_metrics:` entry).

##### `SQLS_SIDS` together with `SQLS_TNSALIAS`

Both may be set for the same section, and they restrict different things in the legacy
plugin: `SQLS_SIDS` selects the monitored SID the section runs on, `SQLS_TNSALIAS` the
connect identifier it uses to get there. The migration keeps both on one instance
entry:

```yaml
instances:
  - sid: NORMALDB
    alias: NORMALDB_ALIAS
    custom_metrics:
      - Invalid objects in DB:
          path: /etc/check_mk/ProdSQLs/invalid_objects.sql
```

Note that `mk-oracle` identifies an instance by its `alias:` as soon as one is set, so
the `sid:` above documents the origin of the entry but no longer restricts the section.
The migration says so for every affected section:

```
# WARNING: Invalid objects in DB: SQLS_SIDS 'NORMALDB' is migrated next to SQLS_TNSALIAS 'NORMALDB_ALIAS', but the instance is resolved by its alias, so the SID no longer restricts the section
```

The SID cannot be kept at all when it does not identify one instance of the migrated
configuration — the section lists several SIDs, several sections use the same alias with
different SIDs, or the alias already belongs to a `DBUSER_*` entry with a SID of its own.
The alias then forms the entry alone and the dropped restriction is reported:

```
# WARNING: Ambiguous: SQLS_SIDS 'ONE, TWO' cannot be kept next to SQLS_TNSALIAS 'SHARED_ALIAS', the instance is resolved by its alias alone; verify that the alias connects to the intended database
```

In both cases, check that the alias resolves to the database the section was meant to
query — the connection now depends on your `tnsnames.ora` alone.

##### `SQLS_ITEM_SID`

The legacy plugin builds the item of the `oracle_sql` output as
`[[[<SQLS_ITEM_SID>|<SQLS_ITEM_NAME>]]]`, which lets the displayed SID differ from the
internal name of the monitored instance. It is mainly used for remote instances, whose
internal name is the `REMOTE_INSTANCE_<ID>` variable:

```bash
foo_views_chk1 () {
    SQLS_SIDS="REMOTE_INSTANCE_PRODPDB1"
    SQLS_SQL=foo_view_check1.sql
    SQLS_ITEM_NAME="foo_views_kim1"
    SQLS_ITEM_SID="PRODPDB1"
}
```

**`mk-oracle` has no equivalent field**: the item is always built from the name of the
instance the section runs on (`sid:`, or the discovered SID). `SQLS_ITEM_SID` is
therefore not migrated, and the migration warns about every section where the item
would change:

```
# WARNING: foo_views_chk1: SQLS_ITEM_SID 'PRODPDB1' is not supported and is not migrated; the item of the oracle_sql section is built from the name of the instance the section runs on, so the name of the service changes and it is rediscovered
```

The item is part of the Checkmk service name, so an affected service disappears and is
rediscovered under the new name — together with the rules, downtimes and history bound
to the old one. Compare the old and the new item before rediscovering, and rename the
instance (`sid:`) if you need to keep the previous service name.

No warning is emitted when the value cannot change anything: the section runs on that
one SID anyway, or it uses a custom `SQLS_SECTION_NAME`, for which the legacy plugin
emits no item at all.

##### `SQLS_PARAMETERS`

The legacy plugin prepends `SQLS_PARAMETERS` to the SQL it pipes into `sqlplus`, which is
how a SQL file gets the substitution variables (`&VAR`) it references `DEFINE`d. The
value may be assembled by the section function itself:

```bash
my_section () {
    SQLS_SQL=invalid_objects.sql
    SQLS_PARAMETERS="
        DEFINE VAR_IFILE = \"${VAR_IFILE}\"
    "
}
```

`DEFINE` is a SQL\*Plus command and `mk-oracle` runs the query through the OCI driver
(see [Adapting Custom SQL Files](#adapting-custom-sql-files)), so **the parameters cannot
be migrated**. The section is migrated without them, and the migration reports it:

```
# WARNING: my_section: SQLS_PARAMETERS is not supported and is not migrated; the SQL*Plus commands it prepends to the query are lost, so convert the substitution variables the SQL file uses into 'sql_params:' manually
```

Until such a section is converted its `&VAR` references stay undefined and the query
fails at runtime. Port it to [`sql_params`](#sql-parameters-sql_params), which substitutes
values textually just as the `DEFINE`s did: replace every `&VAR` in the SQL file by
`${VAR}` and declare the value next to the entry.

```yaml
custom_metrics:
  - my_section:
      path: /etc/check_mk/ProdSQLs/invalid_objects.sql
      sql_params:
        VAR_IFILE: '/etc/check_mk/ifile.txt'
```

The value is a literal; only variables that really come from the environment of the
plugin can be carried over as `'${VAR_IFILE}'`. A shell variable the legacy config
computed is not available to `mk-oracle`.

### What Is Not Migrated

The following variables are recognized but only preserved as comments in the output;
port them manually if you still need them:

| Legacy variable                                       | Remark                                                                                                                   |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `SQLS_DBUSER`, `SQLS_DBPASSWORD`, `SQLS_DBSYSCONNECT` | Per-custom-SQL credentials; use per-instance `authentication:` overrides instead                                         |
| `SQLS_PARAMETERS`                                     | SQL\*Plus parameter passing is not supported; port it to `sql_params:` (see [above](#sqls_parameters))                   |
| `SQLS_ITEM_SID`                                       | The item always carries the name of the instance the section runs on (see [above](#sqls_item_sid))                       |
| `EXCLUDE_<SID>="<section> ..."`                       | Per-SID exclusion of individual sections; only `EXCLUDE_<SID>="ALL"` is converted                                        |
| `ORACLE_HOME`, `REMOTE_ORACLE_HOME`                   | The OCI runtime is located as described in [Options](#options) (`use_host_client`)                                       |
| `ID_BY`                                               | Selects `SID=` vs `SERVICE_NAME=` in the legacy connect string; use the `sid:` / `service_name:` instance fields instead |

On Windows the legacy plugin supports neither `REMOTE_INSTANCE_*` nor custom SQL
sections, so both are ignored when migrating a Windows configuration.

Anything else — custom shell logic, unrecognized variables — is not converted; it
remains visible in the commented-out legacy config at the top of the output.

### Adapting Custom SQL Files

The legacy plugin piped custom SQL files through `sqlplus`; `mk-oracle` executes them
through the Oracle OCI driver (see
[Differences from the legacy `mk_oracle` bash plugin](#differences-from-the-legacy-mk_oracle-bash-plugin)).
Two consequences:

1. **SQL\*Plus commands do not work.** `PROMPT`, `SET`, `COLUMN`, `SPOOL`,
   `EXEC`/`EXECUTE`, `VAR`/`VARIABLE` and similar directives are `sqlplus` features,
   not SQL.
2. **PL/SQL blocks are not supported.** `DECLARE`/`BEGIN … END;` blocks cannot be
   executed; only plain SQL statements run.

The migration scans every referenced SQL file and emits a `# WARNING:` (in the
terminal and in the generated YAML). The affected sections are migrated regardless — fix
the SQL files, otherwise the queries fail at runtime.

Useful properties of the new execution model:

- A `.sql` file may contain **multiple statements** separated by `;` at the top
  level; they are executed in order and their rows are concatenated.
- Each returned row must be a single string column matching the
  [SQL contract](#sql-contract) (`details:`, `perfdata:`, `long:`, `exit:`).

#### Removing SQL\*Plus Commands

Formatting and interactive directives have no equivalent and are simply deleted —
the plugin emits every returned row as-is.

Legacy SQL file:

```sql
SET PAGESIZE 0
SET FEEDBACK OFF
COLUMN details FORMAT A80
PROMPT collecting session count ...
SELECT 'details:' || COUNT(*) || ' sessions' FROM v$session;
```

Adapted SQL file:

```sql
SELECT 'details:' || COUNT(*) || ' sessions' FROM v$session
```

#### Converting a PL/SQL Block to Plain SELECTs

Typical rewrite rules: PL/SQL variables become a `WITH` clause, `IF`/`ELSIF` becomes
`CASE`, and each `DBMS_OUTPUT.PUT_LINE` becomes one returned row (via `UNION ALL` or
a separate `;`-terminated statement).

Legacy SQL file:

```sql
SET SERVEROUTPUT ON
DECLARE
    invalid_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
      FROM dba_objects
     WHERE status = 'INVALID';
    IF invalid_count > 10 THEN
        DBMS_OUTPUT.PUT_LINE('exit:2');
    ELSE
        DBMS_OUTPUT.PUT_LINE('exit:0');
    END IF;
    DBMS_OUTPUT.PUT_LINE('details:' || invalid_count || ' invalid objects');
END;
/
```

Adapted SQL file:

```sql
WITH invalid AS (
    SELECT COUNT(*) AS cnt
      FROM dba_objects
     WHERE status = 'INVALID'
)
SELECT 'exit:' || CASE WHEN cnt > 10 THEN '2' ELSE '0' END FROM invalid
UNION ALL
SELECT 'details:' || cnt || ' invalid objects' FROM invalid
```

#### Wrapping Complex PL/SQL in a Stored Function

When the logic genuinely needs PL/SQL (loops, exception handling, temporary state),
move it into the database as a pipelined function and `SELECT` from it. One-time
setup, run by a DBA in the monitored database:

```sql
CREATE OR REPLACE FUNCTION checkmk_invalid_objects
    RETURN sys.odcivarchar2list PIPELINED
AS
    invalid_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
      FROM dba_objects
     WHERE status = 'INVALID';
    -- arbitrary PL/SQL logic is allowed here
    PIPE ROW ('details:' || invalid_count || ' invalid objects');
    PIPE ROW ('perfdata:invalid_objects=' || invalid_count || ';10;100');
    PIPE ROW (CASE WHEN invalid_count > 10 THEN 'exit:2' ELSE 'exit:0' END);
    RETURN;
END;
/

GRANT EXECUTE ON checkmk_invalid_objects TO checkmk;
```

The custom SQL file then reduces to:

```sql
SELECT column_value FROM TABLE(checkmk_invalid_objects)
```

If the function lives in another schema, qualify it:
`TABLE(owner.checkmk_invalid_objects)`.
