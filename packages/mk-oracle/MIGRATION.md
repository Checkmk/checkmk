# Oracle SQL Migration

## Table of Contents

- [Migrating the Legacy mk_oracle Plugin Configuration](#migrating-the-legacy-mk_oracle-plugin-configuration)
  - [Running the Migration](#running-the-migration)
  - [Migration Output](#migration-output)
  - [What Is Migrated](#what-is-migrated)
  - [What Is Not Migrated](#what-is-not-migrated)
  - [Adapting Custom SQL Files](#adapting-custom-sql-files)
- [Running the Oracle Bakery Migration Tool](#running-the-oracle-bakery-migration-tool)
  - [Arguments](#arguments)
  - [Emitted Warnings](#emitted-warnings)
  - [Suggested Workflow](#suggested-workflow)

## Migrating the Legacy `mk_oracle` Plugin Configuration

`mk-oracle` replaces the shell-based `mk_oracle` agent plugin (Linux/AIX) and the
PowerShell `mk_oracle.ps1` plugin (Windows). The binary contains a built-in migration
command that converts a legacy configuration file into the
[YAML configuration](README.md#yaml-configuration) described above.

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
[Own section header](README.md#own-section-header-header_name-header_sep).

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
fails at runtime. Port it to [`sql_params`](README.md#sql-parameters-sql_params), which substitutes
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

| Legacy variable                                       | Remark                                                                                                                        |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `SQLS_DBUSER`, `SQLS_DBPASSWORD`, `SQLS_DBSYSCONNECT` | Per-custom-SQL credentials; use per-instance `authentication:` overrides instead                                              |
| `SQLS_PARAMETERS`                                     | SQL\*Plus parameter passing is not supported; port it to `sql_params:` (see [README.md](README.md#sql-parameters-sql_params)) |
| `SQLS_ITEM_SID`                                       | The item always carries the name of the instance the section runs on)                                                         |
| `EXCLUDE_<SID>="<section> ..."`                       | Per-SID exclusion of individual sections; only `EXCLUDE_<SID>="ALL"` is converted                                             |
| `ORACLE_HOME`, `REMOTE_ORACLE_HOME`                   | The OCI runtime is located as described in [Options](README.md#options) (`use_host_client`)                                   |
| `ID_BY`                                               | Selects `SID=` vs `SERVICE_NAME=` in the legacy connect string; use the `sid:` / `service_name:` instance fields instead      |

On Windows the legacy plugin supports neither `REMOTE_INSTANCE_*` nor custom SQL
sections, so both are ignored when migrating a Windows configuration.

Anything else — custom shell logic, unrecognized variables — is not converted; it
remains visible in the commented-out legacy config at the top of the output.

### Adapting Custom SQL Files

The legacy plugin piped custom SQL files through `sqlplus`; `mk-oracle` executes them
through the Oracle OCI driver (see
[Differences from the legacy `mk_oracle` bash plugin](README.md#differences-from-the-legacy-mk_oracle-bash-plugin)).
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
  [SQL contract](README.md#sql-contract) (`details:`, `perfdata:`, `long:`, `exit:`).

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

## Running the Oracle Bakery Migration Tool

This is strictly for Checkmk Bakery users.

When running on a site, you will have the following command available to use:

`cmk-migrate-oracle-rulesets`

This tool is used to convert Oracle bakery rules from the original plugin to the new unified plugin.

Note that it can only be run on a central site. It cannot run on a remote site, because the central site would be the
main authority for the remote site configuration.

No rules are deleted - everything is kept as is, though the state depends on the flags used.

### Arguments

- -h or --help: Display the list of arguments and a brief description of what they do.
- --dry-run: Simulates a migration and prints warnings of any issues.
- --apply: Performs a real migration and creates the unified rules. Each rule is created as disabled by default.
- --enable-migrated-rules:
  - Only works with --apply.
  - It creates the new rules as enabled instead of disabled, but only if the original rule was also enabled.
  - It disables the original rule so that there is no failure during baking (both plugins cannot be enabled at the
    same time).

### Emitted Warnings

The warnings displayed are based on known differences with the original plugin and the new one.

Most of them relate to fields which cannot be mapped, these include:

- **sqlnet.ora permission group**
- **Host uses xinetd or systemd**
- **Sqlnet Send timeout**
- **Add pre or postfix to TNSALIASes**
- **ORACLE_HOME to use for remote access**

Other fields have sub-fields which cannot be migrated, which include:

- ts_quotas (under **Sections - data to collect**)
  - This field is unused in the legacy plugin in any case.
- TNS Alias (under **Login Defaults**)
- **Login for ASM** is not supported with any of the following fields:
  - host
  - port
  - wallet

### Usage

`cmk-migrate-oracle-rulesets` by itself prints the command line options.

`cmk-migrate-oracle-rulesets --dry-run` will run the migration and show the warnings for each rule.

Here is the example output of a dry-run with a single empty rule:

    Rule '0c1d64a4-fc7b-46eb-b858-5d1110cf1752' (folder: /)
    - 'Sections' was not configured, so the selection the legacy bakery applied by default has been written out explicitly. The new rule pins that selection instead of deferring to the plugin later.
    - No auth defined in legacy rule. Defaulting to Oracle wallet.

    1 rule(s) processed, 2 total warning(s).

    Dry run only — no rules were written. Re-run with --apply to create them.

`cmk-migrate-oracle-rulesets --apply` will have the same output, sans the "Dry run only" line.

All rules are migrated as disabled by default.

If you have minimal warnings and would prefer to create all the new rules as enabled, use:

`cmk-migrate-oracle-rulesets --apply --enable-migrated-rules`

Any rules that were already migrated will not be migrated again.

Only newly created rules will be migrated if the tool is executed again after a prior run.

Every created rule will have **(Migrated)** in the description to help identify it.

### Suggested Workflow

#### Path 1

The expected workflow for migration is as follows:

`cmk-migrate-oracle-rulesets --dry-run` to see possible problems.

`cmk-migrate-oracle-rulesets --apply` to migrate all rules to the new plugin.

In the GUI1, you then edit the generated rules, enabling them as needed.

The legacy rule corresponding to each new rule has to be disabled to prevent baking errors.

Once you bake and deploy the agent, you can check the services of the relevant hosts to make sure everything works as
expected.

Repeat the process for each rule until everything is all clear.

#### Path 2

Say you run `cmk-migrate-oracle-rulesets --dry-run` and there are minimal to no issues.

If you are confident in your setup, you directly run:

`cmk-migrate-oracle-rulesets --apply --enable-migrated-rules`

This makes sure the old rules are disabled and the new rules are enabled, allowing you to bake new agents as needed.

The same verification for services on existing hosts can be done, by baking the new agents and deploying them.
