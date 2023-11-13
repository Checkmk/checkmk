// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, CheckConfig};
use crate::emit::header;
use crate::ms_sql::queries;
use anyhow::Result;
use futures::stream::{self, StreamExt};

use tiberius::{AuthMethod, Config, Query, Row, SqlBrowser};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

use super::defaults;
pub type Client = tiberius::Client<Compat<TcpStream>>;

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

impl Section {
    pub fn to_header(&self) -> String {
        header(&self.name, self.separator)
    }
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

impl InstanceEngine {
    pub fn generate_leading_entry(&self, sep: char) -> String {
        format!(
            "MSSQL_{}{sep}config{sep}{}{sep}{}{sep}{}\n",
            self.name,
            self.version,
            self.edition,
            self.cluster.as_deref().unwrap_or_default()
        )
    }
    pub async fn generate_section(
        &self,
        _ms_sql: &config::ms_sql::Config,
        section: &Section,
    ) -> String {
        let result = section.to_header();
        result + format!("{} not implemented\n", section.name).as_str()
    }
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
    const INSTANCE_SECTION_NAME: &str = "instance";

    let mut result = to_section("instance").to_header(); // as in old plugin
    let sections = get_work_sections(ms_sql);
    let all = get_instance_engines(ms_sql.auth(), ms_sql.conn()).await?;
    let instances: Vec<InstanceEngine> = [&all.0[..], &all.1[..]].concat();

    for instance in &instances {
        result += &to_section(INSTANCE_SECTION_NAME).to_header();
        result += &instance
            .generate_leading_entry(get_section_separator(INSTANCE_SECTION_NAME).unwrap_or(' '));
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
    let tasks = instances.iter().flat_map(|instance| {
        sections
            .iter()
            .map(move |section| instance.generate_section(ms_sql, section))
    });

    // processing here
    let results = stream::iter(tasks)
        .buffer_unordered(6) // MAX_CONCURRENT is the limit of concurrent tasks you want to allow.
        .collect::<Vec<_>>()
        .await;

    Ok(results.join(""))
}

async fn create_client_from_config(
    auth: &config::ms_sql::Authentication,
    conn: &config::ms_sql::Connection,
) -> Result<Client> {
    let client = match auth.auth_type() {
        config::ms_sql::AuthType::SqlServer | config::ms_sql::AuthType::Windows => {
            if let Some(credentials) = obtain_config_credentials(auth) {
                create_remote_client(conn.hostname(), conn.port(), credentials).await?
            } else {
                anyhow::bail!("Not provided credentials")
            }
        }

        #[cfg(windows)]
        config::ms_sql::AuthType::Integrated => create_local_client().await?,

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
        .map(to_section)
        .collect();
    base.extend(sections.get_filtered_cached().iter().map(to_section));
    base
}

fn to_section(name: impl ToString) -> Section {
    let name = name.to_string();
    let separator = get_section_separator(&name);
    Section { name, separator }
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
) -> Result<Client> {
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
    instance_name: &str,
    host: &str,
    sql_browser_port: Option<u16>,
    credentials: Credentials<'_>,
) -> anyhow::Result<Client> {
    let mut config = Config::new();

    config.host(host);
    // The default port of SQL Browser
    config.port(sql_browser_port.unwrap_or(defaults::SQL_BROWSER_PORT));
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

/// Check `local` (Integrated) connection to MS SQL
#[cfg(windows)]
pub async fn create_local_client() -> Result<Client> {
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
pub async fn create_local_client() -> Result<Client> {
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
) -> anyhow::Result<Client> {
    let mut config = Config::new();

    config.host("localhost");
    // The default port of SQL Browser
    config.port(sql_browser_port.unwrap_or(defaults::SQL_BROWSER_PORT));
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
    _instance_name: &str,
    _port: Option<u16>,
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
    auth: &config::ms_sql::Authentication,
    conn: &config::ms_sql::Connection,
) -> Result<(Vec<InstanceEngine>, Vec<InstanceEngine>)> {
    let mut client = create_client_from_config(auth, conn).await?;
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
        assert!(create_client_from_config(config.auth(), config.conn())
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
}
