// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, ms_sql::AuthType, ms_sql::Endpoint};
use crate::types::{CertPath, Edition, HostName, Port};
use anyhow::Result;

use crate::ms_sql::query::obtain_server_edition;
#[cfg(windows)]
use crate::types::InstanceName; // only on windows possible to connect by name
#[cfg(windows)]
use tiberius::SqlBrowser;
use tiberius::{AuthMethod, Config};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

use super::defaults;
type TiberiusClient = tiberius::Client<Compat<TcpStream>>;
#[derive(Debug)]
pub struct StdClient {
    client: TiberiusClient,
    edition: Edition,
}

impl StdClient {
    pub fn new(client: TiberiusClient) -> Self {
        Self {
            client,
            edition: Edition::Undefined,
        }
    }
    pub fn client(&mut self) -> &mut TiberiusClient {
        &mut self.client
    }
}

#[derive(Debug)]
pub struct OdbcClient {
    conn_string: String,
    edition: Edition,
}

pub trait ManageEdition {
    fn get_edition(&self) -> Edition;
    fn set_edition(&mut self, edition: Edition);
}

impl ManageEdition for StdClient {
    fn get_edition(&self) -> Edition {
        self.edition.clone()
    }
    fn set_edition(&mut self, edition: Edition) {
        self.edition = edition;
    }
}

impl OdbcClient {
    pub fn new(conn_string: impl ToString) -> Self {
        Self {
            conn_string: conn_string.to_string(),
            edition: Edition::Undefined,
        }
    }
    pub fn conn_string(&self) -> &str {
        &self.conn_string
    }
}

impl ManageEdition for OdbcClient {
    fn get_edition(&self) -> Edition {
        self.edition.clone()
    }
    fn set_edition(&mut self, edition: Edition) {
        self.edition = edition;
    }
}

// TODO: remove this and use dynamic dispatch
#[derive(Debug)]
pub enum UniClient {
    Std(Box<StdClient>),
    Odbc(OdbcClient),
}

impl ManageEdition for UniClient {
    fn get_edition(&self) -> Edition {
        match self {
            UniClient::Std(client) => client.get_edition(),
            UniClient::Odbc(client) => client.get_edition(),
        }
    }

    fn set_edition(&mut self, edition: Edition) {
        match self {
            UniClient::Std(client) => client.set_edition(edition),
            UniClient::Odbc(client) => client.set_edition(edition),
        }
    }
}

pub struct RemoteConnection<'a> {
    pub host: HostName,
    pub port: Option<Port>,
    pub credentials: Credentials<'a>,
}

#[cfg(windows)]
#[derive(Default)]
pub struct LocalConnection {
    pub host: HostName,
    pub port: Option<Port>,
}

#[cfg(windows)]
impl LocalConnection {
    pub fn host(&self) -> &HostName {
        &self.host
    }
}

#[cfg(windows)]
pub struct NamedConnection {
    pub host: HostName,
    pub instance_name: InstanceName,
    pub browser_port: Option<Port>,
}

enum ClientConnection<'a> {
    Remote(RemoteConnection<'a>),
    #[cfg(windows)]
    Named(NamedConnection),
    #[cfg(windows)]
    Local(LocalConnection),
}

pub struct ClientBuilder<'a> {
    client_connection: Option<ClientConnection<'a>>,

    database: Option<String>,
    certificate: Option<CertPath>,
    trust_server_certificate: bool,
}

impl<'a> Default for ClientBuilder<'a> {
    fn default() -> Self {
        Self {
            client_connection: None,
            database: None,
            certificate: None,
            trust_server_certificate: config::defines::defaults::TRUST_SERVER_CERTIFICATE,
        }
    }
}

impl<'a> ClientBuilder<'a> {
    pub fn new() -> ClientBuilder<'a> {
        ClientBuilder::default()
    }

    pub fn logon_on_port(
        mut self,
        host: &HostName,
        port: Option<Port>,
        credentials: Credentials<'a>,
    ) -> Self {
        log::info!(
            "Logon at port `{}:{}`",
            &host,
            &port
                .clone()
                .map(|p| p.value().to_string())
                .unwrap_or_default()
        );
        let r = ClientConnection::Remote(RemoteConnection {
            host: host.to_owned(),
            port,
            credentials,
        });
        self.client_connection = Some(r);
        self
    }

    #[cfg(windows)]
    pub fn browse<P: Into<Port>>(
        mut self,
        host: &HostName,
        instance: &InstanceName,
        browser_port: Option<P>,
    ) -> Self {
        let p = browser_port.map(|p| p.into());
        log::info!(
            "Browse connection at port `{}:{}`",
            &host,
            &p.clone().map(|p| p.value().to_string()).unwrap_or_default()
        );
        let i = NamedConnection {
            host: host.to_owned(),
            instance_name: instance.to_owned(),
            browser_port: p,
        };
        self.client_connection = Some(ClientConnection::Named(i));
        self
    }

    #[cfg(windows)]
    pub fn local_by_port(mut self, port: Option<Port>, host: Option<HostName>) -> Self {
        let local_connection = LocalConnection {
            host: host.unwrap_or(crate::constants::LOCAL_HOST.clone()),
            port,
        };
        log::info!(
            "Local connection by port `{}:{}`",
            &local_connection.host,
            &local_connection
                .port
                .as_ref()
                .map(|p| p.value().to_string())
                .unwrap_or_default()
        );
        self.client_connection = Some(ClientConnection::Local(local_connection));
        self
    }

    pub fn database<S: Into<String>>(mut self, database: Option<S>) -> Self {
        self.database = database.map(|d| d.into());
        self
    }

    pub fn certificate<C: Into<CertPath>>(mut self, certificate: Option<C>) -> Self {
        self.certificate = certificate.map(|c| c.into());
        self
    }

    pub fn trust_server_certificate(mut self, trust: bool) -> Self {
        self.trust_server_certificate = trust;
        self
    }

    pub fn make_config(&self) -> Result<Config> {
        let mut config = Config::new();
        if let Some(db) = &self.database {
            config.database(db);
        }

        match &self.client_connection {
            Some(ClientConnection::Remote(connection)) => {
                let port = connection.port.as_ref().map(|p| p.value());
                config.host(&connection.host);
                config.port(port.unwrap_or(defaults::STANDARD_PORT));
                config.authentication(match connection.credentials {
                    Credentials::SqlServer { user, password } => {
                        log::trace!(
                            "Remote connection to {} with user {}",
                            config.get_addr(),
                            user
                        );
                        AuthMethod::sql_server(user, password)
                    }
                    #[cfg(windows)]
                    Credentials::Windows { user, password } => AuthMethod::windows(user, password),
                    #[cfg(unix)]
                    Credentials::Windows {
                        user: _,
                        password: _,
                    } => anyhow::bail!("not supported"),
                });
            }
            #[cfg(windows)]
            Some(ClientConnection::Named(connection)) => {
                let port = connection.browser_port.as_ref().map(|p| p.value());
                config.host(connection.host.clone());
                config.port(port.unwrap_or(defaults::SQL_BROWSER_PORT));
                log::trace!("Named connection to {}", config.get_addr());
                config.authentication(AuthMethod::Integrated);
                if let Some(db) = &self.database {
                    config.database(db);
                }
                config.instance_name(&connection.instance_name);
            }
            #[cfg(windows)]
            Some(ClientConnection::Local(connection)) => {
                let port = connection.port.as_ref().map(|p| p.value());
                config.host(connection.host.clone());
                log::trace!("Local connection to {}", config.get_addr());
                config.port(port.unwrap_or(defaults::STANDARD_PORT));
                config.authentication(AuthMethod::Integrated);
            }
            _ => anyhow::bail!("No client connection provided"),
        }
        if let Some(certificate) = &self.certificate {
            config.trust_cert_ca(certificate);
        } else if self.trust_server_certificate {
            config.trust_cert();
        }
        Ok(config)
    }

    pub async fn build(self) -> Result<UniClient> {
        let tiberius_config = self.make_config()?;
        match self.client_connection {
            Some(ClientConnection::Remote(_)) => create_remote_client(tiberius_config).await,
            #[cfg(windows)]
            Some(ClientConnection::Named(_)) => create_named_instance_client(tiberius_config).await,
            #[cfg(windows)]
            Some(ClientConnection::Local(_)) => connect_via_tcp(tiberius_config).await,
            _ => anyhow::bail!("No client connection provided"),
        }
    }
}

pub enum Credentials<'a> {
    SqlServer { user: &'a str, password: &'a str },
    Windows { user: &'a str, password: &'a str },
}

pub const SQL_LOGIN_ERROR_TAG: &str = "[SQL LOGIN ERROR]";
pub const SQL_TCP_ERROR_TAG: &str = "[SQL TCP ERROR]";

pub async fn connect_main_endpoint(endpoint: &Endpoint) -> Result<UniClient> {
    connect_custom_endpoint(endpoint, endpoint.port()).await
}

pub async fn connect_custom_endpoint(endpoint: &Endpoint, some_port: Port) -> Result<UniClient> {
    let (auth, conn) = endpoint.split();
    let map_elapsed_to_anyhow = |e: tokio::time::error::Elapsed| {
        anyhow::anyhow!(
            "Timeout: {e} when connecting endpoint, timeout = {:?}",
            conn.timeout()
        )
    };
    let use_port = if some_port != Port(0) {
        some_port
    } else if endpoint.port() != Port(0) {
        endpoint.port().clone()
    } else {
        Port(defaults::STANDARD_PORT)
    };
    let client = match auth.auth_type() {
        AuthType::SqlServer | AuthType::Windows => {
            if let Some(credentials) = obtain_config_credentials(auth) {
                tokio::time::timeout(
                    conn.timeout(),
                    ClientBuilder::new()
                        .logon_on_port(&conn.hostname(), Some(use_port), credentials)
                        .certificate(conn.tls().map(|t| t.client_certificate().to_owned()))
                        .trust_server_certificate(conn.trust_server_certificate())
                        .build(),
                )
                .await
                .map_err(map_elapsed_to_anyhow)?
            } else {
                anyhow::bail!("Not provided credentials")
            }
        }

        #[cfg(windows)]
        AuthType::Integrated => tokio::time::timeout(
            conn.timeout(),
            ClientBuilder::new()
                .local_by_port(Some(use_port), Some(conn.hostname()))
                .certificate(conn.tls().map(|t| t.client_certificate().to_owned()))
                .trust_server_certificate(conn.trust_server_certificate())
                .build(),
        )
        .await
        .map_err(map_elapsed_to_anyhow)?,

        _ => anyhow::bail!("Not supported authorization type"),
    };

    client
}

#[cfg(windows)]
pub async fn connect_custom_instance(
    endpoint: &Endpoint,
    instance: &InstanceName,
) -> Result<UniClient> {
    use crate::constants;

    let (auth, conn) = endpoint.split();
    let map_elapsed_to_anyhow = |e: tokio::time::error::Elapsed| {
        anyhow::anyhow!(
            "Timeout: {e} when connecting instance, timeout = {:?}",
            conn.timeout()
        )
    };
    let client = match auth.auth_type() {
        AuthType::SqlServer | AuthType::Windows => {
            if let Some(_credentials) = obtain_config_credentials(auth) {
                tokio::time::timeout(
                    conn.timeout(),
                    ClientBuilder::new()
                        .browse(&conn.hostname(), instance, conn.sql_browser_port())
                        .certificate(conn.tls().map(|t| t.client_certificate().to_owned()))
                        .trust_server_certificate(conn.trust_server_certificate())
                        .build(),
                )
                .await
                .map_err(map_elapsed_to_anyhow)?
            } else {
                anyhow::bail!("Not provided credentials")
            }
        }

        AuthType::Integrated => tokio::time::timeout(
            conn.timeout(),
            ClientBuilder::new()
                .browse(&constants::LOCAL_HOST, instance, conn.sql_browser_port())
                .certificate(conn.tls().map(|t| t.client_certificate().to_owned()))
                .trust_server_certificate(conn.trust_server_certificate())
                .build(),
        )
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

/// Create client for remote MS SQL
async fn create_remote_client(tiberius_config: Config) -> Result<UniClient> {
    let mut config = tiberius_config.clone();
    config.encryption(tiberius::EncryptionLevel::Required);
    match connect_via_tcp(config).await {
        Ok(client) => Ok(client),
        #[cfg(unix)]
        Err(err) => {
            log::warn!(
                "Encryption is not supported by the host, err is {}. Trying without encryption...",
                err
            );
            let mut config = tiberius_config.clone();
            config.encryption(tiberius::EncryptionLevel::NotSupported);
            Ok(connect_via_tcp(config).await?)
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

/// Create client for `named` MS SQL `instance`
#[cfg(windows)]
async fn create_named_instance_client(config: Config) -> anyhow::Result<UniClient> {
    log::info!("Named connection to addr {}", config.get_addr());

    // This will create a new `TcpStream` from `async-std`, connected to the
    // right port of the named instance.
    // The logic is based on SQL browser mechanic
    let tcp = TcpStream::connect_named(&config)
        .await
        .map_err(|e| anyhow::anyhow!("Failed to connect to SQL Browser {}", e))?;
    tcp.set_nodelay(true)?; // in documentation and examples

    let mut client = TiberiusClient::connect(config, tcp.compat_write())
        .await
        .map_err(|e| anyhow::anyhow!("Failed to access SQL Browser {}", e))
        .map(|c| UniClient::Std(Box::new(StdClient::new(c))))?;
    update_edition(&mut client).await;
    Ok(client)
}

async fn connect_via_tcp(config: Config) -> Result<UniClient> {
    log::info!("Connecting to addr '{}'...", config.get_addr());
    let tcp = TcpStream::connect(config.get_addr()).await.map_err(|e| {
        anyhow::anyhow!(
            "{} address:{} error:`{}`",
            SQL_TCP_ERROR_TAG,
            config.get_addr(),
            e
        )
    })?;
    log::info!("Connected to addr '{}'", config.get_addr());
    tcp.set_nodelay(true)?; // in documentation and examples

    // To be able to use Tokio's tcp, we're using the `compat_write` from
    // the `TokioAsyncWriteCompatExt` to get a stream compatible with the
    // traits from the `futures` crate. The same is for upcoming NamedPipe
    let result = TiberiusClient::connect(config, tcp.compat_write())
        .await
        .map_err(|e| anyhow::anyhow!("{} {}", SQL_LOGIN_ERROR_TAG, e));
    if result.is_ok() {
        log::info!("Connection success");
    } else {
        log::warn!("Connection success failed");
    }
    let mut client = result.map(|x| {
        UniClient::Std(Box::new(StdClient {
            client: x,
            edition: Edition::Normal,
        }))
    })?;
    update_edition(&mut client).await;
    Ok(client)
}

pub async fn update_edition(client: &mut UniClient) {
    let edition = obtain_server_edition(client).await.unwrap_or_else(|e| {
        log::warn!("Failed to obtain server edition: {}", e);
        Edition::Normal
    });
    client.set_edition(edition);
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
) -> anyhow::Result<UniClient> {
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
        assert!(connect_main_endpoint(&config.endpoint())
            .await
            .unwrap_err()
            .to_string()
            .contains("Not supported authorization type"));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_create_client_from_config_timeout() {
        let config = make_config_with_auth_type("sql_server");
        let s = connect_main_endpoint(&config.endpoint())
            .await
            .unwrap_err()
            .to_string();
        // in Windows connection is slow enough, we could verify timeout
        #[cfg(windows)]
        assert!(s.contains("Timeout: "), "{s}");

        // in linux connection is too fast, no chance for timeout check
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

    #[cfg(windows)]
    #[tokio::test(flavor = "multi_thread")]
    async fn test_local_with_cert() {
        pub const MS_SQL_DB_CERT: &str = "CI_TEST_MS_SQL_DB_CERT";
        if let Ok(certificate_path) = std::env::var(MS_SQL_DB_CERT) {
            ClientBuilder::new()
                .local_by_port(Some(1433u16.into()), None)
                .certificate(Some(certificate_path))
                .trust_server_certificate(false)
                .build()
                .await
                .unwrap();
            assert!(ClientBuilder::new()
                .local_by_port(Some(1433u16.into()), None)
                .trust_server_certificate(false)
                .build()
                .await
                .is_err());
            assert!(ClientBuilder::new()
                .local_by_port(
                    Some(1433u16.into()),
                    Some(HostName::from("localhost".to_string()))
                )
                .trust_server_certificate(true)
                .build()
                .await
                .is_ok());
        } else {
            eprintln!("Error: environment variable {} is absent", MS_SQL_DB_CERT);
        }
    }

    #[test]
    fn test_client_builder_remote() {
        let credentials = Credentials::SqlServer {
            user: "u",
            password: "p",
        };
        let remote = ClientBuilder::new();
        assert!(remote.client_connection.is_none());
        let host: HostName = "host".to_owned().into();
        let port: Option<Port> = Some(123u16.into());
        let builder = remote.logon_on_port(&host, port, credentials);
        assert!(matches!(
            builder.client_connection,
            Some(ClientConnection::Remote(RemoteConnection {
                host: _,
                port: _,
                credentials: _
            }))
        ));
    }
    #[cfg(windows)]
    #[test]
    fn test_client_builder_local_instance() {
        use crate::constants;
        let local = ClientBuilder::new();
        let instance_name: InstanceName = "i".to_owned().into();
        let browser_port: Option<Port> = Some(123u16.into());
        let builder = local.browse(&constants::LOCAL_HOST, &instance_name, browser_port);
        assert!(matches!(
            builder.client_connection,
            Some(ClientConnection::Named(NamedConnection {
                host: _,
                instance_name: _,
                browser_port: _,
            }))
        ));
    }
    #[cfg(windows)]
    #[test]
    fn test_client_builder_local() {
        let local = ClientBuilder::new();
        let port: Option<Port> = Some(123u16.into());
        let builder = local.local_by_port(port, None);
        assert!(matches!(
            builder.client_connection,
            Some(ClientConnection::Local(LocalConnection {
                host: _,
                port: _
            }))
        ));
    }
}
