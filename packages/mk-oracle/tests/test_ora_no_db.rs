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

//! Component tests that require no database at all: runtime/SID
//! detection, plugin creation, configuration and SQL-file resolution.
//! This is the only component test binary executed on hosts without
//! access to a test database (e.g. the Solaris and AIX test machines).

use mk_oracle::config::authentication::Authentication;
use mk_oracle::config::connection::{setup_wallet_environment, Connection};
use mk_oracle::config::grid::GridInfrastructure;
use mk_oracle::config::ora_sql::CustomInstance;
use mk_oracle::config::target::{TargetId, TargetIdBuilder};
use mk_oracle::config::yaml::test_tools::create_yaml;
use mk_oracle::config::OracleConfig;
use mk_oracle::ora_sql::backend::ClosedSpot;
use mk_oracle::ora_sql::instance::{
    calc_custom_spots, filter_spots_by_oracle_home, local_tns_aliases, TNS_NAMES_FILE,
};
use mk_oracle::platform::get_local_instances;
use mk_oracle::setup::{
    contains_oracle_client_lib, create_plugin, detect_factory_runtime, detect_host_runtime,
    detect_runtime, Env, CLIENT_LIB_NAME, TNS_ADMIN_ENV_VAR,
};
use mk_oracle::types::{EnvVarName, UseHostClient};
use mk_oracle::types::{InstanceAlias, InstanceName, LocalInstance};
use std::collections::HashSet;

/// An Oracle client is installed on this machine: an `ORACLE_HOME` or an
/// oratab/registry entry whose home contains the Oracle client library.
fn local_oracle_client_present() -> bool {
    fn home_has_client(home: &std::path::Path) -> bool {
        let candidate = home.join(if cfg!(windows) { "bin" } else { "lib" });
        candidate.is_dir() && contains_oracle_client_lib(&candidate)
    }
    std::env::var("ORACLE_HOME")
        .is_ok_and(|v| !v.is_empty() && home_has_client(std::path::Path::new(&v)))
        || get_local_instances()
            .unwrap_or_default()
            .iter()
            .any(|local| home_has_client(&local.home))
}

#[test]
fn test_detect_host_runtime() {
    let local_exists = local_oracle_client_present();
    if local_exists {
        assert!(detect_host_runtime().is_some());
    } else {
        assert!(detect_host_runtime().is_none());
    }
}

#[test]
fn test_contains_oracle_client_lib() {
    let dir = tempfile::tempdir().unwrap();
    assert!(!contains_oracle_client_lib(dir.path()));
    #[cfg(unix)]
    // versioned library without the unversioned symlink
    let lib_name = format!("{CLIENT_LIB_NAME}.21.1");
    #[cfg(windows)]
    let lib_name = CLIENT_LIB_NAME.to_string();
    std::fs::File::create(dir.path().join(lib_name)).unwrap();
    assert!(contains_oracle_client_lib(dir.path()));
}

#[test]
fn test_detect_factory_runtime_without_client_lib() {
    let lib_dir = tempfile::tempdir().unwrap();
    let runtime = lib_dir.path().join("plugins/packages/mk-oracle");
    std::fs::create_dir_all(&runtime).unwrap();
    // the directory exists but has no client library -> rejected
    assert!(detect_factory_runtime(lib_dir.path()).is_none());

    std::fs::File::create(runtime.join(CLIENT_LIB_NAME)).unwrap();
    assert_eq!(detect_factory_runtime(lib_dir.path()), Some(runtime));
}

fn base_dir() -> std::path::PathBuf {
    std::path::PathBuf::from(std::env::var("MK_CONFDIR").unwrap_or_else(|_| {
        std::env::current_dir()
            .unwrap()
            .into_os_string()
            .into_string()
            .unwrap()
    }))
}

/// Directory inside the test fixture tree that contains the Oracle client
/// library (populated by the run script / run.ps1).
fn client_runtime_dir() -> std::path::PathBuf {
    let dir = base_dir().join("runtimes/plugins/packages/mk-oracle");
    if cfg!(windows) {
        dir.join("runtime")
    } else {
        dir
    }
}

#[test]
fn test_detect_runtime_with_runtime() {
    // the agent library directory below which a runtime exists
    let good_path = base_dir().join("runtimes");
    let lib_dir = Some(good_path.as_path());
    let local_exists = local_oracle_client_present();

    // Never
    assert!(detect_runtime(&UseHostClient::Never, None, None).is_none()); // no MK_LIBDIR
    assert!(detect_runtime(
        &UseHostClient::Never,
        Some(std::path::Path::new("Hurz")),
        None
    )
    .is_none()); // no such directory
    assert!(detect_runtime(&UseHostClient::Never, lib_dir, None).is_some()); // detected

    // Always
    assert_eq!(
        detect_runtime(&UseHostClient::Always, lib_dir, None).is_some(),
        local_exists
    ); // detected only if local exists(skip factory)
    if local_exists {
        assert!(!detect_runtime(&UseHostClient::Always, lib_dir, None)
            .unwrap()
            .dir
            .into_os_string()
            .into_string()
            .unwrap()
            .contains("mk-oracle")); // path is to host
    }

    // Auto
    let path = detect_runtime(&UseHostClient::Auto, lib_dir, None)
        .unwrap()
        .dir
        .into_os_string()
        .into_string()
        .unwrap();
    assert!(path.contains("mk-oracle")); // detected factory

    // Path:
    // path with a client library -> expected correct path
    let correct_path = client_runtime_dir().into_os_string().into_string().unwrap();
    let path = to_string(detect_runtime(
        &UseHostClient::Path(correct_path.clone()),
        lib_dir,
        None,
    ))
    .unwrap();
    assert_eq!(path, correct_path);

    // existing dir without a client library -> expected nothing
    let lib_less_path = base_dir()
        .join("runtimes")
        .into_os_string()
        .into_string()
        .unwrap();
    assert!(detect_runtime(&UseHostClient::Path(lib_less_path), lib_dir, None).is_none());

    // path is wrong -> expected nothing
    let wrong_path = correct_path + "something-missing";
    let path = detect_runtime(&UseHostClient::Path(wrong_path), lib_dir, None);
    assert!(path.is_none());
}

fn to_string(p: Option<mk_oracle::setup::ClientRuntime>) -> Option<String> {
    p.map(|r| r.dir.into_os_string().into_string().unwrap())
}

#[test]
fn test_detect_runtime_without_runtime() {
    // the agent library directory below which no runtime exists
    let bad_path = base_dir().join("runtimes-wrong");
    let lib_dir = Some(bad_path.as_path());
    let local_installation = local_oracle_client_present();

    // Never
    assert!(detect_runtime(&UseHostClient::Never, lib_dir, None).is_none());

    // Auto and Always are the same if no runtimes
    // If local exists -> expected path to local client otherwise nothing
    for mode in [UseHostClient::Auto, UseHostClient::Always] {
        let path = to_string(detect_runtime(&mode, lib_dir, None));
        if local_installation {
            eprintln!(
                "Local installation path = {:?} {}",
                path, local_installation
            );
            #[cfg(unix)]
            assert!(path.clone().unwrap().ends_with("bin") || path.unwrap().ends_with("lib"));
            #[cfg(windows)]
            eprintln!("DISABLED! On Windows ");
        } else {
            assert!(path.is_none());
        }
    }

    // Path:
    // path with a client library -> expected correct path
    let correct_path = client_runtime_dir().into_os_string().into_string().unwrap();
    let path = to_string(detect_runtime(
        &UseHostClient::Path(correct_path.clone()),
        lib_dir,
        None,
    ))
    .unwrap();
    assert_eq!(path, correct_path);

    // path is wrong -> expected nothing
    let wrong_path = correct_path + "something-missing";
    let path = detect_runtime(&UseHostClient::Path(wrong_path), lib_dir, None);
    assert!(path.is_none());
}

#[test]
fn test_detect_runtime_env_reports_a_missing_client() {
    use mk_oracle::setup::{detect_runtime_env, RuntimeError};

    // Windows counts only a path with a drive prefix as absolute, and a
    // non-absolute use_host_client falls back to `auto`.
    #[cfg(not(windows))]
    let missing = "/no-such-dir/instantclient";
    #[cfg(windows)]
    let missing = r"C:\no-such-dir\instantclient";

    let cfg = OracleConfig::load_str(&make_config_with_use_host(missing)).unwrap();
    assert_eq!(detect_runtime_env(&cfg), Err(RuntimeError::NotFound));
}

fn make_config_with_use_host(use_host: &str) -> String {
    format!(
        r#"
---
oracle:
  main: # mandatory, defines main SQL check to be executed
    options: # optional
      use_host_client: {} # optional, default: auto, values: auto, never, always, "path-to-oci-lib"
    authentication: # mandatory
      username: "foo" # mandatory if not using wallet, examples: "mydbuser", "c##multitenantuser"
      password: "bar" # optional
    discovery:
       detect: no
    connection: # optional
      service_name: "will not be used"
      hostname: "localhost" # optional, default: "localhost"    "#,
        use_host
    )
}

/// NOT ALL CONDITIONS TESTED
#[test]
fn test_add_runtime_to_path() {
    use mk_oracle::setup::{apply_runtime_env, RuntimeEnv};

    fn exec_add_runtime_to_path(
        cfg: &OracleConfig,
        mk_lib: Option<&std::path::Path>,
        mut_env_var: &EnvVarName,
    ) -> Option<std::path::PathBuf> {
        unsafe {
            std::env::set_var(mut_env_var.to_str(), "xxx");
        }
        let ora_sql = cfg.ora_sql().unwrap();
        let runtime_env = RuntimeEnv {
            runtime_dir: detect_runtime(ora_sql.options().use_host_client(), mk_lib, None)
                .map(|r| r.dir),
            oracle_home: None,
        };
        apply_runtime_env(&runtime_env, Some(mut_env_var.clone()), None)
    }
    let mut_env_var = EnvVarName::from("SOME_PATH_TEST_VAR_XXX".to_string());
    let good_path = base_dir().join("runtimes");
    let good_lib_dir = Some(good_path.as_path());
    let local_db_exists = local_oracle_client_present();
    let good_path_str = good_path.clone().into_os_string().into_string().unwrap();

    // *** AUTO ***
    let cfg = OracleConfig::load_str(&make_config_with_use_host("auto")).unwrap();
    // MK_LIBDIR ABSENT
    // depends on local SQL endpoint, if exist -> found otherwise not
    let result = exec_add_runtime_to_path(&cfg, None, &mut_env_var);
    assert_eq!(result.is_some(), local_db_exists);
    // MK_LIBDIR is good_path
    exec_add_runtime_to_path(&cfg, good_lib_dir, &mut_env_var);
    let var_value = std::env::var(mut_env_var.to_str()).unwrap();
    assert!(var_value.starts_with(good_path_str.as_str()));

    // *** NEVER ***
    let cfg = OracleConfig::load_str(&make_config_with_use_host("never")).unwrap();
    // MK_LIBDIR ABSENT
    assert!(exec_add_runtime_to_path(&cfg, None, &mut_env_var).is_none());
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with("xxx"));

    // MK_LIBDIR is good_path
    exec_add_runtime_to_path(&cfg, good_lib_dir, &mut_env_var);
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(good_path_str.as_str()));

    // *** ALWAYS ***
    let cfg = OracleConfig::load_str(&make_config_with_use_host("always")).unwrap();

    // depends on local SQL endpoint, if exist -> found otherwise not
    let result = exec_add_runtime_to_path(&cfg, None, &mut_env_var);
    assert_eq!(result.is_some(), local_db_exists);
    assert_eq!(
        std::env::var(mut_env_var.to_str())
            .unwrap()
            .starts_with("xxx"),
        !local_db_exists
    );
    // MK_LIBDIR is good_path
    exec_add_runtime_to_path(&cfg, good_lib_dir, &mut_env_var);
    // depends on local SQL endpoint, if exist -> found otherwise not
    assert_eq!(
        exec_add_runtime_to_path(&cfg, good_lib_dir, &mut_env_var).is_some(),
        local_db_exists
    );

    // SOME PATH with a client library
    let some_path = client_runtime_dir().into_os_string().into_string().unwrap();
    let cfg = OracleConfig::load_str(&make_config_with_use_host(some_path.as_str())).unwrap();
    // MK_LIBDIR ABSENT
    exec_add_runtime_to_path(&cfg, None, &mut_env_var);
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(some_path.as_str()));
    // MK_LIBDIR is good_path
    exec_add_runtime_to_path(&cfg, good_lib_dir, &mut_env_var);
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(some_path.as_str()));

    // SOME PATH without a client library is rejected
    let lib_less_path = base_dir().into_os_string().into_string().unwrap();
    let cfg = OracleConfig::load_str(&make_config_with_use_host(lib_less_path.as_str())).unwrap();
    assert!(exec_add_runtime_to_path(&cfg, good_lib_dir, &mut_env_var).is_none());
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with("xxx"));
}

#[cfg(unix)]
fn validate_permissions(file: &std::path::Path, mode: u32) {
    use std::os::unix::fs::PermissionsExt;
    let permissions = std::fs::metadata(file).unwrap().permissions();
    assert_eq!(permissions.mode() & 0o777, mode); // is executable
}

#[cfg(windows)]
fn validate_permissions(_file: &std::path::Path, _mode: u32) {}

#[test]
fn test_create_plugin_sync() {
    let plugin = tempfile::tempdir().unwrap();
    let plugin_dir = plugin.path();
    let ret = create_plugin("a", plugin_dir, None, "--filter sync");
    assert!(plugin_dir.join("a").is_file());
    validate_permissions(&plugin_dir.join("a"), 0o755);
    let content = std::fs::read_to_string(plugin_dir.join("a")).unwrap();
    assert!(content.ends_with(" --filter sync\n"));
    assert!(ret);
}

#[cfg(unix)]
#[test]
fn test_create_plugin_async_custom_metrics() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(300), "--filter async-custom-metrics");
    assert!(ret);
    let content = std::fs::read_to_string(plugin_dir.join("300").join("a")).unwrap();
    assert!(content.ends_with(" --filter async-custom-metrics\n"));
}

#[cfg(unix)]
#[test]
fn test_create_plugin_async() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(!ret); // no plugins, no creation
    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(ret);

    let async_plugin_dir_100 = plugin_dir.join("100");
    let plugin_100_path = async_plugin_dir_100.join("a");
    assert!(plugin_100_path.is_file());
    let content = std::fs::read_to_string(async_plugin_dir_100.join("a")).unwrap();
    assert!(content.ends_with(" --filter async\n"));
    validate_permissions(&plugin_100_path, 0o755);

    let ret = create_plugin("a", &plugin_dir, Some(200), "--filter async");
    assert!(ret);

    let async_plugin_dir_200 = plugin_dir.join("200");
    assert!(async_plugin_dir_200.join("a").is_file());
    let content = std::fs::read_to_string(async_plugin_dir_200.join("a")).unwrap();
    assert!(content.ends_with(" --filter async\n"));
    assert!(!async_plugin_dir_100.join("a").exists()); // file must be deleted
}

#[cfg(windows)]
#[test]
fn test_create_plugin_async() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(!ret); // no plugins dir no success

    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(!ret); // no bakery dir no success

    let bakery_dir = lib_dir.path().join("bakery").to_owned();
    std::fs::create_dir_all(&bakery_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(ret);

    assert!(plugin_dir.join("a").is_file());
    let plugin_content = std::fs::read_to_string(plugin_dir.join("a")).unwrap();
    assert!(plugin_content.ends_with(" --filter async\n"));

    let bakery_content = std::fs::read_to_string(bakery_dir.join("check_mk.bakery.yml")).unwrap();
    assert!(bakery_content.contains("    cache: 100"));
    assert!(bakery_content.contains("  - pattern: $CUSTOM_PLUGINS_PATH$\\a"));
}

#[test]
fn test_find_current_instance_runtime() {
    use mk_oracle::setup::find_env_var_lib_runtime;
    assert!(find_env_var_lib_runtime("HURZ-burz").is_none());
    assert!(find_env_var_lib_runtime("PATH").is_none());
    let db_location = tempfile::tempdir().unwrap();
    let temp_var = "ORACLE_HOME_TEST_VAR";
    unsafe {
        std::env::set_var(temp_var, db_location.path());
    }
    assert!(find_env_var_lib_runtime(temp_var).is_none());
    let lib_path = db_location.path().join("lib");
    std::fs::create_dir_all(&lib_path).unwrap();
    // a lib dir without a client library is rejected
    assert!(find_env_var_lib_runtime(temp_var).is_none());
    let lib_file = if cfg!(windows) {
        "oci.dll"
    } else {
        "libclntsh.so.21.1"
    };
    std::fs::File::create(lib_path.join(lib_file)).unwrap();
    assert_eq!(find_env_var_lib_runtime(temp_var).unwrap(), lib_path);
}

#[test]
fn test_sqlnet_ora_file_creation() {
    use std::env;
    use std::fs;

    let random_var = format!("MK_CONFDIR_TEST_{}", std::process::id());
    let tmp_dir = tempfile::tempdir().expect("create temp dir");
    let tmp_dir_path = tmp_dir.path().to_path_buf();

    unsafe {
        env::set_var(&random_var, &tmp_dir_path);
    }

    setup_wallet_environment(Some(random_var.clone())).unwrap();

    let sqlnet_path = tmp_dir_path.join("sqlnet.ora");
    let content = fs::read_to_string(&sqlnet_path).expect("read sqlnet.ora");

    let expected = format!(
        r#"# Auto-generated by mk-oracle for wallet authentication
NAMES.DIRECTORY_PATH = (TNSNAMES, EZCONNECT)
WALLET_LOCATION = (SOURCE = (METHOD = FILE) (METHOD_DATA = (DIRECTORY = {})))
SQLNET.WALLET_OVERRIDE = TRUE
"#,
        tmp_dir_path.join("oracle_wallet").display()
    );

    assert_eq!(content, expected);
}

mod find_sids {
    use mk_oracle::platform::registry::find_oratab_file;
    use std::io::Write;

    /// Emulates a PMON process: `cat` renamed the way Oracle renames its
    /// background processes and held alive by an open stdin pipe. A test-only
    /// prefix keeps the production mask from discovering it as a real instance.
    #[cfg(unix)]
    #[test]
    fn test_find_sids() {
        use mk_oracle::ora_sql::detect::find_sids_by_processes;
        use std::collections::HashSet;
        use std::os::unix::process::CommandExt;

        const TEST_MASK: &str = r"^(mk_ora_test_pmon_)(.+)$";
        let mut fake_pmon = std::process::Command::new("cat")
            .arg0("mk_ora_test_pmon_MKORATEST")
            .stdin(std::process::Stdio::piped())
            .spawn()
            .expect("failed to spawn the fake PMON process");

        // The scan can catch the child between fork and exec, still carrying the
        // parent's argv, so poll rather than assert on the first attempt.
        let mut sids = HashSet::new();
        for _ in 0..50 {
            sids = find_sids_by_processes(Some(TEST_MASK)).expect("process scan failed");
            if sids.contains("MKORATEST") {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        let _ = fake_pmon.kill();
        let _ = fake_pmon.wait();
        assert!(sids.contains("MKORATEST"));
    }

    #[test]
    fn test_find_oratab_file_not_found() {
        let result = find_oratab_file(Some(&["/nonexistent/path/oratab"]));
        assert!(result.is_err());
        if cfg!(windows) {
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("oratab is not supported on Windows"));
        } else {
            assert!(result.unwrap_err().to_string().contains("oratab not found"));
        }
    }

    #[test]
    fn test_find_oratab_file_found() {
        let tmp_dir = tempfile::tempdir().expect("create temp dir");
        let oratab_path = tmp_dir.path().join("oratab");
        let mut file = std::fs::File::create(&oratab_path).expect("create oratab file");
        writeln!(file, "XE:/opt/oracle/product/21c/dbhomeXE:N # xxx").expect("write to oratab");

        let oratab_str = oratab_path.to_str().unwrap();
        let result = find_oratab_file(Some(&["/nonexistent/path/oratab", oratab_str]));
        if cfg!(windows) {
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("oratab is not supported on Windows"));
        } else {
            assert!(result.is_ok());
            assert_eq!(result.unwrap(), oratab_path);
        }
    }

    /// On Unix, get_instances is the oratab parser. It is still live code, so
    /// it keeps its own coverage: comments, a line without colons, and two
    /// entries.
    #[cfg(unix)]
    #[test]
    fn test_get_instances_parses_oratab() {
        use mk_oracle::platform::registry::get_instances;

        let tmp_dir = tempfile::tempdir().expect("create temp dir");
        let oratab_path = tmp_dir.path().join("oratab");
        let mut file = std::fs::File::create(&oratab_path).expect("create oratab file");
        writeln!(file, " # Comment line").expect("write comment");
        writeln!(file, "INVALID_LINE_NO_COLON").expect("write invalid line");
        writeln!(file, "XE:/opt/oracle/product/21c/dbhomeXE:N # some comment")
            .expect("write XE entry");
        writeln!(file, "ORCL:/opt/oracle/product/19c/dbhome1:Y # nothing")
            .expect("write ORCL entry");

        let instances =
            get_instances(Some(oratab_path.to_str().unwrap().to_string())).expect("read oratab");
        let parsed: Vec<(String, String)> = instances
            .iter()
            .map(|i| (i.name.to_string(), i.home.display().to_string()))
            .collect();
        assert_eq!(
            parsed,
            vec![
                (
                    "XE".to_string(),
                    "/opt/oracle/product/21c/dbhomeXE".to_string()
                ),
                (
                    "ORCL".to_string(),
                    "/opt/oracle/product/19c/dbhome1".to_string()
                ),
            ]
        );
    }
}

/// ORACLE_HOME is only exported by apply_runtime_env, never by detection.
#[cfg(unix)]
#[test]
fn test_add_oracle_home_to_env() {
    use mk_oracle::setup::{apply_runtime_env, RuntimeEnv};
    use mk_oracle::types::EnvVarName;

    let make_env_var = |name: &str| Some(EnvVarName::from(name.to_string()));
    let tmp_dir = tempfile::tempdir().expect("create temp dir");
    let home = tmp_dir.path().join("dbhome");
    let home_lib = home.join("lib");
    std::fs::create_dir_all(&home_lib).expect("create home/lib");

    let env_var = "_MK_TEST_ORACLE_HOME_SET";
    assert!(std::env::var(env_var).is_err());
    let runtime_env = RuntimeEnv {
        runtime_dir: Some(home_lib.clone()),
        oracle_home: Some(home.clone()),
    };
    apply_runtime_env(
        &runtime_env,
        make_env_var("_MK_TEST_RUNTIME_PATH_SET"),
        make_env_var(env_var),
    )
    .expect("apply with a runtime dir");
    assert_eq!(std::env::var(env_var).unwrap(), home.to_str().unwrap());

    // no home at all -> the variable is left alone
    let env_var = "_MK_TEST_ORACLE_HOME_UNSET";
    let runtime_env = RuntimeEnv {
        runtime_dir: Some(home_lib),
        oracle_home: None,
    };
    apply_runtime_env(
        &runtime_env,
        make_env_var("_MK_TEST_RUNTIME_PATH_UNSET"),
        make_env_var(env_var),
    )
    .expect("apply with a runtime dir");
    assert!(std::env::var(env_var).is_err());
}

/// effective_oracle_home is pure: an inherited value wins, otherwise the home
/// comes from the client that was selected, and an Instant Client supplies none.
#[cfg(unix)]
#[test]
fn test_effective_oracle_home() {
    use mk_oracle::setup::{effective_oracle_home, ClientRuntime};

    let in_home = ClientRuntime {
        dir: std::path::PathBuf::from("/u01/dbhome_1/lib"),
        home: Some(std::path::PathBuf::from("/u01/dbhome_1")),
    };
    let instant_client = ClientRuntime {
        dir: std::path::PathBuf::from("/opt/instantclient_21_19"),
        home: None,
    };

    assert_eq!(
        effective_oracle_home(Some(&in_home), None),
        Some(std::path::PathBuf::from("/u01/dbhome_1"))
    );
    assert_eq!(effective_oracle_home(Some(&instant_client), None), None);
    assert_eq!(effective_oracle_home(None, None), None);

    // an inherited value wins over anything the client would supply
    assert_eq!(
        effective_oracle_home(Some(&in_home), Some("/already/set".to_string())),
        Some(std::path::PathBuf::from("/already/set"))
    );
    assert_eq!(
        effective_oracle_home(Some(&instant_client), Some("/already/set".to_string())),
        Some(std::path::PathBuf::from("/already/set"))
    );
}

/// An operator-supplied path is the one client the plug-in has to inspect,
/// because nothing else knows what was pointed at.
#[cfg(unix)]
#[test]
fn test_configured_client_path_reports_its_home() {
    use mk_oracle::setup::detect_runtime;
    use mk_oracle::types::UseHostClient;

    let tmp_dir = tempfile::tempdir().expect("create temp dir");

    // full home: <home>/lib with the client library and <home>/oracore next to it
    let home = tmp_dir.path().join("dbhome_1");
    let home_lib = home.join("lib");
    std::fs::create_dir_all(&home_lib).expect("create home/lib");
    std::fs::write(home_lib.join("libclntsh.so.19.1"), "").expect("create client lib");
    std::fs::create_dir_all(home.join("oracore")).expect("create oracore");
    let found = detect_runtime(
        &UseHostClient::Path(home_lib.to_str().unwrap().to_string()),
        None,
        None,
    )
    .expect("full home accepted");
    assert_eq!(found.dir, home_lib);
    assert_eq!(found.home, Some(home));

    // Instant Client: the library sits in the directory itself -> no home
    let instant_client = tmp_dir.path().join("instantclient_19_19");
    std::fs::create_dir_all(&instant_client).expect("create instant client dir");
    std::fs::write(instant_client.join("libclntsh.so.19.1"), "").expect("create client lib");
    let found = detect_runtime(
        &UseHostClient::Path(instant_client.to_str().unwrap().to_string()),
        None,
        None,
    )
    .expect("instant client accepted");
    assert_eq!(found.dir, instant_client);
    assert_eq!(found.home, None);

    // RPM Instant Client: a lib dir, but no oracore next to it -> no home
    let rpm_lib = tmp_dir.path().join("client64").join("lib");
    std::fs::create_dir_all(&rpm_lib).expect("create client64/lib");
    std::fs::write(rpm_lib.join("libclntsh.so.19.1"), "").expect("create client lib");
    let found = detect_runtime(
        &UseHostClient::Path(rpm_lib.to_str().unwrap().to_string()),
        None,
        None,
    )
    .expect("rpm instant client accepted");
    assert_eq!(found.home, None);
}

// NOTE: Test mutates a process-wide environment variable. The unique prefix
// `_MK_TEST_OCI_DIR` is to minimise collision risk with other parallel tests.
#[test]
fn test_options_use_host_client_with_env_var() {
    #[cfg(not(windows))]
    let (env_val, sep) = ("/opt/oracle/product/19c", "/");
    #[cfg(windows)]
    let (env_val, sep) = (r"C:\oracle\product\19c", r"\");

    let env_var = "_MK_TEST_OCI_DIR";
    unsafe {
        std::env::set_var(env_var, env_val);
    }

    // $VAR/lib — starts with '$' so guard passes; expands to an absolute path
    let cfg =
        OracleConfig::load_str(&make_config_with_use_host(&format!("${env_var}{sep}lib"))).unwrap();
    let options = cfg.ora_sql().unwrap().options();
    assert_eq!(
        options.use_host_client(),
        &UseHostClient::Path(format!("{env_val}{sep}lib"))
    );

    // ${VAR}/lib — brace form, also starts with '$'
    let cfg = OracleConfig::load_str(&make_config_with_use_host(&format!(
        "${{{env_var}}}{sep}lib"
    )))
    .unwrap();
    let options = cfg.ora_sql().unwrap().options();
    assert_eq!(
        options.use_host_client(),
        &UseHostClient::Path(format!("{env_val}{sep}lib"))
    );

    unsafe {
        std::env::remove_var(env_var);
    }
}

/// Public-API level checks of the permission validation.
///
/// Only the short-circuits are asserted here, because they are the only outcomes
/// that do not depend on the environment. Every real decision walks the
/// directories above the path under test, and those are not ours to control:
/// inside Bazel's sandbox `/` itself is owned by `nobody`, so an assertion about
/// a rejection would hold no matter what the logic did. The decision itself is
/// covered by the pure unit tests in `src/permissions_linux.rs` and, as root
/// against a tree owned end to end, by `tests/system/mk_oracle`.
#[cfg(unix)]
mod permissions {
    use mk_oracle::permissions_linux::{is_running_as_root, validate};
    use std::fs;
    use std::os::unix::fs::PermissionsExt;

    #[test]
    fn test_validate_as_non_root_accepts_a_world_writable_runtime() {
        if is_running_as_root() {
            return; // the short-circuit under test does not apply
        }
        let tmp = tempfile::tempdir().expect("create temp dir");
        let lib = tmp.path().join("libclntsh.so.19.1");
        fs::write(&lib, b"").unwrap();
        fs::set_permissions(&lib, fs::Permissions::from_mode(0o666)).unwrap();
        assert!(validate(tmp.path(), true, &[]));
    }
}

/// Component tests for the `path:` key of section / custom-metric YAML config.
/// Tests for resolving a custom-metric's SQL from the YAML `path:` key.
///
/// `path:` can point at an absolute file, an absolute directory, or a path
/// relative to a set of search roots. These tests pin down exactly which file
/// gets read in each case, including version-variant selection and the
/// precedence between `path:` and an inline `sql:`.
///
/// # Fixture files (tests/files/, embedded via `include_str!`)
///
/// Each `.sql` file contains a single trivial query whose payload encodes its
/// own origin, e.g. `select 'details:abs' from dual`, so a test can assert
/// which file was resolved purely from the returned query text.
mod custom_path_tests {
    use mk_oracle::config::ora_sql::Config;
    use mk_oracle::ora_sql::section::Section;
    use mk_oracle::types::{InstanceNumVersion, Tenant};
    use std::path::{Path, PathBuf};
    use tempfile::TempDir;

    // SQL fixture bodies committed under tests/files/, embedded at compile time,
    // the `'details:...'` payload identifies which file was resolved.
    const ABS_SQL: &str = include_str!("files/orasql_abs/abs.sql");
    const DIR_METRIC_SQL: &str = include_str!("files/orasql_abs/dir_metric.sql");
    const WINNER_SQL: &str = include_str!("files/orasql_abs/winner.sql");
    const VER_V0_SQL: &str = include_str!("files/orasql_abs/ver_metric.sql");
    const VER_V12_SQL: &str = include_str!("files/orasql_abs/ver_metric@12010000.sql");
    const VER_V19_SQL: &str = include_str!("files/orasql_abs/ver_metric@19000000.sql");
    const RUNTIME_BOTH_SQL: &str = include_str!("files/orasql_runtime/both.sql");
    const RUNTIME_JOBS_SQL: &str = include_str!("files/orasql_runtime/jobs.sql");
    const CONFIG_BOTH_SQL: &str = include_str!("files/orasql_config/both.sql");
    const CONFIG_MAIN_ONLY_SQL: &str = include_str!("files/orasql_config/main_only.sql");

    struct Fixtures {
        _root: TempDir,
        abs_dir: PathBuf,
        /// Injected relative-`path:` search roots: runtime first (so it wins on
        /// collisions), config second — mirroring production order.
        search_dirs: Vec<PathBuf>,
    }

    fn write(dir: &Path, name: &str, body: &str) {
        std::fs::write(dir.join(name), body).expect("write fixture");
    }

    /// Materialise the embedded fixtures into a temp dir:
    /// `orasql_abs/` for absolute-path tests, plus
    /// `orasql_runtime/` and `orasql_config/` as the two relative search roots
    /// (note `both.sql` lives in both, to exercise collision precedence).
    fn fixtures() -> Fixtures {
        let root = tempfile::tempdir().expect("tempdir");
        let abs_dir = root.path().join("orasql_abs");
        let runtime_dir = root.path().join("orasql_runtime");
        let config_dir = root.path().join("orasql_config");
        for d in [&abs_dir, &runtime_dir, &config_dir] {
            std::fs::create_dir_all(d).expect("create fixture dir");
        }

        // Absolute-path test files.
        write(&abs_dir, "abs.sql", ABS_SQL);
        write(&abs_dir, "dir_metric.sql", DIR_METRIC_SQL);
        write(&abs_dir, "winner.sql", WINNER_SQL);
        // Version-variant set: bare stem + two @<version> variants.
        write(&abs_dir, "ver_metric.sql", VER_V0_SQL);
        write(&abs_dir, "ver_metric@12010000.sql", VER_V12_SQL);
        write(&abs_dir, "ver_metric@19000000.sql", VER_V19_SQL);

        // Relative-path search roots. `both.sql` is intentionally present in
        // both roots so a test can prove the runtime root shadows the config one.
        write(&runtime_dir, "both.sql", RUNTIME_BOTH_SQL);
        // Named after the builtin `jobs` section: overrides its factory query.
        write(&runtime_dir, "jobs.sql", RUNTIME_JOBS_SQL);
        write(&config_dir, "both.sql", CONFIG_BOTH_SQL);
        write(&config_dir, "main_only.sql", CONFIG_MAIN_ONLY_SQL);

        Fixtures {
            _root: root,
            abs_dir,
            search_dirs: vec![runtime_dir, config_dir],
        }
    }

    fn section_from_yaml(yaml: &str, item_or_name: &str) -> Section {
        let config = Config::from_string(yaml)
            .expect("config parses")
            .expect("config present");
        let cfg = config
            .all_sections()
            .iter()
            .find(|s| {
                s.item_value()
                    .map(|iv| iv.as_str() == item_or_name)
                    .unwrap_or(false)
                    || s.name().as_str() == item_or_name
            })
            .expect("section not found in config");
        Section::new(cfg, Some(0), config.options())
    }

    /// First resolved query body for `section` at `version`, using `search_dirs`
    /// as the relative-`path:` search roots (irrelevant for absolute paths).
    ///
    /// `Cdb`, not `All`: an `All` argument matches only `All`-tagged entries and
    /// would bypass the tenant-specific jobs query.
    fn first_query(section: &Section, version: u32, search_dirs: &[PathBuf]) -> Option<String> {
        section
            .find_queries_with_search_dirs(
                InstanceNumVersion::from(version),
                Tenant::Cdb,
                &[],
                search_dirs,
            )
            .map(|queries| queries[0].as_str().to_owned())
    }

    #[test]
    fn test_path_absolute_file_reads_file_contents() {
        // `path:` points straight at orasql_abs/abs.sql. An absolute *file* path
        // is read; the item name ("whatever_name") is ignored. Expect
        // the body of abs.sql -> 'details:abs'.
        let fx = fixtures();
        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - whatever_name:
          path: '{}'
"#,
            fx.abs_dir.join("abs.sql").display()
        );
        let section = section_from_yaml(&yaml, "whatever_name");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:abs' from dual")
        );
    }

    #[test]
    fn test_path_absolute_directory_uses_item_name_as_stem() {
        // `path:` points at the orasql_abs/ *directory*, not a file. The file
        // stem is then derived from the custom-metric item name, so item
        // "dir_metric" resolves to orasql_abs/dir_metric.sql -> 'details:dir'.
        let fx = fixtures();
        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - dir_metric:
          path: '{}'
"#,
            fx.abs_dir.display()
        );
        let section = section_from_yaml(&yaml, "dir_metric");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:dir' from dual")
        );
    }

    #[test]
    fn test_path_version_variant_selected_by_instance_version() {
        // Item "ver_metric" against the orasql_abs/ directory, which holds three
        // variants for the same stem:
        //   ver_metric.sql           -> 'details:v0'  (bare, no version floor)
        //   ver_metric@12010000.sql  -> 'details:v12' (applies for version >= 12.1)
        //   ver_metric@19000000.sql  -> 'details:v19' (applies for version >= 19)
        // The highest @<version> floor that the instance version satisfies wins,
        // falling back to the bare stem below the lowest floor. Asserted below
        // for instance versions 10.0, 14.0 and 23.0.
        let fx = fixtures();
        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - ver_metric:
          path: '{}'
"#,
            fx.abs_dir.display()
        );
        let section = section_from_yaml(&yaml, "ver_metric");
        assert_eq!(
            first_query(&section, 10_00_00_00, &[]).as_deref(),
            Some("select 'details:v0' from dual"),
            "below the lowest @-variant falls back to the bare stem"
        );
        assert_eq!(
            first_query(&section, 14_00_00_00, &[]).as_deref(),
            Some("select 'details:v12' from dual"),
            "between the 12.1 and 19 variants selects the 12.1 one"
        );
        assert_eq!(
            first_query(&section, 23_00_00_00, &[]).as_deref(),
            Some("select 'details:v19' from dual"),
            "at/above the 19 variant selects it"
        );
    }

    #[test]
    fn test_path_relative_resolved_via_injected_search_dirs() {
        // A *relative* `path:` is looked up against the injected search roots, in
        // order: orasql_runtime/ first, then orasql_config/. Covers two cases:
        // a collision (file in both roots) and a file present only in the second.
        let fx = fixtures();
        let dirs = &fx.search_dirs;

        // `both.sql` exists in *both* roots (runtime -> 'details:runtime',
        // config -> 'details:config'); the first (runtime) root must win.
        let collision_yaml = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - both_metric:
          path: "both.sql"
"#;
        let section = section_from_yaml(collision_yaml, "both_metric");
        assert_eq!(
            first_query(&section, 0, dirs).as_deref(),
            Some("select 'details:runtime' from dual"),
            "runtime search dir must win over config on collision"
        );

        // `main_only.sql` exists only in the second (config) root, so lookup must
        // fall through past orasql_runtime/ to orasql_config/ -> 'details:config-only'.
        let config_only_yaml = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - config_metric:
          path: "main_only.sql"
"#;
        let section = section_from_yaml(config_only_yaml, "config_metric");
        assert_eq!(
            first_query(&section, 0, dirs).as_deref(),
            Some("select 'details:config-only' from dual"),
            "must fall through to the config search dir"
        );
    }

    #[test]
    fn test_builtin_section_overridden_by_search_dir_file_without_path() {
        // A builtin section with *no* `path:` key still using the search
        // roots: the unset path defaults to "" (a relative path), so each root
        // itself becomes a candidate directory and the lookup stem is the
        // section name. A `jobs.sql` in the runtime root must therefore
        // override the factory query of the builtin `jobs` section.
        let fx = fixtures();
        let yaml = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
"#;
        let section = section_from_yaml(yaml, "jobs");
        assert!(section.path().is_none(), "no path: configured for jobs");

        assert_eq!(
            first_query(&section, 19_00_00_00, &fx.search_dirs).as_deref(),
            Some("select 'details:builtin-override' from dual"),
            "jobs.sql in a search dir must override the builtin query"
        );
        // Sanity check: without the search dirs the factory query is used.
        let factory = first_query(&section, 19_00_00_00, &[]);
        assert!(factory.is_some(), "builtin jobs query must resolve");
        assert_ne!(
            factory.as_deref(),
            Some("select 'details:builtin-override' from dual"),
            "without search dirs the factory query must be returned"
        );
    }

    #[test]
    fn test_path_wins_over_inline_sql_but_falls_back_when_missing() {
        // A custom metric may carry both `path:` and an inline `sql:`. This test
        // pins the precedence: a resolvable `path:` wins, a missing one falls
        // back to the inline `sql:`.
        let fx = fixtures();
        // File resolves (orasql_abs/winner.sql -> 'details:file'), so `path:`
        // takes precedence over the inline `sql:` ('details:inline').
        let present_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - winner:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("winner.sql").display()
        );
        let section = section_from_yaml(&present_yaml, "winner");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:file' from dual"),
            "resolved path: must win over inline sql:"
        );

        // File is missing (does_not_exist.sql), so resolution falls back to the
        // inline `sql:` -> 'details:inline'.
        let missing_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - fallback:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("does_not_exist.sql").display()
        );
        let section = section_from_yaml(&missing_yaml, "fallback");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:inline' from dual"),
            "missing path: must fall back to inline sql:"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_path_override() {
        let fx = fixtures();

        // External `path:` file replaces the built-in instance query.
        let path_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
"#,
            fx.abs_dir.join("abs.sql").display()
        );
        let section = section_from_yaml(&path_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:abs' from dual"),
            "path: file must replace the built-in instance query"
        );
        assert_eq!(section.to_work_header(), "<<<oracle_instance:sep(124)>>>");
        assert!(
            section.pdb_patterns().is_empty(),
            "override runs against CDB only (no PDB targeting)"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_missing_path_falls_back_to_builtin_query() {
        let fx = fixtures();

        // Baseline: the shipped built-in `instance` query.
        let builtin_sql = first_query(
            &section_from_yaml(
                r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
"#,
                "instance",
            ),
            0,
            &[],
        );
        assert!(
            builtin_sql.is_some(),
            "sanity: the built-in instance section ships a query"
        );

        // `path:` points to a nonexistent file and there is no inline `sql:`
        // either, so the section must keep running the built-in query.
        let missing_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
"#,
            fx.abs_dir.join("does_not_exist.sql").display()
        );
        let section = section_from_yaml(&missing_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]),
            builtin_sql,
            "a missing path: file must fall back to the built-in query"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_path_override_does_not_validate_sql() {
        // The plugin must not alter or judge user-provided SQL: the file body
        // is only split on `;` and handed to the server verbatim. Whether the
        // SQL is valid is the DB's call. Its complaint is dealt with on the
        // in the Check plugins, not on Agent side.
        let fx = fixtures();
        write(&fx.abs_dir, "not_sql.sql", "this is not valid sql");

        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
"#,
            fx.abs_dir.join("not_sql.sql").display()
        );
        let section = section_from_yaml(&yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("this is not valid sql"),
            "the file body must be passed through unvalidated"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_path_wins_over_inline_sql() {
        // A built-in section override may carry both `path:` and an inline
        // `sql:`. Precedence is the same as for custom metrics: a resolvable
        // `path:` wins, a missing one falls back to the inline `sql:` (and
        // only without either does the built-in query run).
        let fx = fixtures();
        // File resolves (orasql_abs/winner.sql -> 'details:file'), so `path:`
        // takes precedence over the inline `sql:` ('details:inline').
        let present_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("winner.sql").display()
        );
        let section = section_from_yaml(&present_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:file' from dual"),
            "resolved path: must win over inline sql:"
        );

        // File is missing (does_not_exist.sql), so resolution falls back to
        // the inline `sql:` -> 'details:inline', not to the built-in query.
        let missing_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("does_not_exist.sql").display()
        );
        let section = section_from_yaml(&missing_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:inline' from dual"),
            "missing path: must fall back to inline sql:, not the built-in query"
        );
    }
}

/// Resolve `tests/files` for both Bazel (cwd is the runfiles root) and cargo (cwd is the crate).
#[cfg(not(windows))]
fn files_dir() -> std::path::PathBuf {
    let runfiles = std::env::current_dir()
        .unwrap()
        .join("packages/mk-oracle/tests/files");
    if runfiles.is_dir() {
        runfiles
    } else {
        std::path::PathBuf::from("tests/files")
    }
}

// Config-directory merging is not supported on Windows (the `--migrate-subdir` option is
// compiled out there), so these tests only run on non-Windows targets.
#[cfg(not(windows))]
#[test]
fn test_read_legacy_config_without_dir() {
    let input = files_dir().join("mk_oracle_main.cfg");
    let merged = mk_oracle::config::migration::read_legacy_config(&input, None).unwrap();
    assert_eq!(merged, "MAIN=1\n");
}

#[cfg(not(windows))]
#[test]
fn test_read_legacy_config_merges_sorted_cfg_files() {
    let files = files_dir();
    let input = files.join("mk_oracle_main.cfg");
    let dir = files.join("mk_oracle.d");
    let merged = mk_oracle::config::migration::read_legacy_config(&input, Some(&dir)).unwrap();
    // Only *.cfg files are merged (ignore.ps1 is skipped), in sorted order, each preceded by a
    // newline. Sorting keeps the output stable regardless of the read_dir order.
    assert_eq!(merged, "MAIN=1\n\nA=1\n\nB=2\n\nC=3\n");
}

/// Hidden files must be skipped: the legacy plugin sources `mk_oracle.d/*.cfg` with a
/// shell glob, which never matches names starting with a dot (editor swap files,
/// backups of package managers, ...).
#[cfg(not(windows))]
#[test]
fn test_read_legacy_config_skips_hidden_cfg_files() {
    let tmp = tempfile::tempdir().expect("create temp dir");
    let input = tmp.path().join("mk_oracle.cfg");
    std::fs::write(&input, "MAIN=1\n").unwrap();

    let dir = tmp.path().join("mk_oracle.d");
    std::fs::create_dir(&dir).unwrap();
    std::fs::write(dir.join("a.cfg"), "A=1\n").unwrap();
    std::fs::write(dir.join(".a.cfg.swp"), "SWAP=1\n").unwrap();
    std::fs::write(dir.join(".hidden.cfg"), "HIDDEN=1\n").unwrap();

    let merged = mk_oracle::config::migration::read_legacy_config(&input, Some(&dir)).unwrap();
    assert_eq!(merged, "MAIN=1\n\nA=1\n");
}

/// A config file that cannot be executed must be reported with its path, not be
/// turned into an empty variable set that fails later with a misleading
/// "DBUSER not defined".
#[cfg(not(windows))]
#[test]
fn test_migrate_reports_config_that_cannot_be_executed() {
    let tmp = tempfile::tempdir().expect("create temp dir");
    let main_cfg = tmp.path().join("mk_oracle.cfg");
    std::fs::write(&main_cfg, "DBUSER='checkmk:secret::localhost:1521:'\n").unwrap();

    let dir = tmp.path().join("mk_oracle.d");
    std::fs::create_dir(&dir).unwrap();
    let broken = dir.join("50_broken.cfg");
    std::fs::write(&broken, "echo 'broken fragment' >&2\nexit 3\n").unwrap();

    let err = mk_oracle::config::migration::migrate(&main_cfg, Some(&dir)).expect_err("must fail");
    let message = format!("{err:#}");
    assert!(
        message.contains(&broken.display().to_string()),
        "the offending config file must be named: {message}"
    );
    assert!(
        message.contains("broken fragment"),
        "the shell output must be passed on: {message}"
    );
    assert!(
        !message.contains("DBUSER not defined"),
        "the real cause must not be masked by a downstream error: {message}"
    );
}

/// A custom SQL section defined only in an `mk_oracle.d/*.cfg` fragment must end
/// up in the migrated config, like it does for the legacy plugin which sources
/// the main config and the fragments as one effective configuration.
#[cfg(not(windows))]
#[test]
fn test_migrate_custom_sql_from_config_dir() {
    let tmp = tempfile::tempdir().expect("create temp dir");
    let sql_dir = tmp.path().display();

    let main_cfg = tmp.path().join("mk_oracle.cfg");
    std::fs::write(
        &main_cfg,
        "DBUSER='checkmk:secret::localhost:1521:'\nSYNC_SECTIONS=\"instance\"\n",
    )
    .unwrap();

    let config_dir = tmp.path().join("mk_oracle.d");
    std::fs::create_dir(&config_dir).unwrap();
    std::fs::write(
        config_dir.join("50_foo.cfg"),
        format!(
            r#"SQLS_SECTIONS=foo_views_chk1
SQLS_DIR={sql_dir}
SQLS_MAX_CACHE_AGE=3600

foo_views_chk1 () {{
    SQLS_SIDS="PRODPDB1"
    SQLS_SQL=foo_view_check1.sql
    SQLS_ITEM_NAME="foo_views_kim1"
}}
"#
        ),
    )
    .unwrap();
    std::fs::write(
        tmp.path().join("foo_view_check1.sql"),
        "select 'foo' from dual\n",
    )
    .unwrap();

    let yml = mk_oracle::config::migration::migrate(&main_cfg, Some(&config_dir))
        .expect("migration must succeed");

    assert!(
        yml.contains("    custom_metrics_cache_age: 3600\n"),
        "SQLS_MAX_CACHE_AGE from mk_oracle.d not migrated:\n{yml}"
    );
    assert!(
        yml.contains(&format!(
            "      - sid: PRODPDB1\n        custom_metrics:\n          - foo_views_kim1:\n              path: {sql_dir}/foo_view_check1.sql\n"
        )),
        "custom SQL section from mk_oracle.d not migrated:\n{yml}"
    );
}

/// Writes an `olr.loc` naming `<dir>/grid` and creates that directory, so
/// that the result looks like a node running Grid Infrastructure.
fn make_grid_node(dir: &std::path::Path) -> (std::path::PathBuf, std::path::PathBuf) {
    let crs_home = dir.join("grid");
    std::fs::create_dir_all(&crs_home).unwrap();
    let local_registry = dir.join("olr.loc");
    std::fs::write(
        &local_registry,
        format!(
            "olrconfig_loc={}/olr\ncrs_home={}\n",
            dir.display(),
            crs_home.display()
        ),
    )
    .unwrap();
    (local_registry, crs_home)
}

fn connection_from_olr(local_registry: &std::path::Path) -> Connection {
    let path = local_registry.to_str().unwrap().replace('\\', "/");
    Connection::from_yaml(&create_yaml(format!(
        "connection:\n  oracle_local_registry: \"{path}\"\n"
    )))
    .unwrap()
    .unwrap()
}

#[test]
fn test_grid_detect_uses_configured_registry() {
    let tmp = tempfile::tempdir().unwrap();
    let (local_registry, crs_home) = make_grid_node(tmp.path());

    let grid = GridInfrastructure::detect_in(Some(&local_registry), &[]).unwrap();
    assert_eq!(grid.local_registry(), local_registry);
    assert_eq!(grid.crs_home(), crs_home);
}

#[test]
fn test_grid_detect_probes_standard_locations() {
    let tmp = tempfile::tempdir().unwrap();
    let (local_registry, crs_home) = make_grid_node(tmp.path());
    let locations = ["/no/such/olr.loc", local_registry.to_str().unwrap()];

    let grid = GridInfrastructure::detect_in(None, &locations).unwrap();
    assert_eq!(grid.crs_home(), crs_home);
}

#[test]
fn test_grid_detect_prefers_configured_registry_over_standard_locations() {
    let tmp = tempfile::tempdir().unwrap();
    let (standard, _) = make_grid_node(tmp.path());
    let (configured, configured_home) = make_grid_node(&tmp.path().join("other"));

    let grid =
        GridInfrastructure::detect_in(Some(&configured), &[standard.to_str().unwrap()]).unwrap();
    assert_eq!(grid.crs_home(), configured_home);
}

#[test]
fn test_grid_detect_none_when_grid_home_is_not_a_directory() {
    let tmp = tempfile::tempdir().unwrap();
    let local_registry = tmp.path().join("olr.loc");
    std::fs::write(&local_registry, "crs_home=/no/such/grid\n").unwrap();

    assert!(GridInfrastructure::detect_in(Some(&local_registry), &[]).is_none());
}

#[test]
fn test_grid_detect_none_without_crs_home_entry() {
    let tmp = tempfile::tempdir().unwrap();
    let local_registry = tmp.path().join("olr.loc");
    std::fs::write(&local_registry, "olrconfig_loc=/etc/oracle/olr\n").unwrap();

    assert!(GridInfrastructure::detect_in(Some(&local_registry), &[]).is_none());
}

/// Legacy `mk_oracle` connects to the node name rather than to localhost once
/// it finds Grid Infrastructure, because the listener binds the node address.
#[test]
fn test_connection_host_defaults_to_node_name_under_grid_infrastructure() {
    let tmp = tempfile::tempdir().unwrap();
    let (local_registry, _) = make_grid_node(tmp.path());

    let conn = connection_from_olr(&local_registry);
    assert!(conn.grid().is_some());
    assert!(!conn.is_local());
    // the default is the node name the operating system reports, not merely
    // "something other than localhost"
    let node_name = mk_oracle::platform::node_name().expect("the node has a name");
    assert_eq!(conn.hostname().to_string(), node_name.to_lowercase());
}

/// The node name is read through libc rather than the gethostname crate, which
/// cannot be built on AIX. This is the test that the call itself works.
#[test]
fn test_node_name() {
    let name = mk_oracle::platform::node_name().expect("the node has a name");
    assert!(!name.is_empty());
    assert!(!name.contains('\0'), "must stop at the NUL terminator");
}

#[test]
fn test_connection_host_stays_localhost_without_grid_infrastructure() {
    let conn = connection_from_olr(std::path::Path::new("/no/such/olr.loc"));
    assert!(conn.grid().is_none());
    assert!(conn.is_local());
}

/// On a Grid Infrastructure node oratab may list nothing, which leaves the Grid
/// home as the only Oracle client on the host. Skipped when the machine has a
/// host client of its own, because that one legitimately wins.
#[cfg(unix)]
#[test]
fn test_runtime_dir_falls_back_to_grid_home() {
    if local_oracle_client_present() {
        eprintln!("SKIPPED: a host Oracle client is present and takes precedence");
        return;
    }

    let tmp = tempfile::tempdir().unwrap();
    let (local_registry, crs_home) = make_grid_node(tmp.path());
    let lib_dir = crs_home.join("lib");
    std::fs::create_dir_all(&lib_dir).unwrap();
    std::fs::File::create(lib_dir.join(CLIENT_LIB_NAME)).unwrap();

    let path = local_registry.to_str().unwrap().replace('\\', "/");
    let yaml = format!(
        r#"
---
oracle:
  main:
    options:
      use_host_client: always
    authentication:
      username: "foo"
      password: "bar"
    discovery:
       detect: no
    connection:
      hostname: "localhost"
      oracle_local_registry: "{path}"
"#
    );
    let config = OracleConfig::load_str(&yaml).unwrap();
    let ora_sql = config.ora_sql().unwrap();

    assert_eq!(
        detect_runtime(
            ora_sql.options().use_host_client(),
            None,
            ora_sql.conn().grid()
        )
        .map(|r| r.dir),
        Some(lib_dir)
    );
}

/// `never` means the bundled runtime only, so the Grid home must not be used.
#[cfg(unix)]
#[test]
fn test_runtime_dir_ignores_grid_home_when_host_client_is_never() {
    let tmp = tempfile::tempdir().unwrap();
    let (local_registry, crs_home) = make_grid_node(tmp.path());
    let lib_dir = crs_home.join("lib");
    std::fs::create_dir_all(&lib_dir).unwrap();
    std::fs::File::create(lib_dir.join(CLIENT_LIB_NAME)).unwrap();

    let path = local_registry.to_str().unwrap().replace('\\', "/");
    let yaml = format!(
        r#"
---
oracle:
  main:
    options:
      use_host_client: never
    authentication:
      username: "foo"
      password: "bar"
    discovery:
       detect: no
    connection:
      hostname: "localhost"
      oracle_local_registry: "{path}"
"#
    );
    let config = OracleConfig::load_str(&yaml).unwrap();
    let ora_sql = config.ora_sql().unwrap();

    // no agent library directory either, so the Grid home is the only client
    // that could be found, and `never` must not find it
    assert!(detect_runtime(
        ora_sql.options().use_host_client(),
        None,
        ora_sql.conn().grid()
    )
    .is_none());
}

// --- target filtering: writes a tnsnames.ora, so a component test rather than
// --- a unit test.

/// One instance per target shape the filter distinguishes.
fn instance_for_home(target: Option<TargetId>, wallet: bool) -> CustomInstance {
    let auth = if wallet {
        Authentication::from_yaml(&create_yaml(
            "authentication:\n  username: u\n  password: p\n  type: wallet",
        ))
        .unwrap()
        .unwrap()
    } else {
        Authentication::default()
    };
    CustomInstance::new(auth, Connection::default(), target, None, None)
}

fn sid_target(sid: &str) -> Option<TargetId> {
    TargetIdBuilder::new().sid(Some(sid)).build()
}

fn alias_target(alias: &str) -> Option<TargetId> {
    TargetIdBuilder::new()
        .alias(Some(&InstanceAlias::from(alias.to_string())))
        .build()
}

fn local_instance(name: &str, home: &str) -> LocalInstance {
    LocalInstance {
        name: InstanceName::from(name),
        home: std::path::PathBuf::from(home),
        base: None,
    }
}

/// Names of the spots that survived, as the log reports them.
fn surviving(spots: Vec<ClosedSpot>, env: &Env, known: &[LocalInstance]) -> Vec<String> {
    let mut names: Vec<String> = filter_spots_by_oracle_home(spots, env, known)
        .iter()
        .map(|spot| spot.target().display_name())
        .collect();
    names.sort();
    names
}

#[test]
fn test_local_tns_aliases_reads_the_home_file() {
    if std::env::var_os(TNS_ADMIN_ENV_VAR).is_some() {
        return;
    }
    let home = tempfile::tempdir().expect("temp home");
    let home = home.path();
    let admin = home.join("network").join("admin");
    std::fs::create_dir_all(&admin).expect("tns admin dir");
    std::fs::write(
        admin.join(TNS_NAMES_FILE),
        "known = (ADDRESS = (HOST = h)(PORT = 1521))\n",
    )
    .expect("write tnsnames.ora");

    let aliases = local_tns_aliases(&Env::with_oracle_home(home.to_str(), None));

    let expected: HashSet<String> = ["KNOWN".to_string()].into_iter().collect();
    assert_eq!(aliases, expected);
}

/// The three `LOCAL_ORACLE_HOME_TARGETS` states, against every target shape: a
/// plain sid, a sid with wallet auth, an alias the local `tnsnames.ora` knows,
/// and one it does not.
#[test]
fn test_filter_spots_by_oracle_home() {
    let home = tempfile::tempdir().expect("temp home");
    let home = home.path();
    let tns_admin = home.join("network").join("admin");
    std::fs::create_dir_all(&tns_admin).expect("tns admin dir");
    std::fs::write(
        tns_admin.join("tnsnames.ora"),
        "known = (ADDRESS = (HOST = h)(PORT = 1521))\n",
    )
    .expect("write tnsnames.ora");

    let spots = calc_custom_spots(&[
        instance_for_home(sid_target("plain"), false),
        instance_for_home(sid_target("walletsid"), true),
        instance_for_home(alias_target("known"), false),
        instance_for_home(alias_target("unknown"), false),
    ]);
    let known = [local_instance(
        "walletsid",
        home.to_str().expect("utf-8 temp dir"),
    )];

    let absent = surviving(
        spots.clone(),
        &Env::with_oracle_home(home.to_str(), None),
        &[],
    );
    let global = surviving(
        spots.clone(),
        &Env::with_oracle_home(home.to_str(), Some(false)),
        &[local_instance("walletsid", "/opt/oracle")],
    );
    let local = surviving(
        spots.clone(),
        &Env::with_oracle_home(home.to_str(), Some(true)),
        &known,
    );
    let other_home = surviving(
        spots.clone(),
        &Env::with_oracle_home(Some("/opt/other"), Some(true)),
        &known,
    );
    let no_home = surviving(
        spots.clone(),
        &Env::with_oracle_home(None, Some(true)),
        &known,
    );

    assert_eq!(spots.len(), 4, "every target shape must yield a spot");
    // Absent: nothing states how the targets are divided, so none is dropped.
    assert_eq!(absent, vec!["KNOWN", "PLAIN", "UNKNOWN", "WALLETSID"]);
    // `no`: an alias belongs to whichever tnsnames.ora resolves it - here none
    // does, since no global TNS_ADMIN is set - and a local sid with wallet to
    // the home holding that wallet. Only the sid no home owns stays.
    assert_eq!(global, vec!["PLAIN"]);
    // `yes`: only what this home resolves itself - its own sid with wallet, and
    // the alias its own tnsnames.ora defines.
    assert_eq!(local, vec!["KNOWN", "WALLETSID"]);
    // `yes` for a home no local instance belongs to owns nothing, and `yes`
    // without an ORACLE_HOME cannot own anything either.
    assert!(other_home.is_empty());
    assert!(no_home.is_empty());
}
