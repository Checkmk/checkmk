// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, ms_sql::AuthType, ms_sql::Endpoint};
use anyhow::Result;

#[cfg(windows)]
use tiberius::SqlBrowser;
use tiberius::{AuthMethod, Config};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

#[cfg(windows)]
use super::defaults;
pub type Client = tiberius::Client<Compat<TcpStream>>;

pub enum Credentials<'a> {
    SqlServer { user: &'a str, password: &'a str },
    Windows { user: &'a str, password: &'a str },
}

pub const SQL_LOGIN_ERROR_TAG: &str = "[SQL LOGIN ERROR]";
pub const SQL_TCP_ERROR_TAG: &str = "[SQL TCP ERROR]";

pub async fn create_from_config(endpoint: &Endpoint) -> Result<Client> {
    let (auth, conn) = endpoint.split();
    let map_elapsed_to_anyhow = |e: tokio::time::error::Elapsed| {
        anyhow::anyhow!(
            "Timeout: {e} when creating client from config {:?}",
            conn.timeout()
        )
    };
    let client = match auth.auth_type() {
        AuthType::SqlServer | AuthType::Windows => {
            if let Some(credentials) = obtain_config_credentials(auth) {
                tokio::time::timeout(
                    conn.timeout(),
                    create_remote(conn.hostname(), conn.port(), credentials, None),
                )
                .await
                .map_err(map_elapsed_to_anyhow)?
            } else {
                anyhow::bail!("Not provided credentials")
            }
        }

        #[cfg(windows)]
        AuthType::Integrated => tokio::time::timeout(conn.timeout(), create_local(None))
            .await
            .map_err(map_elapsed_to_anyhow)?,

        _ => anyhow::bail!("Not supported authorization type"),
    };

    client
}

pub fn obtain_config_credentials(auth: &config::ms_sql::Authentication) -> Option<Credentials> {
    match auth.auth_type() {
        AuthType::SqlServer => Some(Credentials::SqlServer {
            user: auth.username(),
            password: auth.password().map(|s| s.as_str()).unwrap_or(""),
        }),
        #[cfg(windows)]
        AuthType::Windows => Some(Credentials::Windows {
            user: auth.username(),
            password: auth.password().map(|s| s.as_str()).unwrap_or(""),
        }),
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
pub async fn create_remote(
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
pub async fn create_local(database: Option<String>) -> Result<Client> {
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
pub async fn create_local(_database: Option<String>) -> Result<Client> {
    anyhow::bail!("not supported");
}

/// Create `local` connection to MS SQL `instance`
///
/// # Arguments
///
/// * `instance_name` - name of the instance to connect to
/// * `port` - Port of MS SQL server BROWSER,  1434 - default
#[cfg(windows)]
pub async fn create_instance_local(
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
pub async fn create_instance_local(
    _instance_name: &str,
    _port: Option<u16>,
    _database: Option<String>,
) -> anyhow::Result<Client> {
    anyhow::bail!("not supported");
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ms_sql::Config;

    fn make_config_with_auth_type(auth_type: &str) -> Config {
        const BASE: &str = r#"
---
mssql:
  main:
    authentication:
       username: "bad_user"
       password: "bad_password"
       type: type_tag
    connection:
       hostname: "localhost" # we use real host to avoid long timeout
       port: 65345 # we use weird port to avoid connection
       timeout: 1
"#;
        Config::from_string(&BASE.replace("type_tag", auth_type))
            .unwrap()
            .unwrap()
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_create_client_from_config_for_error() {
        let config = make_config_with_auth_type("token");
        assert!(create_from_config(&config.endpoint())
            .await
            .unwrap_err()
            .to_string()
            .contains("Not supported authorization type"));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_create_client_from_config_timeout() {
        let config = make_config_with_auth_type("sql_server");
        let s = create_from_config(&config.endpoint())
            .await
            .unwrap_err()
            .to_string();
        // in Windows connection is slow enough, we could verify timeout
        #[cfg(windows)]
        assert!(s.contains("Timeout: "), "{s}");

        // in linux connection is too fast, no chance for timeout
        #[cfg(unix)]
        assert!(s.contains("Connection refused"), "{s}");
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
