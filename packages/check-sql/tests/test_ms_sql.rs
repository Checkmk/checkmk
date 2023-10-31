// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod common;
use check_sql::{config::CheckConfig, ms_sql::api};
use common::tools;
#[cfg(windows)]
use tempfile::TempDir;
#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_local_connection() {
    assert!(api::create_client_for_logged_user("localhost", 1433)
        .await
        .is_ok());
}

#[tokio::test(flavor = "multi_thread")]
async fn test_remote_connection() {
    if let Some(endpoint) = tools::get_remote_sql_from_env_var() {
        assert!(api::create_client(
            &endpoint.host,
            1433,
            api::Credentials::SqlServer {
                user: &endpoint.user,
                password: &endpoint.pwd,
            },
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
async fn test_check_config_exec_remote() {
    let file = tools::create_remote_config(&tools::get_remote_sql_from_env_var().unwrap());
    let check_config = CheckConfig::load_file(file.path()).unwrap();
    assert!(check_config.exec().await.is_ok());
}

#[tokio::test(flavor = "multi_thread")]
async fn test_check_config_exec_local() {
    let file = tools::create_local_config();
    let check_config = CheckConfig::load_file(file.path()).unwrap();
    assert!(check_config.exec().await.is_ok());
}

#[cfg(windows)]
#[test]
fn test_run_local() {
    let file = tools::create_local_config();
    assert!(tools::run_bin()
        .arg("-c")
        .arg(&file.path().to_string_lossy().into_owned())
        .unwrap()
        .status
        .success());
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

#[cfg(windows)]
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

#[cfg(windows)]
#[test]
fn test_run_local_as_plugin_with_config() {
    // Good config
    let content = r#"
---
mssql:
  standard:
    authentication:
       username: "nobody"
       type: "integrated"
    connection:
       hostname: "localhost"
"#;
    let dir = tools::create_config_dir_with_yml(content);
    let exec = tools::run_bin()
        .env("MK_CONFDIR", dir.path())
        .timeout(std::time::Duration::from_secs(5))
        .unwrap();
    let (stdout, code) = tools::get_good_results(&exec).unwrap();
    assert_eq!(code, 0);
    assert!(stdout.starts_with(
        r"<<<mssql_instance:sep(124)>>>
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
<<<mssql_jobs:sep(09)>>>"
    ));

    // Bad config
    invalidate_config_in_dir(&dir);
    let exec_err = tools::run_bin()
        .env("MK_CONFDIR", dir.path())
        .timeout(std::time::Duration::from_secs(5))
        .unwrap_err();
    let (stderr, code) = tools::get_bad_results(&exec_err).unwrap();
    assert_eq!(code, 1);
    assert_eq!(stderr, "Error: No Config\n");
}

#[cfg(windows)]
fn invalidate_config_in_dir(dir: &TempDir) {
    tools::create_file_with_content(dir.path(), "check-sql.yml", "---\n");
}
