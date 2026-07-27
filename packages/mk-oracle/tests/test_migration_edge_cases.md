# mk-oracle: Configuration Migration — Edge Cases

Following is the list of edge cases discovered while performing 2.5.0p9 patch-release testing.

Corresponding to the list, a [gerrit change](https://review.lan.tribe29.com/c/check_mk/+/145845) with AI generated unit-test cases and _assumed_ expected behaviour was created.
The gerrit change highlighted some potentially relevant edge-cases as comments.

Upon discussions, none of the edge-cases were considered as release-blockers.

## Edge cases

#### Credentials with " or \ produce invalid YAML

Passwords and usernames are written into double-quoted YAML scalars without escaping special characters.

```
DBUSER='user:pa"ss::::'   # → password: "pa"ss"   — unclosed scalar, YAML parse error
DBUSER='user:pa\ss::::'   # → password: "pa\ss"   — \s is not a YAML escape, parse error
```

---

#### Unquoted values truncated by YAML comment syntax

hostname, tns_admin, and oracle_local_registry are emitted without quotes. A # preceded by a space starts a YAML comment, silently discarding the rest of the value.

```
TNS_ADMIN='/opt/oracle/tns #v2'
# → tns_admin: /opt/oracle/tns    ← " #v2" treated as comment; path truncated
```

---

#### EXCLUDE\_\*=<section> (non-ALL) silently dropped

Only EXCLUDE\_\*=ALL (full instance exclusion) is migrated. Per-section exclusions are lost without any warning.

```
EXCLUDE_CCC=ALL    # ✓ migrated → discovery.exclude: [CCC]
EXCLUDE_CCC=jobs   # ✗ silently dropped — jobs still runs on CCC after migration
```

---

#### ONLY*SIDS and EXCLUDE*\*=ALL conflict

If the same SID appears in both, the output contains it in both include: and exclude: simultaneously.

```
ONLY_SIDS='AAA BBB'
EXCLUDE_AAA=ALL
# → include: [AAA, BBB]
#   exclude: [AAA]        ← AAA in both; conflict unresolved
```

---

#### Tab-separated section lists not split

SYNC_SECTIONS (and ASYNC_SECTIONS, etc.) are split on a single space character ' '. Tab-separated values are treated as one section name.

```
SYNC_SECTIONS='instance	performance'   # tab between names
# → one section named "instance\tperformance" instead of two
SQLS_SECTIONS has the same problem (splits on ',' and ' ' only).
```

---

#### $ORACLE_SID written as a literal string

When DBUSER has no explicit SID or alias (6th field empty), the migrated YAML contains the literal string $ORACLE_SID. The new plugin does not expand shell variables.

```
DBUSER='user:pass::::'
# → instances:
#     - sid: $ORACLE_SID     ← literal string, not resolved at runtime
#       alias: $ORACLE_SID
```

---

#### Duplicate SID from overlapping DBUSER*\* and REMOTE_INSTANCE*\*

If both define the same SID, two separate instance entries are emitted.

```
DBUSER_ORCL='admin:pass::host1:1521:'
REMOTE_INSTANCE_ORCL='user2:pass2:sysdba:host2:1521::ORCL:11.2'
# → instances:
#     - sid: ORCL   (from DBUSER_ORCL)
#     - sid: ORCL   (from REMOTE_INSTANCE_ORCL)  ← duplicate
```

---

#### ORACLE_HOME, REMOTE_ORACLE_HOME, ID_BY silently dropped

These are extracted and echoed as comments but have no corresponding YAML key. Users relying on a custom ORACLE_HOME get no indication it was ignored.

```
ORACLE_HOME=/opt/oracle/21c    # extracted, commented out, but no YAML field emitted
```

---

#### Per-custom-SQL connection overrides silently dropped

SQLS_DBUSER, SQLS_DBPASSWORD, and SQLS_TNSALIAS set inside a section function are captured but not written to the custom_metrics: output. Custom SQL sections that connected with a different database user will silently run with the main credentials after migration.

```
mycustomsection1 () {
    SQLS_SQL="report.sql"
    SQLS_DBUSER="reporter"       # ✗ dropped — not in custom_metrics output
    SQLS_DBPASSWORD="rpass"      # ✗ dropped
}
```

---

#### Non-numeric cache/task values silently dropped

CACHE_MAXAGE, SQLS_MAX_CACHE_AGE, and MAX_TASKS are parsed as integers; non-numeric values produce no output.

```
CACHE_MAXAGE=600s    # parse fails → cache_age: omitted entirely, no warning
MAX_TASKS=auto       # parse fails → options: omitted entirely, no warning
```

---

#### MAX_TASKS=1 produces no options: block

The migration only emits options.threads for values ≥ 2 (and caps at 8). A legacy setting of MAX_TASKS=1 produces no options: section at all, meaning the new plugin's default thread count applies instead of the explicitly configured 1.

```
MAX_TASKS=1    # → options: block omitted (treated same as absent)
MAX_TASKS=9    # → options:\n  threads: 8   (clamped to 8)
```

---

#### Windows PS1 6-element DBUSER array — trailing colon in alias

The PowerShell extraction script joins array elements with : and appends a trailing :. For a 6-element array (including TNSALIAS), splitn(6, ':') captures the last field as "ALIAS:" — the trailing colon becomes part of the alias value.

```
$DBUSER = @("user", "pass", "", "host", "1521", "MYALIAS")
# joined: "user:pass::host:1521:MYALIAS:"
# → alias: MYALIAS:    ← trailing colon included
```
