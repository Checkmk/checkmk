# Validating the Windows binary against a local Oracle host

The network model (the default `winagt-test-mk-oracle` stage: build node → `oracle-win-ci.lan.checkmk.net` over TCP, see the [README](../README.md)) never touches the host-local paths a co-located agent uses: local `sysdba`/bequeath connections and registry-based instance discovery (`HKLM\SOFTWARE\ORACLE`).
To cover those, run the Windows test binary **on** a Windows Oracle host and point it at the host's own DB — by host name, not `localhost` (see below).

## Automated: `run.ps1 --remote-host`

`run.ps1 --remote-host` (also `-R`) builds the test binary on the current Windows node, ships it plus `tests/files/` to the Oracle host over SSH, and runs it there against the host's own DB, using the installed client via `ORACLE_HOME`.
`CI_ORA2` (external reference) connects as `system`; `CI_ORA1` (local endpoint, which activates the local-connection and registry-discovery tests) connects as `sys` with the `sysdba` role that those tests require.

Endpoints use the DB **host name**, not `localhost`: the listeners bind the host address rather than loopback, so a `localhost` connection is refused (ORA-12541).

The Jenkins job `winagt-test-mk-oracle.groovy` runs this as a second stage after the network tests. It requires the VM and credentials below; provision them before enabling the job so the stage can authenticate.

It is driven entirely by environment variables (all optional; defaults describe the ORACLE-WIN-CI VM):

| Variable                   | Default                         | Meaning                                                         |
| -------------------------- | ------------------------------- | --------------------------------------------------------------- |
| `CI_ORA_WIN_TEST_PASSWORD` | —                               | DB password for `system`/`sys` (required).                      |
| `CI_ORA_WIN_REMOTE_HOST`   | `oracle-win-ci.lan.checkmk.net` | Host to SSH into and run the binary on.                         |
| `CI_ORA_WIN_DB_HOST`       | `oracle-win-ci`                 | DB host used in the connection strings (as resolved on the VM). |
| `CI_ORA_WIN_REMOTE_USER`   | `administrator`                 | SSH user on that host.                                          |
| `CI_ORA_WIN_REMOTE_DIR`    | `C:\ci\mk-oracle-test`          | Working directory created (and removed) on the host.            |
| `CI_ORA_WIN_ORACLE_HOME`   | `C:\oracle\26ai\dbhomeFree`     | Installed Oracle client used on the host.                       |
| `CI_ORA_WIN_SSH_KEYFILE`   | —                               | Private key for non-interactive SSH; required in CI.            |

CI prerequisites on the Oracle host: `sshd` running with port 22 open, and (because Windows OpenSSH ignores per-user `authorized_keys` for administrators) the job's public key installed in `C:\ProgramData\ssh\administrators_authorized_keys` with its ACL restricted to `Administrators` and `SYSTEM`. The matching private key is the Jenkins credential `jenkins-oracle-win-ssh-key`. `sys` must be reachable with the `sysdba` role (`sqlplus sys/<pw>@<db-host>:1521/FREE as sysdba`).

## Manual (ad-hoc)

The steps below do the same thing by hand — useful when debugging outside CI.

### 1. SSH to the host without leaving a key behind

Password auth plus connection multiplexing authenticates once, interactively, then reuses the socket — no `authorized_keys` entry on the host and no password in later commands.

`~/.ssh/config`:

```
Host oracle-win-ci
    HostName 10.200.0.141
    User administrator
    PubkeyAuthentication no
    PreferredAuthentications password,keyboard-interactive
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h-%p
    ControlPersist 30m
```

```bash
# open the master once (prompts for the password, entered locally, never stored):
ssh oracle-win-ci -O check 2>/dev/null || ssh -fN oracle-win-ci
# reuse it with no password (you or tooling):
ssh oracle-win-ci 'powershell -c "reg query HKLM\SOFTWARE\ORACLE /s"'
# tear down when done:
ssh oracle-win-ci -O exit
```

The host needs `sshd` running and port 22 open.
If you prefer key auth instead, note that Windows OpenSSH ignores per-user `authorized_keys` for administrators — install the public key into `C:\ProgramData\ssh\administrators_authorized_keys` and restrict its ACL to `Administrators` and `SYSTEM`.

### 2. Build the test binary

On a Windows host with the toolchain (e.g. the existing `winagt` node):

```powershell
cargo test --release --target x86_64-pc-windows-msvc --no-run
# → target\x86_64-pc-windows-msvc\release\deps\test_ora_sql-<hash>.exe
```

### 3. Stage on the Oracle host

Copy the executable and the `tests/files/` tree (the binary resolves fixtures relative to the working directory) into one directory on the host, preserving the `tests\files\...` layout.

### 4. Run against the local instances

Point both endpoints at the DB **host name** (the listeners refuse `localhost`, see above) and use the installed Oracle client via `ORACLE_HOME`. `CI_ORA1_DB_TEST` must connect as `sys` with the `sysdba` role, mirroring the automated flow:

```powershell
$pw = "<db-password>"
$env:CI_ORA2_DB_TEST = "oracle-win-ci:system:${pw}:1521:_::FREE:FREE:_:"
$env:CI_ORA1_DB_TEST = "oracle-win-ci:sys:${pw}:1521:_:sysdba:FREE:FREE:_:"
$env:ORACLE_HOME     = "C:\oracle\26ai\dbhomeFree"
$env:PATH            = "$env:ORACLE_HOME\bin;$env:PATH"
.\test_ora_sql-<hash>.exe --test-threads=4
```

Connection strings for a host with both a 23ai Free and a 19c instance installed:

| Instance             | Port | service_name | sid      | Connection string                                    |
| -------------------- | ---- | ------------ | -------- | ---------------------------------------------------- |
| 23ai Free (CDB root) | 1521 | `FREE`       | `FREE`   | `oracle-win-ci:system:<pw>:1521:_::FREE:FREE:_:`     |
| 23ai Free (PDB)      | 1521 | `FREEPDB1`   | —        | `oracle-win-ci:system:<pw>:1521:_::FREEPDB1:_:_:`    |
| 19c (CDB root)       | 1522 | `orcl19`     | `ORCL19` | `oracle-win-ci:system:<pw>:1522:_::orcl19:ORCL19:_:` |
| 19c (PDB)            | 1522 | `orcl19pdb`  | —        | `oracle-win-ci:system:<pw>:1522:_::orcl19pdb:_:_:`   |

## Troubleshooting

- `ORA-12170` (TNS connect timeout) — the port is filtered; check the host firewall and that the listener binds a reachable address, not `127.0.0.1`.
- `ORA-01017` (invalid username/password) — reachable, wrong credentials.
- `ORA-12514` (service not known) — wrong `service_name`; confirm with `lsnrctl status` on the host.
- SSH hangs — port 22 blocked; SSH prompts for a password on reuse — the ControlMaster socket is not open, or (key auth) the `administrators_authorized_keys` ACL is wrong.
- `No local endpoint found` in test output — `CI_ORA1_DB_TEST` is unset; local-connection tests are skipped.
