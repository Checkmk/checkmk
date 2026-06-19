// Copyright (C) 2026 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

use anyhow::{bail, Result};
use std::collections::{HashMap, HashSet};
use std::path::Path;

/// Full migration pipeline: read legacy config, execute it, convert to new format.
///
/// Returns the formatted output string. Caller decides whether to write to file or stdout.
pub fn migrate(input: &Path) -> Result<String> {
    let legacy = std::fs::read_to_string(input)?;
    let variables = convert_config(input).unwrap_or_default();
    let timestamp = format_timestamp();
    convert(
        &legacy,
        &input.display().to_string(),
        &variables,
        &timestamp,
    )
}

/// Convert legacy Oracle plugin configuration to mk-oracle.yml content.
///
/// Output structure:
/// - Header with timestamp and source path
/// - Original config content as comments
/// - Extracted environment variables as comments
/// - Resulting YAML configuration
// DBUSER fields: USERNAME:PASSWORD:ROLE:HOST:PORT:TNSALIAS
#[derive(Debug)]
struct LegacyDbUser {
    sid: Option<String>, // None for DBUSER, Some(XE) for DBUSER_XE
    username: String,
    password: String,
    role: Option<String>,
    hostname: String,
    port: Option<String>,
    alias_or_sid: String,
}

fn optional_value(s: &str) -> Option<String> {
    (!s.is_empty()).then(|| s.to_string())
}

fn parse_sections(variables: &HashMap<String, String>, key: &str) -> HashSet<String> {
    variables
        .get(key)
        .map(|v| {
            v.split(' ')
                .filter(|s| !s.is_empty())
                .map(String::from)
                .collect()
        })
        .unwrap_or_default()
}

// TODO(sk): parse whole config and return Vec<LegacyDbUser> instead of just DBUSER
fn parse_dbuser(name: &str, value: &str) -> Result<LegacyDbUser> {
    if name != "DBUSER" && !name.starts_with("DBUSER_") {
        bail!("invalid variable name: {name}, expected DBUSER or DBUSER_*");
    }
    let fields: Vec<&str> = value.splitn(6, ':').collect();
    if fields.len() < 2 {
        bail!("DBUSER must have at least username:password, got: {value}");
    }
    let field = |i: usize| fields.get(i).copied().unwrap_or("");
    let sid = name
        .strip_prefix("DBUSER_")
        .map(|suffix| suffix.to_string());
    let raw_username = field(0);
    // Legacy "/" means OS authentication; replace with empty for YAML output
    let username = if raw_username == "/" {
        log::info!("{name}: replacing '/' username with empty string (OS authentication)");
        String::new()
    } else {
        raw_username.to_string()
    };
    Ok(LegacyDbUser {
        sid,
        username,
        password: field(1).to_string(),
        role: optional_value(field(2)),
        hostname: field(3).to_string(),
        port: optional_value(field(4)),
        alias_or_sid: optional_value(field(5)).unwrap_or_else(|| "$ORACLE_SID".to_string()),
    })
}

pub fn convert(
    legacy: &str,
    source_path: &str,
    variables: &HashMap<String, String>,
    timestamp: &str,
) -> Result<String> {
    let dbuser_raw = variables
        .get("DBUSER")
        .ok_or_else(|| anyhow::anyhow!("DBUSER not defined in legacy config, cannot generate"))?;
    let dbuser = parse_dbuser("DBUSER", dbuser_raw)?;

    let mut dbuser_extras: Vec<LegacyDbUser> = Vec::new();
    for (name, value) in variables {
        if let Some(_suffix) = name.strip_prefix("DBUSER_") {
            dbuser_extras.push(parse_dbuser(name, value)?);
        }
    }

    let mut out = String::new();

    out.push_str(&format!(
        "# --- Converted from {source_path} at {timestamp} ---\n"
    ));
    for line in legacy.lines() {
        out.push_str("# ");
        out.push_str(line);
        out.push('\n');
    }

    out.push_str("# --- Known environment variables defined in legacy config ---\n");
    for (name, value) in variables {
        out.push_str(&format!("# {name} {value}\n"));
    }

    let sync_normal = parse_sections(variables, "SYNC_SECTIONS");
    let async_normal = parse_sections(variables, "ASYNC_SECTIONS");
    let sync_asm = parse_sections(variables, "SYNC_ASM_SECTIONS");
    let async_asm = parse_sections(variables, "ASYNC_ASM_SECTIONS");

    let all_normal: HashSet<&str> = sync_normal
        .iter()
        .chain(async_normal.iter())
        .map(|s| s.as_str())
        .collect();
    let all_asm: HashSet<&str> = sync_asm
        .iter()
        .chain(async_asm.iter())
        .map(|s| s.as_str())
        .collect();
    let all_async: HashSet<&str> = async_normal
        .iter()
        .chain(async_asm.iter())
        .map(|s| s.as_str())
        .collect();
    let all_sections: HashSet<&str> = all_normal.union(&all_asm).copied().collect();

    out.push_str("# --- Unified Config ---\n---\noracle:\n  main:\n");

    // connection
    let host = if dbuser.hostname.is_empty() {
        "localhost"
    } else {
        &dbuser.hostname
    };
    out.push_str(&format!("    connection:\n      hostname: {host}\n"));
    if let Some(port) = &dbuser.port {
        out.push_str(&format!("      port: {port}\n"));
    }
    if let Some(tns_admin) = variables.get("TNS_ADMIN") {
        out.push_str(&format!("      tns_admin: {tns_admin}\n"));
    }

    // authentication
    out.push_str(&format!(
        "    authentication:\n      username: \"{}\"\n      password: \"{}\"\n      type: standard\n",
        dbuser.username, dbuser.password
    ));
    if let Some(role) = &dbuser.role {
        out.push_str(&format!("      role: {}\n", role.to_lowercase()));
    }

    // instances from DBUSER and DBUSER_*
    out.push_str("    instances:\n");
    let all_dbusers = std::iter::once(&dbuser).chain(dbuser_extras.iter());
    for entry in all_dbusers {
        let sid = entry.sid.as_deref().unwrap_or(&entry.alias_or_sid);
        out.push_str(&format!("      - sid: {sid}\n"));
        if entry.sid.is_some() && entry.alias_or_sid == "$ORACLE_SID" {
            // sid known from variable name suffix, no explicit alias needed
        } else {
            out.push_str(&format!("        alias: {}\n", entry.alias_or_sid));
        }
        // DBUSER (sid=None) uses main-level connection/auth, skip in instance
        if entry.sid.is_some() {
            let has_connection = !entry.hostname.is_empty() || entry.port.is_some();
            if has_connection {
                out.push_str("        connection:\n");
                if !entry.hostname.is_empty() {
                    out.push_str(&format!("          hostname: {}\n", entry.hostname));
                }
                if let Some(port) = &entry.port {
                    out.push_str(&format!("          port: {port}\n"));
                }
            }
            let has_auth = !entry.username.is_empty() || !entry.password.is_empty();
            if has_auth {
                out.push_str(&format!(
                    "        authentication:\n          username: \"{}\"\n          password: \"{}\"\n          type: standard\n",
                    entry.username, entry.password
                ));
                if let Some(role) = &entry.role {
                    out.push_str(&format!("          role: {}\n", role.to_lowercase()));
                }
            }
        }
    }

    // sections
    if !all_sections.is_empty() {
        let mut sorted: Vec<&str> = all_sections.into_iter().collect();
        sorted.sort();
        out.push_str("    sections:\n");
        for name in sorted {
            out.push_str(&format!("      - {name}:\n"));
            if all_async.contains(name) {
                out.push_str("          is_async: yes\n");
            }
            if all_normal.contains(name) && all_asm.contains(name) {
                out.push_str("          affinity: \"all\"\n");
            } else if all_asm.contains(name) {
                out.push_str("          affinity: \"asm\"\n");
            }
        }
    }

    Ok(out)
}

fn format_timestamp() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let (year, month, day) = civil_from_days((secs / 86400) as i64);
    let t = (secs % 86400) as u32;
    format!(
        "{year:04}-{month:02}-{day:02} {:02}:{:02}:{:02} UTC",
        t / 3600,
        (t % 3600) / 60,
        t % 60
    )
}

/// Convert days since Unix epoch to (year, month, day).
fn civil_from_days(days: i64) -> (i64, u32, u32) {
    let z = days + 719468;
    let era = (if z >= 0 { z } else { z - 146096 }) / 146097;
    let doe = (z - era * 146097) as u32;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

/// Variables to extract from legacy config files.
const KNOWN_VARIABLES: &[&str] = &[
    "DBUSER",
    "ASMUSER",
    "SYNC_SECTIONS",
    "ASYNC_SECTIONS",
    "SYNC_ASM_SECTIONS",
    "ASYNC_ASM_SECTIONS",
    "CACHE_MAXAGE",
    "REMOTE_ORACLE_HOME",
    "ONLY_SIDS",
    "SKIP_SIDS",
    "ORACLE_HOME",
    "TNS_ADMIN",
    "OLRLOC",
    "MAX_TASKS",
    "ID_BY",
    "SQLS_SECTIONS",
    "SQLS_DBUSER",
    "SQLS_DBPASSWORD",
    "SQLS_DBSYSCONNECT",
    "SQLS_TNSALIAS",
    "SQLS_SIDS",
    "SQLS_DIR",
    "SQLS_SQL",
    "SQLS_PARAMETERS",
    "SQLS_SECTION_NAME",
    "SQLS_MAX_CACHE_AGE",
];

/// Variable name prefixes for dynamic matching (e.g. REMOTE_INSTANCE_XE).
const KNOWN_PREFIXES: &[&str] = &["DBUSER_", "REMOTE_INSTANCE_", "EXCLUDE_"];

/// Execute a legacy config file in its native shell and return extracted variables.
///
/// Sources the config in the platform's shell (bash on Linux, ksh on AIX,
/// powershell on Windows) and captures known variable values.
///
/// Returns pairs of (name, value) for variables with non-empty values.
pub fn convert_config(config_path: &Path) -> Result<HashMap<String, String>> {
    let output = run_config_shell(config_path)?;
    parse_variable_output(&output)
}

#[cfg(target_os = "windows")]
fn run_config_shell(config_path: &Path) -> Result<String> {
    run_shell(
        "powershell",
        &["-NoProfile", "-NonInteractive", "-Command"],
        &build_powershell_script(config_path),
    )
}

#[cfg(target_os = "aix")]
fn run_config_shell(config_path: &Path) -> Result<String> {
    run_shell("ksh", &["-c"], &build_posix_script(config_path))
}

#[cfg(not(any(target_os = "windows", target_os = "aix")))]
fn run_config_shell(config_path: &Path) -> Result<String> {
    run_shell("bash", &["-c"], &build_posix_script(config_path))
}

fn run_shell(shell: &str, args: &[&str], script: &str) -> Result<String> {
    let output = std::process::Command::new(shell)
        .args(args)
        .arg(script)
        .output()?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("Config execution failed (exit {}): {stderr}", output.status);
    }
    Ok(String::from_utf8(output.stdout)?)
}

#[cfg(unix)]
fn build_posix_script(config_path: &Path) -> String {
    let quoted_path = posix_quote(&config_path.display().to_string());
    let vars = KNOWN_VARIABLES.join(" ");
    let prefixes = KNOWN_PREFIXES
        .iter()
        .map(|p| format!("{p}*"))
        .collect::<Vec<_>>()
        .join("|");
    format!(
        r#". {quoted_path}
for __n in {vars}; do
  eval "__v=\$$__n"
  [ -n "$__v" ] && printf '%s %s\n' "$__n" "$__v"
done
set 2>/dev/null | while IFS='=' read -r __n __rest; do
  case "$__n" in {prefixes}) eval "__v=\$$__n"; [ -n "$__v" ] && printf '%s %s\n' "$__n" "$__v";; esac
done"#
    )
}

#[cfg(windows)]
fn build_powershell_script(config_path: &Path) -> String {
    let quoted_path = powershell_quote(&config_path.display().to_string());
    let var_list = KNOWN_VARIABLES
        .iter()
        .map(|v| format!("'{v}'"))
        .collect::<Vec<_>>()
        .join(",");
    let prefix_filter = KNOWN_PREFIXES
        .iter()
        .map(|p| format!("$_.Name -like '{p}*'"))
        .collect::<Vec<_>>()
        .join(" -or ");
    format!(
        r#". {quoted_path}
foreach ($__n in @({var_list})) {{
  $__v = (Get-Variable -Name $__n -ValueOnly -ErrorAction SilentlyContinue)
  if ($__v -is [array]) {{
    if ($__n -like 'DBUSER*' -or $__n -like 'ASMUSER*') {{ $__v = ($__v -join ':') + ':' }}
    else {{ $__v = $__v -join ' ' }}
  }}
  if ($__v) {{ Write-Output "$__n $__v" }}
}}
Get-Variable | Where-Object {{ {prefix_filter} }} | ForEach-Object {{
  $__v = $_.Value
  if ($__v -is [array]) {{ $__v = ($__v -join ':') + ':' }}
  if ($__v) {{ Write-Output "$($_.Name) $__v" }}
}}"#
    )
}

#[cfg(unix)]
fn posix_quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "'\\''"))
}

#[cfg(windows)]
fn powershell_quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "''"))
}

fn parse_variable_output(output: &str) -> Result<HashMap<String, String>> {
    Ok(output
        .lines()
        .filter_map(|line| {
            let (name, value) = line.split_once(' ')?;
            if name.is_empty() || value.is_empty() {
                return None;
            }
            Some((name.to_string(), value.to_string()))
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    const TS: &str = "2026-06-15 12:00:00 UTC";

    #[test]
    fn test_convert_minimal() {
        let legacy = "DBUSER='checkmk:secret::localhost::XE'\n";
        let vars = HashMap::from([("DBUSER".into(), "checkmk:secret::localhost::XE".into())]);
        let result = convert(legacy, "/test/mk_oracle.cfg", &vars, TS).unwrap();
        assert!(result.starts_with(
            "# --- Converted from /test/mk_oracle.cfg at 2026-06-15 12:00:00 UTC ---\n"
        ));
        assert!(result.contains("# DBUSER='checkmk:secret::localhost::XE'"));
        assert!(result.contains("# --- Known environment variables defined in legacy config ---\n"));
        assert!(result.contains("# --- Unified Config ---\n"));
        assert!(result.contains("hostname: localhost"));
        assert!(result.contains("      - sid: XE"));
        assert!(result.contains("        alias: XE"));
        assert!(result.contains("username: \"checkmk\""));
        assert!(result.contains("password: \"secret\""));
    }

    #[test]
    fn test_convert_no_dbuser_fails() {
        let result = convert("", "/test/empty.cfg", &HashMap::new(), TS);
        assert!(result.is_err());
        let err = result.unwrap_err().to_string();
        assert!(err.contains("DBUSER not defined"), "got: {err}");
    }

    #[test]
    fn test_convert_preserves_all_lines() {
        let legacy = "DBUSER='user:pass:::'\n\
                       ASMUSER='/::SYSASM:::'\n\
                       CACHE_MAXAGE=600\n\
                       REMOTE_INSTANCE_XE='user:pass::host:1521::XE::'\n";
        let vars = HashMap::from([("DBUSER".into(), "user:pass::::".into())]);
        let result = convert(legacy, "/test/cfg", &vars, TS).unwrap();
        for line in legacy.lines() {
            assert!(result.contains(&format!("# {line}")), "missing: {line}");
        }
    }

    #[test]
    fn test_convert_result_is_valid_yaml() {
        let legacy = "DBUSER='checkmk:secret::::'\n";
        let vars = HashMap::from([("DBUSER".into(), "checkmk:secret::::".into())]);
        let result = convert(legacy, "/test/mk_oracle.cfg", &vars, TS).unwrap();
        let config = super::super::OracleConfig::load_str(&result);
        assert!(config.is_ok(), "generated YAML must be loadable: {result}");
        assert!(config.unwrap().ora_sql().is_some());
    }

    #[test]
    fn test_convert_tns_admin() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("TNS_ADMIN".into(), "/opt/oracle/tns".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("tns_admin: /opt/oracle/tns"));
    }

    #[test]
    fn test_convert_dbuser_extra_omits_default_alias() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE2".into(), "xe2user:xe2pwd:::1521:".into()),
            ("DBUSER_XE1".into(), "/:::::oooo".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(!result.contains("      - sid: XE2\n        alias:"));
        assert!(result.contains("      - sid: XE1\n        alias: oooo\n"));
    }

    #[test]
    fn test_parse_sections() {
        let vars = HashMap::from([("SYNC_SECTIONS".into(), "instance performance locks".into())]);
        let result = parse_sections(&vars, "SYNC_SECTIONS");
        assert_eq!(
            result,
            HashSet::from(["instance".into(), "performance".into(), "locks".into()])
        );
        assert!(parse_sections(&vars, "MISSING").is_empty());
    }

    #[test]
    fn test_convert_sections_with_async_flag() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("SYNC_SECTIONS".into(), "instance locks".into()),
            ("ASYNC_SECTIONS".into(), "tablespaces rman".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("      - instance:\n"));
        assert!(result.contains("      - locks:\n"));
        assert!(result.contains("      - rman:\n          is_async: yes\n"));
        assert!(result.contains("      - tablespaces:\n          is_async: yes\n"));
    }

    #[test]
    fn test_convert_sections_asm_affinity() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("SYNC_SECTIONS".into(), "instance locks".into()),
            ("ASYNC_SECTIONS".into(), "tablespaces".into()),
            ("SYNC_ASM_SECTIONS".into(), "instance processes".into()),
            ("ASYNC_ASM_SECTIONS".into(), "asm_diskgroup".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        // asm_diskgroup: async + asm-only
        assert!(result.contains(
            "      - asm_diskgroup:\n          is_async: yes\n          affinity: \"asm\"\n"
        ));
        // instance: sync normal + sync asm → affinity: all, not async
        assert!(result.contains("      - instance:\n          affinity: \"all\"\n"));
        assert!(!result.contains("      - instance:\n          is_async:"));
        // processes: asm-only (not in normal)
        assert!(result.contains("      - processes:\n          affinity: \"asm\"\n"));
        // locks: normal-only, sync → no affinity, no async
        assert!(result.contains("      - locks:\n"));
        assert!(!result.contains("      - locks:\n          affinity:"));
        // tablespaces: normal-only, async
        assert!(result.contains("      - tablespaces:\n          is_async: yes\n"));
        assert!(
            !result.contains("      - tablespaces:\n          is_async: yes\n          affinity:")
        );
    }

    #[test]
    fn test_convert_dbuser_extra_has_connection_and_auth() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_ORCL".into(), "admin:secret::myhost:1522:".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains(
            r#"      - sid: ORCL
        connection:
          hostname: myhost
          port: 1522
        authentication:
          username: "admin"
          password: "secret"
          type: standard
"#
        ));
    }

    #[test]
    fn test_convert_dbuser_extra_no_connection_when_empty() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE".into(), "xe:xepwd::::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(!result.contains("      - sid: XE\n        connection:"));
    }

    #[test]
    fn test_convert_dbuser_instance_no_connection_no_auth() {
        let vars = HashMap::from([("DBUSER".into(), "admin:secret::myhost:1522:ORCL".into())]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("      - sid: ORCL\n        alias: ORCL\n"));
        assert!(!result.contains("      - sid: ORCL\n        alias: ORCL\n        connection:"));
    }

    #[test]
    fn test_convert_dbuser_role_in_auth() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE".into(), "admin:secret:SYSDBA:::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(result.contains("          role: sysdba\n"));
    }

    #[test]
    fn test_convert_slash_username_no_auth_block() {
        let vars = HashMap::from([
            ("DBUSER".into(), "user:pass::::".into()),
            ("DBUSER_XE3".into(), "/::SYSASM:::".into()),
        ]);
        let result = convert("", "/test/cfg", &vars, TS).unwrap();
        assert!(
            !result.contains("      - sid: XE3\n        connection:"),
            "XE3 must have no connection (empty hostname)"
        );
        assert!(
            !result.contains("      - sid: XE3\n        authentication:"),
            "XE3 must have no authentication ('/' → empty username)"
        );
    }

    #[test]
    fn test_parse_dbuser_slash_username_replaced() {
        let db = parse_dbuser("DBUSER", "/::SYSASM:::").unwrap();
        assert!(db.username.is_empty(), "'/' must be replaced with empty");
        assert_eq!(db.role.as_deref(), Some("SYSASM"));
    }

    #[test]
    fn test_parse_dbuser() {
        let db = parse_dbuser("DBUSER", "checkmk:secret:SYSDBA:myhost:1522:ORCL").unwrap();
        assert!(db.sid.is_none(), "DBUSER has no SID suffix");
        assert_eq!(db.username, "checkmk");
        assert_eq!(db.password, "secret");
        assert_eq!(db.role.as_deref(), Some("SYSDBA"));
        assert_eq!(db.hostname, "myhost");
        assert_eq!(db.port.as_deref(), Some("1522"));
        assert_eq!(db.alias_or_sid, "ORCL");
    }

    #[test]
    fn test_parse_dbuser_with_sid_suffix() {
        let db = parse_dbuser("DBUSER_XE1", "/:::::oooo").unwrap();
        assert_eq!(db.sid.as_deref(), Some("XE1"));
        assert!(db.username.is_empty(), "'/' replaced with empty");
        assert_eq!(db.alias_or_sid, "oooo");
    }

    #[test]
    fn test_parse_dbuser_empty_optionals() {
        let db = parse_dbuser("DBUSER", "user:pass::::").unwrap();
        assert!(db.sid.is_none());
        assert_eq!(db.username, "user");
        assert_eq!(db.password, "pass");
        assert!(db.role.is_none());
        assert!(db.hostname.is_empty());
        assert!(db.port.is_none());
        assert_eq!(db.alias_or_sid, "$ORACLE_SID");
    }

    #[test]
    fn test_parse_dbuser_minimal() {
        let db = parse_dbuser("DBUSER", "user:pass").unwrap();
        assert!(db.sid.is_none());
        assert_eq!(db.username, "user");
        assert_eq!(db.password, "pass");
        assert!(db.role.is_none());
        assert!(db.hostname.is_empty());
        assert!(db.port.is_none());
        assert_eq!(db.alias_or_sid, "$ORACLE_SID");
    }

    #[test]
    fn test_parse_dbuser_too_few_fields() {
        assert!(parse_dbuser("DBUSER", "onlyuser").is_err());
    }

    #[test]
    fn test_parse_dbuser_invalid_name() {
        let err = parse_dbuser("ASMUSER", "/:::::").unwrap_err();
        assert!(err.to_string().contains("invalid variable name"));
        assert!(parse_dbuser("DB_USER", "user:pass").is_err());
        assert!(parse_dbuser("DBUSER", "user:pass").is_ok());
        assert!(parse_dbuser("DBUSER_XE", "user:pass").is_ok());
    }

    #[test]
    fn test_format_timestamp() {
        let ts = format_timestamp();
        assert!(ts.ends_with(" UTC"));
        assert!(ts.contains('-'));
        assert!(ts.contains(':'));
        assert_eq!(ts.len(), 23);
    }

    #[test]
    fn test_civil_from_days() {
        assert_eq!(civil_from_days(0), (1970, 1, 1));
        assert_eq!(civil_from_days(365), (1971, 1, 1));
        assert_eq!(civil_from_days(19889), (2024, 6, 15));
    }

    #[test]
    fn test_parse_variable_output() {
        let output = "DBUSER checkmk:secret\nCACHE_MAXAGE 600\nSYNC_SECTIONS instance sessions\n";
        let result = parse_variable_output(output).unwrap();
        assert_eq!(result.len(), 3);
        assert_eq!(result["DBUSER"], "checkmk:secret");
        assert_eq!(result["CACHE_MAXAGE"], "600");
        assert!(result["SYNC_SECTIONS"].contains("sessions"));
    }

    #[test]
    fn test_parse_variable_output_skips_malformed() {
        let output = "DBUSER checkmk\n\n BADNAME value\nNOSPACE\nVAR \n";
        let result = parse_variable_output(output).unwrap();
        assert_eq!(result.len(), 1);
        assert_eq!(result["DBUSER"], "checkmk");
    }

    #[cfg(unix)]
    #[test]
    fn test_build_posix_script() {
        let script = build_posix_script(Path::new("/tmp/test.cfg"));
        assert!(script.starts_with(". '/tmp/test.cfg'"));
        assert!(script.contains("DBUSER"));
        assert!(script.contains("CACHE_MAXAGE"));
        assert!(script.contains("REMOTE_INSTANCE_"));
        assert!(script.contains("EXCLUDE_"));
    }

    #[cfg(unix)]
    #[test]
    fn test_execute_config_basic() {
        let config_path =
            std::env::temp_dir().join(format!("mk_oracle_test_exec_{}.cfg", std::process::id()));
        std::fs::write(
            &config_path,
            "DBUSER='checkmk:secret'\nCACHE_MAXAGE=600\nREMOTE_INSTANCE_XE='user:pass::host'\n",
        )
        .unwrap();
        let result = convert_config(&config_path);
        let _ = std::fs::remove_file(&config_path);
        let vars = result.unwrap();
        assert_eq!(vars["DBUSER"], "checkmk:secret");
        assert_eq!(vars["CACHE_MAXAGE"], "600");
        assert_eq!(vars["REMOTE_INSTANCE_XE"], "user:pass::host");
    }
}
