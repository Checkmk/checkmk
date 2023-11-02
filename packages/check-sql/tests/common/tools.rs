// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use assert_cmd::output::OutputError;
use assert_cmd::Command;
use std::io::{self, Write};
use std::path::Path;
use std::process::Output;
use tempfile::NamedTempFile;
use tempfile::{Builder, TempDir};
use tokio::net::TcpStream;
use tokio_util::compat::Compat;

use tiberius::Client;

pub fn run_bin() -> Command {
    Command::cargo_bin("check-sql").unwrap()
}

/// returns stderr content +  resulting code
pub fn get_bad_results(output_err: &OutputError) -> Result<(String, i32)> {
    let output = output_err.as_output().unwrap();
    let stderr = std::str::from_utf8(&output.stderr).map(|s| s.to_string());
    Ok((stderr?, output.status.code().unwrap()))
}

/// returns stdout content +  resulting code
pub fn get_good_results(output: &Output) -> Result<(String, i32)> {
    let stdout = std::str::from_utf8(&output.stdout).map(|s| s.to_string());
    Ok((stdout?, output.status.code().unwrap()))
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

pub fn create_file_with_content(dir: &Path, file_name: &str, content: &str) {
    let file_path = dir.join(file_name);
    let mut file = std::fs::File::create(file_path).unwrap();
    file.write_all(content.as_bytes()).unwrap();
}

pub fn create_temp_process_dir() -> TempDir {
    let dir = Builder::new()
        .prefix(&format!("check-sql-{}", std::process::id()))
        .rand_bytes(5)
        .tempdir()
        .unwrap();

    dir
}

pub async fn create_remote_client(endpoint: &SqlDbEndpoint) -> Result<Client<Compat<TcpStream>>> {
    crate::api::create_client(
        &endpoint.host,
        1433,
        crate::api::Credentials::SqlServer {
            user: &endpoint.user,
            password: &endpoint.pwd,
        },
    )
    .await
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

/// write non captured message to stdout
pub fn skip_on_lack_of_ms_sql_endpoint() {
    #[allow(clippy::explicit_write)]
    write!(
        io::stdout(),
        "SKIPPING remote connection test: environment variable {} not set",
        crate::tools::SQL_DB_ENDPOINT
    )
    .unwrap();
}
