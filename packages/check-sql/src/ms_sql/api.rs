// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, CheckConfig};
use crate::emit::header;
use crate::ms_sql::queries;
use anyhow::Result;

use tiberius::{AuthMethod, Client, Config, Query, Row, SqlBrowser};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

use super::defaults;

pub const SQL_LOGIN_ERROR_TAG: &str = "[SQL LOGIN ERROR]";
pub const SQL_TCP_ERROR_TAG: &str = "[SQL TCP ERROR]";

pub enum Credentials<'a> {
    SqlServer { user: &'a str, password: &'a str },
    Windows { user: &'a str, password: &'a str },
}

pub struct Section {
    pub name: String,
    pub separator: Option<char>,
}

pub trait Column {
    fn get_string(&self, idx: usize) -> String;
    fn get_optional_string(&self, idx: usize) -> Option<String>;
}

#[derive(Clone, Debug)]
pub struct InstanceEngine {
    pub name: String,
    pub id: String,
    pub version: String,
    pub edition: String,
    pub cluster: Option<String>,
    pub port: Option<u16>,
    pub available: Option<bool>,
}

impl Column for Row {
    fn get_string(&self, idx: usize) -> String {
        self.try_get::<&str, usize>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
            .to_string()
    }

    fn get_optional_string(&self, idx: usize) -> Option<String> {
        self.try_get::<&str, usize>(idx)
            .unwrap_or_default()
            .map(str::to_string)
    }
}

impl From<&Row> for InstanceEngine {
    /// NOTE: ignores any bad data in the row
    /// try_get is used to not panic
    fn from(row: &Row) -> Self {
        InstanceEngine {
            name: row.get_string(0),
            id: row.get_string(1),
            edition: row.get_string(2),
            version: row.get_string(3),
            cluster: row.get_optional_string(4),
            port: row
                .get_optional_string(5)
                .and_then(|s| s.parse::<u16>().ok()),
            available: None,
        }
    }
}

impl CheckConfig {
    pub async fn exec(&self) -> Result<String> {
        if let Some(ms_sql) = self.ms_sql() {
            let empty_header = Self::generate_dumb_header(ms_sql);
            Ok(empty_header)
        } else {
            anyhow::bail!("No Config")
        }
    }

    /// Generate header for each section without any data
    fn generate_dumb_header(ms_sql: &config::ms_sql::Config) -> String {
        let sections = ms_sql.sections();
        let always: Vec<Section> = sections
            .get_filtered_always()
            .iter()
            .map(to_section)
            .collect();
        let cached: Vec<Section> = sections
            .get_filtered_cached()
            .iter()
            .map(to_section)
            .collect();
        always
            .iter()
            .chain(cached.iter())
            .map(|s| header(&s.name, s.separator))
            .collect::<Vec<String>>()
            .join("")
    }
}

fn to_section(name: &String) -> Section {
    Section {
        name: name.to_owned(),
        separator: get_section_separator(name),
    }
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
) -> Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

    config.host(host);
    config.port(port);
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

/// Create `remote` connection to MS SQL `instance`
///
/// # Arguments
///
/// * `host` - Hostname of MS SQL server
/// * `port` - Port of MS SQL server BROWSER,  1434 - default
/// * `credentials` - defines connection type and credentials itself
/// * `instance_name` - name of the instance to connect to
pub async fn create_remote_instance_client(
    host: &str,
    port: Option<u16>,
    credentials: Credentials<'_>,
    instance_name: &str,
) -> anyhow::Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

    config.host(host);
    // The default port of SQL Browser
    config.port(port.unwrap_or(defaults::BROWSER_PORT));
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
#[cfg(windows)]
pub async fn create_local_instance_client(
    port: Option<u16>,
    instance_name: &str,
) -> anyhow::Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

    config.host("localhost");
    // The default port of SQL Browser
    config.port(port.unwrap_or(defaults::BROWSER_PORT));
    config.authentication(AuthMethod::Integrated);

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
    _port: Option<u16>,
    _instance_name: &str,
) -> anyhow::Result<Client<Compat<TcpStream>>> {
    anyhow::bail!("not supported");
}

/// Check Integrated connection to MS SQL
#[cfg(windows)]
pub async fn create_local_client() -> Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

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
pub async fn create_local_client() -> Result<Client<Compat<TcpStream>>> {
    anyhow::bail!("not supported");
}

/// return Vec<Vec<Row>> as a Results Vec: one Vec<Row> per one statement in query.
pub async fn run_query(
    client: &mut Client<Compat<TcpStream>>,
    query: &str,
) -> Result<Vec<Vec<Row>>> {
    let stream = Query::new(query).query(client).await?;
    let rows: Vec<Vec<Row>> = stream.into_results().await?;
    Ok(rows)
}

/// return all MS SQL instances installed
pub async fn find_instance_engines(
    client: &mut Client<Compat<TcpStream>>,
) -> Result<(Vec<InstanceEngine>, Vec<InstanceEngine>)> {
    Ok((
        get_engines(client, &queries::get_instances_query()).await?,
        get_engines(client, &queries::get_32bit_instances_query()).await?,
    ))
}

async fn get_engines(
    client: &mut Client<Compat<TcpStream>>,
    query: &str,
) -> Result<Vec<InstanceEngine>> {
    let rows = run_query(client, query).await?;
    Ok(rows[0]
        .iter()
        .map(InstanceEngine::from)
        .collect::<Vec<InstanceEngine>>()
        .to_vec())
}

/// return all MS SQL instances installed
pub async fn get_computer_name(client: &mut Client<Compat<TcpStream>>) -> Result<Option<String>> {
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
