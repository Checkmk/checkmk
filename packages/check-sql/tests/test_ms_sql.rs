// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_sql::{config::CheckConfig, ms_sql::api};

mod tools {
    use assert_cmd::Command;
    use std::io::Write;
    use tempfile::NamedTempFile;

    pub fn run_bin() -> Command {
        Command::cargo_bin("check-sql").unwrap()
    }

    pub const SQL_DB_ENDPOINT: &str = "CI_TEST_SQL_DB_ENDPOINT";
    const SQL_DB_ENDPOINT_SPLITTER: char = ':';
    pub struct SqlDbEndpoint {
        pub host: String,
        pub user: String,
        pub pwd: String,
    }

    pub fn get_remote_sql_from_env_var() -> Option<SqlDbEndpoint> {
        if let Ok(content) = std::env::var(SQL_DB_ENDPOINT) {
            let x: Vec<&str> = content.split(SQL_DB_ENDPOINT_SPLITTER).collect();
            if x.len() == 3 {
                return Some(SqlDbEndpoint {
                    host: x[0].to_owned(),
                    user: x[1].to_owned(),
                    pwd: x[2].to_owned(),
                });
            } else {
                println!(
                    "Error: environment variable {} is invalid, must have format 'host:user:password' expected",
                    SQL_DB_ENDPOINT
                );
            }
        } else {
            println!("Error: environment variable {} is absent", SQL_DB_ENDPOINT);
        }
        None
    }

    pub fn create_remote_config(end_point: &SqlDbEndpoint) -> NamedTempFile {
        let mut l = NamedTempFile::new().unwrap();
        let config = format!(
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
            end_point.user, end_point.pwd, end_point.host
        );
        l.write_all(config.as_bytes()).unwrap();
        l
    }
    pub fn create_local_config() -> NamedTempFile {
        let mut l = NamedTempFile::new().unwrap();
        let config = r#"
---
mssql:
  standard:
    authentication:
       username: "nobody"
       type: "integrated"
    connection:
       hostname: "localhost"
"#;
        l.write_all(config.as_bytes()).unwrap();
        l
    }
}
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
