// Copyright (C) 2025 Checkmk GmbH
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

use assert_cmd::Command;
use mk_oracle::version::VERSION;
use std::ffi::OsString;
use std::fs;
use std::sync::OnceLock;

static BIN_COMMAND_PATH: OnceLock<OsString> = OnceLock::new();

#[cfg(not(feature = "build_system_bazel"))]
fn bin_command_path_impl() -> OsString {
    let path = assert_cmd::cargo::cargo_bin("mk-oracle");
    assert!(path.is_file());
    path.into()
}

#[cfg(feature = "build_system_bazel")]
fn bin_command_path_impl() -> OsString {
    let cwd = std::env::current_dir().unwrap();
    let relative_path: std::path::PathBuf = ["packages", "mk-oracle", "mk-oracle"].iter().collect();
    let path = cwd.join(relative_path);
    assert!(path.is_file());
    path.into()
}

fn run_bin() -> Command {
    let bin_command_path = BIN_COMMAND_PATH.get_or_init(bin_command_path_impl);
    Command::new(bin_command_path)
}

#[test]
fn test_version() {
    let output = run_bin().arg("--version").ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();
    let expected = format!("mk-oracle {VERSION}\n");
    assert_eq!(stdout, expected, "Unexpected version output");

    if let Ok(cmk_version) = std::env::var("CMK_VERSION") {
        assert_eq!(
            stdout,
            format!("mk-oracle {cmk_version}\n"),
            "Binary version doesn't match CMK_VERSION env var"
        );
    }
}

#[test]
fn test_help() {
    let output = run_bin().arg("--help").ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();
    // Each option must be advertised; for options with a short form the help
    // lists it as "-x, --long", so this also checks the short/long pairing.
    for expected in [
        "-v, --verbose",
        "-l, --display-log",
        "--print-info",
        "--log-dir",
        "--temp-dir",
        "--state-dir",
        "--no-spool",
        "-c, --config-file",
        "--detect-sids",
        "--find-runtime",
        "--runtime-ready",
        "-f, --filter",
        "-g, --generate-plugins",
        "-M, --migrate-config",
        "--migrate-output",
        "-h, --help",
        "-V, --version",
    ] {
        assert!(
            stdout.contains(expected),
            "Missing option in --help output: {expected}"
        );
    }
}

struct TestEnv {
    _tmp: tempfile::TempDir,
    plugins_dir: std::path::PathBuf,
    config: std::path::PathBuf,
}

fn setup_test_env() -> TestEnv {
    let tmp = tempfile::tempdir().unwrap();
    let plugins_dir = tmp.path().join("plugins");
    fs::create_dir(&plugins_dir).unwrap();
    #[cfg(windows)]
    fs::create_dir(tmp.path().join("bakery")).unwrap();

    let config = tmp.path().join("mk-oracle.yml");
    fs::write(
        &config,
        r#"---
oracle:
  main:
    connection:
      hostname: localhost
    authentication:
      username: dummy
      password: dummy
      type: standard
"#,
    )
    .unwrap();

    TestEnv {
        _tmp: tmp,
        plugins_dir,
        config,
    }
}

#[cfg(windows)]
#[test]
fn test_generate_plugins() {
    let env = setup_test_env();
    run_bin()
        .args(["-c", env.config.to_str().unwrap()])
        .args(["-g", env.plugins_dir.to_str().unwrap()])
        .assert()
        .success();
    let sync_content = fs::read_to_string(env.plugins_dir.join("oracle_unified_sync.ps1"))
        .expect("sync plugin missing");
    let async_content = fs::read_to_string(env.plugins_dir.join("oracle_unified_async.ps1"))
        .expect("async plugin missing");
    assert!(!sync_content.is_empty(), "sync plugin empty");
    assert!(!async_content.is_empty(), "async plugin empty");
}

#[cfg(not(windows))]
#[test]
fn test_generate_plugins() {
    use std::os::unix::fs::PermissionsExt;

    let env = setup_test_env();
    run_bin()
        .args(["-c", env.config.to_str().unwrap()])
        .args(["-g", env.plugins_dir.to_str().unwrap()])
        .assert()
        .success();
    let sync_path = env.plugins_dir.join("oracle_unified_sync");
    let async_path = env.plugins_dir.join("600").join("oracle_unified_async");
    let sync_content = fs::read_to_string(&sync_path).expect("sync plugin missing");
    let async_content = fs::read_to_string(&async_path).expect("async plugin missing");
    assert!(!sync_content.is_empty(), "sync plugin empty");
    assert!(!async_content.is_empty(), "async plugin empty");
    const EXECUTABLE_BITS: u32 = 0o111;
    let sync_mode = sync_path.metadata().unwrap().permissions().mode();
    let async_mode = async_path.metadata().unwrap().permissions().mode();
    assert_eq!(
        sync_mode & EXECUTABLE_BITS,
        EXECUTABLE_BITS,
        "sync plugin not executable"
    );
    assert_eq!(
        async_mode & EXECUTABLE_BITS,
        EXECUTABLE_BITS,
        "async plugin not executable"
    );
}

#[test]
fn test_print_info() {
    let env = setup_test_env();
    let output = run_bin()
        .args(["-c", env.config.to_str().unwrap()])
        .args(["--print-info", "-l"])
        .output() // exit code varies: no Oracle runtime on Linux → exit 1
        .unwrap();
    let stderr = String::from_utf8(output.stderr).unwrap();
    for expected in ["Log level", "Log dir", "Temp dir", "MK_CONFDIR"] {
        assert!(
            stderr.contains(expected),
            "Missing in --print-info output: {expected}"
        );
    }
}

fn reference_path(name: &str) -> String {
    let ext = if cfg!(windows) { "ps1" } else { "cfg" };
    let file = format!("{name}.{ext}");

    if cfg!(feature = "build_system_bazel") {
        let cwd = std::env::current_dir().unwrap();
        cwd.join("packages/mk-oracle/references")
            .join(&file)
            .to_str()
            .unwrap()
            .to_string()
    } else {
        format!("references/{file}")
    }
}

fn legacy_cfg_path() -> String {
    reference_path("output-multiple")
}

#[test]
fn test_migrate_config_to_stdout() {
    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(
        stdout.starts_with(&format!("# --- Converted from {cfg} at ")),
        "must start with conversion header"
    );
    assert!(stdout.contains("DBUSER"), "legacy config not in comments");
    assert!(
        stdout.contains("# --- Known environment variables defined in legacy config ---\n"),
        "missing env vars section"
    );
    assert!(
        stdout.contains("# --- Unified Config ---\n"),
        "missing unified config header"
    );
    assert!(stdout.contains("oracle:"), "missing oracle: key");
    assert!(stdout.contains("main:"), "missing main: key");
    assert!(
        stdout.contains("authentication:"),
        "missing authentication:"
    );
    assert!(stdout.contains("connection:"), "missing connection:");
}

#[test]
fn test_migrate_config_yaml_structure() {
    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    // Header
    assert!(stdout.starts_with(&format!("# --- Converted from {cfg} at ")));

    // Legacy config echoed as comments
    for var in ["DBUSER", "ASMUSER", "SYNC_SECTIONS", "ASYNC_SECTIONS"] {
        assert!(stdout.contains(var), "legacy config missing {var}");
    }

    // Extracted environment variables as comments
    assert!(stdout.contains("# --- Known environment variables defined in legacy config ---\n"));
    let env_value_of = |var: &str| -> Option<&str> {
        let prefix = format!("# {var} ");
        stdout
            .lines()
            .find(|l| l.starts_with(&prefix))
            .map(|l| &l[prefix.len()..])
    };
    assert_eq!(
        env_value_of("DBUSER"),
        Some("c##checkmk:********::localhost:1521:")
    );
    assert_eq!(env_value_of("ASMUSER"), Some("/::SYSASM:::"));
    assert_eq!(env_value_of("CACHE_MAXAGE"), Some("601"));
    // assert_eq!(env_value_of("ONLY_SIDS"), Some("..."));
    // assert_eq!(env_value_of("ORACLE_HOME"), Some("..."));
    // assert_eq!(env_value_of("TNS_ADMIN"), Some("..."));

    // Unified config section — values must come from DBUSER parsing
    assert!(stdout.contains("# --- Unified Config ---\n"));
    // From DBUSER='c##checkmk:********::localhost:1521:'
    // assert!(stdout.contains("      hostname: localhost\n"));
    // assert!(stdout.contains("      port: 1521\n"));
    // assert!(stdout.contains("      username: c##checkmk\n"));
    // From DBUSER_XE1='/:::::oooo'
    // assert!(stdout.contains("      - sid: $ORACLE_SID\n"));
    // assert!(stdout.contains("        alias: oooo\n"));
    // From DBUSER_XE2='xe2user:xe2pwd:SYSDBA:localhost1:1521:'
    // assert!(stdout.contains("      - sid: $ORACLE_SID\n"));

    // Output must be loadable as valid Oracle config
    // let config = mk_oracle::config::OracleConfig::load_str(&stdout);
    // assert!(
    //     config.is_ok(),
    //     "migrated output must parse as YAML: {stdout}"
    // );
    // assert!(config.unwrap().ora_sql().is_some());
}

#[test]
fn test_migrate_config_to_file() {
    let cfg = legacy_cfg_path();
    let tmp = tempfile::tempdir().unwrap();
    let output_path = tmp.path().join("migrated.yml");
    run_bin()
        .args(["-M", &cfg])
        .args(["--migrate-output", output_path.to_str().unwrap()])
        .assert()
        .success();
    let content = fs::read_to_string(&output_path).expect("output file missing");
    assert!(
        content.starts_with("# --- Converted from "),
        "must start with conversion header"
    );
    assert!(
        content.contains("# --- Unified Config ---\n"),
        "missing unified config header"
    );
    assert!(content.contains("oracle:"), "missing oracle: key");
}

#[test]
fn test_execute_config_reference() {
    use std::path::Path;

    let cfg = legacy_cfg_path();
    let vars = mk_oracle::config::migration::convert_config(Path::new(&cfg)).unwrap();
    let lines: Vec<String> = vars.iter().map(|(n, v)| format!("{n} {v}")).collect();

    let value_of = |var: &str| -> Option<&str> {
        let prefix = format!("{var} ");
        lines
            .iter()
            .find(|l| l.starts_with(&prefix))
            .map(|l| &l[prefix.len()..])
    };

    assert_eq!(
        value_of("DBUSER"),
        Some("c##checkmk:********::localhost:1521:")
    );
    if cfg!(windows) {
        // windows ps1 doesn't support tnsalias
        assert_eq!(value_of("DBUSER_XE1"), Some("/:::::"));
    } else {
        assert_eq!(value_of("DBUSER_XE1"), Some("/:::::oooo"));
    }
    assert_eq!(
        value_of("DBUSER_XE2"),
        Some("xe2user:xe2pwd:SYSDBA:localhost1:1521:")
    );
    assert_eq!(value_of("ASMUSER"), Some("/::SYSASM:::"));
    assert_eq!(value_of("CACHE_MAXAGE"), Some("601"));
    assert!(
        value_of("SYNC_SECTIONS").unwrap().contains("instance"),
        "SYNC_SECTIONS must contain instance"
    );
    assert!(
        value_of("ASYNC_SECTIONS").unwrap().contains("tablespaces"),
        "ASYNC_SECTIONS must contain tablespaces"
    );
}

#[test]
fn test_migrate_reference_config_connection_and_auth() {
    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");

    // Connection
    let conn = ora.conn();
    assert!(conn.is_local(), "hostname must be localhost");
    assert_eq!(
        conn.port().to_string(),
        "1521",
        "empty port defaults to 1521"
    );
    // output-multiple.cfg has no TNS_ADMIN
    assert!(
        conn.tns_admin().is_none(),
        "tns_admin must be None for multiple config"
    );

    // connection must not have sid
    assert!(
        ora.target_id().is_none(),
        "main target_id must be None (no sid/alias at top level)"
    );

    // Authentication from DBUSER='c##checkmk:********::localhost:1521:'
    let auth = ora.auth();
    assert_eq!(auth.username(), "c##checkmk");
    assert_eq!(auth.password(), Some("********"));
    assert_eq!(auth.auth_type().to_string(), "standard");
    assert!(auth.role().is_none(), "empty role must be None");

    // Instances: DBUSER (empty tnsalias), DBUSER_XE1 (tnsalias=oooo), DBUSER_XE2
    let instances = ora.instances();
    assert_eq!(
        instances.len(),
        3,
        "must have 3 instances from DBUSER + DBUSER_XE1 + DBUSER_XE2"
    );

    // DBUSER instance: sid=$ORACLE_SID, alias=$ORACLE_SID, connection=localhost:1521, auth=c##checkmk
    let dbuser_inst = instances
        .iter()
        .find(|i| i.alias().as_ref().map(|a| a.to_string()).as_deref() == Some("$ORACLE_SID"))
        .expect("DBUSER instance with alias $ORACLE_SID");
    assert!(dbuser_inst.conn().is_local());
    assert_eq!(dbuser_inst.auth().username(), "c##checkmk");

    // DBUSER_XE1: sid=XE1, alias=oooo, inherits main connection and auth
    #[cfg(not(windows))]
    let xe1_inst = instances
        .iter()
        .find(|i| i.alias().as_ref().map(|a| a.to_string()).as_deref() == Some("oooo"))
        .expect("DBUSER_XE1 instance with alias oooo");
    #[cfg(windows)]
    let xe1_inst = instances
        .iter()
        .find(|i| i.standalone_sid().map(|s| s.to_string()).as_deref() == Some("XE1"))
        .expect("DBUSER_XE1 instance with sid XE1");
    #[cfg(windows)]
    assert!(xe1_inst.alias().is_none());

    assert_eq!(
        xe1_inst.conn().hostname().to_string(),
        conn.hostname().to_string(),
        "XE1 connection must inherit main hostname"
    );
    assert_eq!(
        xe1_inst.auth().username(),
        auth.username(),
        "XE1 auth must inherit main username"
    );

    // No MAX_TASKS in output-multiple.cfg → threads defaults to 1
    assert_eq!(ora.options().threads(), 1, "threads must default to 1");

    // DBUSER_XE2: sid=XE2, no alias, connection=localhost1:1521, auth=xe2user, role=SYSDBA
    let xe2_inst = instances
        .iter()
        .find(|i| i.auth().username() == "xe2user")
        .expect("DBUSER_XE2 instance with username xe2user");
    assert_eq!(xe2_inst.conn().hostname().to_string(), "localhost1");
    assert_eq!(
        xe2_inst.auth().role().map(|r| r.to_string()),
        Some("sysdba".to_string())
    );
}

#[test]
fn test_migrate_reference_config_cache_age() {
    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    assert_eq!(
        ora.cache_age(),
        601,
        "cache_age must match CACHE_MAXAGE from reference config"
    );
}

#[test]
fn test_migrate_reference_config_discovery() {
    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    let discovery = ora.discovery();
    assert!(discovery.detect(), "detect must be true");
    assert_eq!(
        discovery.include(),
        &["XE1", "XEXE"],
        "include must match ONLY_SIDS"
    );
    let mut exclude = discovery.exclude().clone();
    exclude.sort();
    assert_eq!(
        exclude,
        &["AAA", "BBB", "XE2"],
        "exclude must match SKIP_SIDS + EXCLUDE_*=ALL"
    );
}

#[test]
fn test_migrate_reference_config_sections() {
    use mk_oracle::config::section::SectionKind;
    use mk_oracle::types::SectionAffinity;

    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    let sections = ora.all_sections();

    let find = |name: &str| -> &mk_oracle::config::section::Section {
        sections
            .iter()
            .find(|s| s.name().as_str() == name)
            .unwrap_or_else(|| panic!("section {name} not found"))
    };

    // (name, expected_kind, expected_affinity)
    use SectionAffinity::{All, Asm, Db};
    use SectionKind::{Async, Sync};
    let expected: &[(&str, SectionKind, SectionAffinity)] = &[
        ("asm_diskgroup", Async, Asm),
        ("dataguard_stats", Sync, Db),
        ("instance", Sync, All),
        ("jobs", Async, Db),
        ("locks", Sync, Db),
        ("logswitches", Sync, Db),
        ("longactivesessions", Sync, Db),
        ("performance", Sync, Db),
        ("processes", Sync, All),
        ("recovery_area", Sync, Db),
        ("recovery_status", Sync, Db),
        ("resumable", Async, Db),
        ("rman", Async, Db),
        ("sessions", Sync, Db),
        // windows agent plugin does not implement systemparameter
        #[cfg(not(windows))]
        ("systemparameter", Sync, Db),
        ("tablespaces", Async, Db),
        ("undostat", Sync, Db),
    ];

    assert_eq!(
        sections.len(),
        expected.len(),
        "expected {:#?} sections, got {:#?}",
        expected,
        sections
    );

    for (name, kind, affinity) in expected {
        let s = find(name);
        assert_eq!(s.kind(), *kind, "{name}: wrong kind");
        assert_eq!(*s.affinity(), *affinity, "{name}: wrong affinity");
    }
}

#[cfg(not(windows))]
fn legacy_cfg_no_tnsalias_path() -> String {
    const REFERENCE_FILE: &str = "output-xe-no-tnsalias.cfg";

    #[cfg(feature = "build_system_bazel")]
    {
        let cwd = std::env::current_dir().unwrap();
        cwd.join("packages/mk-oracle/references")
            .join(REFERENCE_FILE)
            .to_str()
            .unwrap()
            .to_string()
    }
    #[cfg(not(feature = "build_system_bazel"))]
    {
        format!("references/{REFERENCE_FILE}")
    }
}

#[cfg(not(windows))]
#[test]
fn test_migrate_no_tnsalias_falls_back_to_oracle_sid() {
    let cfg = legacy_cfg_no_tnsalias_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    assert!(
        stdout.contains("      - sid: $ORACLE_SID"),
        "sid must fall back to $ORACLE_SID"
    );
    assert!(
        stdout.contains("        alias: $ORACLE_SID"),
        "alias must fall back to $ORACLE_SID"
    );
}

#[test]
fn test_migrate_optional_config_threads() {
    let cfg = reference_path("output-optional");
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    assert_eq!(
        ora.options().threads(),
        7,
        "MAX_TASKS=7 must set threads to 7"
    );
}
