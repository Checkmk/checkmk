// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_sql::ms_sql::api;

mod tools {
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
