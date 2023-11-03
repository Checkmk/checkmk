// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::CheckConfig;
use crate::emit::header;
use crate::ms_sql::queries;
use anyhow::Result;

use tiberius::{AuthMethod, Client, Config, Query, Row};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

pub enum Credentials<'a> {
    SqlServer { user: &'a str, password: &'a str },
    Windows { user: &'a str, password: &'a str },
}

pub struct Section {
    pub name: String,
    pub separator: Option<char>,
}

#[derive(Clone, Debug)]
pub struct Instance {
    pub name: String,
    pub id: String,
    pub version: String,
    pub edition: String,
    pub cluster: Option<String>,
    pub port: Option<u16>,
}

impl Instance {
    /// NOTE: ignores any bad data in the row
    fn from_row(row: &Row) -> Instance {
        Instance {
            name: row
                .try_get::<&str, usize>(0)
                .unwrap_or_default()
                .unwrap_or_default()
                .to_string(),
            id: row
                .try_get::<&str, usize>(1)
                .unwrap_or_default()
                .unwrap_or_default()
                .to_string(),
            edition: row
                .try_get::<&str, usize>(2)
                .unwrap_or_default()
                .unwrap_or_default()
                .to_string(),
            version: row
                .try_get::<&str, usize>(3)
                .unwrap_or_default()
                .unwrap_or_default()
                .to_string(),
            cluster: row
                .try_get::<&str, usize>(4)
                .unwrap_or_default()
                .map(str::to_string),
            port: row
                .try_get::<&str, usize>(5)
                .unwrap_or_default()
                .and_then(|s| s.parse::<u16>().ok()),
        }
    }
}

impl CheckConfig {
    pub async fn exec(&self) -> Result<String> {
        if let Some(ms_sql) = self.ms_sql() {
            let sqls = ms_sql.sqls();
            let always: Vec<Section> = sqls.get_filtered_always().iter().map(to_section).collect();
            let cached: Vec<Section> = sqls.get_filtered_cached().iter().map(to_section).collect();
            Ok(always
                .iter()
                .chain(cached.iter())
                .map(|s| header(&s.name, s.separator))
                .collect::<Vec<String>>()
                .join(""))
        } else {
            anyhow::bail!("No Config")
        }
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

/// Check SQL connection to MS SQL
///
/// # Arguments
///
/// * `host` - Hostname of MS SQL server
/// * `port` - Port of MS SQL server
/// * `credentials` - defines connection type and credentials itself
pub async fn create_client(
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

/// Check Integrated connection to MS SQL
///
/// # Arguments
///
/// * `host` - Hostname of MS SQL server
/// * `port` - Port of MS SQL server
#[cfg(windows)]
pub async fn create_client_for_logged_user(
    host: &str,
    port: u16,
) -> Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

    config.host(host);
    config.port(port);
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
pub async fn create_client_for_logged_user(
    _host: &str,
    _port: u16,
) -> Result<Client<Compat<TcpStream>>> {
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
pub async fn get_all_instances(
    client: &mut Client<Compat<TcpStream>>,
) -> Result<(Vec<Instance>, Vec<Instance>)> {
    Ok((
        get_instances(client, &queries::get_instances_query()).await?,
        get_instances(client, &queries::get_32bit_instances_query()).await?,
    ))
}

async fn get_instances(
    client: &mut Client<Compat<TcpStream>>,
    query: &str,
) -> Result<Vec<Instance>> {
    let rows = run_query(client, query).await?;
    Ok(rows[0]
        .iter()
        .map(Instance::from_row)
        .collect::<Vec<Instance>>()
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
