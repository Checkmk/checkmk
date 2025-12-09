// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::defines::{defaults, keys, values};
use super::section::{Section, SectionKind, Sections};
use super::yaml::{Get, Yaml};
use crate::config::defines::keys::EXCLUDE_DATABASES;
use crate::platform;
use crate::platform::registry::get_instances;
use crate::platform::InstanceInfo;
use crate::types::{
    CertPath, HostName, InstanceAlias, InstanceName, MaxConnections, MaxQueries, Port,
};
use anyhow::{anyhow, bail, Context, Result};
use std::collections::hash_map::DefaultHasher;
use std::collections::HashSet;
use std::hash::{Hash, Hasher};
use std::path::{Path, PathBuf};
use std::time::Duration;
use yaml_rust2::YamlLoader;

#[derive(PartialEq, Debug)]
pub struct Config {
    auth: Authentication,
    conn: Connection,
    sections: Sections,
    discovery: Discovery,
    piggyback_host: Option<String>,
    mode: Mode,
    custom_instances: Vec<CustomInstance>,
    configs: Vec<Config>,
    hash: String,
    options: Options,
}

#[derive(PartialEq, Debug, Clone)]
pub struct Options {
    max_connections: MaxConnections,
    max_queries: MaxQueries,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            max_connections: defaults::MAX_CONNECTIONS.into(),
            max_queries: defaults::MAX_QUERIES.into(),
        }
    }
}

impl Options {
    pub fn new(max_connections: MaxConnections) -> Self {
        Self {
            max_connections,
            max_queries: defaults::MAX_QUERIES.into(),
        }
    }

    pub fn max_connections(&self) -> MaxConnections {
        self.max_connections.clone()
    }

    pub fn max_queries(&self) -> MaxQueries {
        self.max_queries.clone()
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let options = yaml.get(keys::OPTIONS);
        if options.is_badvalue() {
            return Ok(None);
        }

        Ok(Some(Self {
            max_connections: options
                .get_int::<u32>(keys::MAX_CONNECTIONS)
                .unwrap_or_else(|| {
                    log::debug!("no max_connections specified, using default");
                    defaults::MAX_CONNECTIONS
                })
                .into(),
            max_queries: defaults::MAX_QUERIES.into(),
        }))
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            auth: Authentication::default(),
            conn: Connection::default(),
            sections: Sections::default(),
            discovery: Discovery::default(),
            piggyback_host: None,
            mode: Mode::Port,
            custom_instances: vec![],
            configs: vec![],
            hash: String::new(),
            options: Options::default(),
        }
    }
}

impl Config {
    pub fn from_string(source: &str) -> Result<Option<Self>> {
        YamlLoader::load_from_str(source)?
            .first()
            .and_then(|e| Config::from_yaml(e).transpose())
            .transpose()
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let root = yaml.get(keys::MSSQL);
        if root.is_badvalue() {
            return Ok(None);
        }
        let default_config = Config {
            auth: Authentication {
                auth_type: AuthType::Undefined,
                ..Default::default()
            },
            ..Default::default()
        };
        let config = Config::parse_main_from_yaml(root, &default_config)?;
        match config {
            Some(c) if !c.auth.defined() => {
                anyhow::bail!("Bad/absent user name");
            }
            Some(mut c) => {
                c.configs = root
                    .get_yaml_vector(keys::CONFIGS)
                    .into_iter()
                    .filter_map(|v| Config::parse_main_from_yaml(&v, &c).transpose())
                    .collect::<Result<Vec<Config>>>()?;

                Ok(Some(c))
            }
            _ => Ok(config),
        }
    }

    fn parse_main_from_yaml(root: &Yaml, default: &Config) -> Result<Option<Self>> {
        let mut hasher = DefaultHasher::new();
        root.hash(&mut hasher);
        let hash = format!("{:016X}", hasher.finish());
        let main = root.get(keys::MAIN);
        if main.is_badvalue() {
            bail!("main key is absent");
        }

        let auth = Authentication::from_yaml(main).unwrap_or_else(|_| default.auth.clone());
        let conn =
            Connection::from_yaml(main, Some(&auth))?.unwrap_or_else(|| default.conn().clone());
        let options = Options::from_yaml(main)?.unwrap_or_else(|| default.options().clone());
        let discovery = Discovery::from_yaml(main)?.unwrap_or_else(|| default.discovery().clone());
        let section_info = Sections::from_yaml(main, &default.sections)?;

        let mut custom_instances = main
            .get_yaml_vector(keys::INSTANCES)
            .into_iter()
            .map(|v| CustomInstance::from_yaml(&v, &auth, &conn, &section_info))
            .collect::<Result<Vec<CustomInstance>>>()?;
        if discovery.detect() {
            let registry_instances =
                get_additional_registry_instances(&custom_instances, &auth, &conn);
            log::info!(
                "Found {} SQL server instances in REGISTRY: [ {} ]",
                registry_instances.len(),
                registry_instances
                    .iter()
                    .map(|i| format!("{}:{:?}", i.name, i.conn().port()))
                    .collect::<Vec<_>>()
                    .join(", ")
            );

            custom_instances.extend(registry_instances);
        } else {
            log::info!("skipping registry instances: the reason detection disabled");
        }
        let mode = Mode::from_yaml(main).unwrap_or_else(|_| default.mode().clone());
        let piggyback_host = main.get_string(keys::PIGGYBACK_HOST);

        Ok(Some(Self {
            auth,
            conn,
            sections: section_info,
            discovery,
            piggyback_host,
            mode,
            custom_instances,
            configs: vec![],
            hash,
            options,
        }))
    }

    pub fn options(&self) -> &Options {
        &self.options
    }

    pub fn endpoint(&self) -> Endpoint {
        Endpoint::new(&self.auth, &self.conn)
    }
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }
    pub fn conn(&self) -> &Connection {
        &self.conn
    }
    pub fn all_sections(&self) -> &Vec<Section> {
        self.sections.sections()
    }
    pub fn valid_sections(&self) -> Vec<&Section> {
        self.sections
            .select(&[SectionKind::Sync, SectionKind::Async])
    }

    pub fn cache_age(&self) -> u32 {
        self.sections.cache_age()
    }

    pub fn piggyback_host(&self) -> Option<&str> {
        self.piggyback_host.as_deref()
    }

    pub fn discovery(&self) -> &Discovery {
        &self.discovery
    }
    pub fn mode(&self) -> &Mode {
        &self.mode
    }
    pub fn instances(&self) -> &Vec<CustomInstance> {
        &self.custom_instances
    }
    pub fn configs(&self) -> &Vec<Config> {
        &self.configs
    }

    pub fn config_cache_dir(&self) -> String {
        "mssql-".to_owned() + &self.hash
    }

    pub fn sections(&self) -> &Sections {
        &self.sections
    }

    pub fn is_instance_allowed(&self, name: &impl ToString) -> bool {
        self.discovery
            .is_instance_allowed(&InstanceName::from(name.to_string()))
    }
}

pub fn get_registry_instance_info(name: &InstanceName) -> Option<InstanceInfo> {
    let all = get_instances(None);
    let a = all.iter().find(|i| &i.name == name);
    a.cloned()
}

fn get_additional_registry_instances(
    already_found_instances: &[CustomInstance],
    auth: &Authentication,
    conn: &Connection,
) -> Vec<CustomInstance> {
    if !is_local_endpoint(auth, conn) {
        log::info!("skipping registry instances: the host is not enough localhost");
        return vec![];
    }

    let names: HashSet<String> = already_found_instances
        .iter()
        .map(|i| i.name().to_string().to_lowercase().clone())
        .collect();
    log::info!("localhost is defined, adding registry instances");
    platform::registry::get_instances(None)
        .into_iter()
        .filter_map(|registry_instance_info| {
            if names.contains(&registry_instance_info.name.to_string().to_lowercase()) {
                log::info!(
                    "{} is ignored as already defined in custom instances",
                    registry_instance_info.name
                );
                return None;
            }

            Some(CustomInstance::from_registry(
                &registry_instance_info.name,
                auth,
                conn,
                &registry_instance_info.final_host(),
                &registry_instance_info.final_port(),
            ))
        })
        .collect::<Vec<CustomInstance>>()
}

pub fn is_local_endpoint(auth: &Authentication, conn: &Connection) -> bool {
    auth.auth_type() == &AuthType::Integrated
        || conn.hostname() == HostName::from("localhost".to_owned())
        || conn.hostname() == HostName::from("127.0.0.1".to_owned())
}

#[derive(PartialEq, Debug, Clone)]
pub struct Authentication {
    username: String,
    password: Option<String>,
    auth_type: AuthType,
    access_token: Option<String>,
}

impl Default for Authentication {
    fn default() -> Self {
        Self {
            username: "".to_owned(),
            password: None,
            auth_type: AuthType::default(),
            access_token: None,
        }
    }
}
impl Authentication {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let auth = yaml.get(keys::AUTHENTICATION);
        if auth.is_badvalue() {
            anyhow::bail!("authentication is missing");
        }

        Ok(Self {
            username: auth.get_string(keys::USERNAME).unwrap_or_default(),
            password: auth.get_string(keys::PASSWORD),
            auth_type: AuthType::try_from(
                auth.get_string(keys::TYPE)
                    .as_deref()
                    .unwrap_or(defaults::AUTH_TYPE),
            )?,
            access_token: auth.get_string(keys::ACCESS_TOKEN),
        }
        .ensure())
    }
    pub fn username(&self) -> &str {
        &self.username
    }
    pub fn password(&self) -> Option<&String> {
        self.password.as_ref()
    }
    pub fn auth_type(&self) -> &AuthType {
        &self.auth_type
    }
    pub fn access_token(&self) -> Option<&String> {
        self.access_token.as_ref()
    }

    pub fn defined(&self) -> bool {
        self.auth_type() == &AuthType::Integrated || !self.username().is_empty()
    }

    fn ensure(mut self) -> Self {
        if self.auth_type() == &AuthType::Integrated {
            self.username = String::new();
            self.password = None;
            self.access_token = None;
        }
        self
    }
}

#[derive(PartialEq, Debug, Clone)]
pub enum AuthType {
    SqlServer,
    Windows,
    Integrated,
    Token,
    Undefined,
}

impl Default for AuthType {
    #[cfg(unix)]
    fn default() -> Self {
        Self::SqlServer
    }
    #[cfg(windows)]
    fn default() -> Self {
        Self::Integrated
    }
}

impl TryFrom<&str> for AuthType {
    type Error = anyhow::Error;

    fn try_from(val: &str) -> Result<Self> {
        match str::to_ascii_lowercase(val).as_ref() {
            values::SQL_SERVER => Ok(AuthType::SqlServer),
            #[cfg(windows)]
            values::WINDOWS => Ok(AuthType::Windows),
            #[cfg(windows)]
            values::INTEGRATED => Ok(AuthType::Integrated),
            values::TOKEN => Ok(AuthType::Token),
            _ => Err(anyhow!("unsupported auth type `{val}`")),
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub enum Backend {
    Auto,
    Tcp,
    #[cfg(windows)]
    Odbc,
}

impl Default for Backend {
    #[cfg(unix)]
    fn default() -> Self {
        Self::Tcp
    }
    #[cfg(windows)]
    fn default() -> Self {
        Self::Auto
    }
}

impl Backend {
    fn from_string<T>(value: T) -> Option<Self>
    where
        T: AsRef<str>,
    {
        match value.as_ref() {
            "auto" => Some(Self::Auto),
            "tcp" => Some(Self::Tcp),
            #[cfg(unix)]
            "odbc" => Some(Self::Auto), // at the moment unix ignores odbc
            #[cfg(windows)]
            "odbc" => Some(Self::Odbc),
            _ => None,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Connection {
    hostname: HostName,
    fail_over_partner: Option<String>,
    port: Port,
    socket: Option<PathBuf>,
    trust_server_certificate: bool,
    tls: Option<ConnectionTls>,
    timeout: u64,
    backend: Backend,
    exclude_databases: Vec<String>,
    force_local_host: bool,
}

impl Connection {
    pub fn from_yaml(yaml: &Yaml, auth: Option<&Authentication>) -> Result<Option<Self>> {
        let conn = yaml.get(keys::CONNECTION);
        if conn.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(
            Self {
                force_local_host: conn.get_bool(keys::FORCE_LOCAL_HOST, false),
                hostname: conn
                    .get_string(keys::HOSTNAME)
                    .map(|s| {
                        if s.is_empty() {
                            defaults::CONNECTION_HOST_NAME.to_string()
                        } else {
                            s
                        }
                    })
                    .unwrap_or_else(|| defaults::CONNECTION_HOST_NAME.to_string())
                    .to_lowercase()
                    .into(),
                fail_over_partner: conn.get_string(keys::FAIL_OVER_PARTNER),
                port: Port(conn.get_int::<u16>(keys::PORT).unwrap_or_else(|| {
                    log::debug!("no port specified, using default");
                    defaults::CONNECTION_PORT
                })),
                socket: conn.get_pathbuf(keys::SOCKET),
                trust_server_certificate: conn.get_bool(
                    keys::TRUST_SERVER_CERTIFICATE,
                    defaults::TRUST_SERVER_CERTIFICATE,
                ),
                tls: ConnectionTls::from_yaml(conn)?,
                timeout: conn.get_int::<u64>(keys::TIMEOUT).unwrap_or_else(|| {
                    log::debug!("no timeout specified, using default");
                    defaults::CONNECTION_TIMEOUT
                }),
                backend: {
                    let value: String = conn
                        .get_string(keys::BACKEND)
                        .unwrap_or_default()
                        .to_lowercase();
                    Backend::from_string(value.as_str()).unwrap_or_else(|| {
                        log::error!("Unknown backend '{}'", &value);
                        Backend::default()
                    })
                },
                exclude_databases: { conn.get_string_vector(EXCLUDE_DATABASES, &[]) },
            }
            .ensure(auth),
        ))
    }
    pub fn hostname(&self) -> HostName {
        if self.force_local_host {
            HostName::from("localhost".to_owned())
        } else {
            self.hostname.clone()
        }
    }
    pub fn fail_over_partner(&self) -> Option<&String> {
        self.fail_over_partner.as_ref()
    }
    pub fn port(&self) -> Port {
        self.port.clone()
    }
    pub fn sql_browser_port(&self) -> Option<u16> {
        None
    }
    pub fn socket(&self) -> Option<&PathBuf> {
        self.socket.as_ref()
    }
    pub fn trust_server_certificate(&self) -> bool {
        self.trust_server_certificate
    }
    pub fn tls(&self) -> Option<&ConnectionTls> {
        self.tls.as_ref()
    }
    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.timeout)
    }
    pub fn backend(&self) -> &Backend {
        &self.backend
    }
    pub fn exclude_databases(&self) -> &Vec<String> {
        &self.exclude_databases
    }

    fn ensure(mut self, auth: Option<&Authentication>) -> Self {
        match auth {
            Some(auth) if auth.auth_type() == &AuthType::Integrated => {
                self.fail_over_partner = None;
                self.socket = None;
            }
            _ => {}
        }
        self
    }
}

impl Default for Connection {
    fn default() -> Self {
        Self {
            hostname: defaults::CONNECTION_HOST_NAME.to_string().into(),
            fail_over_partner: None,
            port: Port(defaults::CONNECTION_PORT),
            socket: None,
            trust_server_certificate: defaults::TRUST_SERVER_CERTIFICATE,
            tls: None,
            timeout: defaults::CONNECTION_TIMEOUT,
            backend: Backend::default(),
            exclude_databases: vec![],
            force_local_host: false,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct ConnectionTls {
    ca: PathBuf,
    client_certificate: CertPath,
}

impl ConnectionTls {
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let tls = yaml.get(keys::TLS);
        if tls.is_badvalue() {
            return Ok(None);
        }
        let ca = tls.get_pathbuf(keys::CA).context("Bad/Missing CA")?;
        let client_certificate = tls
            .get_string(keys::CLIENT_CERTIFICATE)
            .map(|s| s.into())
            .context("bad/Missing CLIENT_CERTIFICATE")?;
        log::info!(
            "Using ca '{}' client certificate: '{}'",
            ca.display(),
            client_certificate,
        );
        Ok(Some(Self {
            ca,
            client_certificate,
        }))
    }
    pub fn ca(&self) -> &Path {
        &self.ca
    }
    pub fn client_certificate(&self) -> &CertPath {
        &self.client_certificate
    }
}

#[derive(PartialEq, Debug, Clone, Default)]
pub struct Endpoint {
    auth: Authentication,
    conn: Connection,
}

impl Endpoint {
    pub fn new(auth: &Authentication, conn: &Connection) -> Self {
        Self {
            auth: auth.clone(),
            conn: conn.clone(),
        }
    }
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }

    pub fn conn(&self) -> &Connection {
        &self.conn
    }

    pub fn port(&self) -> Port {
        self.conn.port()
    }

    pub fn split(&self) -> (&Authentication, &Connection) {
        (self.auth(), self.conn())
    }

    pub fn hostname(&self) -> HostName {
        self.conn().hostname().clone()
    }

    pub fn dump_compact(&self) -> String {
        format!(
            "host: {} port: {} user: {} auth: {:?}",
            self.hostname(),
            self.port(),
            self.auth().username(),
            self.auth().auth_type()
        )
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Discovery {
    detect: bool,
    include: Vec<String>,
    exclude: Vec<String>,
}

impl Default for Discovery {
    fn default() -> Self {
        Self {
            detect: defaults::DISCOVERY_DETECT,
            include: vec![],
            exclude: vec![],
        }
    }
}

impl Discovery {
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let discovery = yaml.get(keys::DISCOVERY);
        if discovery.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            detect: discovery.get_bool(keys::DETECT, defaults::DISCOVERY_DETECT),
            include: discovery.get_string_vector(keys::INCLUDE, &[]),
            exclude: discovery.get_string_vector(keys::EXCLUDE, &[]),
        }))
    }
    pub fn detect(&self) -> bool {
        self.detect
    }
    pub fn include(&self) -> &Vec<String> {
        &self.include
    }
    pub fn exclude(&self) -> &Vec<String> {
        &self.exclude
    }

    pub fn is_instance_allowed(&self, name: &InstanceName) -> bool {
        if !self.include.is_empty() {
            return self.include.contains(&name.to_string());
        }

        if self.exclude.contains(&name.to_string()) {
            return false;
        }

        true
    }
}

#[derive(PartialEq, Debug, Clone)]
pub enum Mode {
    Port,
    Socket,
    Special,
}

impl Mode {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        Mode::try_from(yaml.get_string(keys::MODE).as_deref().unwrap_or_default())
    }
}

impl TryFrom<&str> for Mode {
    type Error = anyhow::Error;

    fn try_from(str: &str) -> Result<Self> {
        match str::to_ascii_lowercase(str).as_ref() {
            values::PORT => Ok(Mode::Port),
            values::SOCKET => Ok(Mode::Socket),
            values::SPECIAL => Ok(Mode::Special),
            _ => Err(anyhow!("unsupported mode")),
        }
    }
}

#[derive(PartialEq, Debug, Clone, Default)]
pub struct CustomInstance {
    /// also known as sid
    name: InstanceName,
    auth: Authentication,
    conn: Connection,
    alias: Option<InstanceAlias>,
    piggyback: Option<Piggyback>,
    tcp: bool,
}

impl CustomInstance {
    pub fn is_tcp(&self) -> bool {
        self.tcp
    }

    pub fn from_yaml(
        yaml: &Yaml,
        main_auth: &Authentication,
        main_conn: &Connection,
        sections: &Sections,
    ) -> Result<Self> {
        let name = InstanceName::from(
            yaml.get_string(keys::SID)
                .context("Bad/Missing sid in instance")?
                .to_uppercase(),
        );
        let (auth, conn) = CustomInstance::ensure_auth_and_conn(yaml, main_auth, main_conn, &name)?;
        let tcp = is_use_tcp(&name, &auth, &conn);
        Ok(Self {
            name,
            auth,
            conn,
            alias: yaml.get_string(keys::ALIAS).map(InstanceAlias::from),
            piggyback: Piggyback::from_yaml(yaml, sections)?,
            tcp,
        })
    }

    pub fn from_registry(
        name: &InstanceName,
        main_auth: &Authentication,
        main_conn: &Connection,
        hostname: &Option<HostName>,
        port: &Option<Port>,
    ) -> Self {
        let (auth, conn) = CustomInstance::make_registry_auth_and_conn(
            main_auth,
            main_conn,
            hostname,
            port.as_ref().unwrap_or(&Port::from(0)),
        );
        Self {
            name: name.clone(),
            auth,
            conn,
            alias: None,
            piggyback: None,
            tcp: port.is_some(),
        }
    }

    /// Make auth and conn for custom instance using yaml
    /// - fallback on main_auth and main_conn if not defined in yaml
    /// - correct connection hostname if needed
    fn ensure_auth_and_conn(
        yaml: &Yaml,
        main_auth: &Authentication,
        main_conn: &Connection,
        sid: &InstanceName,
    ) -> Result<(Authentication, Connection)> {
        let auth = Authentication::from_yaml(yaml).unwrap_or(main_auth.clone());
        let conn = Connection::from_yaml(yaml, Some(&auth))?.unwrap_or(main_conn.clone());

        let instance_host = calc_real_host(&auth, &conn);
        let main_host = calc_real_host(main_auth, main_conn);
        if instance_host != main_host {
            log::warn!(
                "Host {instance_host} defined in {sid} doesn't match to main host {main_host}"
            );
            if main_auth.auth_type() != auth.auth_type() {
                log::warn!(
                    "Auth are different {:?} {:?}",
                    main_auth.auth_type(),
                    auth.auth_type()
                );
            }
        }
        Ok((
            auth,
            Connection {
                force_local_host: conn.force_local_host || main_conn.force_local_host,
                ..conn
            },
        ))
    }

    /// Make auth and conn for custom instance using windows registry
    fn make_registry_auth_and_conn(
        main_auth: &Authentication,
        main_conn: &Connection,
        hostname: &Option<HostName>,
        port: &Port,
    ) -> (Authentication, Connection) {
        let conn = Connection {
            hostname: hostname
                .clone()
                .unwrap_or_else(|| main_conn.hostname().clone()),
            port: port.clone(),
            ..main_conn.clone()
        };
        (main_auth.clone(), conn)
    }

    /// also known as sid
    pub fn name(&self) -> &InstanceName {
        &self.name
    }
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }
    pub fn conn(&self) -> &Connection {
        &self.conn
    }
    pub fn endpoint(&self) -> Endpoint {
        Endpoint::new(&self.auth, &self.conn)
    }
    pub fn alias(&self) -> &Option<InstanceAlias> {
        &self.alias
    }
    pub fn piggyback(&self) -> Option<&Piggyback> {
        self.piggyback.as_ref()
    }
    pub fn calc_real_host(&self) -> HostName {
        calc_real_host(&self.auth, &self.conn)
    }
}

pub fn calc_real_host(auth: &Authentication, conn: &Connection) -> HostName {
    if is_local_endpoint(auth, conn) {
        "localhost".to_string().into()
    } else {
        conn.hostname().clone()
    }
}

pub fn is_use_tcp(name: &InstanceName, auth: &Authentication, conn: &Connection) -> bool {
    if conn.backend() != &Backend::Auto && conn.backend() != &Backend::Tcp {
        return false;
    }
    if is_local_endpoint(auth, conn) {
        get_registry_instance_info(name)
            .map(|i| i.is_tcp())
            .unwrap_or(true)
    } else {
        true
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Piggyback {
    hostname: String,
    sections: Sections,
}

impl Piggyback {
    pub fn from_yaml(yaml: &Yaml, sections: &Sections) -> Result<Option<Self>> {
        let piggyback = yaml.get(keys::PIGGYBACK);
        if piggyback.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            hostname: piggyback
                .get_string(keys::HOSTNAME)
                .context("Bad/Missing hostname in piggyback")?,
            sections: Sections::from_yaml(piggyback, sections)?,
        }))
    }

    pub fn hostname(&self) -> &String {
        &self.hostname
    }

    pub fn sections(&self) -> &Sections {
        &self.sections
    }
}

#[cfg(test)]
mod tests {
    use tests::defaults::{MAX_CONNECTIONS, MAX_QUERIES};

    use self::data::TEST_CONFIG;

    use super::*;
    use crate::config::{ms_sql::Backend, section::SectionKind, yaml::test_tools::create_yaml};
    use crate::constants::tests::expected_instances_in_config;
    mod data {
        /// copied from tests/files/test-config.yaml
        pub const TEST_CONFIG: &str = r#"
---
mssql:
  main: # mandatory, to be used if no specific config
    options:
      max_connections: 5
    authentication: # mandatory
      username: "foo" # mandatory
      password: "bar" # optional
      type: "sql_server" # optional, default: "integrated", values: sql_server, windows, token and integrated (current windows user)
      access_token: "baz" # optional
    connection: # optional
      hostname: "localhost" # optional(default: "localhost")
      failoverpartner: "localhost2" # optional
      port: 1433 # optional(default: 1433)
      socket: 'C:\path\to\file' # optional
      trust_server_certificate: no
      tls: # optional
        ca: 'C:\path\to\file' # mandatory
        client_certificate: 'C:\path\to\file' # mandatory
      timeout: 5 # optional(default: 5)
    sections: # optional
    - instance:  # special section
    - databases:
    - counters:
    - blocked_sessions:
    - transactionlogs:
    - clusters:
    - mirroring:
    - availability_groups:
    - connections:
    - tablespaces:
        is_async : yes
    - datafiles:
        is_async: yes
    - backup:
        is_async: yes
    - jobs:
        is_async: yes
    - someOtherSQL:
        is_async: yes
        disabled: yes
    cache_age: 600 # optional(default:600)
    piggyback_host: "my_pb_host"
    discovery: # optional
      detect: true # optional(default:yes)
      include: ["foo", "bar", "INST2"] # optional prio 2; use instance even if excluded
      exclude: ["baz"] # optional, prio 3
    mode: "socket" # optional(default:"port") - "socket", "port" or "special"
    instances: # optional
      - sid: "INST1" # mandatory
        authentication: # optional, same as above
        connection: # optional,  same as above
          backend: odbc
          exclude_databases: ["model"]
        alias: "someApplicationName" # optional
        piggyback: # optional
          hostname: "myPiggybackHost" # mandatory
          sections: # optional, same as above
      - sid: "INST2"
        authentication:
          username: "u"
          password: "p"
          type: "sql_server"
          access_token: "b"
        connection:
          hostname: "local"
          port: 500
          backend: tcp
          exclude_databases: ["master", "model"]
  configs:
    - main:
        options:
          max_connections: 11
        authentication: # mandatory
          username: "f" # mandatory
          password: "b"
          type: "sql_server"
        connection: # optional
          hostname: "localhost" # optional(default: "localhost")
          timeout: 5 # optional(default: 5)
        discovery: # optional
          detect: yes # optional(default:yes)
    - main:
        options:
          max_connections: 11
        connection: # optional
          hostname: "localhost" # optional(default: "localhost")
          timeout: 5 # optional(default: 5)
        piggyback_host: "no"
        discovery: # optional
          detect: yes # optional(default:yes)
    - main:
        authentication: # optional
          username: "f"
          password: "b"
          type: "sql_server"
  "#;
        pub const AUTHENTICATION_FULL: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "sql_server"
  access_token: "baz"
"#;
        #[cfg(windows)]
        pub const AUTHENTICATION_INTEGRATED: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "integrated"
  access_token: "baz"
"#;
        pub const AUTHENTICATION_MINI: &str = r#"
authentication:
  username: "foo"
  _password: "bar"
  _type: "system"
  _access_token: "baz"
"#;

        pub const CONNECTION_FULL: &str = r#"
connection:
  hostname: "alice"
  failoverpartner: "bob"
  port: 9999
  socket: 'C:\path\to\file_socket'
  trust_server_certificate: no
  tls:
    ca: 'C:\path\to\file_ca'
    client_certificate: 'C:\path\to\file_client'
  timeout: 341
"#;
        pub const DISCOVERY_FULL: &str = r#"
discovery:
  detect: false
  include: ["a", "b" ]
  exclude: ["c", "d" ]
"#;
        pub const PIGGYBACK_HOST: &str = "piggyback_host: zuzu";

        pub const PIGGYBACK_FULL: &str = r#"
piggyback:
  hostname: "piggy_host"
  sections:
    - alw1:
    - alw2:
    - cached1:
        is_async: yes
    - cached2:
        is_async: yes
    - disabled:
        disabled: yes
  cache_age: 111
"#;
        pub const PIGGYBACK_SHORT: &str = r#"
piggyback:
  hostname: "piggy_host"
"#;
        pub const INSTANCE: &str = r#"
sid: "INST1"
authentication:
  username: "u1"
  type: "sql_server"
connection:
  hostname: "h1"
alias: "a1"
piggyback:
  hostname: "Piggy"
  sections:
  cache_age: 123
"#;
        pub const PIGGYBACK_NO_HOSTNAME: &str = r#"
piggyback:
  _hostname: "piggy_host"
  sections:
    cache_age: 111
"#;
        pub const PIGGYBACK_NO_SECTIONS: &str = r#"
piggyback:
  hostname: "piggy_host"
  _sections:
    cache_age: 111
"#;
    }

    #[test]
    fn test_config_default() {
        assert_eq!(
            Config::default(),
            Config {
                auth: Authentication::default(),
                conn: Connection::default(),
                sections: Sections::default(),
                discovery: Discovery::default(),
                piggyback_host: None,
                mode: Mode::Port,
                custom_instances: vec![],
                configs: vec![],
                hash: String::new(),
                options: Options::default(),
            }
        );
    }

    #[test]
    fn test_system_default() {
        let s = Options::default();
        assert_eq!(s.max_connections(), MAX_CONNECTIONS.into());
        assert_eq!(s.max_queries(), MAX_QUERIES.into());
    }

    #[test]
    fn test_config_inheritance() {
        let mut c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        clean_config_from_custom_instances(&mut c);
        assert_eq!(c.configs.len(), 3);
        assert_eq!(c.custom_instances.len(), 2 + expected_count_in_registry());
        assert_eq!(c.configs[0].options(), &Options::new(11.into()));
        assert_eq!(c.configs[1].options(), &Options::new(11.into()));
        assert_eq!(c.configs[1].auth(), c.auth());
        assert_ne!(c.configs[1].conn(), c.conn());
        assert_ne!(c.configs[1].discovery(), c.discovery());
        assert_ne!(c.configs[1].options(), c.options());
        assert_ne!(c.configs[1].piggyback_host(), c.piggyback_host());
        assert_ne!(c.configs[2].auth(), c.auth());
        assert_eq!(c.configs[2].conn(), c.conn());
        assert_eq!(c.configs[2].discovery(), c.discovery());
        assert_eq!(c.configs[2].options(), c.options());
        assert_eq!(c.configs[2].sections(), c.sections());
        assert_eq!(c.configs[2].mode(), c.mode());

        // NON INHERITED
        assert_eq!(c.configs[2].piggyback_host(), None);
        assert_ne!(c.configs[2].piggyback_host(), c.piggyback_host());
        assert_ne!(c.configs[2].instances(), c.instances());
    }

    #[test]
    fn test_authentication_from_yaml() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_FULL)).unwrap();
        assert_eq!(a.username(), "foo");
        assert_eq!(a.password(), Some(&"bar".to_owned()));
        assert_eq!(a.auth_type(), &AuthType::SqlServer);
        assert_eq!(a.access_token(), Some(&"baz".to_owned()));
    }

    #[test]
    fn test_authentication_from_yaml_empty() {
        assert!(Authentication::from_yaml(&create_yaml(r"authentication:")).is_ok());
    }

    #[test]
    fn test_authentication_from_yaml_no_username() {
        assert!(Authentication::from_yaml(&create_yaml(
            r#"
authentication:
  _username: 'aa'
"#
        ))
        .is_ok());
    }

    #[test]
    fn test_authentication_from_yaml_mini() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_MINI)).unwrap();
        #[cfg(windows)]
        assert_eq!(a.username(), "");
        #[cfg(unix)]
        assert_eq!(a.username(), "foo");
        assert_eq!(a.password(), None);
        #[cfg(windows)]
        assert_eq!(a.auth_type(), &AuthType::Integrated);
        #[cfg(unix)]
        assert_eq!(a.auth_type(), &AuthType::SqlServer);
        assert_eq!(a.access_token(), None);
    }

    #[cfg(windows)]
    #[test]
    fn test_authentication_from_yaml_integrated() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_INTEGRATED)).unwrap();
        assert_eq!(a.username(), "");
        assert_eq!(a.password(), None);
        assert_eq!(a.auth_type(), &AuthType::Integrated);
        assert_eq!(a.access_token(), None);
    }

    #[test]
    fn test_connection_from_yaml() {
        let c = Connection::from_yaml(&create_yaml(data::CONNECTION_FULL), None)
            .unwrap()
            .unwrap();
        assert_eq!(c.hostname(), "alice".to_string().into());
        assert_eq!(c.fail_over_partner(), Some(&"bob".to_owned()));
        assert_eq!(c.port(), Port(9999));
        assert_eq!(c.socket(), Some(&PathBuf::from(r"C:\path\to\file_socket")));
        assert!(!c.trust_server_certificate());
        assert_eq!(c.timeout(), Duration::from_secs(341));
        let tls = c.tls().unwrap();
        assert_eq!(tls.ca(), PathBuf::from(r"C:\path\to\file_ca"));
        assert_eq!(
            tls.client_certificate(),
            &r"C:\path\to\file_client".to_owned().into()
        );
        assert_eq!(c.backend(), &Backend::default());
        assert!(c.exclude_databases().is_empty());
    }

    fn connection_force_local_host(param: Option<bool>) -> String {
        format!(
            r#"
connection:
  hostname: "alice"
  {}
"#,
            match param {
                Some(v) => format!("force_local_host: {}", if v { "yes" } else { "no" }),
                None => "".to_string(),
            }
        )
    }

    #[test]
    fn test_connection_force_local_host_from_yaml() {
        for (inp, expected) in [
            (connection_force_local_host(Some(true)), "localhost"),
            (connection_force_local_host(Some(false)), "alice"),
            (connection_force_local_host(None), "alice"),
        ] {
            let c = Connection::from_yaml(&create_yaml(&inp), None)
                .unwrap()
                .unwrap();
            assert_eq!(c.hostname(), expected.to_string().into());
        }
    }

    #[test]
    fn test_connection_backend() {
        let test: Vec<(&str, Backend)> = vec![
            ("auto", Backend::Auto),
            ("tcp", Backend::Tcp),
            #[cfg(unix)]
            ("odbc", Backend::Auto),
            #[cfg(windows)]
            ("odbc", Backend::Odbc),
            ("unknown", Backend::default()),
            ("", Backend::default()),
        ];
        for (value, expected) in test {
            let config_text = create_full_connection_with_backend(value);
            let c = Connection::from_yaml(&create_yaml(&config_text), None)
                .unwrap()
                .unwrap();
            assert_eq!(c.backend(), &expected);
        }
    }

    fn create_full_connection_with_backend(value: &str) -> String {
        format!(
            r#"{}
  backend: {}
"#,
            data::CONNECTION_FULL,
            value
        )
    }

    #[cfg(windows)]
    #[test]
    fn test_connection_from_yaml_auth_integrated() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_INTEGRATED)).unwrap();
        let c = Connection::from_yaml(&create_yaml(data::CONNECTION_FULL), Some(&a))
            .unwrap()
            .unwrap();
        assert_eq!(c.hostname(), "alice".to_string().into());
        assert_eq!(c.fail_over_partner(), None);
        assert_eq!(c.port(), Port(9999));
        assert_eq!(c.socket(), None);
        assert_eq!(c.timeout(), Duration::from_secs(341));
        let tls = c.tls().unwrap();
        assert_eq!(tls.ca(), PathBuf::from(r"C:\path\to\file_ca"));
        assert_eq!(
            tls.client_certificate(),
            &r"C:\path\to\file_client".to_owned().into()
        );
    }

    #[test]
    fn test_connection_from_yaml_default() {
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_default(), None)
                .unwrap()
                .unwrap(),
            Connection::default()
        );
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_empty_host(), None)
                .unwrap()
                .unwrap(),
            Connection::default()
        );
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_non_empty_host(), None)
                .unwrap()
                .unwrap(),
            Connection {
                hostname: HostName::from("aa".to_string()),
                ..Default::default()
            }
        );
        assert_eq!(
            Connection::from_yaml(&create_yaml("nothing: "), None).unwrap(),
            None
        );
    }

    fn create_connection_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
connection:
  _nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }

    fn create_connection_yaml_empty_host() -> Yaml {
        const SOURCE: &str = r#"
connection:
  hostname: ''
"#;
        create_yaml(SOURCE)
    }

    fn create_connection_yaml_non_empty_host() -> Yaml {
        const SOURCE: &str = r#"
connection:
  hostname: 'Aa'
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_discovery_from_yaml_full() {
        let discovery = Discovery::from_yaml(&create_yaml(data::DISCOVERY_FULL))
            .unwrap()
            .unwrap();
        assert!(!discovery.detect());
        assert_eq!(discovery.include(), &vec!["a".to_string(), "b".to_string()]);
        assert_eq!(discovery.exclude(), &vec!["c".to_string(), "d".to_string()]);
    }

    #[test]
    fn test_piggyback_host() {
        let ph = &create_yaml(data::PIGGYBACK_HOST).get_string(keys::PIGGYBACK_HOST);
        assert_eq!(ph.as_deref(), Some("zuzu"));
    }

    #[test]
    fn test_discovery_from_yaml_default() {
        let discovery = Discovery::from_yaml(&create_discovery_yaml_default())
            .unwrap()
            .unwrap();
        assert!(discovery.detect());
        assert!(discovery.include().is_empty());
        assert!(discovery.exclude().is_empty());
    }

    fn create_discovery_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
discovery:
  _nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_mode_try_from() {
        assert!(Mode::try_from("a").is_err());
        assert_eq!(Mode::try_from("poRt").unwrap(), Mode::Port);
        assert_eq!(Mode::try_from("soCKET").unwrap(), Mode::Socket);
        assert_eq!(Mode::try_from("SPecial").unwrap(), Mode::Special);
    }

    #[test]
    fn test_mode_from_yaml() {
        assert!(Mode::from_yaml(&create_yaml("mode: Zu")).is_err());
        assert!(Mode::from_yaml(&create_yaml("no_mode: port")).is_err());
        assert_eq!(
            Mode::from_yaml(&create_yaml("mode: Special")).unwrap(),
            Mode::Special
        );
    }

    fn as_names(sections: Vec<&Section>) -> Vec<&str> {
        sections.iter().map(|s| s.name()).collect()
    }

    #[test]
    fn test_piggyback() {
        let piggyback =
            Piggyback::from_yaml(&create_yaml(data::PIGGYBACK_FULL), &Sections::default())
                .unwrap()
                .unwrap();
        assert_eq!(piggyback.hostname(), "piggy_host");
        let all = piggyback.sections();
        assert_eq!(as_names(all.select(&[SectionKind::Sync])), ["alw1", "alw2"],);
        assert_eq!(
            as_names(all.select(&[SectionKind::Async])),
            ["cached1", "cached2"]
        );
        assert_eq!(as_names(all.select(&[SectionKind::Disabled])), ["disabled"]);
    }

    #[test]
    fn test_piggyback_short() {
        let piggyback =
            Piggyback::from_yaml(&create_yaml(data::PIGGYBACK_SHORT), &Sections::default())
                .unwrap()
                .unwrap();
        assert_eq!(piggyback.hostname(), "piggy_host");
        let all = piggyback.sections();
        assert_eq!(Sections::default(), all.clone());
    }

    #[test]
    fn test_piggyback_error() {
        assert!(Piggyback::from_yaml(
            &create_yaml(data::PIGGYBACK_NO_HOSTNAME),
            &Sections::default()
        )
        .is_err());
        assert_eq!(
            Piggyback::from_yaml(
                &create_yaml(data::PIGGYBACK_NO_SECTIONS),
                &Sections::default()
            )
            .unwrap()
            .unwrap()
            .sections(),
            &Sections::default()
        );
    }

    #[test]
    fn test_piggyback_none() {
        assert_eq!(
            Piggyback::from_yaml(&create_yaml("source:\n  xxx"), &Sections::default()).unwrap(),
            None
        );
    }
    #[test]
    fn test_custom_instance() {
        let a = Authentication {
            username: "ux".to_string(),
            auth_type: AuthType::SqlServer,
            ..Default::default()
        };
        let instance = CustomInstance::from_yaml(
            &create_yaml(data::INSTANCE),
            &a,
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.name().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.conn().hostname(), "h1".to_string().into());
        assert_eq!(instance.calc_real_host(), "h1".to_string().into());
        assert_eq!(instance.alias(), &Some("a1".to_string().into()));
        assert_eq!(instance.piggyback().unwrap().hostname(), "Piggy");
        assert_eq!(instance.piggyback().unwrap().sections().cache_age(), 123);
    }

    #[test]
    fn test_custom_instance_always_localhost() {
        let a = Authentication {
            username: "ux".to_string(),
            auth_type: AuthType::SqlServer,
            ..Default::default()
        };
        let instance = CustomInstance::from_yaml(
            &create_yaml(data::INSTANCE),
            &a,
            &Connection {
                force_local_host: true,
                ..Default::default()
            },
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.name().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.conn().hostname(), "localhost".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost".to_string().into());
        assert_eq!(instance.alias(), &Some("a1".to_string().into()));
        assert_eq!(instance.piggyback().unwrap().hostname(), "Piggy");
        assert_eq!(instance.piggyback().unwrap().sections().cache_age(), 123);
    }

    fn expected_count_in_registry() -> usize {
        #[cfg(windows)]
        return 3;
        #[cfg(unix)]
        return 0;
    }

    #[cfg(windows)]
    #[test]
    fn test_custom_instance_integrated() {
        pub const INSTANCE_INTEGRATED: &str = r#"
sid: "INST1"
authentication:
  username: "u1"
  type: "integrated"
connection:
  hostname: "h1"
"#;
        let instance = CustomInstance::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.name().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "");
        assert_eq!(instance.conn().hostname(), "h1".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost".to_string().into());
    }

    #[cfg(windows)]
    #[test]
    fn test_custom_instance_integrated_default() {
        pub const INSTANCE_INTEGRATED: &str = r#"
sid: "INST1"
authentication:
  username: "u1"
  type: "integrated"
connection:
  port: 5555
"#;
        let instance = CustomInstance::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.name().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "");
        assert_eq!(instance.auth().auth_type(), &AuthType::Integrated);
        assert_eq!(instance.conn().hostname(), "localhost".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost".to_string().into());
    }

    #[test]
    fn test_custom_instance_remote_default() {
        pub const INSTANCE_INTEGRATED: &str = r#"
sid: "INST1"
authentication:
  username: "u1"
  password: "pwd"
  type: "sql_server"
connection:
  port: 5555
"#;
        let instance = CustomInstance::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.name().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.auth().password().unwrap(), "pwd");
        assert_eq!(instance.auth().auth_type(), &AuthType::SqlServer);
        assert_eq!(instance.conn().hostname(), "localhost".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost".to_string().into());
    }

    /// remove some custom instances
    fn clean_config_from_custom_instances(c: &mut Config) {
        c.custom_instances
            .retain(|i| expected_instances_in_config().contains(i.name()));
    }

    #[test]
    fn test_config() {
        let mut c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        clean_config_from_custom_instances(&mut c);
        assert_eq!(c.options(), &Options::new(5.into()));
        assert_eq!(c.instances().len(), 2 + expected_count_in_registry());
        assert!(c.instances()[0].piggyback().is_some());
        assert_eq!(
            c.instances()[0].piggyback().unwrap().hostname(),
            "myPiggybackHost"
        );
        assert_eq!(c.instances()[0].name().to_string(), "INST1");
        let inst1 = &c.instances()[0];
        #[cfg(unix)]
        assert_eq!(inst1.conn().backend(), &Backend::Auto);
        #[cfg(windows)]
        assert_eq!(inst1.conn().backend(), &Backend::Odbc);
        assert_eq!(inst1.conn().exclude_databases(), &vec!["model"]);
        let inst2 = &c.instances()[1];

        assert_eq!(inst2.name().to_string(), "INST2");
        assert_eq!(inst2.auth().password, Some("p".to_string()));
        assert_eq!(&inst2.auth().username, "u");
        assert_eq!(inst2.auth().auth_type, AuthType::SqlServer);
        assert_eq!(inst2.conn().hostname, HostName::from("local".to_string()));
        assert_eq!(inst2.conn().port, Port(500));
        assert_eq!(inst2.conn().backend(), &Backend::Tcp);
        assert_eq!(inst2.conn().exclude_databases(), &vec!["master", "model"]);
        assert_eq!(c.mode(), &Mode::Socket);
        assert_eq!(
            c.discovery().include(),
            &vec!["foo".to_string(), "bar".to_string(), "INST2".to_string()]
        );
        assert_eq!(c.discovery().exclude(), &vec!["baz".to_string()]);
        assert!(c.discovery().detect());
        assert_eq!(c.auth().username(), "foo");
        assert_eq!(c.auth().password().unwrap(), "bar");
        assert_eq!(c.auth().auth_type(), &AuthType::SqlServer);
        assert_eq!(c.auth().access_token().unwrap(), "baz");
        assert_eq!(c.conn().hostname(), "localhost".to_string().into());
        assert_eq!(c.conn().fail_over_partner().unwrap(), "localhost2");
        assert_eq!(c.conn().port(), Port(defaults::CONNECTION_PORT));
        assert!(!c.conn().trust_server_certificate());
        assert_eq!(
            c.conn().socket().unwrap(),
            &PathBuf::from(r"C:\path\to\file")
        );
        assert_eq!(c.piggyback_host(), Some("my_pb_host"));
        assert_eq!(c.conn().tls().unwrap().ca(), Path::new(r"C:\path\to\file"));
        assert_eq!(
            c.conn().tls().unwrap().client_certificate(),
            &r"C:\path\to\file".to_owned().into()
        );
        assert_eq!(
            c.conn().timeout(),
            std::time::Duration::from_secs(defaults::CONNECTION_TIMEOUT)
        );
        let as_names = |sections: &[Section], kind: SectionKind| {
            sections
                .iter()
                .filter(|s| s.kind() == kind)
                .map(|s| s.name().to_string())
                .collect::<Vec<String>>()
        };
        assert_eq!(
            as_names(c.all_sections(), SectionKind::Sync),
            defaults::SECTIONS_ALWAYS
        );
        assert_eq!(
            as_names(c.all_sections(), SectionKind::Async),
            defaults::SECTIONS_CACHED
        );
        assert_eq!(
            as_names(c.all_sections(), SectionKind::Disabled),
            ["someOtherSQL".to_string()]
        );
        assert_eq!(c.cache_age(), defaults::SECTIONS_CACHE_AGE);
    }

    #[test]
    fn test_config_discovery() {
        let c = make_detect_config(&[], &[]);
        assert!(c.is_instance_allowed(&"weird"));
        let c = make_detect_config(&["a", "b"], &["a", "b"]);
        assert!(!c.is_instance_allowed(&"weird"));
        assert!(c.is_instance_allowed(&"a"));
        assert!(c.is_instance_allowed(&"b"));
    }

    #[cfg(windows)]
    fn filter_from_custom_instances(full: Vec<CustomInstance>) -> Vec<CustomInstance> {
        full.into_iter()
            .filter(|i| expected_instances_in_config().contains(i.name()))
            .collect::<Vec<_>>()
    }

    #[cfg(windows)]
    #[test]
    fn test_get_additional_registry_instances() {
        // nothing found
        fn print_array(a: &[CustomInstance]) -> String {
            a.iter()
                .map(|i| format!("{}: {}-{}", i.name(), i.conn().port(), i.is_tcp()))
                .collect::<Vec<String>>()
                .join(", ")
        }
        let auth = Authentication::default();
        let conn = Connection::default();
        let found: Vec<CustomInstance> = vec![];
        let full = get_additional_registry_instances(&found, &auth, &conn);
        let full = filter_from_custom_instances(full);
        assert_eq!(full.len(), 3);
        assert!(full.iter().all(|i| i.is_tcp()), "{:?}", print_array(&full));
        assert!(
            full.iter().all(|i| i.conn().port() >= Port(1433)),
            "{:?}",
            print_array(&full)
        );

        // one is found
        let found: Vec<CustomInstance> = vec![CustomInstance {
            name: "MSSQLSERVER".to_string().into(),
            ..Default::default()
        }];
        let a = get_additional_registry_instances(&found, &auth, &conn);
        let a = filter_from_custom_instances(a);
        assert_eq!(a.len(), 2);
        assert!(a.iter().all(|i| i.conn().port() > Port(10000)));
    }

    #[cfg(windows)]
    #[test]
    fn test_get_additional_registry_instances_non_localhost() {
        let auth = Authentication {
            username: "ux".to_string(),
            auth_type: AuthType::SqlServer,
            ..Default::default()
        };
        let conn = Connection {
            hostname: HostName::from("ux".to_string()),
            ..Default::default()
        };
        let found: Vec<CustomInstance> = vec![];
        let a = get_additional_registry_instances(&found, &auth, &conn);
        assert!(a.is_empty());
    }
    #[cfg(unix)]
    #[test]
    fn test_get_additional_registry_instances() {
        let auth = Authentication::default();
        let conn = Connection::default();
        let found: Vec<CustomInstance> = vec![];
        let a = get_additional_registry_instances(&found, &auth, &conn);
        assert!(a.is_empty());
    }

    fn make_detect_config(include: &[&str], exclude: &[&str]) -> Config {
        let source = format!(
            r"---
mssql:
  main:
    authentication:
      username: foo
    discovery:
      detect: true # doesn't matter for us
      include: {include:?}
      exclude: {exclude:?}
    instances:
      - sid: sid1
      - sid: sid2
        connection:
          hostname: ab
"
        );
        Config::from_string(&source).unwrap().unwrap()
    }

    #[test]
    fn test_calc_hash() {
        let c1 = Config::from_string(TEST_CONFIG).unwrap().unwrap();
        let c2 = Config::from_string(&(TEST_CONFIG.to_string() + "\n# xxx"))
            .unwrap()
            .unwrap();
        let c3 = Config::from_string(
            &(TEST_CONFIG.to_string()
                + r#"
    - main:
        authentication: # mandatory
          username: "f" # mandatory"#),
        )
        .unwrap()
        .unwrap();
        assert_eq!(c1.hash.len(), 16);
        assert_eq!(c1.hash, c2.hash);
        assert_ne!(c1.hash, c3.hash);
    }

    #[test]
    fn test_calc_effective_host() {
        let conn_to_bar = Connection {
            hostname: "bAr".to_string().into(),
            ..Default::default()
        };
        let auth_integrated = Authentication {
            auth_type: AuthType::Integrated,
            ..Default::default()
        };
        let auth_sql_server = Authentication {
            auth_type: AuthType::SqlServer,
            ..Default::default()
        };

        assert_eq!(
            calc_real_host(&auth_integrated, &conn_to_bar),
            "localhost".to_string().into()
        );
        assert_eq!(
            calc_real_host(&auth_sql_server, &conn_to_bar),
            "bAr".to_string().into()
        );
    }

    #[test]
    fn test_sections_enabled() {
        const CONFIG: &str = r#"
---
mssql:
  main: # mandatory, to be used if no specific config
    authentication: # mandatory
      username: "f" # mandatory
    sections:
      - instance:
      - jobs:
          is_async: yes
      - backup:
          disabled: yes
"#;
        let config = Config::from_string(CONFIG).unwrap().unwrap();
        assert_eq!(
            config
                .all_sections()
                .iter()
                .map(|s| (s.name(), s.kind()))
                .collect::<Vec<(&str, SectionKind)>>(),
            [
                ("instance", SectionKind::Sync),
                ("jobs", SectionKind::Async),
                ("backup", SectionKind::Disabled),
            ]
        );
        assert_eq!(
            config
                .valid_sections()
                .iter()
                .map(|s| (s.name(), s.kind()))
                .collect::<Vec<(&str, SectionKind)>>(),
            [
                ("instance", SectionKind::Sync),
                ("jobs", SectionKind::Async),
            ]
        );
    }

    #[test]
    fn test_is_use_tcp_local() {
        let a = Authentication::default();
        let c = Connection::default();
        assert!(is_use_tcp(&"foo".to_string().into(), &a, &c));
        assert!(is_use_tcp(&"MSSQLSERVER".to_string().into(), &a, &c));
        assert!(is_use_tcp(&"SQLEXPRESS_NAME".to_string().into(), &a, &c));
    }
    #[test]
    fn test_is_use_tcp_remote() {
        let a = Authentication {
            auth_type: AuthType::Undefined,
            ..Default::default()
        };
        let c = Connection::default();
        assert!(is_use_tcp(&"MSSQLSERVER".to_string().into(), &a, &c));
    }

    fn _make_non_local_host_name() -> HostName {
        "localhost.com".to_string().into()
    }

    fn _make_non_local_connection(backend: Backend) -> Connection {
        Connection {
            hostname: _make_non_local_host_name(),
            backend,
            ..Default::default()
        }
    }
    #[test]
    fn test_is_use_tcp() {
        let srv_name: InstanceName = "SERVER".to_string().into();
        let auth_sql = Authentication {
            auth_type: AuthType::SqlServer,
            ..Default::default()
        };
        let conn_non_local_tcp = _make_non_local_connection(Backend::Tcp);
        assert!(is_use_tcp(&srv_name, &auth_sql, &conn_non_local_tcp));

        let conn_non_local_auto = _make_non_local_connection(Backend::Auto);
        assert!(is_use_tcp(&srv_name, &auth_sql, &conn_non_local_auto));

        #[cfg(windows)]
        {
            let conn_non_local_odbc = _make_non_local_connection(Backend::Odbc);
            assert!(!is_use_tcp(&srv_name, &auth_sql, &conn_non_local_odbc));
        }
    }
    #[test]
    fn test_is_local_endpoint() {
        let auth_integrated = Authentication {
            auth_type: AuthType::Integrated,
            ..Default::default()
        };
        let auth_sql = Authentication {
            auth_type: AuthType::SqlServer,
            ..Default::default()
        };
        let conn_non_local = Connection {
            hostname: HostName::from("localhost.com".to_string()),
            ..Default::default()
        };
        let conn_local = Connection {
            hostname: HostName::from("localhost".to_string()),
            ..Default::default()
        };
        let conn_127 = Connection {
            hostname: HostName::from("127.0.0.1".to_string()),
            ..Default::default()
        };
        assert!(is_local_endpoint(&auth_integrated, &conn_local));
        assert!(is_local_endpoint(&auth_integrated, &conn_non_local));
        assert!(is_local_endpoint(&auth_sql, &conn_local));
        assert!(is_local_endpoint(&auth_sql, &conn_127));
        assert!(!is_local_endpoint(&auth_sql, &conn_non_local));
    }
}
