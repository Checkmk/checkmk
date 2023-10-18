// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod tools;

use check_sql::{config::CheckConfig, ms_sql::api};
#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_local_connection() {
    assert!(api::create_client_for_logged_user("localhost", 1433)
        .await
        .is_ok());
}

#[tokio::test(flavor = "multi_thread")]
#[ignore]
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
#[ignore]
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
#[ignore]
fn test_run_remote() {
    let file = tools::create_remote_config(&tools::get_remote_sql_from_env_var().unwrap());
    assert!(tools::run_bin()
        .arg("-c")
        .arg(&file.path().to_string_lossy().into_owned())
        .unwrap()
        .status
        .success());
}
