// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::client::{self, Client};
use super::section::{Section, SectionKind};
use crate::config::{
    self,
    ms_sql::{AuthType, CustomInstance, Endpoint},
    section::names,
    CheckConfig,
};
use crate::emit;
use crate::ms_sql::query::{get_computer_name, run_query, Answer, Column};
use crate::ms_sql::sqls;
use crate::setup::Env;
use crate::utils;

use anyhow::Result;
use futures::stream::{self, StreamExt};
use std::collections::{HashMap, HashSet};
use std::path::Path;

use tiberius::Row;

use super::defaults;

pub const SQL_LOGIN_ERROR_TAG: &str = "[SQL LOGIN ERROR]";
pub const SQL_TCP_ERROR_TAG: &str = "[SQL TCP ERROR]";

#[derive(Clone, Debug, Default)]
pub struct SqlInstanceBuilder {
    alias: Option<String>,
    pub name: Option<String>,
    id: Option<String>,
    edition: Option<String>,
    version: Option<String>,
    cluster: Option<String>,
    port: Option<u16>,
    dynamic_port: Option<u16>,
    endpoint: Option<Endpoint>,
    computer_name: Option<String>,
    environment: Option<Env>,
    hash: Option<String>,
    piggyback: Option<String>,
}

impl SqlInstanceBuilder {
    pub fn new() -> SqlInstanceBuilder {
        SqlInstanceBuilder::default()
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
    pub fn computer_name<S: ToString>(mut self, computer_name: &Option<S>) -> Self {
        self.computer_name = computer_name.as_ref().map(|s| s.to_string());
        self
    }

    pub fn environment(mut self, environment: &Env) -> Self {
        self.environment = environment.clone().into();
        self
    }
    pub fn hash<S: Into<String>>(mut self, hash: S) -> Self {
        self.hash = Some(hash.into());
        self
    }
    pub fn piggyback<S: Into<String>>(mut self, piggyback: Option<S>) -> Self {
        self.piggyback = piggyback.map(|s| s.into().to_lowercase());
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

    pub fn get_name(&self) -> String {
        self.name.clone().unwrap_or_default().to_uppercase()
    }

    pub fn get_endpoint(&self) -> Option<&Endpoint> {
        self.endpoint.as_ref()
    }

    pub fn get_port(&self) -> u16 {
        self.port.unwrap_or_else(|| self.dynamic_port.unwrap_or(0))
    }

    pub fn build(self) -> SqlInstance {
        SqlInstance {
            alias: self.alias,
            name: self.name.unwrap_or_default().to_uppercase(),
            id: self.id.unwrap_or_default(),
            edition: self.edition.unwrap_or_default(),
            version: self.version.unwrap_or_default(),
            cluster: self.cluster,
            port: self.port,
            dynamic_port: self.dynamic_port,
            available: None,
            endpoint: self.endpoint.unwrap_or_default(),
            computer_name: self.computer_name,
            environment: self.environment.unwrap_or_default(),
            hash: self.hash.unwrap_or_default(),
            piggyback: self.piggyback,
        }
    }
}

#[derive(Clone, Debug)]
pub struct SqlInstance {
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
    environment: Env,
    hash: String,
    piggyback: Option<String>,
}

impl AsRef<SqlInstance> for SqlInstance {
    fn as_ref(&self) -> &SqlInstance {
        self
    }
}

impl SqlInstance {
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

    pub fn hash(&self) -> &str {
        &self.hash
    }

    pub fn temp_dir(&self) -> Option<&Path> {
        self.environment.temp_dir()
    }

    pub fn piggyback(&self) -> &Option<String> {
        &self.piggyback
    }

    pub fn hostname(&self) -> String {
        self.endpoint.hostname()
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

    pub fn generate_header(&self) -> String {
        self.piggyback
            .as_ref()
            .map(|h| emit::piggyback_header(h))
            .unwrap_or_default()
            .to_owned()
    }

    pub fn generate_footer(&self) -> String {
        self.piggyback
            .as_ref()
            .map(|_| emit::piggyback_footer())
            .unwrap_or_default()
            .to_owned()
    }

    pub async fn generate_sections(
        &self,
        ms_sql: &config::ms_sql::Config,
        sections: &[Section],
    ) -> String {
        let mut result = self.generate_header();
        let endpoint = &ms_sql.endpoint();
        match self.create_client(endpoint, None).await {
            Ok(mut client) => {
                for section in sections.iter() {
                    result += &self.generate_section(&mut client, endpoint, section).await;
                }
            }
            Err(err) => {
                let instance_section = Section::make_instance_section(); // this is important section always present
                result += &instance_section.to_plain_header();
                result += &self.generate_state_entry(false, instance_section.sep());
                log::warn!("Can't access {} instance with err {err}\n", self.id);
            }
        };
        result += &self.generate_footer();
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
        let r = SqlInstanceProperties::obtain_by_query(client).await;
        match r {
            Ok(properties) => self.process_details_rows(&properties, sep),
            Err(err) => {
                log::error!("Failed to get sql instance properties: {}", err);
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
        let body = match self.read_data_from_cache(section.name(), section.cache_age() as u64) {
            Some(from_cache) => from_cache,
            None => {
                let from_sql = self.generate_section_body(client, endpoint, section).await;
                if section.kind() == &SectionKind::Async {
                    self.write_data_in_cache(section.name(), &from_sql);
                };
                from_sql
            }
        };
        section.to_work_header() + body.as_str()
    }

    async fn generate_section_body(
        &self,
        client: &mut Client,
        endpoint: &Endpoint,
        section: &Section,
    ) -> String {
        let sep = section.sep();
        match section.name() {
            names::INSTANCE => {
                self.generate_state_entry(true, section.sep())
                    + &self.generate_details_entry(client, section.sep()).await
            }
            names::COUNTERS => {
                self.generate_utc_entry(client, sep).await
                    + &self.generate_counters_entry(client, sep).await
            }
            names::BLOCKED => {
                self.generate_blocking_sessions_section(
                    client,
                    &sqls::get_blocking_sessions_query(),
                    sep,
                )
                .await
            }
            names::TABLE_SPACES => {
                let databases = self.generate_databases(client).await;
                self.generate_table_spaces_section(endpoint, &databases, sep)
                    .await
            }
            names::BACKUP => self.generate_backup_section(client, sep).await,
            names::TRANSACTION_LOG => {
                let databases = self.generate_databases(client).await;
                self.generate_transaction_logs_section(endpoint, &databases, sep)
                    .await
            }
            names::DATAFILES => {
                let databases = self.generate_databases(client).await;
                self.generate_datafiles_section(endpoint, &databases, sep)
                    .await
            }
            names::DATABASES => {
                self.generate_databases_section(client, sqls::QUERY_DATABASES, sep)
                    .await
            }
            names::CLUSTERS => {
                let databases = self.generate_databases(client).await;
                self.generate_clusters_section(endpoint, &databases, sep)
                    .await
            }
            names::CONNECTIONS => {
                self.generate_connections_section(client, sqls::QUERY_CONNECTIONS, sep)
                    .await
            }
            names::MIRRORING | names::JOBS | names::AVAILABILITY_GROUPS => {
                self.generate_query_section(endpoint, section, None).await
            }
            _ => format!("{} not implemented\n", section.name()).to_string(),
        }
    }

    fn read_data_from_cache(&self, name: &str, cache_age: u64) -> Option<String> {
        if cache_age == 0 {
            return None;
        }
        if let Some(path) = self
            .environment
            .obtain_cache_sub_dir(self.hash())
            .map(|d| d.join(self.make_cache_entry_name(name)))
        {
            match utils::get_modified_age(&path) {
                Ok(file_age) if file_age <= cache_age => {
                    log::info!("Cache file {path:?} is new enough for {cache_age} cache_age",);
                    std::fs::read_to_string(&path)
                        .map_err(|e| {
                            log::error!("{e} reading cache file {:?}", &path);
                            e
                        })
                        .ok()
                }
                _ => None,
            }
        } else {
            None
        }
    }

    fn write_data_in_cache(&self, name: &str, body: &str) {
        if let Some(dir) = self.environment.obtain_cache_sub_dir(self.hash()) {
            let file_name = self.make_cache_entry_name(name);
            std::fs::write(dir.join(file_name), body)
                .unwrap_or_else(|e| log::error!("Error {e} writing cache"));
        }
    }

    fn make_cache_entry_name(&self, name: &str) -> String {
        format!("{};{};{}.mssql", self.hostname(), self.name, name)
    }

    pub async fn generate_counters_entry(&self, client: &mut Client, sep: char) -> String {
        let x = run_query(client, sqls::QUERY_COUNTERS)
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
                    result += &run_query(&mut c, sqls::QUERY_SPACE_USED)
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

    pub async fn generate_backup_section(&self, client: &mut Client, sep: char) -> String {
        let databases = self.generate_databases(client).await;

        let result = run_query(client, sqls::QUERY_BACKUP)
            .await
            .map(|rows| self.process_backup_rows(&rows, &databases, sep));
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
                    result += &run_query(&mut c, sqls::QUERY_TRANSACTION_LOGS)
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
                    result += &run_query(&mut c, sqls::QUERY_DATAFILES)
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
    ) -> String {
        let databases = self.generate_databases(client).await;
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
        let result = run_query(client, sqls::QUERY_DATABASE_NAMES)
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
        let rows = &run_query(client, sqls::QUERY_IS_CLUSTERED)
            .await
            .and_then(validate_rows)?;
        Ok(&rows[0][0].get_value_by_name("is_clustered") != "0")
    }

    async fn get_database_cluster_nodes(&self, client: &mut Client) -> Result<String> {
        let rows = &run_query(client, sqls::QUERY_CLUSTER_NODES).await?;
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
        let rows = &run_query(client, sqls::QUERY_CLUSTER_ACTIVE_NODES).await?;
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
        let result = run_query(client, sqls::QUERY_UTC)
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
        let utc = row[0].get_value_by_name(sqls::QUERY_UTC_TIME_PARAM);
        Ok(format!("None{sep}utc_time{sep}None{sep}{utc}\n"))
    }

    fn process_databases_rows(&self, rows: &[Vec<Row>]) -> Vec<String> {
        let row = &rows[0];
        row.iter()
            .map(|row| row.get_value_by_idx(0))
            .collect::<Vec<String>>()
    }

    fn process_details_rows(&self, properties: &SqlInstanceProperties, sep: char) -> String {
        format!(
            "{}{sep}details{sep}{}{sep}{}{sep}{}\n",
            self.mssql_name(),
            properties.version,
            properties.product_level,
            properties.edition
        )
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

    pub fn computer_name(&self) -> &Option<String> {
        &self.computer_name
    }
}

#[derive(Debug)]
pub struct SqlInstanceProperties {
    pub name: String,
    pub version: String,
    pub machine_name: String,
    pub edition: String,
    pub product_level: String,
    pub net_bios: String,
}

impl From<&Vec<Row>> for SqlInstanceProperties {
    fn from(row: &Vec<Row>) -> Self {
        let row = &row[0];
        let name = row.get_value_by_name("InstanceName");
        let version = row.get_value_by_name("ProductVersion");
        let machine_name = row.get_value_by_name("MachineName");
        let edition = row.get_value_by_name("Edition");
        let product_level = row.get_value_by_name("ProductLevel");
        let net_bios = row.get_value_by_name("NetBios");
        Self {
            name: if name.is_empty() {
                "MSSQLSERVER".to_string()
            } else {
                name
            },
            version,
            machine_name,
            edition,
            product_level,
            net_bios,
        }
    }
}

impl SqlInstanceProperties {
    pub async fn obtain_by_query(client: &mut Client) -> Result<Self> {
        let r = run_query(client, sqls::QUERY_INSTANCE_PROPERTIES).await?;
        if r.is_empty() {
            anyhow::bail!(
                "Empty answer from server on query {}",
                sqls::QUERY_INSTANCE_PROPERTIES
            );
        }
        Ok(Self::from(&r[0]))
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

struct Counter {
    name: String,
    object: String,
    instance: String,
    value: String,
}

impl From<&Row> for Counter {
    fn from(row: &Row) -> Self {
        Self {
            name: row.get_value_by_idx(0).trim().replace(' ', "_").to_string(),
            object: row
                .get_value_by_idx(1)
                .trim()
                .replace([' ', '$'], "_")
                .to_string(),
            instance: row.get_value_by_idx(2).trim().replace(' ', "_").to_string(),
            value: row.get_bigint_by_idx(3).to_string(),
        }
    }
}

impl Counter {
    pub fn into_string(self, sep: char) -> String {
        format!(
            "{}{sep}{}{sep}{}{sep}{}\n",
            self.object,
            self.name,
            if self.instance.is_empty() {
                "None"
            } else {
                &self.instance
            },
            self.value
        )
    }
}

fn to_counter_entry(row: &Row, sep: char) -> String {
    let counter = Counter::from(row);
    counter.into_string(sep)
}

fn to_blocked_session_entry(instance_name: &str, row: &Row, sep: char) -> String {
    let session_id = row.get_value_by_idx(0).trim().to_string();
    let wait_duration_ms = row.get_bigint_by_idx(1).to_string();
    let wait_type = row.get_value_by_idx(2).trim().to_string();
    let blocking_session_id = row.get_value_by_idx(3).trim().to_string();
    format!("{instance_name}{sep}{session_id}{sep}{wait_duration_ms}{sep}{wait_type}{sep}{blocking_session_id}\n",)
}

impl CheckConfig {
    pub async fn exec(&self, environment: &Env) -> Result<String> {
        if let Some(ms_sql) = self.ms_sql() {
            CheckConfig::prepare_cache_sub_dir(environment, ms_sql.hash());
            log::info!("Generating main data");
            let data = generate_data(ms_sql, environment)
                .await
                .unwrap_or_else(|e| {
                    log::error!("Error generating data: {e}");
                    format!("{e}\n")
                });
            let mut output: Vec<String> = Vec::new();
            for config in ms_sql.configs() {
                log::info!("Generating configs data");
                CheckConfig::prepare_cache_sub_dir(environment, config.hash());
                let configs_data = generate_data(config, environment)
                    .await
                    .unwrap_or_else(|e| {
                        log::error!("Error generating data: {e}");
                        format!("{e}\n")
                    });
                output.push(configs_data);
            }
            Ok(data + &output.join(""))
        } else {
            log::error!("No config");
            anyhow::bail!("No Config")
        }
    }

    fn prepare_cache_sub_dir(environment: &Env, hash: &str) {
        match environment.obtain_cache_sub_dir(hash).map(utils::touch_dir) {
            Some(Err(e)) => log::error!("Error touching dir: {e}, caching may be not possible"),
            Some(Ok(p)) => log::info!("Using cache dir {p:?}"),
            None => log::warn!("No cache dir defined, caching is not possible"),
        }
    }
}

/// Generate header for each section without any data, see vbs plugin
fn generate_dumb_header(ms_sql: &config::ms_sql::Config) -> String {
    ms_sql
        .valid_sections()
        .iter()
        .map(|s| Section::new(s, ms_sql.cache_age()).to_plain_header())
        .collect::<Vec<_>>()
        .join("")
}

fn generate_signaling_blocks(ms_sql: &config::ms_sql::Config, instances: &[SqlInstance]) -> String {
    instances
        .iter()
        .map(|i| i.piggyback().as_deref().unwrap_or_default().to_string())
        .collect::<HashSet<String>>()
        .into_iter()
        .map(|h| generate_signaling_block(ms_sql, &h))
        .collect::<Vec<String>>()
        .join("")
}

fn generate_signaling_block(ms_sql: &config::ms_sql::Config, piggyback_host: &str) -> String {
    let body = generate_dumb_header(ms_sql) + &Section::make_instance_section().to_plain_header();
    if piggyback_host.is_empty() {
        body
    } else {
        emit::piggyback_header(piggyback_host) + &body + &emit::piggyback_footer()
    }
}

/// Generate data as defined by config
/// Consists from two parts: instance entries + sections for every instance
async fn generate_data(ms_sql: &config::ms_sql::Config, environment: &Env) -> Result<String> {
    let instances = find_usable_instances(ms_sql, environment).await?;
    if instances.is_empty() {
        return Ok("ERROR: Failed to gather SQL server instances".to_string());
    } else {
        log::info!("Found {} SQL server instances", instances.len())
    }

    let sections = ms_sql
        .valid_sections()
        .into_iter()
        .map(|s| Section::new(s, ms_sql.cache_age()))
        .collect::<Vec<_>>();

    Ok(generate_signaling_blocks(ms_sql, &instances)
        + &generate_instance_entries(&instances)
        + &generate_result(&instances, &sections, ms_sql).await?)
}

fn generate_instance_entries<P: AsRef<SqlInstance>>(instances: &[P]) -> String {
    instances
        .iter()
        .map(|i| generate_instance_entry(i.as_ref()))
        .collect::<Vec<String>>()
        .join("")
}

fn generate_instance_entry<P: AsRef<SqlInstance>>(instance: &P) -> String {
    let section = Section::make_instance_section();
    [
        instance.as_ref().generate_header(),
        section.to_plain_header(),
        instance.as_ref().generate_leading_entry(section.sep()),
        instance.as_ref().generate_footer(),
    ]
    .into_iter()
    .filter(|s| !s.is_empty())
    .collect::<Vec<_>>()
    .join("")
}

async fn find_usable_instances(
    ms_sql: &config::ms_sql::Config,
    environment: &Env,
) -> Result<Vec<SqlInstance>> {
    let builders = find_usable_instance_builders(ms_sql).await?;
    if builders.is_empty() {
        return Ok(Vec::new());
    } else {
        log::info!("Found {} SQL server instances", builders.len());
    }

    Ok(builders
        .into_iter()
        .map(|b: SqlInstanceBuilder| b.environment(environment).hash(ms_sql.hash()).build())
        .collect::<Vec<SqlInstance>>())
}

async fn find_usable_instance_builders(
    ms_sql: &config::ms_sql::Config,
) -> Result<Vec<SqlInstanceBuilder>> {
    Ok(find_all_instance_builders(ms_sql)
        .await?
        .into_iter()
        .filter(|i| ms_sql.is_instance_allowed(&i.get_name()))
        .collect::<Vec<SqlInstanceBuilder>>())
}

pub async fn find_all_instance_builders(
    ms_sql: &config::ms_sql::Config,
) -> Result<Vec<SqlInstanceBuilder>> {
    let detected = if ms_sql.discovery().detect() {
        find_detectable_instance_builders(ms_sql).await
    } else {
        ms_sql
            .discovery()
            .include()
            .iter()
            .map(|name| SqlInstanceBuilder::new().name(name))
            .collect()
    };
    let customizations: HashMap<&String, &CustomInstance> =
        ms_sql.instances().iter().map(|i| (i.sid(), i)).collect();
    let builders = apply_customizations(detected, &customizations);
    add_custom_instance_builders(builders, &customizations).await
}

/// find instances described in the config but not detected by the discovery
async fn find_detectable_instance_builders(
    ms_sql: &config::ms_sql::Config,
) -> Vec<SqlInstanceBuilder> {
    get_instance_builders(&ms_sql.endpoint())
        .await
        .unwrap_or_else(|e| {
            log::warn!("Error discovering instances: {e}");
            vec![]
        })
}

/// find instances described in the config but not detected by the discovery
/// may NOT work - should be approved during testing
async fn add_custom_instance_builders(
    builders: Vec<SqlInstanceBuilder>,
    customizations: &HashMap<&String, &CustomInstance>,
) -> Result<Vec<SqlInstanceBuilder>> {
    let reconnects = determine_reconnect(builders, customizations);

    let mut builders: Vec<SqlInstanceBuilder> = Vec::new();
    for (builder, endpoint) in reconnects.into_iter() {
        if let Some(endpoint) = endpoint {
            if let Some(b) = get_custom_instance_builder(&builder, &endpoint).await {
                builders.push(b);
            }
        } else {
            builders.push(builder);
        }
    }
    Ok(builders)
}

async fn get_custom_instance_builder(
    builder: &SqlInstanceBuilder,
    endpoint: &Endpoint,
) -> Option<SqlInstanceBuilder> {
    let port = get_reasonable_port(builder, endpoint);
    let instance_name = &builder.get_name();
    match client::create_on_endpoint_port(endpoint, port).await {
        Ok(mut client) => {
            let b = obtain_properties(&mut client, instance_name)
                .await
                .map(|p| to_instance_builder(endpoint, &p));
            if b.is_none() {
                log::info!("Instance `{instance_name}` not found. Try to find it");
                find_custom_instance(endpoint, instance_name).await
            } else {
                b
            }
        }
        Err(e) => {
            log::error!("Error creating client for `{instance_name}`: {e}");
            None
        }
    }
}

async fn find_custom_instance(
    endpoint: &Endpoint,
    instance_name: &str,
) -> Option<SqlInstanceBuilder> {
    let builders = get_instance_builders(endpoint).await.unwrap_or_else(|e| {
        log::error!("Error creating client for instance `{instance_name}`: {e}",);
        Vec::<SqlInstanceBuilder>::new()
    });
    match detect_instance_port(instance_name, &builders) {
        Some(port) => {
            if let Ok(mut client) = client::create_on_endpoint_port(endpoint, port).await {
                obtain_properties(&mut client, instance_name)
                    .await
                    .map(|p| to_instance_builder(endpoint, &p))
            } else {
                None
            }
        }
        _ => {
            log::error!(
                "Impossible to detect port for `{instance_name}` known: `{}`",
                builders
                    .iter()
                    .map(|i| i.get_name())
                    .collect::<Vec<String>>()
                    .join(", ")
            );
            None
        }
    }
}

fn detect_instance_port(name: &str, builders: &[SqlInstanceBuilder]) -> Option<u16> {
    builders
        .iter()
        .find(|b| b.get_name() == name)
        .map(|b| b.get_port())
}

fn get_reasonable_port(builder: &SqlInstanceBuilder, endpoint: &Endpoint) -> u16 {
    if builder.get_port() == 0 {
        log::info!("Connecting using port from endpoint {}", endpoint.port());
        endpoint.port()
    } else {
        log::info!(
            "Connecting using port from detection {}",
            builder.get_port()
        );
        builder.get_port()
    }
}

async fn obtain_properties(client: &mut Client, name: &str) -> Option<SqlInstanceProperties> {
    match SqlInstanceProperties::obtain_by_query(client).await {
        Ok(properties) => {
            if properties.name == *name {
                log::info!("Custom instance `{name}` added");
                return Some(properties);
            }
            log::error!(
                "Wrong instance: expected `{name}` but found `{}`",
                properties.name
            );
        }
        Err(e) => {
            log::error!("Error accessing instance `{name}` with error: {e:?}");
        }
    }
    None
}

/// converts detected instance and custom instance to SqlInstanceBuilder
fn to_instance_builder(
    endpoint: &Endpoint,
    properties: &SqlInstanceProperties,
) -> SqlInstanceBuilder {
    SqlInstanceBuilder::new()
        .name(properties.name.to_uppercase())
        .computer_name(&Some(properties.machine_name.clone()))
        .version(&properties.version)
        .edition(&properties.edition)
        .port(Some(endpoint.conn().port()))
}
/// returns
/// - SQL instances with custom endpoint if any
fn determine_reconnect(
    builders: Vec<SqlInstanceBuilder>,
    customizations: &HashMap<&String, &CustomInstance>,
) -> Vec<(SqlInstanceBuilder, Option<Endpoint>)> {
    let mut found: HashSet<String> = HashSet::new();
    let mut b = builders
        .into_iter()
        .map(|instance_builder| {
            found.insert(instance_builder.get_name());
            match customizations.get(&instance_builder.get_name()) {
                Some(customization)
                    if Some(&customization.endpoint()) != instance_builder.get_endpoint() =>
                {
                    log::info!(
                        "Instance {} to be reconnected `{:?}` `{:?}`",
                        instance_builder.get_name(),
                        customization.endpoint(),
                        instance_builder.get_endpoint()
                    );
                    (instance_builder, Some(customization.endpoint()))
                }
                _ => {
                    log::info!(
                        "Add detected instance {} reconnect not required ",
                        &instance_builder.get_name()
                    );
                    (instance_builder, None)
                }
            }
        })
        .collect::<Vec<(SqlInstanceBuilder, Option<Endpoint>)>>();

    customizations
        .iter()
        .filter(|(&k, _)| !found.contains(k))
        .map(|(name, customization)| {
            log::info!("Add custom instance {} ", name);
            let builder = SqlInstanceBuilder::new().name(name.to_uppercase());
            (
                apply_customization(builder, customization),
                Some(customization.endpoint()),
            )
        })
        .for_each(|a| b.push(a));

    b
}

fn apply_customizations(
    detected: Vec<SqlInstanceBuilder>,
    customizations: &HashMap<&String, &CustomInstance>,
) -> Vec<SqlInstanceBuilder> {
    detected
        .into_iter()
        .map(
            |instance_builder| match customizations.get(&instance_builder.get_name()) {
                Some(customization) => apply_customization(instance_builder, customization),
                None => instance_builder.clone(),
            },
        )
        .collect::<Vec<SqlInstanceBuilder>>()
}

fn apply_customization(
    builder: SqlInstanceBuilder,
    customization: &CustomInstance,
) -> SqlInstanceBuilder {
    builder
        .piggyback(customization.piggyback().map(|p| p.hostname()))
        .alias(
            customization
                .alias()
                .map(|i| str::to_string(i))
                .unwrap_or_default(),
        )
}

/// Intelligent async processing of the data
async fn generate_result(
    instances: &[SqlInstance],
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

/// return all MS SQL instances installed
async fn get_instance_builders(endpoint: &Endpoint) -> Result<Vec<SqlInstanceBuilder>> {
    let all = obtain_instance_builders_from_registry(endpoint).await?;
    Ok([&all.0[..], &all.1[..]].concat().to_vec())
}

// TODO(sk):probably SQL is better as registry
/// [low level helper] return all MS SQL instances installed
pub async fn obtain_instance_builders_from_registry(
    endpoint: &Endpoint,
) -> Result<(Vec<SqlInstanceBuilder>, Vec<SqlInstanceBuilder>)> {
    match client::create_on_endpoint(endpoint).await {
        Ok(mut client) => Ok((
            exec_win_registry_sql_instances_query(
                &mut client,
                endpoint,
                &sqls::get_win_registry_instances_query(),
            )
            .await?,
            exec_win_registry_sql_instances_query(
                &mut client,
                endpoint,
                &sqls::get_wow64_32_registry_instances_query(),
            )
            .await?,
        )),
        Err(err) => {
            log::error!("Failed to create client: {err}");
            anyhow::bail!("Failed to create client: {err}")
        }
    }
}

/// return all MS SQL instances installed
async fn exec_win_registry_sql_instances_query(
    client: &mut Client,
    endpoint: &Endpoint,
    query: &str,
) -> Result<Vec<SqlInstanceBuilder>> {
    let answers = run_query(client, query).await?;
    if let Some(rows) = answers.get(0) {
        let computer_name = get_computer_name(client, sqls::QUERY_COMPUTER_NAME)
            .await
            .unwrap_or_default();
        let instances = to_sql_instance(rows, endpoint, computer_name);
        log::info!("Instances found {}", instances.len());
        Ok(instances)
    } else {
        log::warn!("Empty answer by query: {query}");
        Ok(vec![])
    }
}

fn to_sql_instance(
    rows: &Answer,
    endpoint: &Endpoint,
    computer_name: Option<String>,
) -> Vec<SqlInstanceBuilder> {
    rows.iter()
        .map(|r| {
            SqlInstanceBuilder::new()
                .row(r)
                .computer_name(&computer_name)
                .endpoint(endpoint)
        })
        .collect::<Vec<SqlInstanceBuilder>>()
        .to_vec()
}

#[cfg(test)]
mod tests {
    use super::{
        generate_instance_entries, generate_signaling_blocks, SqlInstance, SqlInstanceBuilder,
    };
    use crate::args::Args;
    use crate::setup::Env;
    use std::path::Path;

    #[test]
    fn test_generate_state_entry() {
        let i = SqlInstanceBuilder::new().name("test_name").build();

        assert_eq!(
            i.generate_state_entry(false, '.'),
            format!("MSSQL_TEST_NAME.state.0\n")
        );
        assert_eq!(
            i.generate_state_entry(true, '.'),
            format!("MSSQL_TEST_NAME.state.1\n")
        );
    }

    fn make_instances() -> Vec<SqlInstance> {
        let builders = vec![
            SqlInstanceBuilder::new().name("A"),
            SqlInstanceBuilder::new().name("B").piggyback(Some("Y")),
        ];

        builders
            .into_iter()
            .map(|b: SqlInstanceBuilder| b.build())
            .collect::<Vec<SqlInstance>>()
    }
    #[test]
    fn test_instance_entries() {
        let instances = make_instances();
        assert_eq!(
            generate_instance_entries(&instances),
            "\
             <<<mssql_instance:sep(124)>>>\n\
             MSSQL_A|config|||\n\
             <<<<y>>>>\n\
             <<<mssql_instance:sep(124)>>>\n\
             MSSQL_B|config|||\n\
             <<<<>>>>\n\
             "
        );
    }

    #[test]
    fn test_signaling_blocks() {
        const CONFIG_WITH_INSTANCES: &str = r#"---
mssql:
  main: # mandatory, to be used if no specific config
    authentication: # mandatory
      username: u # mandatory
      password: u
      type: sql_server
    connection:
      hostname: am
    sections:
      - instance:
      - backup:
          is_async: yes
      - counters:
          disabled: yes
    discovery:
      detect: no
      include: [ "A", "B"]
    instances:
      - sid: "B"
        piggyback:
          hostname: Y
"#;
        // blocks below may follow in any order
        const EXPECTED_OK_BLOCK: &str = "\
        <<<mssql_instance>>>\n\
        <<<mssql_backup>>>\n\
        <<<mssql_instance:sep(124)>>>\n\
        ";
        const EXPECTED_PB_BLOCK: &str = "\
        <<<<y>>>>\n\
        <<<mssql_instance>>>\n\
        <<<mssql_backup>>>\n\
        <<<mssql_instance:sep(124)>>>\n\
        <<<<>>>>\n\
        ";
        let ms_sql = crate::config::ms_sql::Config::from_string(CONFIG_WITH_INSTANCES)
            .unwrap()
            .unwrap();
        let instances = make_instances();
        let blocks = generate_signaling_blocks(&ms_sql, &instances);
        assert!(blocks.contains(EXPECTED_OK_BLOCK));
        assert!(blocks.contains(EXPECTED_PB_BLOCK));
        assert_eq!(
            blocks.len(),
            EXPECTED_OK_BLOCK.len() + EXPECTED_PB_BLOCK.len()
        );
    }

    #[test]
    fn test_instance_header_footer() {
        let normal = SqlInstanceBuilder::new().name("test_name").build();
        assert_eq!(normal.generate_header(), "");
        assert_eq!(normal.generate_footer(), "");
        let piggyback = SqlInstanceBuilder::new()
            .name("test_name")
            .piggyback(Some("Y"))
            .build();
        assert_eq!(piggyback.generate_header(), "<<<<y>>>>\n");
        assert_eq!(piggyback.generate_footer(), "<<<<>>>>\n");
    }

    #[test]
    fn test_sql_builder() {
        let args = Args {
            temp_dir: Some(".".into()),
            ..Default::default()
        };
        let standard = SqlInstanceBuilder::new()
            .name("name")
            .alias("alias")
            .dynamic_port(Some(1u16))
            .port(Some(2u16))
            .computer_name(&Some("computer_name".to_owned()))
            .hash("hash")
            .version("version")
            .edition("edition")
            .environment(&Env::new(&args))
            .id("id")
            .piggyback(Some("piggYback"));
        let cluster = standard.clone().cluster(Some("cluster"));
        assert_eq!(standard.get_port(), 2u16);

        let s = standard.build();
        assert_eq!(s.id, "id");
        assert_eq!(s.name, "NAME");
        assert_eq!(s.alias.as_deref(), Some("alias"));
        assert!(s.cluster.is_none());
        assert_eq!(s.version, "version");
        assert_eq!(s.edition, "edition");
        assert_eq!(s.hash, "hash");
        assert_eq!(s.port, Some(2u16));
        assert_eq!(s.dynamic_port, Some(1u16));

        assert_eq!(s.piggyback().as_deref(), Some("piggyback"));
        assert_eq!(s.computer_name().as_deref(), Some("computer_name"));
        assert_eq!(s.temp_dir(), Some(Path::new(".")));
        assert_eq!(s.full_name(), "localhost/NAME");
        assert_eq!(s.mssql_name(), "MSSQL_NAME");
        assert_eq!(s.legacy_name(), "computer_name/NAME");
        assert_eq!(
            s.generate_leading_entry('.'),
            "MSSQL_NAME.config.version.edition.\n"
        );
        let c = cluster.build();
        assert_eq!(c.cluster.as_deref(), Some("cluster"));
        assert_eq!(c.legacy_name(), "cluster/NAME");
        assert_eq!(
            c.generate_leading_entry('.'),
            "MSSQL_NAME.config.version.edition.cluster\n"
        );
    }
}
