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
use mk_oracle::config::merge::{merge_configs, MergedConfig};
use mk_oracle::config::OracleConfig;
use mk_oracle::ora_sql::detect::parse_tns_names_ora;
use mk_oracle::setup::CLIENT_LIB_NAME;
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
    // --migrate-subdir is compiled only on non-Windows targets.
    #[cfg(not(windows))]
    assert!(
        stdout.contains("--migrate-subdir"),
        "Missing option in --help output: --migrate-subdir"
    );
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

/// The environment report needs no flag of its own, only debug verbosity.
#[test]
fn test_environment_info_is_logged_at_debug() {
    let env = setup_test_env();
    let output = run_bin()
        .args(["-c", env.config.to_str().unwrap()])
        .args(["-l", "-v"])
        .output() // exit code varies: no Oracle runtime on Linux -> exit 1
        .unwrap();
    let stderr = String::from_utf8(output.stderr).unwrap();
    for expected in [
        "Log level",
        "Log dir",
        "Temp dir",
        "MK_CONFDIR",
        "MK_LIBDIR",
    ] {
        assert!(
            stderr.contains(expected),
            "Missing in environment info: {expected}"
        );
    }
}

#[test]
fn test_find_runtime_reports_environment() {
    let env = setup_test_env();
    // factory runtime layout under MK_LIBDIR:
    // plugins/packages/mk-oracle on Unix, + /runtime on Windows
    let lib_dir = tempfile::tempdir().unwrap();
    let package_dir = lib_dir.path().join("plugins/packages/mk-oracle");
    fs::create_dir_all(package_dir.join("runtime")).unwrap();
    let expected_dir = if cfg!(windows) {
        package_dir.join("runtime")
    } else {
        package_dir
    };
    // runtime detection requires the client library to be present
    fs::File::create(expected_dir.join(CLIENT_LIB_NAME)).unwrap();

    let output = run_bin()
        .env("MK_LIBDIR", lib_dir.path())
        .env_remove("ORACLE_HOME")
        .env_remove("LD_LIBRARY_PATH")
        .args(["-c", env.config.to_str().unwrap(), "--find-runtime"])
        .output()
        .unwrap();
    assert!(output.status.success(), "--find-runtime must succeed");
    let stdout = String::from_utf8(output.stdout).unwrap();
    let path_var = if cfg!(windows) {
        "PATH"
    } else {
        "LD_LIBRARY_PATH"
    };
    let first_line = stdout.lines().next().unwrap_or_default();
    assert!(
        first_line.starts_with(&format!("{path_var}={}", expected_dir.display())),
        "first line must report the detected runtime, got: {stdout}"
    );
    assert!(
        !stdout.contains('"'),
        "output must not be Debug-quoted, got: {stdout}"
    );
    assert!(stdout.ends_with('\n'), "output must end with a newline");
}

#[test]
fn test_find_runtime_without_runtime_fails() {
    // use_host_client "never" + an empty MK_LIBDIR: nothing to detect
    let tmp = tempfile::tempdir().unwrap();
    let config = tmp.path().join("mk-oracle.yml");
    fs::write(
        &config,
        r#"---
oracle:
  main:
    options:
      use_host_client: never
    connection:
      hostname: localhost
    authentication:
      username: dummy
      password: dummy
      type: standard
"#,
    )
    .unwrap();

    let output = run_bin()
        .env("MK_LIBDIR", tmp.path())
        .args(["-c", config.to_str().unwrap(), "--find-runtime"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1), "must fail without a runtime");
    assert!(
        output.stdout.is_empty(),
        "nothing must be printed on stdout without a runtime"
    );
    let stderr = String::from_utf8(output.stderr).unwrap();
    assert!(
        stderr.contains("Stop on error"),
        "error must be reported on stderr, got: {stderr}"
    );
}

#[cfg(unix)]
fn write_use_host_client_config(
    dir: &std::path::Path,
    client_dir: &std::path::Path,
) -> std::path::PathBuf {
    let config = dir.join("mk-oracle.yml");
    fs::write(
        &config,
        format!(
            r#"---
oracle:
  main:
    options:
      use_host_client: {}
    connection:
      hostname: localhost
    authentication:
      username: dummy
      password: dummy
      type: standard
"#,
            client_dir.display()
        ),
    )
    .unwrap();
    config
}

#[cfg(unix)]
#[test]
fn test_find_runtime_derives_oracle_home_for_full_home_lib_dir() {
    // full home layout: <home>/lib with the client library, oracore next to it
    let tmp = tempfile::tempdir().unwrap();
    let home = tmp.path().join("dbhome_1");
    let home_lib = home.join("lib");
    fs::create_dir_all(&home_lib).unwrap();
    fs::File::create(home_lib.join(CLIENT_LIB_NAME)).unwrap();
    fs::create_dir_all(home.join("oracore/mesg")).unwrap();
    let config = write_use_host_client_config(tmp.path(), &home_lib);

    let output = run_bin()
        .env("MK_LIBDIR", tmp.path())
        .env_remove("ORACLE_HOME")
        .env_remove("LD_LIBRARY_PATH")
        .args(["-c", config.to_str().unwrap(), "--find-runtime"])
        .output()
        .unwrap();
    assert!(output.status.success(), "--find-runtime must succeed");
    let stdout = String::from_utf8(output.stdout).unwrap();
    let first_line = stdout.lines().next().unwrap_or_default();
    assert!(
        first_line.starts_with(&format!("LD_LIBRARY_PATH={}", home_lib.display())),
        "first line must report the configured runtime, got: {stdout}"
    );
    assert!(
        stdout.contains(&format!("ORACLE_HOME={}\n", home.display())),
        "the home derived from the lib dir must be reported, got: {stdout}"
    );
}

#[cfg(unix)]
#[test]
fn test_find_runtime_no_oracle_home_for_instant_client_dir() {
    // Instant Client layout: the client library directly in the directory,
    // no ORACLE_HOME needed
    let tmp = tempfile::tempdir().unwrap();
    let instant_client = tmp.path().join("instantclient_19_19");
    fs::create_dir_all(&instant_client).unwrap();
    fs::File::create(instant_client.join(CLIENT_LIB_NAME)).unwrap();
    let config = write_use_host_client_config(tmp.path(), &instant_client);

    let output = run_bin()
        .env("MK_LIBDIR", tmp.path())
        .env_remove("ORACLE_HOME")
        .env_remove("LD_LIBRARY_PATH")
        .args(["-c", config.to_str().unwrap(), "--find-runtime"])
        .output()
        .unwrap();
    assert!(output.status.success(), "--find-runtime must succeed");
    let stdout = String::from_utf8(output.stdout).unwrap();
    let first_line = stdout.lines().next().unwrap_or_default();
    assert!(
        first_line.starts_with(&format!("LD_LIBRARY_PATH={}", instant_client.display())),
        "first line must report the configured runtime, got: {stdout}"
    );
    assert!(
        !stdout.contains("ORACLE_HOME="),
        "no home must be derived for an Instant Client dir, got: {stdout}"
    );
}

#[cfg(not(windows))]
#[test]
fn test_user_config_overrides_bakery() {
    let tmp = tempfile::tempdir().unwrap();
    let lib_dir = tmp.path();

    // Bakery config under a dedicated conf dir, discovered via MK_CONFDIR.
    let conf_dir = lib_dir.join("conf");
    fs::create_dir(&conf_dir).unwrap();
    fs::write(
        conf_dir.join("mk-oracle.yml"),
        r#"---
oracle:
  main:
    connection:
      hostname: localhost
    authentication:
      username: dummy
      password: dummy
      type: standard
    cache_age: 600
"#,
    )
    .unwrap();

    // User config in the runtime dir overrides cache_age.
    let runtime_dir = lib_dir.join("plugins/packages/mk-oracle");
    fs::create_dir_all(&runtime_dir).unwrap();
    fs::write(
        runtime_dir.join("mk-oracle.user.yml"),
        "oracle:\n  main:\n    cache_age: 123\n",
    )
    .unwrap();

    let out = lib_dir.join("out");
    fs::create_dir(&out).unwrap();

    let output = run_bin()
        .env("MK_LIBDIR", lib_dir)
        .env("MK_CONFDIR", &conf_dir)
        .args(["-g", out.to_str().unwrap(), "-l"])
        .output()
        .unwrap();
    assert!(output.status.success(), "generate-plugins must succeed");

    // The async plugin lands in the overridden cache_age subdir, not the default.
    assert!(
        out.join("123").join("oracle_unified_async").is_file(),
        "async plugin should use the overridden cache_age (123)"
    );
    assert!(
        !out.join("600").join("oracle_unified_async").exists(),
        "async plugin must not use the default cache_age (600)"
    );

    // The override is logged (acceptance criterion).
    let stderr = String::from_utf8(output.stderr).unwrap();
    assert!(
        stderr.contains("overrides bakery config at: oracle.main.cache_age"),
        "override not logged; stderr: {stderr}"
    );
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
    // custom SQL warnings are printed before the converted config
    assert!(
        stdout.contains(&format!("# --- Converted from {cfg} at ")),
        "missing conversion header"
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

    // Header (custom SQL warnings are printed before it)
    assert!(stdout.contains(&format!("# --- Converted from {cfg} at ")));

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
    assert_eq!(env_value_of("DBUSER"), Some("***"));
    assert_eq!(env_value_of("ASMUSER"), Some("***"));
    assert_eq!(env_value_of("CACHE_MAXAGE"), Some("601"));
    assert_eq!(env_value_of("OLRLOC"), Some("/etc/oracle/olr.loc"));
    // assert_eq!(env_value_of("ONLY_SIDS"), Some("..."));
    // assert_eq!(env_value_of("ORACLE_HOME"), Some("..."));
    // assert_eq!(env_value_of("TNS_ADMIN"), Some("..."));

    // Unified config section — values must come from DBUSER parsing
    assert!(stdout.contains("# --- Unified Config ---\n"));
    assert!(stdout.contains("      oracle_local_registry: /etc/oracle/olr.loc\n"));
    // From DBUSER='c##checkmk:********::localhost:1521:'
    // assert!(stdout.contains("      hostname: localhost\n"));
    // assert!(stdout.contains("      port: 1521\n"));
    // assert!(stdout.contains("      username: c##checkmk\n"));
    // From DBUSER_XE1='/:::::oooo'
    // assert!(stdout.contains("      - sid: XE1\n"));
    // assert!(stdout.contains("        alias: oooo\n"));
    // From DBUSER_XE2='xe2user:xe2pwd:SYSDBA:localhost1:1521:'
    // assert!(stdout.contains("      - sid: XE2\n"));

    // Output must be loadable as valid Oracle config
    // let config = mk_oracle::config::OracleConfig::load_str(&stdout);
    // assert!(
    //     config.is_ok(),
    //     "migrated output must parse as YAML: {stdout}"
    // );
    // assert!(config.unwrap().ora_sql().is_some());
}

/// A fragment the shell cannot source (here: a syntax error) does not fail the
/// config execution, it only makes the shell complain on stderr. That complaint
/// names the file and must reach the user instead of being swallowed, which would
/// leave a config silently migrated from an incomplete set of variables.
#[cfg(not(windows))]
#[test]
fn test_migrate_config_warns_about_unsourceable_fragment() {
    let tmp = tempfile::tempdir().unwrap();
    let main_cfg = tmp.path().join("mk_oracle.cfg");
    fs::write(&main_cfg, "DBUSER='checkmk:secret::localhost:1521:'\n").unwrap();

    let config_dir = tmp.path().join("mk_oracle.d");
    fs::create_dir(&config_dir).unwrap();
    let broken = config_dir.join("50_broken.cfg");
    fs::write(&broken, "SYNC_SECTIONS=(\n").unwrap();

    let output = run_bin()
        .args(["-M", main_cfg.to_str().unwrap()])
        .args(["--migrate-subdir", config_dir.to_str().unwrap()])
        .ok()
        .unwrap();
    let stderr = String::from_utf8(output.stderr).unwrap();
    assert!(
        stderr.contains(&broken.display().to_string()),
        "the unsourceable fragment must be named on stderr, got: {stderr}"
    );
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
    use std::path::PathBuf;

    let cfg = legacy_cfg_path();
    let vars = mk_oracle::config::migration::convert_configs(&[PathBuf::from(&cfg)]).unwrap();
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
    assert_eq!(
        value_of("ASMUSER"),
        Some("asm-user:asm-password:SYSASM:ignored:ignored:")
    );
    assert_eq!(value_of("CACHE_MAXAGE"), Some("601"));
    assert_eq!(value_of("OLRLOC"), Some("/etc/oracle/olr.loc"));
    assert!(
        value_of("SYNC_SECTIONS").unwrap().contains("instance"),
        "SYNC_SECTIONS must contain instance"
    );
    assert!(
        value_of("ASYNC_SECTIONS").unwrap().contains("tablespaces"),
        "ASYNC_SECTIONS must contain tablespaces"
    );
    #[cfg(not(windows))]
    assert_eq!(
        value_of("REMOTE_INSTANCE_1"),
        Some("check_mk:mypassword:sysdba:myRemoteHost:1521:myOracleHost:MYINST3:11.2")
    );
}

// windows ps1 legacy plugin doesn't support custom SQL sections
#[cfg(not(windows))]
#[test]
fn test_execute_config_custom_sqls() {
    use std::path::PathBuf;

    let cfg = legacy_cfg_path();
    let vars = mk_oracle::config::migration::convert_configs(&[PathBuf::from(&cfg)]).unwrap();

    // variables set inside the section function are extracted per section
    assert_eq!(
        vars["SQLS_SECTIONS"],
        "mycustomsection1 mycustomsection2 mycustomsection3 mycustomsection4 mycustomsection5 mycustomsection6"
    );
    assert_eq!(vars["SQLS.mycustomsection1.SQLS_SIDS"], "MYINST3");
    assert_eq!(vars["SQLS.mycustomsection1.SQLS_DIR"], "/etc/check_mk");
    assert_eq!(vars["SQLS.mycustomsection1.SQLS_SQL"], "MyCustomSQL.sql");
    assert_eq!(vars["SQLS.mycustomsection1.SQLS_ITEM_NAME"], "my_item");
    // section 1 values must not leak into section 2
    assert_eq!(vars["SQLS.mycustomsection2.SQLS_SQL"], "OtherSQL.sql");
    assert_eq!(
        vars["SQLS.mycustomsection2.SQLS_SECTION_NAME"],
        "my_custom_section"
    );
    assert_eq!(vars["SQLS.mycustomsection2.SQLS_SECTION_SEP"], "124");
    assert!(!vars.contains_key("SQLS.mycustomsection2.SQLS_DIR"));
    // SQLS_SIDS=$(...) evaluates to empty during extraction (AWK/GREP unset)
    assert_eq!(vars["SQLS.mycustomsection3.SQLS_SQL"], "custom_sql.sql");
    assert!(!vars.contains_key("SQLS.mycustomsection3.SQLS_SIDS"));
    assert_eq!(vars["SQLS.mycustomsection4.SQLS_SIDS"], "MYINST3 MYINST2");
    assert_eq!(vars["SQLS.mycustomsection4.SQLS_SQL"], "custom_sql_2.sql");
    assert_eq!(vars["SQLS.mycustomsection5.SQLS_TNSALIAS"], "TNS");
    assert_eq!(vars["SQLS.mycustomsection5.SQLS_SQL"], "custom_sql_2.sql");
    assert_eq!(vars["SQLS.mycustomsection6.SQLS_SIDS"], "REMOTE_INSTANCE_1");
    assert_eq!(vars["SQLS.mycustomsection6.SQLS_SQL"], "custom_sql_3.sql");
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

    assert_eq!(
        conn.oracle_local_registry(),
        Some(&std::path::PathBuf::from("/etc/oracle/olr.loc"))
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

    // Instances: DBUSER_XE1 (tnsalias=oooo), DBUSER_XE2, REMOTE_INSTANCE_1,
    // MYINST2 from static SQLS_SIDS and TNS from SQLS_TNSALIAS (Linux only)
    let instances = ora.instances();
    #[cfg(not(windows))]
    assert_eq!(
        instances.len(),
        5,
        "must have 5 instances from DBUSER_XE1 + DBUSER_XE2 + REMOTE_INSTANCE_1 + MYINST2 + TNS"
    );
    #[cfg(windows)]
    assert!(
        instances.len() >= 2,
        "must have at least 2 instances from DBUSER_XE1 + DBUSER_XE2"
    );

    // DBUSER_XE1 inherits the main connection, and its "/" username migrates to
    // external/wallet auth (empty username), not the main credentials.
    //
    // Both references name the instance by an alias, but not the same one: the
    // .cfg carries an explicit TNSALIAS (`/:::::oooo`), while the .ps1 array has
    // no sixth field, so the SID stands in as the alias - wallet auth resolves
    // its SEPS credential through the alias, not through host and port.
    #[cfg(not(windows))]
    let alias_of_xe1 = "oooo";
    #[cfg(windows)]
    let alias_of_xe1 = "XE1";
    let xe1_inst = instances
        .iter()
        .find(|i| i.alias().as_ref().map(|a| a.to_string()).as_deref() == Some(alias_of_xe1))
        .unwrap_or_else(|| panic!("DBUSER_XE1 instance with alias {alias_of_xe1}"));

    assert_eq!(
        xe1_inst.conn().hostname().to_string(),
        conn.hostname().to_string(),
        "XE1 connection must inherit main hostname"
    );
    // "/" username → wallet auth: empty username, not the inherited main user.
    assert_eq!(
        xe1_inst.auth().username(),
        "",
        "XE1 '/' username must migrate to empty"
    );
    assert_eq!(
        xe1_inst.auth().auth_type().to_string(),
        "wallet",
        "XE1 '/' username must migrate to wallet auth"
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

    // REMOTE_INSTANCE_1: sid=MYINST3, host=myRemoteHost, auth=check_mk, role=sysdba
    // piggyback_host=myOracleHost (Linux only — ps1 has no REMOTE_INSTANCE support)
    #[cfg(not(windows))]
    {
        let ri = instances
            .iter()
            .find(|i| i.auth().username() == "check_mk")
            .expect("REMOTE_INSTANCE_1 instance with username check_mk");
        assert_eq!(ri.conn().hostname().to_string(), "myremotehost");
        assert_eq!(
            ri.auth().role().map(|r| r.to_string()),
            Some("sysdba".to_string())
        );
    }
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
fn test_migrate_reference_config_custom_metrics_cache_age() {
    let cfg = legacy_cfg_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    assert_eq!(
        ora.custom_metrics_cache_age(),
        301,
        "custom_metrics_cache_age must match SQLS_MAX_CACHE_AGE from reference config"
    );
}

#[test]
fn test_migrate_reference_config_custom_metrics() {
    let cfg = legacy_cfg_path();
    // the dynamic SQLS_SIDS of the reference config read the variables the
    // legacy plugin sets at runtime; drop them so the expansion does not depend
    // on the environment the test runs in
    let output = run_bin()
        .env_remove("ORACLE_SID")
        .env_remove("SIDS")
        .args(["-M", &cfg])
        .ok()
        .unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    let global: Vec<_> = ora
        .all_sections()
        .iter()
        .filter(|s| s.is_custom_metric())
        .map(|s| (s.item_value().unwrap().as_str(), s.path()))
        .collect();
    #[cfg(windows)]
    // windows ps1 legacy plugin doesn't support custom SQL sections
    assert!(global.is_empty(), "no custom metrics on windows");
    #[cfg(not(windows))]
    {
        use std::path::Path;

        // dynamic SQLS_SIDS (env var / command) expand to nothing during the
        // migration, so their sections are dropped instead of made global
        assert!(
            global.is_empty(),
            "no section may become a global custom metric, got: {global:?}"
        );
        for section in ["mycustomsection2", "mycustomsection3"] {
            assert!(
                stdout.contains(&format!(
                    "# WARNING: {section}: SQLS_SIDS is built by a shell expression that expanded to no SID, skipping custom SQL section; assign the intended instances manually\n"
                )),
                "got: {stdout}"
            );
            assert!(
                !stdout.contains(&format!("- {section}:")),
                "the dropped section must not reach the config, got: {stdout}"
            );
        }

        // static SQLS_SIDS → custom_metrics on the matching instances,
        // MYINST3 exists (REMOTE_INSTANCE_1), MYINST2 is created for the metric
        let custom_metrics_of = |sid: &str| -> Vec<(String, Option<&Path>)> {
            ora.instances()
                .iter()
                .find(|i| {
                    i.standalone_sid().map(|s| s.to_string()).as_deref() == Some(sid)
                        || i.alias().as_ref().map(|a| a.to_string()).as_deref() == Some(sid)
                })
                .unwrap_or_else(|| panic!("instance {sid} not found"))
                .custom_metrics()
                .iter()
                .map(|s| (s.item_value().unwrap().as_str().to_string(), s.path()))
                .collect()
        };
        assert_eq!(
            custom_metrics_of("MYINST3"),
            [
                // SQLS_ITEM_NAME renames mycustomsection1 to my_item
                (
                    "my_item".to_string(),
                    Some(Path::new("/etc/check_mk/MyCustomSQL.sql"))
                ),
                (
                    "mycustomsection4".to_string(),
                    Some(Path::new("custom_sql_2.sql"))
                ),
                // SQLS_SIDS=REMOTE_INSTANCE_1 addresses the same instance by
                // the name of its variable
                (
                    "mycustomsection6".to_string(),
                    Some(Path::new("custom_sql_3.sql"))
                ),
            ]
        );
        assert_eq!(
            custom_metrics_of("MYINST2"),
            [(
                "mycustomsection4".to_string(),
                Some(Path::new("custom_sql_2.sql"))
            )]
        );

        // SQLS_TNSALIAS pins the metric to the aliased instance, and its
        // SQLS_SIDS is preserved as the SID of that same entry
        assert_eq!(
            custom_metrics_of("TNS"),
            [(
                "mycustomsection5".to_string(),
                Some(Path::new("custom_sql_2.sql"))
            )]
        );
        assert!(
            stdout.contains("      - sid: ALIASED_SID\n        alias: TNS\n"),
            "SQLS_SIDS and SQLS_TNSALIAS must both be migrated, got: {stdout}"
        );
        assert!(
            stdout.contains(
                "# WARNING: mycustomsection5: SQLS_SIDS 'ALIASED_SID' is migrated next to SQLS_TNSALIAS 'TNS', but the instance is resolved by its alias, so the SID no longer restricts the section\n"
            ),
            "got: {stdout}"
        );
        assert!(
            !stdout.contains("- sid: REMOTE_INSTANCE_"),
            "a REMOTE_INSTANCE_* reference must not become an own instance, got: {stdout}"
        );
    }
}

// windows ps1 legacy plugin doesn't support custom SQL sections
#[cfg(not(windows))]
#[test]
fn test_migrate_custom_sql_unknown_remote_instance() {
    let tmp = tempfile::tempdir().unwrap();
    let dir = tmp.path();
    let cfg = dir.join("mk_oracle.cfg");
    fs::write(
        &cfg,
        r#"DBUSER='user:pass'
REMOTE_INSTANCE_KNOWN='user:pass::remotehost:1521::PRODSID:11.2'
SQLS_SECTIONS="dangling partly"
dangling () {
    SQLS_SIDS="REMOTE_INSTANCE_GONE"
    SQLS_SQL="a.sql"
}
partly () {
    SQLS_SIDS="REMOTE_INSTANCE_GONE,REMOTE_INSTANCE_KNOWN"
    SQLS_SQL="b.sql"
}
"#,
    )
    .unwrap();

    let output = run_bin().args(["-M", cfg.to_str().unwrap()]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    assert!(
        stdout.contains(
            "# WARNING: dangling: SQLS_SIDS references 'REMOTE_INSTANCE_GONE', but no such remote instance is defined, ignoring it\n"
        ),
        "got: {stdout}"
    );
    assert!(
        stdout.contains(
            "# WARNING: dangling: no instance left to run on, skipping custom SQL section\n"
        ),
        "got: {stdout}"
    );
    assert!(
        !stdout.contains("- sid: REMOTE_INSTANCE_"),
        "the unresolvable reference must not become an instance, got: {stdout}"
    );

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    assert!(
        ora.all_sections().iter().all(|s| !s.is_custom_metric()),
        "a dropped section must not become a global custom metric"
    );
    let instance = ora
        .instances()
        .iter()
        .find(|i| i.standalone_sid().map(|s| s.to_string()).as_deref() == Some("PRODSID"))
        .expect("the remote instance must be migrated");
    let metrics: Vec<_> = instance
        .custom_metrics()
        .iter()
        .map(|s| s.item_value().unwrap().as_str().to_string())
        .collect();
    assert_eq!(
        metrics,
        ["partly"],
        "a section keeping one valid reference stays on that instance"
    );
}

// windows ps1 legacy plugin doesn't support custom SQL sections
#[cfg(not(windows))]
#[test]
fn test_migrate_custom_sql_tnsalias_with_sids() {
    let tmp = tempfile::tempdir().unwrap();
    let dir = tmp.path();
    let cfg = dir.join("mk_oracle.cfg");
    fs::write(
        &cfg,
        r#"DBUSER='user:pass'
SQLS_SECTIONS="Invalid1 Invalid2 Ambiguous"
Invalid1 () {
    SQLS_TNSALIAS=NORMALDB_ALIAS
    SQLS_SIDS=NORMALDB
    SQLS_SQL=invalid_objects1.sql
}
Invalid2 () {
    SQLS_TNSALIAS=ORCLCDB_ALIAS
    SQLS_SIDS=ORCLCDB
    SQLS_SQL=invalid_objects2.sql
}
Ambiguous () {
    SQLS_TNSALIAS=SHARED_ALIAS
    SQLS_SIDS="ONE,TWO"
    SQLS_SQL=ambiguous.sql
}
"#,
    )
    .unwrap();

    let output = run_bin().args(["-M", cfg.to_str().unwrap()]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    // each section keeps its own SID next to its alias instead of being
    // collected under an alias-only instance
    for (sid, alias, section, sql) in [
        ("NORMALDB", "NORMALDB_ALIAS", "Invalid1", "invalid_objects1"),
        ("ORCLCDB", "ORCLCDB_ALIAS", "Invalid2", "invalid_objects2"),
    ] {
        assert!(
            stdout.contains(&format!(
                "      - sid: {sid}\n        alias: {alias}\n        custom_metrics:\n          - {section}:\n              path: {sql}.sql\n"
            )),
            "got: {stdout}"
        );
        assert!(
            stdout.contains(&format!(
                "# WARNING: {section}: SQLS_SIDS '{sid}' is migrated next to SQLS_TNSALIAS '{alias}', but the instance is resolved by its alias, so the SID no longer restricts the section\n"
            )),
            "got: {stdout}"
        );
    }

    // several SIDs cannot identify one aliased instance: the alias stays alone,
    // but the loss is reported instead of happening silently
    assert!(
        stdout.contains("      - alias: SHARED_ALIAS\n"),
        "got: {stdout}"
    );
    assert!(
        stdout.contains(
            "# WARNING: Ambiguous: SQLS_SIDS 'ONE, TWO' cannot be kept next to SQLS_TNSALIAS 'SHARED_ALIAS', the instance is resolved by its alias alone; verify that the alias connects to the intended database\n"
        ),
        "got: {stdout}"
    );

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    let aliased: Vec<String> = ora
        .instances()
        .iter()
        .filter_map(|i| i.alias().as_ref().map(|a| a.to_string()))
        .collect();
    assert_eq!(
        aliased,
        ["NORMALDB_ALIAS", "ORCLCDB_ALIAS", "SHARED_ALIAS"],
        "every alias must get exactly one instance"
    );
}

// windows ps1 legacy plugin doesn't support custom SQL sections
#[cfg(not(windows))]
#[test]
fn test_migrate_custom_sql_dynamic_sids() {
    let tmp = tempfile::tempdir().unwrap();
    let dir = tmp.path();
    let cfg = dir.join("mk_oracle.cfg");
    // "inherited" takes the top-level SQLS_SIDS, which reads a variable the
    // legacy plugin only defines at runtime
    fs::write(
        &cfg,
        r#"DBUSER='user:pass'
SQLS_SIDS="$(echo "$SIDS" | paste -sd,)"
SQLS_SECTIONS="expanded inherited"
expanded () {
    SQLS_SIDS=$(echo "PROD1 PROD2")
    SQLS_SQL="a.sql"
}
inherited () {
    SQLS_SQL="b.sql"
}
"#,
    )
    .unwrap();

    let output = run_bin()
        .env_remove("SIDS")
        .args(["-M", cfg.to_str().unwrap()])
        .ok()
        .unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    assert!(
        stdout.contains(
            "# WARNING: expanded: SQLS_SIDS is built by a shell expression, which cannot be migrated reliably; using the SIDs it expanded to: PROD1, PROD2\n"
        ),
        "got: {stdout}"
    );
    assert!(
        stdout.contains(
            "# WARNING: inherited: SQLS_SIDS is built by a shell expression that expanded to no SID, skipping custom SQL section; assign the intended instances manually\n"
        ),
        "got: {stdout}"
    );

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    assert!(
        ora.all_sections().iter().all(|s| !s.is_custom_metric()),
        "an unresolved expression must not become a global custom metric"
    );
    let metrics_of = |sid: &str| -> Vec<String> {
        ora.instances()
            .iter()
            .find(|i| i.standalone_sid().map(|s| s.to_string()).as_deref() == Some(sid))
            .unwrap_or_else(|| panic!("instance {sid} not found in: {stdout}"))
            .custom_metrics()
            .iter()
            .map(|s| s.item_value().unwrap().as_str().to_string())
            .collect()
    };
    assert_eq!(metrics_of("PROD1"), ["expanded"]);
    assert_eq!(metrics_of("PROD2"), ["expanded"]);
}

// windows ps1 legacy plugin doesn't support custom SQL sections
#[cfg(not(windows))]
#[test]
fn test_migrate_custom_sql_warnings() {
    let tmp = tempfile::tempdir().unwrap();
    let dir = tmp.path();
    fs::write(dir.join("plain.sql"), "SELECT * FROM dual;\n").unwrap();
    fs::write(dir.join("block.sql"), "BEGIN\n  NULL;\nEND;\n").unwrap();

    let dir_str = dir.to_str().unwrap();
    let cfg = dir.join("mk_oracle.cfg");
    fs::write(
        &cfg,
        format!(
            r#"DBUSER='user:pass'
SQLS_SECTIONS="plain block missing"
plain () {{
    SQLS_DIR="{dir_str}"
    SQLS_SQL="plain.sql"
}}
block () {{
    SQLS_DIR="{dir_str}"
    SQLS_SQL="block.sql"
}}
missing () {{
    SQLS_DIR="{dir_str}"
    SQLS_SQL="missing.sql"
}}
"#
        ),
    )
    .unwrap();

    let output = run_bin().args(["-M", cfg.to_str().unwrap()]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(
        !stdout.contains("# WARNING: plain:"),
        "readable plain SQL must not warn, got: {stdout}"
    );
    assert!(
        stdout.contains(&format!(
            "# WARNING: block: SQL file '{dir_str}/block.sql' contains a PL/SQL block"
        )),
        "got: {stdout}"
    );
    assert!(
        stdout.contains(&format!(
            "# WARNING: missing: cannot read SQL file '{dir_str}/missing.sql'"
        )),
        "got: {stdout}"
    );
}

/// A `SQLS_PARAMETERS` written across several lines, as in the legacy
/// documentation, must still be seen by the migration: the parameters cannot be
/// migrated, so every section using them has to be reported.
// windows ps1 legacy plugin doesn't support custom SQL sections
#[cfg(not(windows))]
#[test]
fn test_migrate_warns_on_multiline_custom_sql_parameters() {
    let tmp = tempfile::tempdir().unwrap();
    let dir = tmp.path();
    fs::write(dir.join("invalid_objects.sql"), "SELECT * FROM dual\n").unwrap();

    let dir_str = dir.to_str().unwrap();
    let cfg = dir.join("mk_oracle.cfg");
    fs::write(
        &cfg,
        format!(
            r#"DBUSER='user:pass'
VAR_IFILE="/tmp/ifile.txt"
SQLS_SECTIONS="multiline plain"
multiline () {{
    SQLS_DIR="{dir_str}"
    SQLS_SQL="invalid_objects.sql"
    SQLS_PARAMETERS="
        DEFINE VAR_IFILE = \"${{VAR_IFILE}}\"
    "
}}
plain () {{
    SQLS_DIR="{dir_str}"
    SQLS_SQL="invalid_objects.sql"
}}
"#
        ),
    )
    .unwrap();

    let output = run_bin().args(["-M", cfg.to_str().unwrap()]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(
        stdout.contains("# WARNING: multiline: SQLS_PARAMETERS is not supported"),
        "got: {stdout}"
    );
    assert!(
        !stdout.contains("# WARNING: plain:"),
        "a section without SQLS_PARAMETERS must not warn, got: {stdout}"
    );
    // the value is folded into one line, so its continuation lines cannot be
    // mistaken for further variables
    let extracted = stdout
        .lines()
        .find(|l| l.starts_with("# SQLS.multiline.SQLS_PARAMETERS "))
        .unwrap_or_else(|| panic!("SQLS_PARAMETERS not extracted, got: {stdout}"));
    assert!(
        extracted.contains(r#"DEFINE VAR_IFILE = "/tmp/ifile.txt""#),
        "the whole value belongs to one line, got: {extracted}"
    );
    assert!(
        !stdout.contains("# DEFINE "),
        "a continuation line must not become a variable of its own, got: {stdout}"
    );
    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    let mut metrics: Vec<String> = ora
        .all_sections()
        .iter()
        .filter(|s| s.is_custom_metric())
        .map(|s| s.item_value().unwrap().as_str().to_string())
        .collect();
    metrics.sort();
    assert_eq!(
        metrics,
        ["multiline", "plain"],
        "the sections are migrated regardless"
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
    // EXCLUDE_AAA / EXCLUDE_BBB name sections, not instances, so they must not
    // reach the instance-level exclude list.
    assert_eq!(exclude, &["XE2"], "exclude must match SKIP_SIDS only");
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
    // custom metrics are appended to sections; covered by
    // test_migrate_reference_config_custom_metrics
    let sections: Vec<_> = ora
        .all_sections()
        .iter()
        .filter(|s| !s.is_custom_metric())
        .collect();

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
fn test_migrate_no_tnsalias_omits_instances_and_uses_discovery() {
    let cfg = legacy_cfg_no_tnsalias_path();
    let output = run_bin().args(["-M", &cfg]).ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();

    // A bare DBUSER without SID or TNS alias must not synthesize an instance
    // (it previously emitted a bogus literal `$ORACLE_SID`); the SID from
    // ONLY_SIDS drives discovery instead. Assert on structural YAML keys, not
    // the bare word "alias", which also appears in the echoed source filename.
    assert!(
        !stdout.contains("instances:"),
        "no instance block expected, got: {stdout}"
    );
    assert!(
        !stdout.contains("alias:"),
        "no alias field expected, got: {stdout}"
    );
    assert!(
        !stdout.contains("- sid"),
        "no SID instance expected, got: {stdout}"
    );
    assert!(
        stdout.contains("include: [XE]"),
        "ONLY_SIDS must drive discovery, got: {stdout}"
    );

    let config = mk_oracle::config::OracleConfig::load_str(&stdout)
        .expect("migrated output must be valid YAML");
    let ora = config.ora_sql().expect("must have oracle config");
    assert!(
        ora.instances().is_empty(),
        "bare DBUSER must not produce an explicit instance"
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

#[test]
fn test_connection_olr_loc_parsing() {
    use mk_oracle::config::connection::Connection;
    use mk_oracle::config::yaml::test_tools::create_yaml;
    use std::path::PathBuf;

    let tmp = tempfile::tempdir().expect("create temp dir");
    let crs_home = tmp.path().join("grid");
    fs::create_dir(&crs_home).expect("create crs_home dir");

    let olr_loc_path = tmp.path().join("olr.loc");
    fs::write(
        &olr_loc_path,
        format!(
            "olrconfig_loc={0}\ncrs_home={1}\n",
            tmp.path().display(),
            crs_home.display()
        ),
    )
    .expect("write olr.loc");

    let olr_loc_yaml = olr_loc_path.to_str().unwrap().replace('\\', "/");
    let yaml_str = format!(
        "connection:\n  hostname: \"localhost\"\n  oracle_local_registry: \"{olr_loc_yaml}\"\n"
    );
    let conn = Connection::from_yaml(&create_yaml(&yaml_str))
        .expect("valid YAML")
        .expect("connection present");

    let grid = conn.grid().expect("Grid Infrastructure must be detected");
    assert_eq!(grid.crs_home(), crs_home);
    assert_eq!(
        conn.oracle_local_registry(),
        Some(&PathBuf::from(&olr_loc_yaml))
    );
}

const BAKERY_YML: &str = r#"
oracle:
  main:
    connection:
      hostname: bakery-host
      port: 1521
    authentication:
      username: u
"#;

fn merged_hostname(merged: &MergedConfig) -> String {
    let config = OracleConfig::from_yaml(merged.config.as_ref().unwrap()).unwrap();
    config.ora_sql().unwrap().conn().hostname().to_string()
}

#[test]
fn test_merge_configs_merges_user() {
    let tmp = tempfile::tempdir().unwrap();
    let bakery = tmp.path().join("mk-oracle.yml");
    let user = tmp.path().join("user-mk-oracle.yml");
    fs::write(&bakery, BAKERY_YML).unwrap();
    fs::write(
        &user,
        "oracle:\n  main:\n    connection:\n      hostname: user-host\n",
    )
    .unwrap();

    let merged = merge_configs(&bakery, &user).unwrap();
    // user overrides hostname (port etc. inherited; see merge.rs unit tests)
    assert_eq!(merged_hostname(&merged), "user-host");
    assert!(merged
        .overrides
        .contains(&"oracle.main.connection.hostname".to_string()));
    assert!(merged.notes.is_empty());
}

#[test]
fn test_merge_configs_bakery_only() {
    let tmp = tempfile::tempdir().unwrap();
    let bakery = tmp.path().join("mk-oracle.yml");
    fs::write(&bakery, BAKERY_YML).unwrap();

    let merged = merge_configs(&bakery, &tmp.path().join("absent.yml")).unwrap();
    assert_eq!(merged_hostname(&merged), "bakery-host");
    assert!(merged.overrides.is_empty());
    assert!(merged.notes.is_empty());
}

#[test]
fn test_merge_configs_user_only() {
    let tmp = tempfile::tempdir().unwrap();
    let user = tmp.path().join("user-mk-oracle.yml");
    fs::write(&user, BAKERY_YML).unwrap();

    let merged = merge_configs(&tmp.path().join("absent.yml"), &user).unwrap();
    assert_eq!(merged_hostname(&merged), "bakery-host");
    assert!(merged.overrides.is_empty());
}

#[test]
fn test_merge_configs_ignores_broken_user() {
    let tmp = tempfile::tempdir().unwrap();
    let bakery = tmp.path().join("mk-oracle.yml");
    let user = tmp.path().join("user-mk-oracle.yml");
    fs::write(&bakery, BAKERY_YML).unwrap();
    // Unterminated quoted scalar -> YAML parse error.
    fs::write(&user, "oracle:\n  main: \"unterminated\n").unwrap();

    let merged = merge_configs(&bakery, &user).unwrap();
    // bakery config is used as-is, the broken user file is just noted
    assert_eq!(merged_hostname(&merged), "bakery-host");
    assert!(merged.overrides.is_empty());
    assert_eq!(merged.notes.len(), 1);
    assert!(merged.notes[0].contains("user config"));
}

#[test]
fn test_merge_configs_none_when_both_missing() {
    let tmp = tempfile::tempdir().unwrap();
    let merged = merge_configs(
        &tmp.path().join("no-bakery.yml"),
        &tmp.path().join("no-user.yml"),
    )
    .unwrap();
    assert!(merged.config.is_none());
}

/// `tnsnames.ora` aliases are read from disk, and an `IFILE` include is followed:
/// its aliases are appended after the ones of the including file, while `IFILE`
/// itself is no alias. A relative include resolves against the including file.
#[test]
fn test_parse_tns_names_ora_follows_ifile() {
    let tmp = tempfile::tempdir().unwrap();
    let main = tmp.path().join("tnsnames.ora");
    std::fs::write(
        &main,
        "IFILE = included.ora\nOWN = (ADDRESS = (HOST = own.example.net)(PORT = 1521))\n",
    )
    .unwrap();
    std::fs::write(
        tmp.path().join("included.ora"),
        "FROM_INCLUDE = (ADDRESS = (HOST = inc.example.net)(PORT = 1522))\n",
    )
    .unwrap();

    let entries = parse_tns_names_ora(&main).expect("the written file must be readable");

    assert_eq!(
        entries
            .iter()
            .map(|e| (
                e.alias.to_string(),
                e.host_name.as_ref().map(ToString::to_string),
                e.port.as_ref().map(|p| p.value()),
            ))
            .collect::<Vec<_>>(),
        vec![
            (
                "OWN".to_string(),
                Some("own.example.net".to_string()),
                Some(1521)
            ),
            (
                "FROM_INCLUDE".to_string(),
                Some("inc.example.net".to_string()),
                Some(1522)
            ),
        ]
    );
}

/// Two files including each other must terminate: the depth budget stops the
/// recursion instead of exhausting the stack. Each pass adds the aliases it
/// finds, so the result is bounded but non-empty.
#[test]
fn test_parse_tns_names_ora_stops_on_an_ifile_cycle() {
    let tmp = tempfile::tempdir().unwrap();
    let first = tmp.path().join("first.ora");
    let second = tmp.path().join("second.ora");
    std::fs::write(
        &first,
        "IFILE = second.ora\nFIRST = (ADDRESS = (HOST = first.example.net)(PORT = 1521))\n",
    )
    .unwrap();
    std::fs::write(
        &second,
        "IFILE = first.ora\nSECOND = (ADDRESS = (HOST = second.example.net)(PORT = 1522))\n",
    )
    .unwrap();

    // Returning at all is the assertion: an unbounded walk would never get here.
    let entries = parse_tns_names_ora(&first).expect("the written file must be readable");

    let names: Vec<String> = entries.iter().map(|e| e.alias.to_string()).collect();
    assert!(
        names.len() > 1 && names.len() < 32,
        "the cycle must be cut, not walked forever: {names:?}"
    );
    assert_eq!(
        names[0], "FIRST",
        "the including file comes first: {names:?}"
    );
    assert!(
        names.iter().all(|n| n == "FIRST" || n == "SECOND"),
        "only the two aliases of the cycle may appear: {names:?}"
    );
}
