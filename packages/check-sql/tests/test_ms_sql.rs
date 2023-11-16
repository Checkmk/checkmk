// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod common;

use check_sql::ms_sql::{api::Client, api::InstanceEngine, queries};
use check_sql::{config::CheckConfig, ms_sql::api};
use common::tools::{self, SqlDbEndpoint};
use tempfile::TempDir;
use yaml_rust::YamlLoader;

fn expected_instances() -> Vec<String> {
    const EXPECTED_INSTANCES: [&str; 3] = ["MSSQLSERVER", "SQLEXPRESS_NAME", "SQLEXPRESS_WOW"];

    EXPECTED_INSTANCES
        .iter()
        .map(|&s| str::to_string(s))
        .collect()
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_local_connection() {
    assert!(api::create_local_client().await.is_ok());
}

fn is_instance_good(i: &InstanceEngine) -> bool {
    !i.name.is_empty()
        && i.id.contains(&i.name[..4])
        && i.id.contains("MSSQL")
        && i.version.chars().filter(|&c| c == '.').count() == 3
        && i.port().is_some()
        && i.cluster.is_none()
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_find_all_instances_local() {
    let mut client = api::create_local_client().await.unwrap();
    let instances = api::detect_instance_engines(&mut client).await.unwrap();
    let all: Vec<InstanceEngine> = [&instances.0[..], &instances.1[..]].concat();
    assert!(all.iter().all(is_instance_good), "{:?}", all);
    let mut names: Vec<String> = all.into_iter().map(|i| i.name).collect();
    names.sort();

    assert_eq!(names, expected_instances(), "During connecting to `local`");
}

#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_local() {
    let mut client = api::create_local_client().await.unwrap();
    let instances = api::detect_instance_engines(&mut client).await.unwrap();
    let names: Vec<String> = [&instances.0[..], &instances.1[..]]
        .concat()
        .into_iter()
        .map(|i| i.name)
        .collect();

    for name in names {
        let c = api::create_local_instance_client(&name, None).await;
        match c {
            Ok(mut c) => assert!(tools::run_get_version(&mut c).await.is_some()),
            Err(e) if e.to_string().starts_with(api::SQL_LOGIN_ERROR_TAG) => {
                // we may not have valid credentials to connect - it's normal
            }
            Err(e) if e.to_string().starts_with(api::SQL_TCP_ERROR_TAG) => {
                panic!("Unexpected CONNECTION error: `{:?}`", e);
            }
            Err(e) => {
                panic!("Unexpected error: `{:?}`", e);
            }
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_remote_connection() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        assert!(api::create_remote_client(
            &endpoint.host,
            check_sql::ms_sql::defaults::STANDARD_PORT,
            api::Credentials::SqlServer {
                user: &endpoint.user,
                password: &endpoint.pwd,
            }
        )
        .await
        .is_ok());
    } else {
        panic!(
            "Skipping remote connection test: environment variable {} not set",
            tools::SQL_DB_ENDPOINT
        );
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_find_all_instances_remote() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = tools::create_remote_client(&endpoint).await.unwrap();
        let instances = api::detect_instance_engines(&mut client).await.unwrap();
        let all: Vec<InstanceEngine> = [&instances.0[..], &instances.1[..]].concat();
        assert!(all.iter().all(is_instance_good));
        let mut names: Vec<String> = all.into_iter().map(|i| i.name).collect();
        names.sort();

        assert_eq!(
            names,
            expected_instances(),
            "During connecting to `{} with `{}`. {}",
            endpoint.host,
            endpoint.user,
            "Check, please, the database is accessible and use has sysadmin rights"
        );
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_remote() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = tools::create_remote_client(&endpoint).await.unwrap();
        let instances = api::detect_instance_engines(&mut client).await.unwrap();
        let is = [&instances.0[..], &instances.1[..]].concat();

        let r = YamlLoader::load_from_str(&create_remote_config(endpoint)).unwrap();
        let cfg = check_sql::config::ms_sql::Config::from_yaml(&r[0])
            .unwrap()
            .unwrap();
        for i in is {
            match i.create_client(cfg.auth(), cfg.conn()).await {
                Ok(mut c) => {
                    assert!(
                        tools::run_get_version(&mut c).await.is_some()
                            && api::get_computer_name(&mut c)
                                .await
                                .unwrap()
                                .unwrap()
                                .to_lowercase()
                                .starts_with("agentbuild")
                    );
                    validate_counters(&i, &mut c).await;
                    validate_blocked_sessions(&i, &mut c).await;
                    validate_all_sessions_to_check_format(&i, &mut c).await;
                    assert!(&i
                        .generate_waiting_sessions_entry(&mut c, queries::BAD_QUERY, '|',)
                        .await
                        .contains(" error: "),);
                }
                Err(e) => {
                    panic!("Unexpected error: `{:?}`", e);
                }
            }
        }
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

async fn validate_counters(instance: &InstanceEngine, client: &mut Client) {
    let counters = instance.generate_counters_entry(client, '|').await;
    assert!(
        counters.split('\n').collect::<Vec<&str>>().len() > 100,
        "{:?}",
        counters
    );
    assert!(!counters.contains(' '));
    assert!(!counters.contains('$'));
}

async fn validate_blocked_sessions(instance: &InstanceEngine, client: &mut Client) {
    let blocked_sessions = &instance
        .generate_waiting_sessions_entry(client, &queries::get_blocked_sessions_query(), '|')
        .await;
    assert_eq!(
        blocked_sessions,
        &format!("{}|No blocking sessions\n", instance.name)
    );
}

async fn validate_all_sessions_to_check_format(instance: &InstanceEngine, client: &mut Client) {
    let all_sessions = &instance
        .generate_waiting_sessions_entry(client, queries::QUERY_WAITING_TASKS, '|')
        .await;

    let lines: Vec<&str> = all_sessions.split('\n').collect::<Vec<&str>>();
    assert!(lines[lines.len() - 1].is_empty());
    for l in lines[..lines.len() - 1].iter() {
        assert!(
            l.starts_with(&format!("{}|", instance.name)),
            "bad line: {}",
            l
        );
        let values = l.split('|').collect::<Vec<&str>>();
        assert!(values[2].parse::<u64>().is_ok(), "bad line: {}", l);
        assert!(
            values[1].is_empty() || values[1].parse::<u64>().is_ok(),
            "bad line: {}",
            l
        );
        assert!(!values[3].is_empty(), "bad line: {}", l);
    }
}

/// This test is ignored because it requires real credentials and real server
/// Intended to be used manually by dev to check whether all instances are accessible.
/// TODO(sk): remove on branching
#[ignore]
#[tokio::test(flavor = "multi_thread")]
async fn test_validate_all_instances_remote_extra() {
    use yaml_rust::YamlLoader;
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = tools::create_remote_client(&endpoint).await.unwrap();
        let instances = api::detect_instance_engines(&mut client).await.unwrap();
        let is = [&instances.0[..], &instances.1[..]].clone().concat();
        let ms_sql = check_sql::config::ms_sql::Config::from_yaml(
            &YamlLoader::load_from_str(
                r"---
mssql:
  standard:
    authentication:
      username: your_user
      password: your_password
      type: sql_server
    connection:
      hostname: your_host
",
            )
            .expect("fix test string!")[0]
                .clone(),
        )
        .unwrap()
        .unwrap();

        for i in is {
            let c = i.create_client(ms_sql.auth(), ms_sql.conn()).await;
            match c {
                Ok(mut c) => assert!(
                    tools::run_get_version(&mut c).await.is_some()
                        && api::get_computer_name(&mut c)
                            .await
                            .unwrap()
                            .unwrap()
                            .to_lowercase()
                            .starts_with("agentbuild")
                ),
                Err(e) => {
                    panic!("Unexpected error: `{:?}`", e);
                }
            }
        }
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_get_computer_name() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let mut client = tools::create_remote_client(&endpoint).await.unwrap();
        let name = api::get_computer_name(&mut client).await.unwrap();
        assert!(name
            .clone()
            .unwrap()
            .to_lowercase()
            .starts_with("agentbuild"),);
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint();
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_exec_remote() {
    let file = tools::create_remote_config(&tools::get_remote_sql_from_env_var().unwrap());
    let check_config = CheckConfig::load_file(file.path()).unwrap();
    assert!(check_config.exec().await.is_ok());
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_exec_local() {
    let file = tools::create_local_config();
    let res = CheckConfig::load_file(file.path());
    #[cfg(windows)]
    assert!(res.unwrap().exec().await.is_ok());
    #[cfg(unix)]
    assert!(res.is_err());
}

#[test]
fn test_no_ms_sql() {
    #[cfg(windows)]
    const EXPECTED_ERROR: &str = "No such host is known";
    #[cfg(unix)]
    const EXPECTED_ERROR: &str = "failed to lookup address information";

    let file = tools::create_config_with_missing_ms_sql();
    let r = tools::run_bin()
        .arg("-c")
        .arg(&file.path().to_string_lossy().into_owned())
        .unwrap();
    let (stdout, code) = tools::get_good_results(&r).unwrap();
    assert_eq!(code, 0);
    assert!(stdout.contains(EXPECTED_ERROR));
}

#[cfg(windows)]
#[test]
fn test_run_local() {
    let file = tools::create_local_config();
    let r = tools::run_bin()
        .arg("-c")
        .arg(&file.path().to_string_lossy().into_owned())
        .unwrap()
        .status
        .success();
    assert!(r);
}

#[cfg(unix)]
#[test]
fn test_run_local() {
    let file = tools::create_local_config();
    let code = tools::run_bin()
        .arg("-c")
        .arg(&file.path().to_string_lossy().into_owned())
        .unwrap_err()
        .as_output()
        .unwrap()
        .status
        .code();

    assert_eq!(code, Some(1));
}

#[test]
fn test_run_remote() {
    let file = tools::create_remote_config(&tools::get_remote_sql_from_env_var().unwrap());
    assert!(tools::run_bin()
        .arg("-c")
        .arg(&file.path().to_string_lossy().into_owned())
        .unwrap()
        .status
        .success());
}

#[test]
fn test_run_local_as_plugin_without_config() {
    assert!(
        tools::run_bin()
            .unwrap_err()
            .as_output()
            .unwrap()
            .status
            .code()
            == Some(1)
    );
    assert!(
        tools::run_bin()
            .env("MK_CONFDIR", ".")
            .unwrap_err()
            .as_output()
            .unwrap()
            .status
            .code()
            == Some(1)
    );
}

#[test]
fn test_check_log_file() {
    let log_dir = tools::create_temp_process_dir();
    let log_dir_path = log_dir.path();
    let _ = tools::run_bin()
        .env("MK_CONFDIR", ".")
        .env("MK_LOGDIR", log_dir_path)
        .unwrap_err()
        .as_output()
        .unwrap();
    assert!(log_dir_path.join("check-sql_rCURRENT.log").exists());
}

const EXPECTED_START: &str = r"<<<mssql_instance:sep(124)>>>
<<<mssql_databases:sep(124)>>>
<<<mssql_counters:sep(124)>>>
<<<mssql_blocked_sessions:sep(124)>>>
<<<mssql_transactionlogs:sep(124)>>>
<<<mssql_clusters:sep(124)>>>
<<<mssql_mirroring:sep(09)>>>
<<<mssql_availability_groups:sep(09)>>>
<<<mssql_connections>>>
<<<mssql_tablespaces>>>
<<<mssql_datafiles:sep(124)>>>
<<<mssql_backup:sep(124)>>>
<<<mssql_jobs:sep(09)>>>";

#[test]
fn test_run_as_plugin_with_config() {
    // Good config
    let dir = tools::create_temp_process_dir();
    for (label, content) in create_config_contents() {
        update_config_in_dir(&dir, &content);
        let exec = tools::run_bin()
            .env("MK_CONFDIR", dir.path())
            .timeout(std::time::Duration::from_secs(5))
            .unwrap();
        let (stdout, code) = tools::get_good_results(&exec).unwrap();
        assert_eq!(code, 0, "For label: {}", &label);
        assert!(stdout.starts_with(EXPECTED_START), "For label: {}", &label);
        validate_stdout(&stdout, &label);
    }

    // Bad config
    update_config_in_dir(&dir, "---\n");
    let exec_err = tools::run_bin()
        .env("MK_CONFDIR", dir.path())
        .timeout(std::time::Duration::from_secs(5))
        .unwrap_err();
    let (stderr, code) = tools::get_bad_results(&exec_err).unwrap();
    assert_eq!(code, 1);
    assert_eq!(stderr, "Error: No Config\n");
}

/// Minimally validates stdout for a given key words.
/// This is NOT real integration test. May be replaced in the future with a real testing.
fn validate_stdout(stdout: &str, label: &str) {
    let contains =
        |lines: &Vec<&str>, label: &str| lines.iter().filter(|&s| s.contains(label)).count();

    let lines: Vec<&str> = stdout.lines().collect();
    // - config entries: one per engine
    assert_eq!(contains(&lines, "|config|"), 3, "{}\n{}", &label, stdout);
    // - state entries: one per engine
    assert_eq!(contains(&lines, "|state|1"), 3, "{}\n{}", &label, stdout);
    // - details entries: one per engine
    assert_eq!(contains(&lines, "|details|"), 3, "{}\n{}", &label, stdout);
    assert_eq!(
        contains(&lines, "|RTM|Express Edition"),
        2,
        "{}\n{}",
        &label,
        stdout
    );
    assert_eq!(
        contains(&lines, "|RTM|Express Edition (64-bit)"),
        1,
        "{}\n{}",
        &label,
        stdout
    );
    assert_eq!(
        contains(&lines, "|RTM|Standard Edition"),
        1,
        "{}\n{}",
        &label,
        stdout
    );
}

/// create [local,  remote] or [local]  for Windows
/// create [remote] or []  for Linux
fn create_config_contents() -> Vec<(String, String)> {
    let mut result: Vec<(String, String)> = Vec::new();
    #[cfg(windows)]
    {
        let content_local = r#"
---
mssql:
  standard:
    authentication:
       username: ""
       type: "integrated"
    connection:
       hostname: "localhost"
"#;
        result.push(("local".to_owned(), content_local.to_string()));
    }

    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        let content_remote = create_remote_config(endpoint);
        result.push(("remote".to_owned(), content_remote.to_string()));
    } else {
        tools::skip_on_lack_of_ms_sql_endpoint()
    }
    result
}

fn create_remote_config(endpoint: SqlDbEndpoint) -> String {
    format!(
        r#"
---
mssql:
  standard:
    authentication:
       username: {}
       password: {}
       type: "sql_server"
    connection:
       hostname: {}
"#,
        endpoint.user, endpoint.pwd, endpoint.host
    )
}

fn update_config_in_dir(dir: &TempDir, content: &str) {
    tools::create_file_with_content(dir.path(), "check-sql.yml", content);
}
