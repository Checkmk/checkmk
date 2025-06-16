// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use anyhow::Result;
use assert_cmd::output::OutputError;
use assert_cmd::Command;
use flexi_logger::{self, DeferredNow, FileSpec, LogSpecification, Record};
use mk_sql::config::ms_sql::{Authentication, Connection, Endpoint};
use mk_sql::ms_sql::client::UniClient;
use mk_sql::ms_sql::query;
use std::ffi::OsString;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Output;
use std::sync::OnceLock;
use tempfile::Builder;
use tempfile::NamedTempFile;
pub use tempfile::TempDir;
use yaml_rust2::YamlLoader;

static CONTROLLER_COMMAND_PATH: OnceLock<OsString> = OnceLock::new();

#[cfg(not(feature = "build_system_bazel"))]
fn controller_command_path_impl() -> OsString {
    let path = assert_cmd::cargo::cargo_bin("mk-sql");
    assert!(path.is_file());
    path.into()
}

#[cfg(feature = "build_system_bazel")]
fn controller_command_path_impl() -> OsString {
    let cwd = std::env::current_dir().unwrap();
    // Binary has same name as parent directory
    let relative_path: std::path::PathBuf = ["packages", "mk-sql", "mk-sql"].iter().collect();
    let path = cwd.join(relative_path);
    assert!(path.is_file());
    path.into()
}

pub fn run_bin() -> Command {
    let controller_command_path = CONTROLLER_COMMAND_PATH.get_or_init(controller_command_path_impl);
    Command::new(controller_command_path)
}

pub fn run_bin_error() -> Output {
    run_bin().unwrap_err().as_output().unwrap().clone()
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

pub const MS_SQL_DB_CERT: &str = "CI_TEST_MS_SQL_DB_CERT";
pub const SQL_DB_ENDPOINT: &str = "CI_TEST_SQL_DB_ENDPOINT";
const SQL_DB_ENDPOINT_SPLITTER: char = ':';
pub struct SqlDbEndpoint {
    pub host: String,
    pub user: String,
    pub pwd: String,
}

impl SqlDbEndpoint {
    pub fn make_ep(&self) -> Endpoint {
        let a = format!(
            r"
authentication:
  username: {}
  password: {}
  type: sql_server",
            self.user, self.pwd
        );
        let auth =
            Authentication::from_yaml(&YamlLoader::load_from_str(&a).unwrap()[0].clone()).unwrap();

        let c = format!(
            r"
connection:
  hostname: {}
  ",
            self.host
        );

        let conn = Connection::from_yaml(&YamlLoader::load_from_str(&c).unwrap()[0].clone(), None)
            .unwrap()
            .unwrap();

        Endpoint::new(&auth, &conn)
    }
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

pub fn create_file_with_content(dir: &Path, file_name: &str, content: &str) -> PathBuf {
    let file_path = dir.join(file_name);
    let mut file = std::fs::File::create(&file_path).unwrap();
    file.write_all(content.as_bytes()).unwrap();
    file_path
}

pub fn create_temp_process_dir() -> TempDir {
    let dir = Builder::new()
        .prefix(&format!("mk-sql-{}", std::process::id()))
        .rand_bytes(5)
        .tempdir()
        .unwrap();

    dir
}

pub fn create_remote_config(end_point: &SqlDbEndpoint) -> NamedTempFile {
    let mut l = NamedTempFile::new().unwrap();
    let config = format!(
        r#"
---
mssql:
  main:
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
    let config = format!(
        r#"
---
mssql:
  main:
    authentication:
       username: "nobody"
       type: "integrated"
    connection:
       hostname: "localhost"
       {}
"#,
        make_tls_block()
    );
    l.write_all(config.as_bytes()).unwrap();
    l
}

pub fn create_config_with_wrong_host() -> NamedTempFile {
    let mut l = NamedTempFile::new().unwrap();
    let config = r#"
---
mssql:
  main:
    authentication:
       username: "nobody"
       password: "doesnt_matter"
       type: "sql_server"
    connection:
       hostname: "no_host"
       timeout: 30 # long timeout to avoid timeout error
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

pub async fn run_get_version(client: &mut UniClient) -> Option<String> {
    let answers = query::run_custom_query(client, "select @@VERSION")
        .await
        .unwrap();
    let answer = &answers[0];
    match answer {
        query::UniAnswer::Rows(rows) => rows
            .first()
            .and_then(|v| v.try_get::<&str, usize>(0).ok()) // drop error
            .flatten()
            .map(str::to_string),
        query::UniAnswer::Block(block) => block.get_first_row_column(0),
    }
}

#[allow(dead_code)]
pub struct LogMe {
    temp_dir: TempDir,
    name: String,
}

#[allow(dead_code)]
impl LogMe {
    pub fn new(name: &str) -> Self {
        let dir = create_temp_process_dir();
        Self {
            temp_dir: dir,
            name: name.to_string(),
        }
    }

    pub fn dir(&self) -> &Path {
        self.temp_dir.path()
    }

    pub fn start(self, level: log::Level) -> Self {
        self.apply_logging_parameters(level).unwrap();
        self
    }

    fn make_log_file_spec(&self) -> FileSpec {
        FileSpec::default()
            .directory(self.dir().to_owned())
            .suppress_timestamp()
            .basename(&self.name)
    }

    fn apply_logging_parameters(&self, level: log::Level) -> Result<flexi_logger::LoggerHandle> {
        let spec =
            LogSpecification::parse(format!("{}, tiberius=warn", level.as_str().to_lowercase()))?;
        let mut logger = flexi_logger::Logger::with(spec);

        logger = logger.log_to_file(self.make_log_file_spec());

        logger = logger
            .duplicate_to_stderr(flexi_logger::Duplicate::None)
            .duplicate_to_stdout(flexi_logger::Duplicate::None);

        log::info!("Log level: {}", level.as_str());
        Ok(logger.format(custom_format).start()?)
    }
}

fn custom_format(
    w: &mut dyn std::io::Write,
    now: &mut DeferredNow,
    record: &Record,
) -> Result<(), std::io::Error> {
    write!(
        w,
        "{} [{}] [{}]: {}",
        now.format("%Y-%m-%d %H:%M:%S%.3f %:z"),
        record.level(),
        record.module_path().unwrap_or("<unnamed>"),
        &record.args()
    )
}

pub fn make_tls_block() -> String {
    if let Ok(certificate_path) = std::env::var(MS_SQL_DB_CERT) {
        format!(
            r#"tls:
        ca: {}
        client_certificate: {}
"#,
            "''", certificate_path
        )
    } else {
        String::new()
    }
}
