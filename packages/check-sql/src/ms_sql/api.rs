// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::client::{self, Client};
use super::section::{self, Section};
use crate::config::{self, ms_sql::AuthType, ms_sql::Endpoint, CheckConfig};
use crate::ms_sql::queries;
use anyhow::Result;
use futures::stream::{self, StreamExt};
use std::collections::HashSet;
use std::time::Instant;

use tiberius::{ColumnData, Query, Row};

use super::defaults;
type Answer = Vec<Row>;

pub const SQL_LOGIN_ERROR_TAG: &str = "[SQL LOGIN ERROR]";
pub const SQL_TCP_ERROR_TAG: &str = "[SQL TCP ERROR]";

pub trait Column<'a> {
    fn get_bigint_by_idx(&self, idx: usize) -> i64;
    fn get_bigint_by_name(&self, idx: &str) -> i64;
    fn get_value_by_idx(&self, idx: usize) -> String;
    fn get_optional_value_by_idx(&self, idx: usize) -> Option<String>;
    fn get_value_by_name(&self, idx: &str) -> String;
    fn get_optional_value_by_name(&self, idx: &str) -> Option<String>;
    fn get_all(self, sep: char) -> String;
}

#[derive(Clone, Debug, Default)]
pub struct InstanceEngineBuilder {
    alias: Option<String>,
    name: Option<String>,
    id: Option<String>,
    edition: Option<String>,
    version: Option<String>,
    cluster: Option<String>,
    port: Option<u16>,
    dynamic_port: Option<u16>,
    endpoint: Option<Endpoint>,
    computer_name: Option<String>,
}

impl InstanceEngineBuilder {
    pub fn new() -> InstanceEngineBuilder {
        InstanceEngineBuilder::default()
    }

    pub fn name<S: Into<String>>(mut self, name: S) -> Self {
        self.name = Some(name.into());
        self
    }
    pub fn alias<S: Into<String>>(mut self, alias: S) -> Self {
        self.alias = Some(alias.into());
        self
    }
    pub fn id<S: Into<String>>(mut self, id: S) -> Self {
        self.id = Some(id.into());
        self
    }
    pub fn edition<S: Into<String>>(mut self, edition: S) -> Self {
        self.edition = Some(edition.into());
        self
    }
    pub fn version<S: Into<String>>(mut self, version: S) -> Self {
        self.version = Some(version.into());
        self
    }
    pub fn cluster<S: Into<String>>(mut self, cluster: Option<S>) -> Self {
        self.cluster = cluster.map(|s| s.into());
        self
    }
    pub fn port<S: Into<u16>>(mut self, port: Option<S>) -> Self {
        self.port = port.map(|s| s.into());
        self
    }
    pub fn dynamic_port<S: Into<u16>>(mut self, port: Option<S>) -> Self {
        self.dynamic_port = port.map(|s| s.into());
        self
    }
    pub fn endpoint(mut self, endpoint: &Endpoint) -> Self {
        self.endpoint = Some(endpoint.clone());
        self
    }
    pub fn computer_name<'a, S>(mut self, computer_name: &'a Option<S>) -> Self
    where
        std::string::String: From<&'a S>,
    {
        self.computer_name = computer_name.as_ref().map(|s| s.into());
        self
    }

    pub fn row(self, row: &Row) -> Self {
        self.name(row.get_value_by_idx(0))
            .id(row.get_value_by_idx(1))
            .edition(row.get_value_by_idx(2))
            .version(row.get_value_by_idx(3))
            .cluster(row.get_optional_value_by_idx(4))
            .port(
                row.get_optional_value_by_idx(5)
                    .and_then(|s| s.parse::<u16>().ok()),
            )
            .dynamic_port(
                row.get_optional_value_by_idx(6)
                    .and_then(|s| s.parse::<u16>().ok()),
            )
    }

    pub fn build(self) -> InstanceEngine {
        InstanceEngine {
            alias: self.alias,
            name: self.name.unwrap_or_default(),
            id: self.id.unwrap_or_default(),
            edition: self.edition.unwrap_or_default(),
            version: self.version.unwrap_or_default(),
            cluster: self.cluster,
            port: self.port,
            dynamic_port: self.dynamic_port,
            available: None,
            endpoint: self.endpoint.unwrap_or_default(),
            computer_name: self.computer_name,
        }
    }
}

#[derive(Clone, Debug)]
pub struct InstanceEngine {
    pub alias: Option<String>,
    pub name: String,
    pub id: String,
    pub version: String,
    pub edition: String,
    pub cluster: Option<String>,
    port: Option<u16>,
    dynamic_port: Option<u16>,
    pub available: Option<bool>,
    endpoint: Endpoint,
    computer_name: Option<String>,
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

    pub fn full_name(&self) -> String {
        format!("{}/{}", self.endpoint.hostname(), self.name)
    }

    /// not tested, because it is a bit legacy
    pub fn legacy_name(&self) -> String {
        if self.name != "MSSQLSERVER" {
            return format!("{}/{}", self.legacy_name_prefix(), self.name);
        }

        if let Some(cluster) = &self.cluster {
            cluster.clone()
        } else {
            "(local)".to_string()
        }
    }

    fn legacy_name_prefix(&self) -> &str {
        if let Some(cluster) = &self.cluster {
            return cluster;
        }
        if let Some(computer_name) = &self.computer_name {
            computer_name
        } else {
            ""
        }
    }

    pub async fn generate_sections(
        &self,
        ms_sql: &config::ms_sql::Config,
        sections: &[Section],
    ) -> String {
        let mut result = String::new();
        let endpoint = &ms_sql.endpoint();
        match self.create_client(endpoint, None).await {
            Ok(mut client) => {
                for section in sections.iter() {
                    result += &section.to_header();
                    result += &self.generate_section(&mut client, endpoint, section).await;
                }
            }
            Err(err) => {
                let instance_section = Section::new(section::INSTANCE_SECTION_NAME); // this is important section always present
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
        endpoint: &Endpoint,
        database: Option<String>,
    ) -> Result<Client> {
        let (auth, conn) = endpoint.split();
        let client = match auth.auth_type() {
            AuthType::SqlServer | AuthType::Windows => {
                if let Some(credentials) = client::obtain_config_credentials(auth) {
                    client::create_remote(
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
            AuthType::Integrated => {
                client::create_instance_local(&self.name, conn.sql_browser_port(), database).await?
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

    pub async fn generate_section(
        &self,
        client: &mut Client,
        endpoint: &Endpoint,
        section: &Section,
    ) -> String {
        let sep = section.sep();
        let databases = self.generate_databases(client).await;
        match section.name() {
            section::INSTANCE_SECTION_NAME => {
                self.generate_state_entry(true, section.sep())
                    + &self.generate_details_entry(client, section.sep()).await
            }
            section::COUNTERS_SECTION_NAME => {
                self.generate_utc_entry(client, sep).await
                    + &self.generate_counters_entry(client, sep).await
            }
            section::BLOCKED_SESSIONS_SECTION_NAME => {
                self.generate_blocking_sessions_section(
                    client,
                    &queries::get_blocking_sessions_query(),
                    sep,
                )
                .await
            }
            section::TABLE_SPACES_SECTION_NAME => {
                self.generate_table_spaces_section(endpoint, &databases, sep)
                    .await
            }
            section::BACKUP_SECTION_NAME => {
                self.generate_backup_section(client, &databases, sep).await
            }
            section::TRANSACTION_LOG_SECTION_NAME => {
                self.generate_transaction_logs_section(endpoint, &databases, sep)
                    .await
            }
            section::DATAFILES_SECTION_NAME => {
                self.generate_datafiles_section(endpoint, &databases, sep)
                    .await
            }
            section::DATABASES_SECTION_NAME => {
                self.generate_databases_section(client, queries::QUERY_DATABASES, sep, &databases)
                    .await
            }
            section::CLUSTERS_SECTION_NAME => {
                self.generate_clusters_section(endpoint, &databases, sep)
                    .await
            }
            section::CONNECTIONS_SECTION_NAME => {
                self.generate_connections_section(client, queries::QUERY_CONNECTIONS, sep)
                    .await
            }
            section::MIRRORING_SECTION_NAME
            | section::JOBS_SECTION_NAME
            | section::AVAILABILITY_GROUPS_SECTION_NAME => {
                self.generate_query_section(endpoint, section, None).await
            }
            _ => format!("{} not implemented\n", section.name()).to_string(),
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
        endpoint: &Endpoint,
        databases: &Vec<String>,
        sep: char,
    ) -> String {
        let format_error = |d: &str, e: &anyhow::Error| {
            format!(
                "{} {} - - - - - - - - - - - - {:?}\n",
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

    pub async fn generate_transaction_logs_section(
        &self,
        endpoint: &Endpoint,
        databases: &Vec<String>,
        sep: char,
    ) -> String {
        let mut result = String::new();
        for d in databases {
            match self.create_client(endpoint, Some(d.clone())).await {
                Ok(mut c) => {
                    result += &run_query(&mut c, queries::QUERY_TRANSACTION_LOGS)
                        .await
                        .map(|rows| to_transaction_logs_entries(&self.name, d, &rows, sep))
                        .unwrap_or_else(|e| self.format_some_file_error(d, &e, sep));
                }
                Err(err) => {
                    result += &self.format_some_file_error(d, &err, sep);
                }
            }
        }
        result
    }

    fn format_some_file_error(&self, d: &str, e: &anyhow::Error, sep: char) -> String {
        format!(
            "{}{sep}{}|-|-|-|-|-|-|{:?}\n",
            self.name,
            d.replace(' ', "_"),
            e
        )
        .to_string()
    }

    pub async fn generate_datafiles_section(
        &self,
        endpoint: &Endpoint,
        databases: &Vec<String>,
        sep: char,
    ) -> String {
        let mut result = String::new();
        for d in databases {
            match self.create_client(endpoint, Some(d.clone())).await {
                Ok(mut c) => {
                    result += &run_query(&mut c, queries::QUERY_DATAFILES)
                        .await
                        .map(|rows| to_datafiles_entries(&self.name, d, &rows, sep))
                        .unwrap_or_else(|e| self.format_some_file_error(d, &e, sep));
                }
                Err(err) => {
                    result += &self.format_some_file_error(d, &err, sep);
                }
            }
        }
        result
    }

    pub async fn generate_databases_section(
        &self,
        client: &mut Client,
        query: &str,
        sep: char,
        databases: &[String],
    ) -> String {
        run_query(client, query)
            .await
            .map(|rows| to_databases_entries(&self.name, &rows, sep))
            .unwrap_or_else(|e| {
                databases
                    .iter()
                    .map(|d| self.format_databases_error(d, &e, sep))
                    .collect::<Vec<String>>()
                    .join("")
            })
    }

    fn format_databases_error(&self, d: &str, e: &anyhow::Error, sep: char) -> String {
        format!(
            "{}{sep}{}{sep}{:?}{}\n",
            self.name,
            d.replace(' ', "_"),
            e,
            format!("{sep}-").repeat(3),
        )
    }

    /// doesn't return error - the same behavior as plugin
    pub async fn generate_databases(&self, client: &mut Client) -> Vec<String> {
        let result = run_query(client, queries::QUERY_DATABASE_NAMES)
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

    /// Todo(sk): write a test
    pub async fn generate_clusters_section(
        &self,
        endpoint: &Endpoint,
        databases: &Vec<String>,
        sep: char,
    ) -> String {
        let format_error = |d: &str, e: &anyhow::Error| {
            format!(
                "{}{sep}{}{sep}{sep}{sep}{:?}\n",
                self.name,
                d.replace(' ', "_"),
                e
            )
        };
        let mut result = String::new();
        for d in databases {
            match self.create_client(endpoint, Some(d.clone())).await {
                Ok(mut c) => match self.generate_clusters_entry(&mut c, d, sep).await {
                    Ok(None) => {}
                    Ok(Some(entry)) => result += &entry,
                    Err(err) => result += &format_error(d, &err),
                },
                Err(err) => {
                    result += &format_error(d, &err);
                }
            }
        }
        result
    }

    async fn generate_clusters_entry(
        &self,
        client: &mut Client,
        d: &str,
        sep: char,
    ) -> Result<Option<String>> {
        if !self.is_database_clustered(client).await? {
            return Ok(None);
        }
        let nodes = self.get_database_cluster_nodes(client).await?;
        let active_node = self.get_database_cluster_active_node(client).await?;
        Ok(Some(format!(
            "{}{sep}{}{sep}{}{sep}{}",
            self.name,
            d.replace(' ', "_"),
            active_node,
            nodes
        )))
    }

    async fn is_database_clustered(&self, client: &mut Client) -> Result<bool> {
        let rows = &run_query(client, queries::QUERY_IS_CLUSTERED)
            .await
            .and_then(validate_rows)?;
        Ok(&rows[0][0].get_value_by_name("is_clustered") != "0")
    }

    async fn get_database_cluster_nodes(&self, client: &mut Client) -> Result<String> {
        let rows = &run_query(client, queries::QUERY_CLUSTER_NODES).await?;
        if !rows.is_empty() && !rows[0].is_empty() {
            return Ok(rows[0]
                .iter()
                .map(|r| r.get_value_by_name("nodename"))
                .collect::<Vec<String>>()
                .join(","));
        }
        Ok("".to_string())
    }

    async fn get_database_cluster_active_node(&self, client: &mut Client) -> Result<String> {
        let rows = &run_query(client, queries::QUERY_CLUSTER_ACTIVE_NODES).await?;
        if !rows.is_empty() && !rows[0].is_empty() {
            return Ok(rows[0]
                .last() // as in legacy plugin
                .expect("impossible")
                .get_value_by_name("active_node"));
        }
        Ok("-".to_string())
    }

    pub async fn generate_connections_section(
        &self,
        client: &mut Client,
        query: &str,
        sep: char,
    ) -> String {
        run_query(client, query)
            .await
            .map(|rows| self.to_connections_entries(&rows, sep))
            .unwrap_or_else(|e| format!("{}{sep}{:?}\n", self.name, e))
    }

    fn to_connections_entries(&self, rows: &[Vec<Row>], sep: char) -> String {
        if rows.is_empty() {
            return String::new();
        }
        let rows = &rows[0];
        rows.iter()
            .map(|row| {
                format!(
                    "{}{sep}{}{sep}{}\n",
                    self.name,
                    row.get_value_by_idx(0).replace(' ', "_"), // for unknown reason we can't get it by name
                    row.get_bigint_by_name("NumberOfConnections")
                )
            })
            .collect::<Vec<String>>()
            .join("")
    }

    /// NOTE: uses ' ' instead of '\t' in error messages
    pub async fn generate_query_section(
        &self,
        endpoint: &Endpoint,
        section: &Section,
        query: Option<&str>,
    ) -> String {
        match self.create_client(endpoint, section.main_db()).await {
            Ok(mut c) => {
                let q = section.query_selector(query).unwrap_or_default();
                run_query(&mut c, q)
                    .await
                    .and_then(|r| section.validate_rows(r))
                    .map(|rows| {
                        format!(
                            "{}{}",
                            section.first_line(|| format!("{}\n", &self.name)),
                            self.to_entries(rows, section.sep())
                        )
                    })
                    .unwrap_or_else(|e| format!("{} {:?}\n", self.name, e))
            }
            Err(err) => format!("{} {:?}\n", self.name, err),
        }
    }

    /// rows must be not empty
    fn to_entries(&self, rows: Vec<Vec<Row>>, sep: char) -> String {
        // just a safety guard, the function should not get empty rows
        if rows.is_empty() {
            return String::new();
        }

        let mut r = rows;
        let rows = r.remove(0);
        let result = rows
            .into_iter()
            .map(|r| r.get_all(sep))
            .collect::<Vec<String>>()
            .join("\n");

        if result.is_empty() {
            result
        } else {
            result + "\n"
        }
    }

    fn process_blocked_sessions_rows(&self, rows: &[Vec<Row>], sep: char) -> String {
        let rows = &rows[0];
        rows.iter()
            .map(|row| to_blocked_session_entry(&self.name, row, sep))
            .collect::<Vec<String>>()
            .join("")
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

    fn process_backup_rows(&self, rows: &Vec<Vec<Row>>, databases: &[String], sep: char) -> String {
        let (mut ready, missing_data) = self.process_backup_rows_partly(rows, databases, sep);
        let missing: Vec<String> = self.process_missing_backup_rows(&missing_data, sep);
        ready.extend(missing);
        ready.join("")
    }

    /// generates lit of correct backup entries + list of missing required backups
    fn process_backup_rows_partly(
        &self,
        rows: &Vec<Vec<Row>>,
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

fn to_transaction_logs_entries(
    instance_name: &str,
    database_name: &str,
    rows: &[Vec<Row>],
    sep: char,
) -> String {
    if rows.is_empty() {
        return String::new();
    }
    rows[0]
        .iter()
        .map(|row| to_transaction_logs_entry(row, instance_name, database_name, sep))
        .collect::<Vec<String>>()
        .join("")
}

fn to_transaction_logs_entry(
    row: &Row,
    instance_name: &str,
    database_name: &str,
    sep: char,
) -> String {
    let name = row.get_value_by_name("name");
    let physical_name = row.get_value_by_name("physical_name");
    let max_size = row.get_bigint_by_name("MaxSize");
    let allocated_size = row.get_bigint_by_name("AllocatedSize");
    let used_size = row.get_bigint_by_name("UsedSize");
    let unlimited = row.get_bigint_by_name("Unlimited");
    format!(
        "{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}\n",
        instance_name,
        database_name.replace(' ', "_"),
        name,
        physical_name,
        max_size,
        allocated_size,
        used_size,
        unlimited
    )
}

fn to_datafiles_entries(
    instance_name: &str,
    database_name: &str,
    rows: &[Vec<Row>],
    sep: char,
) -> String {
    if rows.is_empty() {
        return String::new();
    }
    rows[0]
        .iter()
        .map(|row| to_datafiles_entry(row, instance_name, database_name, sep))
        .collect::<Vec<String>>()
        .join("")
}

fn to_datafiles_entry(row: &Row, instance_name: &str, database_name: &str, sep: char) -> String {
    let name = row.get_value_by_name("name");
    let physical_name = row.get_value_by_name("physical_name");
    let max_size = row.get_bigint_by_name("MaxSize");
    let allocated_size = row.get_bigint_by_name("AllocatedSize");
    let used_size = row.get_bigint_by_name("UsedSize");
    let unlimited = row.get_bigint_by_name("Unlimited");
    format!(
        "{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}\n",
        instance_name,
        database_name.replace(' ', "_"),
        name.replace(' ', "_"),
        physical_name.replace(' ', "_"),
        max_size,
        allocated_size,
        used_size,
        unlimited
    )
}

fn to_databases_entries(instance_name: &str, rows: &[Vec<Row>], sep: char) -> String {
    if rows.is_empty() {
        return String::new();
    }
    rows[0]
        .iter()
        .map(|row| to_databases_entry(row, instance_name, sep))
        .collect::<Vec<String>>()
        .join("")
}

fn to_databases_entry(row: &Row, instance_name: &str, sep: char) -> String {
    let name = row.get_value_by_name("name");
    let status = row.get_value_by_name("Status");
    let recovery = row.get_value_by_name("Recovery");
    let auto_close = row.get_bigint_by_name("auto_close");
    let auto_shrink = row.get_bigint_by_name("auto_shrink");
    format!(
        "{}{sep}{}{sep}{}{sep}{}{sep}{}{sep}{}\n",
        instance_name,
        name.replace(' ', "_").trim(),
        status.trim(),
        recovery.trim(),
        auto_close,
        auto_shrink,
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

impl<'a> Column<'a> for Row {
    fn get_bigint_by_idx(&self, idx: usize) -> i64 {
        self.try_get::<i64, usize>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
    }

    fn get_bigint_by_name(&self, idx: &str) -> i64 {
        self.try_get::<i64, &str>(idx)
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

    /// more or less correct method to extract all data from the tiberius.Row
    /// unfortunately tiberius::Row implements only into_iter -> we are using `self``, not `&self``
    fn get_all(self, sep: char) -> String {
        self.into_iter()
            .map(|c| match c {
                ColumnData::Guid(v) => v
                    .map(|v| format!("{{{}}}", v.to_string().to_uppercase()))
                    .unwrap_or_default(),
                ColumnData::I16(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::I32(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::F32(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::F64(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::Bit(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::U8(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::String(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::Numeric(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                _ => format!("Unsupported '{:?}'", c),
            })
            .collect::<Vec<String>>()
            .join(&sep.to_string())
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
        section::get_work_sections(ms_sql)
            .iter()
            .map(Section::to_header)
            .collect::<Vec<String>>()
            .join("")
    }
}

/// Generate header for each section without any data
async fn generate_instances_data(ms_sql: &config::ms_sql::Config) -> Result<String> {
    let instances = discovery_instances(ms_sql)
        .await?
        .into_iter()
        .filter(|i| ms_sql.is_instance_allowed(&i.name))
        .collect::<Vec<InstanceEngine>>();

    let section = Section::new(section::INSTANCE_SECTION_NAME);
    let result = section.to_header() // as in old plugin
     + &instances
        .iter()
        .flat_map(|i| [section.to_header(), i.generate_leading_entry(section.sep())])
        .collect::<Vec<String>>()
        .join("");

    let sections = section::get_work_sections(ms_sql);
    Ok(result + &generate_result(&instances, &sections, ms_sql).await?)
}

async fn discovery_instances(ms_sql: &config::ms_sql::Config) -> Result<Vec<InstanceEngine>> {
    let instances = if ms_sql.discovery().detect() {
        get_instance_engines(&ms_sql.endpoint()).await?
    } else {
        Vec::new()
    };

    Ok(instances)
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
        .map(move |instance| instance.generate_sections(ms_sql, sections));

    // processing here
    let results = stream::iter(tasks)
        .buffer_unordered(6) // MAX_CONCURRENT is the limit of concurrent tasks you want to allow.
        .collect::<Vec<_>>()
        .await;

    Ok(results.join(""))
}

/// return Vec<Vec<Row>> as a Results Vec: one Vec<Row> per one statement in query.
pub async fn run_query(client: &mut Client, query: &str) -> Result<Vec<Answer>> {
    if query.is_empty() {
        log::error!("Empty query");
        anyhow::bail!("Empty query");
    }
    let start = Instant::now();
    let result = _run_query(client, query).await;
    log_query(start, &result, query);
    result
}

fn log_query(start: Instant, result: &Result<Vec<Answer>>, query: &str) {
    let total = (Instant::now() - start).as_millis();
    let q = short_query(query);
    match result {
        Ok(_) => log::info!("Query [SUCCESS], took {total} ms, `{q}`"),
        Err(err) => log::info!("Query [ERROR], took {total} ms, error: `{err}`, query: `{q}`",),
    }
}

async fn _run_query(client: &mut Client, query: &str) -> Result<Vec<Answer>> {
    log::debug!("Query to run: `{}`", short_query(query));
    let stream = Query::new(query).query(client).await?;
    let rows: Vec<Answer> = stream.into_results().await?;
    Ok(rows)
}

fn short_query(query: &str) -> String {
    query.to_owned()[0..std::cmp::max(16, query.len() - 1)].to_string()
}

/// return all MS SQL instances installed
async fn get_instance_engines(endpoint: &Endpoint) -> Result<Vec<InstanceEngine>> {
    let all = detect_instance_engines(endpoint).await?;
    Ok([&all.0[..], &all.1[..]].concat().to_vec())
}

/// [low level helper] return all MS SQL instances installed
pub async fn detect_instance_engines(
    endpoint: &Endpoint,
) -> Result<(Vec<InstanceEngine>, Vec<InstanceEngine>)> {
    let mut client = client::create_from_config(endpoint).await?;
    Ok((
        get_engines(&mut client, endpoint, &queries::get_instances_query()).await?,
        get_engines(&mut client, endpoint, &queries::get_32bit_instances_query()).await?,
    ))
}

/// return all MS SQL instances installed
async fn get_engines(
    client: &mut Client,
    endpoint: &Endpoint,
    query: &str,
) -> Result<Vec<InstanceEngine>> {
    let answers = run_query(client, query).await?;
    let computer_name = get_computer_name(client, queries::QUERY_COMPUTER_NAME)
        .await
        .unwrap_or_default();
    if let Some(rows) = answers.get(0) {
        Ok(to_engines(rows, endpoint, computer_name))
    } else {
        log::warn!("Empty answer by query: {query}");
        Ok(vec![])
    }
}

fn to_engines(
    rows: &Answer,
    endpoint: &Endpoint,
    computer_name: Option<String>,
) -> Vec<InstanceEngine> {
    rows.iter()
        .map(|r| {
            InstanceEngineBuilder::new()
                .row(r)
                .computer_name(&computer_name)
                .endpoint(endpoint)
                .build()
        })
        .collect::<Vec<InstanceEngine>>()
        .to_vec()
}

pub async fn get_computer_name(client: &mut Client, query: &str) -> Result<Option<String>> {
    let rows = run_query(client, query).await?;
    if rows.is_empty() || rows[0].is_empty() {
        log::warn!("Computer name not found with query {query}");
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
    use super::InstanceEngineBuilder;

    #[test]
    fn test_generate_state_entry() {
        let i = InstanceEngineBuilder::new().name("test_name").build();

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
