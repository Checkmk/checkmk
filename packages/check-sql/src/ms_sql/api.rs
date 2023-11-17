// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::vec;

use crate::config::{self, CheckConfig};
use crate::emit::header;
use crate::ms_sql::queries;
use anyhow::Result;
use futures::stream::{self, StreamExt};
use std::collections::HashSet;

#[cfg(windows)]
use tiberius::SqlBrowser;
use tiberius::{AuthMethod, Config, Query, Row};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

use super::defaults;
pub type Client = tiberius::Client<Compat<TcpStream>>;

pub const SQL_LOGIN_ERROR_TAG: &str = "[SQL LOGIN ERROR]";
pub const SQL_TCP_ERROR_TAG: &str = "[SQL TCP ERROR]";
const INSTANCE_SECTION_NAME: &str = "instance";
const COUNTERS_SECTION_NAME: &str = "counters";
const BLOCKED_SESSIONS_SECTION_NAME: &str = "blocked_sessions";
const TABLE_SPACES_SECTION_NAME: &str = "tablespaces";
const BACKUP_SECTION_NAME: &str = "backup";

pub enum Credentials<'a> {
    SqlServer { user: &'a str, password: &'a str },
    Windows { user: &'a str, password: &'a str },
}

pub struct Section {
    name: String,
    sep: Option<char>,
}

impl Section {
    pub fn new(name: impl ToString) -> Self {
        let name = name.to_string();
        let sep = get_section_separator(&name);
        Self { name, sep }
    }
    pub fn to_header(&self) -> String {
        header(&self.name, self.sep)
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn sep(&self) -> char {
        self.sep.unwrap_or(' ')
    }
}

pub trait Column {
    fn get_bigint_by_idx(&self, idx: usize) -> i64;
    fn get_value_by_idx(&self, idx: usize) -> String;
    fn get_optional_value_by_idx(&self, idx: usize) -> Option<String>;
    fn get_value_by_name(&self, idx: &str) -> String;
    fn get_optional_value_by_name(&self, idx: &str) -> Option<String>;
}

#[derive(Clone, Debug, Default)]
pub struct InstanceEngine {
    pub name: String,
    pub id: String,
    pub version: String,
    pub edition: String,
    pub cluster: Option<String>,
    port: Option<u16>,
    dynamic_port: Option<u16>,
    pub available: Option<bool>,
}

impl InstanceEngine {
    pub fn generate_leading_entry(&self, sep: char) -> String {
        format!(
            "{}{sep}config{sep}{}{sep}{}{sep}{}\n",
            self.mssql_name(),
            self.version,
            self.edition,
            self.cluster.as_deref().unwrap_or_default()
        )
    }

    pub fn mssql_name(&self) -> String {
        format!("MSSQL_{}", self.name)
    }

    pub async fn generate_sections(
        &self,
        ms_sql: &config::ms_sql::Config,
        sections: &[Section],
    ) -> String {
        let mut result = String::new();
        let instance_section = Section::new(INSTANCE_SECTION_NAME); // this is important section always present
        let endpoint = &ms_sql.endpoint();
        match self.create_client(endpoint, None).await {
            Ok(mut client) => {
                for section in sections {
                    result += &section.to_header();
                    match section.name.as_str() {
                        INSTANCE_SECTION_NAME => {
                            result += &self.generate_state_entry(true, instance_section.sep());
                            result += &self
                                .generate_details_entry(&mut client, instance_section.sep())
                                .await;
                        }
                        COUNTERS_SECTION_NAME
                        | BLOCKED_SESSIONS_SECTION_NAME
                        | TABLE_SPACES_SECTION_NAME
                        | BACKUP_SECTION_NAME => {
                            result += &self
                                .generate_known_sections(&mut client, endpoint, &section.name)
                                .await;
                        }
                        _ => {
                            result += format!("{} not implemented\n", section.name).as_str();
                        }
                    }
                }
            }
            Err(err) => {
                result += &instance_section.to_header();
                result += &self.generate_state_entry(false, instance_section.sep());
                log::warn!("Can't access {} instance with err {err}\n", self.id);
            }
        };
        result
    }

    /// Create a client for an Instance based on Config
    pub async fn create_client(
        &self,
        endpoint: &config::ms_sql::Endpoint,
        database: Option<String>,
    ) -> Result<Client> {
        let (auth, conn) = endpoint.split();
        let client = match auth.auth_type() {
            config::ms_sql::AuthType::SqlServer | config::ms_sql::AuthType::Windows => {
                if let Some(credentials) = obtain_config_credentials(auth) {
                    create_remote_client(
                        conn.hostname(),
                        self.port().unwrap_or(defaults::STANDARD_PORT),
                        credentials,
                        database,
                    )
                    .await?
                } else {
                    anyhow::bail!("Not provided credentials")
                }
            }

            #[cfg(windows)]
            config::ms_sql::AuthType::Integrated => {
                create_local_instance_client(&self.name, conn.sql_browser_port(), None).await?
            }

            _ => anyhow::bail!("Not supported authorization type"),
        };
        Ok(client)
    }

    pub async fn generate_details_entry(&self, client: &mut Client, sep: char) -> String {
        match run_query(client, &queries::get_details_query()).await {
            Ok(rows) => self.process_details_rows(rows, sep),
            Err(err) => {
                log::error!("Failed to get details: {}", err);
                format!("{}{:?}", sep.to_string().repeat(4), err).to_string()
            }
        }
    }

    pub fn generate_state_entry(&self, accessible: bool, sep: char) -> String {
        format!("{}{sep}state{sep}{}\n", self.mssql_name(), accessible as u8)
    }

    pub async fn generate_known_sections(
        &self,
        client: &mut Client,
        endpoint: &config::ms_sql::Endpoint,
        name: &str,
    ) -> String {
        let sep = Section::new(name).sep();
        let databases = self.generate_databases(client).await;
        match name {
            COUNTERS_SECTION_NAME => {
                self.generate_utc_entry(client, sep).await
                    + &self.generate_counters_entry(client, sep).await
            }
            BLOCKED_SESSIONS_SECTION_NAME => {
                self.generate_blocking_sessions_section(
                    client,
                    &queries::get_blocking_sessions_query(),
                    sep,
                )
                .await
            }
            TABLE_SPACES_SECTION_NAME => {
                self.generate_table_spaces_section(endpoint, &databases, sep)
                    .await
            }
            BACKUP_SECTION_NAME => self.generate_backup_section(client, &databases, sep).await,
            _ => format!("{} not implemented\n", name).to_string(),
        }
    }

    pub async fn generate_counters_entry(&self, client: &mut Client, sep: char) -> String {
        let x = run_query(client, queries::QUERY_COUNTERS)
            .await
            .and_then(validate_rows)
            .and_then(|rows| self.process_counters_rows(&rows, sep));
        match x {
            Ok(result) => result,
            Err(err) => {
                log::error!("Failed to get counters: {}", err);
                format!("{sep}{sep}{}{sep}{}\n", self.name, err).to_string()
            }
        }
    }

    fn process_counters_rows(&self, rows: &[Vec<Row>], sep: char) -> Result<String> {
        let rows = &rows[0];
        let z: Vec<String> = rows.iter().map(|row| to_counter_entry(row, sep)).collect();
        Ok(z.join(""))
    }

    pub async fn generate_blocking_sessions_section(
        &self,
        client: &mut Client,
        query: &str,
        sep: char,
    ) -> String {
        match run_query(client, query).await {
            Ok(rows) => {
                if rows.is_empty() || rows[0].is_empty() {
                    log::info!("No blocking sessions");
                    return format!("{}{sep}No blocking sessions\n", self.name).to_string();
                }
                self.process_blocked_sessions_rows(&rows, sep)
            }
            Err(err) => {
                log::info!("No blocking sessions: {}", err);
                format!("{}{sep}{err:?}\n", self.name).to_string()
            }
        }
    }

    pub async fn generate_table_spaces_section(
        &self,
        endpoint: &config::ms_sql::Endpoint,
        databases: &[String],
        sep: char,
    ) -> String {
        let format_error = |d: &str, e: &anyhow::Error| {
            format!(
                "{}{sep}{} - - - - - - - - - - - - {:?}\n",
                self.mssql_name(),
                d.replace(' ', "_"),
                e
            )
            .to_string()
        };
        let mut result = String::new();
        for d in databases {
            match self.create_client(endpoint, Some(d.clone())).await {
                Ok(mut c) => {
                    result += &run_query(&mut c, queries::QUERY_SPACE_USED)
                        .await
                        .map(|rows| to_table_spaces_entry(&self.mssql_name(), d, &rows, sep))
                        .unwrap_or_else(|e| format_error(d, &e));
                }
                Err(err) => {
                    result += &format_error(d, &err);
                }
            }
        }
        result
    }

    pub async fn generate_backup_section(
        &self,
        client: &mut Client,
        databases: &[String],
        sep: char,
    ) -> String {
        let result = run_query(client, queries::QUERY_BACKUP)
            .await
            .map(|rows| self.process_backup_rows(&rows, databases, sep));
        match result {
            Ok(output) => output,
            Err(err) => {
                log::error!("Failed to get backup: {}", err);
                databases
                    .iter()
                    .map(|d| {
                        format!(
                            "{}{sep}{}{sep}-{sep}-{sep}-{sep}{:?}\n",
                            self.mssql_name(),
                            d.replace(' ', "_"),
                            err
                        )
                    })
                    .collect::<Vec<String>>()
                    .join("")
            }
        }
    }

    /// doesn't return error - the same behavior as plugin
    pub async fn generate_databases(&self, client: &mut Client) -> Vec<String> {
        let result = run_query(client, queries::QUERY_DATABASES)
            .await
            .and_then(validate_rows)
            .map(|rows| self.process_databases_rows(&rows));
        match result {
            Ok(result) => result,
            Err(err) => {
                log::error!("Failed to get databases: {}", err);
                vec![]
            }
        }
    }
    fn process_blocked_sessions_rows(&self, rows: &[Vec<Row>], sep: char) -> String {
        let rows = &rows[0];
        let z: Vec<String> = rows
            .iter()
            .map(|row| to_blocked_session_entry(&self.name, row, sep))
            .collect();
        z.join("")
    }

    async fn generate_utc_entry(&self, client: &mut Client, sep: char) -> String {
        let result = run_query(client, queries::QUERY_UTC)
            .await
            .and_then(validate_rows)
            .and_then(|rows| self.process_utc_rows(&rows, sep));
        match result {
            Ok(result) => result,
            Err(err) => {
                log::error!("Failed to get UTC: {}", err);
                format!("{sep}{sep}{}{sep}{}\n", self.name, err).to_string()
            }
        }
    }

    fn process_utc_rows(&self, rows: &[Vec<Row>], sep: char) -> Result<String> {
        let row = &rows[0];
        let utc = row[0].get_value_by_name(queries::QUERY_UTC_TIME_PARAM);
        Ok(format!("None{sep}utc_time{sep}None{sep}{utc}\n"))
    }

    fn process_databases_rows(&self, rows: &[Vec<Row>]) -> Vec<String> {
        let row = &rows[0];
        row.iter()
            .map(|row| row.get_value_by_idx(0))
            .collect::<Vec<String>>()
    }

    fn process_details_rows(&self, rows: Vec<Vec<Row>>, sep: char) -> String {
        if rows.is_empty() || rows[0].is_empty() {
            const ERROR: &str = "No output from query";
            log::warn!("{}", ERROR);
            format!("{}{}", sep.to_string().repeat(4), ERROR).to_string()
        } else {
            let row = &rows[0];
            let version = get_row_value(&row[0], queries::QUERY_DETAILS_VERSION_PARAM);
            let level = get_row_value(&row[0], queries::QUERY_DETAILS_LEVEL_PARAM);
            let edition = get_row_value(&row[0], queries::QUERY_DETAILS_EDITION_PARAM);

            format!(
                "{}{sep}details{sep}{}{sep}{}{sep}{}\n",
                self.mssql_name(),
                version,
                level,
                edition
            )
        }
    }

    fn process_backup_rows(&self, rows: &[Vec<Row>], databases: &[String], sep: char) -> String {
        let (mut ready, missing_data) = self.process_backup_rows_partly(rows, databases, sep);
        let missing: Vec<String> = self.process_missing_backup_rows(&missing_data, sep);
        ready.extend(missing);
        ready.join("")
    }

    /// generates lit of correct backup entries + list of missing required backups
    fn process_backup_rows_partly(
        &self,
        rows: &[Vec<Row>],
        databases: &[String],
        sep: char,
    ) -> (Vec<String>, HashSet<String>) {
        let mut only_databases: HashSet<String> = databases.iter().cloned().collect();
        let s: Vec<String> = if !rows.is_empty() {
            rows[0]
                .iter()
                .filter_map(|row| {
                    let backup_database = row.get_value_by_name("database_name");
                    if only_databases.contains(&backup_database) {
                        only_databases.remove(&backup_database);
                        to_backup_entry(&self.mssql_name(), &backup_database, row, sep)
                    } else {
                        None
                    }
                })
                .collect()
        } else {
            vec![]
        };
        (s, only_databases)
    }

    fn process_missing_backup_rows(&self, data: &HashSet<String>, sep: char) -> Vec<String> {
        data.iter()
            .map(|db| {
                format!(
                    "{}{sep}{}{sep}-{sep}-{sep}-{sep}No backup found\n",
                    self.mssql_name(),
                    db.replace(' ', "_")
                )
            })
            .collect()
    }

    pub fn port(&self) -> Option<u16> {
        self.port.or(self.dynamic_port)
    }
}

fn validate_rows(rows: Vec<Vec<Row>>) -> Result<Vec<Vec<Row>>> {
    if rows.is_empty() || rows[0].is_empty() {
        Err(anyhow::anyhow!("No output from query"))
    } else {
        Ok(rows)
    }
}

fn to_table_spaces_entry(
    instance_name: &str,
    database_name: &str,
    rows: &Vec<Vec<Row>>,
    sep: char,
) -> String {
    let extract = |rows: &Vec<Vec<Row>>, part: usize, name: &str| {
        if (rows.len() < part) || rows[part].is_empty() {
            String::new()
        } else {
            rows[part][0].get_value_by_name(name).trim().to_string()
        }
    };
    let db_size = extract(rows, 0, "database_size");
    let unallocated = extract(rows, 0, "unallocated space");
    let reserved = extract(rows, 1, "reserved");
    let data = extract(rows, 1, "data");
    let index_size = extract(rows, 1, "index_size");
    let unused = extract(rows, 1, "unused");
    format!(
        "{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}\n",
        instance_name,
        database_name.replace(' ', "_"),
        db_size,
        unallocated,
        reserved,
        data,
        index_size,
        unused
    )
}

fn to_backup_entry(
    instance_name: &str,
    database_name: &str,
    row: &Row,
    sep: char,
) -> Option<String> {
    let last_backup_date = row.get_value_by_name("last_backup_date").trim().to_string();
    if last_backup_date.is_empty() {
        return None;
    }
    let backup_type = row.get_value_by_name("type").trim().to_string();
    let backup_type = if backup_type.is_empty() {
        "-".to_string()
    } else {
        backup_type
    };
    let replica_id = row.get_value_by_name("replica_id").trim().to_string();
    let is_primary_replica = row
        .get_value_by_name("is_primary_replica")
        .trim()
        .to_string();
    if replica_id.is_empty() && is_primary_replica == "True" {
        format!(
            "{}{sep}{}{sep}{}{sep}{}\n",
            instance_name,
            database_name.replace(' ', "_"),
            last_backup_date.replace(' ', "|"),
            backup_type,
        )
        .into()
    } else {
        None
    }
}

fn to_counter_entry(row: &Row, sep: char) -> String {
    let counter = row
        .get_value_by_idx(0)
        .trim()
        .replace(' ', "_")
        .to_lowercase();
    let object = row.get_value_by_idx(1).trim().replace([' ', '$'], "_");
    let instance = row.get_value_by_idx(2).trim().replace(' ', "_");
    let value = row.get_bigint_by_idx(3).to_string();
    format!(
        "{object}{sep}{counter}{sep}{}{sep}{value}\n",
        if instance.is_empty() {
            "None"
        } else {
            &instance
        }
    )
}

fn to_blocked_session_entry(instance_name: &str, row: &Row, sep: char) -> String {
    let session_id = row.get_value_by_idx(0).trim().to_string();
    let wait_duration_ms = row.get_bigint_by_idx(1).to_string();
    let wait_type = row.get_value_by_idx(2).trim().to_string();
    let blocking_session_id = row.get_value_by_idx(3).trim().to_string();
    format!("{instance_name}{sep}{session_id}{sep}{wait_duration_ms}{sep}{wait_type}{sep}{blocking_session_id}\n",)
}

fn get_row_value(row: &Row, idx: &str) -> String {
    row.get_optional_value_by_name(idx).unwrap_or_else(|| {
        log::warn!("Failed to get {idx} from query");
        String::new()
    })
}

impl Column for Row {
    fn get_bigint_by_idx(&self, idx: usize) -> i64 {
        self.try_get::<i64, usize>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
    }

    fn get_value_by_idx(&self, idx: usize) -> String {
        self.try_get::<&str, usize>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
            .to_string()
    }

    fn get_optional_value_by_idx(&self, idx: usize) -> Option<String> {
        self.try_get::<&str, usize>(idx)
            .unwrap_or_default()
            .map(str::to_string)
    }

    fn get_value_by_name(&self, idx: &str) -> String {
        self.try_get::<&str, &str>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
            .to_string()
    }

    fn get_optional_value_by_name(&self, idx: &str) -> Option<String> {
        self.try_get::<&str, &str>(idx)
            .unwrap_or_default()
            .map(str::to_string)
    }
}

impl From<&Row> for InstanceEngine {
    /// NOTE: ignores any bad data in the row
    /// try_get is used to not panic
    fn from(row: &Row) -> Self {
        InstanceEngine {
            name: row.get_value_by_idx(0),
            id: row.get_value_by_idx(1),
            edition: row.get_value_by_idx(2),
            version: row.get_value_by_idx(3),
            cluster: row.get_optional_value_by_idx(4),
            port: row
                .get_optional_value_by_idx(5)
                .and_then(|s| s.parse::<u16>().ok()),
            dynamic_port: row
                .get_optional_value_by_idx(6)
                .and_then(|s| s.parse::<u16>().ok()),
            available: None,
        }
    }
}

impl CheckConfig {
    pub async fn exec(&self) -> Result<String> {
        if let Some(ms_sql) = self.ms_sql() {
            let dumb_header = Self::generate_dumb_header(ms_sql);
            let instances_data = generate_instances_data(ms_sql).await.unwrap_or_else(|e| {
                log::error!("Error generating instances data: {e}");
                format!("{e}\n")
            });
            Ok(dumb_header + &instances_data)
        } else {
            anyhow::bail!("No Config")
        }
    }

    /// Generate header for each section without any data, see vbs plugin
    fn generate_dumb_header(ms_sql: &config::ms_sql::Config) -> String {
        let sections = get_work_sections(ms_sql);
        sections
            .iter()
            .map(Section::to_header)
            .collect::<Vec<String>>()
            .join("")
    }
}

/// Generate header for each section without any data
async fn generate_instances_data(ms_sql: &config::ms_sql::Config) -> Result<String> {
    let instance_section_sep = get_section_separator(INSTANCE_SECTION_NAME).unwrap_or(' ');

    let mut result = Section::new(INSTANCE_SECTION_NAME).to_header(); // as in old plugin
    let sections = get_work_sections(ms_sql);
    let all = get_instance_engines(&ms_sql.endpoint()).await?;
    let instances: Vec<InstanceEngine> = [&all.0[..], &all.1[..]].concat();

    for instance in &instances {
        result += &Section::new(INSTANCE_SECTION_NAME).to_header();
        result += &instance.generate_leading_entry(instance_section_sep);
    }
    // TODO(sk): remove this reference code after fucntionality of [futures] will be verified
    //for instance in &instances {
    //    for section in &sections {
    //        result += &instance.generate_section(&client, section).await;
    //    }
    //}
    Ok(result + &generate_result(&instances, &sections, ms_sql).await?)
}

/// Intelligent async processing of the data
async fn generate_result(
    instances: &[InstanceEngine],
    sections: &[Section],
    ms_sql: &config::ms_sql::Config,
) -> Result<String> {
    // place all futures now in vector for future asynchronous processing
    let tasks = instances
        .iter()
        .map(move |instance| instance.generate_sections(ms_sql, sections.clone()));

    // processing here
    let results = stream::iter(tasks)
        .buffer_unordered(6) // MAX_CONCURRENT is the limit of concurrent tasks you want to allow.
        .collect::<Vec<_>>()
        .await;

    Ok(results.join(""))
}

async fn create_client_from_config(endpoint: &config::ms_sql::Endpoint) -> Result<Client> {
    let (auth, conn) = endpoint.split();
    let client = match auth.auth_type() {
        config::ms_sql::AuthType::SqlServer | config::ms_sql::AuthType::Windows => {
            if let Some(credentials) = obtain_config_credentials(auth) {
                create_remote_client(conn.hostname(), conn.port(), credentials, None).await?
            } else {
                anyhow::bail!("Not provided credentials")
            }
        }

        #[cfg(windows)]
        config::ms_sql::AuthType::Integrated => create_local_client(None).await?,

        _ => anyhow::bail!("Not supported authorization type"),
    };
    Ok(client)
}

fn obtain_config_credentials(auth: &config::ms_sql::Authentication) -> Option<Credentials> {
    match auth.auth_type() {
        config::ms_sql::AuthType::SqlServer => Some(Credentials::SqlServer {
            user: auth.username(),
            password: auth.password().map(|s| s.as_str()).unwrap_or(""),
        }),
        #[cfg(windows)]
        config::ms_sql::AuthType::Windows => Some(Credentials::Windows {
            user: auth.username(),
            password: auth.password().map(|s| s.as_str()).unwrap_or(""),
        }),
        _ => None,
    }
}

pub fn get_work_sections(ms_sql: &config::ms_sql::Config) -> Vec<Section> {
    let sections = ms_sql.sections();
    let mut base: Vec<Section> = sections
        .get_filtered_always()
        .iter()
        .map(Section::new)
        .collect();
    base.extend(sections.get_filtered_cached().iter().map(Section::new));
    base
}

fn get_section_separator(name: &str) -> Option<char> {
    match name {
        "instance" | "databases" | "counters" | "blocked_sessions" | "transactionlogs"
        | "datafiles" | "cluster" | "clusters" | "backup" => Some('|'),
        "jobs" | "mirroring" | "availability_groups" => Some('\t'),
        "tablespaces" | "connections" => None,
        _ => None,
    }
}

/// Create connection to remote MS SQL
///
/// # Arguments
///
/// * `host` - Hostname of MS SQL server
/// * `port` - Port of MS SQL server
/// * `credentials` - defines connection type and credentials itself
/// * `instance_name` - name of the instance to connect to
pub async fn create_remote_client(
    host: &str,
    port: u16,
    credentials: Credentials<'_>,
    database: Option<String>,
) -> Result<Client> {
    match _create_remote_client(
        host,
        port,
        &credentials,
        tiberius::EncryptionLevel::Required,
        &database,
    )
    .await
    {
        Ok(client) => Ok(client),
        #[cfg(unix)]
        Err(err) => {
            log::warn!(
                "Encryption is not supported by the host, err is {}. Trying without encryption...",
                err
            );
            Ok(_create_remote_client(
                host,
                port,
                &credentials,
                tiberius::EncryptionLevel::NotSupported,
                &database,
            )
            .await?)
        }
        #[cfg(windows)]
        Err(err) => {
            log::warn!(
                "Encryption is not supported by the host, err is {}. Stopping...",
                err
            );
            Err(err)
        }
    }
}

pub async fn _create_remote_client(
    host: &str,
    port: u16,
    credentials: &Credentials<'_>,
    encryption: tiberius::EncryptionLevel,
    database: &Option<String>,
) -> Result<Client> {
    let mut config = Config::new();

    config.host(host);
    config.port(port);
    config.encryption(encryption);
    if let Some(db) = database {
        config.database(db);
    }
    config.authentication(match credentials {
        Credentials::SqlServer { user, password } => AuthMethod::sql_server(user, password),
        #[cfg(windows)]
        Credentials::Windows { user, password } => AuthMethod::windows(user, password),
        #[cfg(unix)]
        Credentials::Windows {
            user: _,
            password: _,
        } => anyhow::bail!("not supported"),
    });
    config.trust_cert(); // on production, it is not a good idea to do this

    let tcp = TcpStream::connect(config.get_addr()).await?;
    tcp.set_nodelay(true)?;

    // To be able to use Tokio's tcp, we're using the `compat_write` from
    // the `TokioAsyncWriteCompatExt` to get a stream compatible with the
    // traits from the `futures` crate.
    Ok(Client::connect(config, tcp.compat_write()).await?)
}

/// Check `local` (Integrated) connection to MS SQL
#[cfg(windows)]
pub async fn create_local_client(database: Option<String>) -> Result<Client> {
    let mut config = Config::new();

    if let Some(db) = database {
        config.database(db);
    }
    config.authentication(AuthMethod::Integrated);
    config.trust_cert(); // on production, it is not a good idea to do this

    let tcp = TcpStream::connect(config.get_addr()).await?;
    tcp.set_nodelay(true)?;

    // To be able to use Tokio's tcp, we're using the `compat_write` from
    // the `TokioAsyncWriteCompatExt` to get a stream compatible with the
    // traits from the `futures` crate.
    Ok(Client::connect(config, tcp.compat_write()).await?)
}

#[cfg(unix)]
pub async fn create_local_client(_database: Option<String>) -> Result<Client> {
    anyhow::bail!("not supported");
}

/// Create `local` connection to MS SQL `instance`
///
/// # Arguments
///
/// * `instance_name` - name of the instance to connect to
/// * `port` - Port of MS SQL server BROWSER,  1434 - default
#[cfg(windows)]
pub async fn create_local_instance_client(
    instance_name: &str,
    sql_browser_port: Option<u16>,
    database: Option<String>,
) -> anyhow::Result<Client> {
    let mut config = Config::new();

    config.host("localhost");
    // The default port of SQL Browser
    config.port(sql_browser_port.unwrap_or(defaults::SQL_BROWSER_PORT));
    config.authentication(AuthMethod::Integrated);
    if let Some(db) = database {
        config.database(db);
    }

    // The name of the database server instance.
    config.instance_name(instance_name);

    // on production, it is not a good idea to do this
    config.trust_cert();

    // This will create a new `TcpStream` from `async-std`, connected to the
    // right port of the named instance.
    let tcp = TcpStream::connect_named(&config)
        .await
        .map_err(|e| anyhow::anyhow!("{} {}", SQL_TCP_ERROR_TAG, e))?;

    // And from here on continue the connection process in a normal way.
    let s = Client::connect(config, tcp.compat_write())
        .await
        .map_err(|e| anyhow::anyhow!("{} {}", SQL_LOGIN_ERROR_TAG, e))?;
    Ok(s)
}

/// Create `local` connection to MS SQL `instance`
///
/// # Arguments
///
/// * `port` - Port of MS SQL server BROWSER,  1434 - default
/// * `instance_name` - name of the instance to connect to
#[cfg(unix)]
pub async fn create_local_instance_client(
    _instance_name: &str,
    _port: Option<u16>,
    _database: Option<String>,
) -> anyhow::Result<Client> {
    anyhow::bail!("not supported");
}

/// return Vec<Vec<Row>> as a Results Vec: one Vec<Row> per one statement in query.
pub async fn run_query(client: &mut Client, query: &str) -> Result<Vec<Vec<Row>>> {
    let stream = Query::new(query).query(client).await?;
    let rows: Vec<Vec<Row>> = stream.into_results().await?;
    Ok(rows)
}

/// return all MS SQL instances installed
pub async fn get_instance_engines(
    endpoint: &config::ms_sql::Endpoint,
) -> Result<(Vec<InstanceEngine>, Vec<InstanceEngine>)> {
    let mut client = create_client_from_config(endpoint).await?;
    detect_instance_engines(&mut client).await
}

/// [low level helper] return all MS SQL instances installed
pub async fn detect_instance_engines(
    client: &mut Client,
) -> Result<(Vec<InstanceEngine>, Vec<InstanceEngine>)> {
    Ok((
        get_engines(client, &queries::get_instances_query()).await?,
        get_engines(client, &queries::get_32bit_instances_query()).await?,
    ))
}

async fn get_engines(client: &mut Client, query: &str) -> Result<Vec<InstanceEngine>> {
    let rows = run_query(client, query).await?;
    Ok(rows[0]
        .iter()
        .map(InstanceEngine::from)
        .collect::<Vec<InstanceEngine>>()
        .to_vec())
}

/// return all MS SQL instances installed
pub async fn get_computer_name(client: &mut Client) -> Result<Option<String>> {
    let rows = run_query(client, queries::QUERY_COMPUTER_NAME).await?;
    if rows.is_empty() || rows[0].is_empty() {
        log::warn!("Computer name not found");
        return Ok(None);
    }
    let row = &rows[0];
    Ok(row[0]
        .try_get::<&str, usize>(0)
        .ok()
        .flatten()
        .map(str::to_string))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ms_sql::Config;
    use yaml_rust::YamlLoader;

    fn make_config_with_auth_type(auth_type: &str) -> Config {
        const BASE: &str = r#"
---
mssql:
  standard:
    authentication:
       username: "bad_user"
       password: "bad_password"
       type: type_tag
    connection:
       hostname: "bad_host"
"#;
        Config::from_yaml(
            &YamlLoader::load_from_str(&BASE.replace("type_tag", auth_type))
                .expect("fix test string!")[0]
                .clone(),
        )
        .unwrap()
        .unwrap()
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_create_client_from_config_for_error() {
        let config = make_config_with_auth_type("token");
        assert!(create_client_from_config(&config.endpoint())
            .await
            .unwrap_err()
            .to_string()
            .contains("Not supported authorization type"));
    }

    #[test]
    fn test_obtain_credentials_from_config() {
        #[cfg(windows)]
        assert!(obtain_config_credentials(make_config_with_auth_type("windows").auth()).is_some());
        assert!(
            obtain_config_credentials(make_config_with_auth_type("sql_server").auth()).is_some()
        );
    }
    #[test]
    fn test_generate_state_entry() {
        let i = InstanceEngine {
            name: "test_name".to_string(),
            ..Default::default()
        };
        assert_eq!(
            i.generate_state_entry(false, '.'),
            format!("MSSQL_test_name.state.0\n")
        );
        assert_eq!(
            i.generate_state_entry(true, '.'),
            format!("MSSQL_test_name.state.1\n")
        );
    }
}
