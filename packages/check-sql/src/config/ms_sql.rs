// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::yaml::{Get, Yaml};
use anyhow::{anyhow, bail, Context, Result};
use std::path::{Path, PathBuf};
use std::time::Duration;
use yaml_rust::YamlLoader;

mod keys {
    pub const MSSQL: &str = "mssql";
    pub const MAIN: &str = "main";

    pub const AUTHENTICATION: &str = "authentication";
    pub const USERNAME: &str = "username";
    pub const PASSWORD: &str = "password";
    pub const TYPE: &str = "type";
    pub const ACCESS_TOKEN: &str = "access_token";

    pub const CONNECTION: &str = "connection";
    pub const HOSTNAME: &str = "hostname";
    pub const FAIL_OVER_PARTNER: &str = "failoverpartner";
    pub const TLS: &str = "tls";
    pub const PORT: &str = "port";
    pub const SOCKET: &str = "socket";
    pub const TIMEOUT: &str = "timeout";
    pub const CA: &str = "ca";
    pub const CLIENT_CERTIFICATE: &str = "client_certificate";

    pub const SECTIONS: &str = "sections";
    pub const ALWAYS: &str = "always";
    pub const CACHED: &str = "cached";
    pub const CACHE_AGE: &str = "cache_age";
    pub const DISABLED: &str = "disabled";

    pub const DISCOVERY: &str = "discovery";
    pub const DETECT: &str = "detect";
    pub const ALL: &str = "all";
    pub const INCLUDE: &str = "include";
    pub const EXCLUDE: &str = "exclude";

    pub const MODE: &str = "mode";

    pub const CUSTOM: &str = "custom";

    pub const SID: &str = "sid";
    pub const ALIAS: &str = "alias";
    pub const PIGGYBACK: &str = "piggyback";

    pub const CONFIGS: &str = "configs";
}

mod values {
    /// AuthType::System
    pub const SQL_SERVER: &str = "sql_server";
    /// AuthType::Windows
    #[cfg(windows)]
    pub const WINDOWS: &str = "windows";
    /// AuthType::Integrated
    #[cfg(windows)]
    pub const INTEGRATED: &str = "integrated";
    /// AuthType::Token
    pub const TOKEN: &str = "token";
    /// Mode::Port
    pub const PORT: &str = "port";
    /// Mode::Socket
    pub const SOCKET: &str = "socket";
    /// AuthType::Special
    pub const SPECIAL: &str = "special";
}

mod defaults {
    use crate::config::ms_sql::values;
    #[cfg(windows)]
    pub const AUTH_TYPE: &str = values::INTEGRATED;
    #[cfg(unix)]
    pub const AUTH_TYPE: &str = values::SQL_SERVER;
    pub const MODE: &str = values::PORT;
    pub const CONNECTION_HOST_NAME: &str = "localhost";
    pub const CONNECTION_PORT: u16 = 1433;
    pub const CONNECTION_TIMEOUT: u64 = 5;
    pub const SECTIONS_CACHE_AGE: u32 = 600;
    pub const SECTIONS_ALWAYS: &[&str] = &[
        "instance",
        "databases",
        "counters",
        "blocked_sessions",
        "transactionlogs",
        "clusters",
        "mirroring",
        "availability_groups",
        "connections",
    ];
    pub const SECTIONS_CACHED: &[&str] = &["tablespaces", "datafiles", "backup", "jobs"];

    pub const DISCOVERY_DETECT: bool = true;
    pub const DISCOVERY_ALL: bool = true;
}

#[derive(PartialEq, Debug)]
pub struct Config {
    auth: Authentication,
    conn: Connection,
    sections: Sections,
    discovery: Discovery,
    mode: Mode,
    custom_instances: Vec<CustomInstance>,
    configs: Vec<Config>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            auth: Authentication::default(),
            conn: Connection::default(),
            sections: Sections::default(),
            discovery: Discovery::default(),
            mode: Mode::Port,
            custom_instances: vec![],
            configs: vec![],
        }
    }
}

impl Config {
    pub fn from_string(source: &str) -> Result<Option<Self>> {
        YamlLoader::load_from_str(source)?
            .get(0)
            .and_then(|e| Config::from_yaml(e).transpose())
            .transpose()
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let root = yaml.get(keys::MSSQL);
        if root.is_badvalue() {
            return Ok(None);
        }
        let c = Config::parse_main_from_yaml(root);
        match c {
            Ok(Some(c)) if c.auth().username().is_empty() => {
                anyhow::bail!("Bad/absent user name");
            }
            _ => c,
        }
    }

    fn parse_main_from_yaml(root: &Yaml) -> Result<Option<Self>> {
        let main = root.get(keys::MAIN);
        if main.is_badvalue() {
            bail!("main key is absent");
        }
        let auth = Authentication::from_yaml(main)?;
        let conn = Connection::from_yaml(main)?.unwrap_or_default();
        let sections = Sections::from_yaml(main)?.unwrap_or_default();
        let custom_instances: Result<Vec<CustomInstance>> = main
            .get_yaml_vector(keys::CUSTOM)
            .into_iter()
            .map(|v| CustomInstance::from_yaml(&v, &auth, &conn, &sections))
            .collect();

        let configs: Result<Vec<Config>> = root
            .get_yaml_vector(keys::CONFIGS)
            .into_iter()
            .filter_map(|v| Config::parse_main_from_yaml(&v).transpose())
            .collect();

        Ok(Some(Self {
            auth,
            conn,
            sections,
            discovery: Discovery::from_yaml(main)?,
            mode: Mode::from_yaml(main)?,
            custom_instances: custom_instances?,
            configs: configs?,
        }))
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
    pub fn sections(&self) -> &Sections {
        &self.sections
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

    pub fn is_instance_allowed(&self, name: &impl ToString) -> bool {
        if self.discovery.all() {
            return true;
        }

        if !self.discovery.include().is_empty() {
            return self.discovery.include().contains(&name.to_string());
        }

        if self.discovery.exclude().contains(&name.to_string()) {
            return false;
        }

        false
    }
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
        Ok(Self {
            username: auth.get_string(keys::USERNAME).unwrap_or_default(),
            password: auth.get_string(keys::PASSWORD),
            auth_type: AuthType::try_from(
                auth.get_string(keys::TYPE)
                    .as_deref()
                    .unwrap_or(defaults::AUTH_TYPE),
            )?,
            access_token: auth.get_string(keys::ACCESS_TOKEN),
        })
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
}

#[derive(PartialEq, Debug, Clone)]
pub enum AuthType {
    SqlServer,
    Windows,
    Integrated,
    Token,
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
pub struct Connection {
    hostname: String,
    fail_over_partner: Option<String>,
    port: u16,
    socket: Option<PathBuf>,
    tls: Option<ConnectionTls>,
    timeout: u64,
}

impl Connection {
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let conn = yaml.get(keys::CONNECTION);
        if conn.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            hostname: conn
                .get_string(keys::HOSTNAME)
                .unwrap_or_else(|| defaults::CONNECTION_HOST_NAME.to_string())
                .to_lowercase(),
            fail_over_partner: conn.get_string(keys::FAIL_OVER_PARTNER),
            port: conn.get_int::<u16>(keys::PORT, defaults::CONNECTION_PORT),
            socket: conn.get_pathbuf(keys::SOCKET),
            tls: ConnectionTls::from_yaml(conn)?,
            timeout: conn.get_int::<u64>(keys::TIMEOUT, defaults::CONNECTION_TIMEOUT),
        }))
    }
    pub fn hostname(&self) -> &str {
        &self.hostname
    }
    pub fn fail_over_partner(&self) -> Option<&String> {
        self.fail_over_partner.as_ref()
    }
    pub fn port(&self) -> u16 {
        self.port
    }
    pub fn sql_browser_port(&self) -> Option<u16> {
        None
    }
    pub fn socket(&self) -> Option<&PathBuf> {
        self.socket.as_ref()
    }
    pub fn tls(&self) -> Option<&ConnectionTls> {
        self.tls.as_ref()
    }
    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.timeout)
    }
}

impl Default for Connection {
    fn default() -> Self {
        Self {
            hostname: defaults::CONNECTION_HOST_NAME.to_owned(),
            fail_over_partner: None,
            port: defaults::CONNECTION_PORT,
            socket: None,
            tls: None,
            timeout: defaults::CONNECTION_TIMEOUT,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct ConnectionTls {
    ca: PathBuf,
    client_certificate: PathBuf,
}

impl ConnectionTls {
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let tls = yaml.get(keys::TLS);
        if tls.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            ca: tls.get_pathbuf(keys::CA).context("Bad/Missing CA")?,
            client_certificate: tls
                .get_pathbuf(keys::CLIENT_CERTIFICATE)
                .context("bad/Missing CLIENT_CERTIFICATE")?,
        }))
    }
    pub fn ca(&self) -> &Path {
        &self.ca
    }
    pub fn client_certificate(&self) -> &Path {
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

    pub fn split(&self) -> (&Authentication, &Connection) {
        (self.auth(), self.conn())
    }

    pub fn hostname(&self) -> String {
        if self.auth().auth_type() == &AuthType::Integrated {
            "localhost"
        } else {
            self.conn().hostname()
        }
        .to_string()
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Sections {
    always: Vec<String>,
    cached: Vec<String>,
    disabled: Vec<String>,
    cache_age: u32,
}

impl Default for Sections {
    fn default() -> Self {
        Self {
            always: defaults::SECTIONS_ALWAYS
                .iter()
                .map(|s| s.to_string())
                .collect(),
            cached: defaults::SECTIONS_CACHED
                .iter()
                .map(|s| s.to_string())
                .collect(),
            disabled: vec![],
            cache_age: defaults::SECTIONS_CACHE_AGE,
        }
    }
}

impl Sections {
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let sections = yaml.get(keys::SECTIONS);
        if sections.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            always: sections.get_string_vector(keys::ALWAYS, defaults::SECTIONS_ALWAYS),
            cached: sections.get_string_vector(keys::CACHED, defaults::SECTIONS_CACHED),
            disabled: sections.get_string_vector(keys::DISABLED, &[]),
            cache_age: sections.get_int(keys::CACHE_AGE, defaults::SECTIONS_CACHE_AGE),
        }))
    }
    pub fn always(&self) -> &Vec<String> {
        &self.always
    }
    pub fn cached(&self) -> &Vec<String> {
        &self.cached
    }
    pub fn disabled(&self) -> &Vec<String> {
        &self.disabled
    }
    pub fn cache_age(&self) -> u32 {
        self.cache_age
    }

    pub fn get_filtered_always(&self) -> Vec<String> {
        self.get_filtered(self.always())
    }

    pub fn get_filtered_cached(&self) -> Vec<String> {
        self.get_filtered(self.cached())
    }

    fn get_filtered(&self, sections: &[String]) -> Vec<String> {
        sections
            .iter()
            .filter_map(|sql| {
                if self.disabled().iter().any(|s| s == sql) {
                    None
                } else {
                    Some(sql.to_owned())
                }
            })
            .collect()
    }
}

#[derive(PartialEq, Debug)]
pub struct Discovery {
    detect: bool,
    all: bool,
    include: Vec<String>,
    exclude: Vec<String>,
}

impl Default for Discovery {
    fn default() -> Self {
        Self {
            detect: defaults::DISCOVERY_DETECT,
            all: defaults::DISCOVERY_ALL,
            include: vec![],
            exclude: vec![],
        }
    }
}

impl Discovery {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let discovery = yaml.get(keys::DISCOVERY);
        if discovery.is_badvalue() {
            return Ok(Discovery::default());
        }
        Ok(Self {
            detect: discovery.get_bool(keys::DETECT, defaults::DISCOVERY_DETECT)?,
            all: discovery.get_bool(keys::ALL, defaults::DISCOVERY_ALL)?,
            include: discovery.get_string_vector(keys::INCLUDE, &[]),
            exclude: discovery.get_string_vector(keys::EXCLUDE, &[]),
        })
    }
    pub fn detect(&self) -> bool {
        self.detect
    }
    pub fn all(&self) -> bool {
        self.all
    }
    pub fn include(&self) -> &Vec<String> {
        &self.include
    }
    pub fn exclude(&self) -> &Vec<String> {
        &self.exclude
    }
}

#[derive(PartialEq, Debug)]
pub enum Mode {
    Port,
    Socket,
    Special,
}

impl Mode {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        Mode::try_from(
            yaml.get_string(keys::MODE)
                .as_deref()
                .unwrap_or(defaults::MODE),
        )
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

#[derive(PartialEq, Debug, Clone)]
pub struct CustomInstance {
    sid: String,
    auth: Authentication,
    conn: Connection,
    alias: Option<String>,
    piggyback: Option<Piggyback>,
}

impl CustomInstance {
    pub fn from_yaml(
        yaml: &Yaml,
        main_auth: &Authentication,
        main_conn: &Connection,
        sections: &Sections,
    ) -> Result<Self> {
        let sid = yaml
            .get_string(keys::SID)
            .context("Bad/Missing sid in instance")?
            .to_lowercase();
        let (auth, conn) = CustomInstance::make_auth_and_conn(yaml, main_auth, main_conn, &sid)?;
        Ok(Self {
            sid,
            auth,
            conn,
            alias: yaml.get_string(keys::ALIAS),
            piggyback: Piggyback::from_yaml(yaml, sections)?,
        })
    }

    /// Make auth and conn for custom instance using yaml
    /// - fallback on main_auth and main_conn if not defined in yaml
    /// - correct connection hostname if needed
    fn make_auth_and_conn(
        yaml: &Yaml,
        main_auth: &Authentication,
        main_conn: &Connection,
        sid: &str,
    ) -> Result<(Authentication, Connection)> {
        let mut auth = Authentication::from_yaml(yaml).unwrap_or(main_auth.clone());
        let mut conn = Connection::from_yaml(yaml)?.unwrap_or(main_conn.clone());
        let instance_host = calc_real_host(&auth, &conn);
        let main_host = calc_real_host(main_auth, main_conn);
        if instance_host != main_host {
            log::error!("Host {instance_host} defined in {sid} doesn't match to main host {main_host}. Try to fall back");
            if main_auth.auth_type() == auth.auth_type()
                || main_auth.auth_type() == &AuthType::Integrated
            {
                log::warn!("Fall back to main conn host {main_host}");
                conn = Connection {
                    hostname: main_host.to_string(),
                    ..conn
                };
            } else if auth.auth_type() == &AuthType::Integrated {
                log::warn!(
                    "Instance auth is `integrated`: fall back to main auth type {:?}",
                    main_auth.auth_type()
                );
                auth = Authentication {
                    auth_type: main_auth.auth_type().clone(),
                    ..auth
                };
            } else {
                log::error!(
                    "Fall back is impossible {:?} {:?}",
                    main_auth.auth_type(),
                    auth.auth_type()
                );
            }
        }
        if auth.auth_type() == &AuthType::Integrated {
            conn = Connection {
                hostname: "localhost".to_string(),
                ..conn
            };
        }
        Ok((auth, conn))
    }

    pub fn sid(&self) -> &String {
        &self.sid
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
    pub fn alias(&self) -> Option<&String> {
        self.alias.as_ref()
    }
    pub fn piggyback(&self) -> Option<&Piggyback> {
        self.piggyback.as_ref()
    }
    pub fn calc_real_host(&self) -> String {
        calc_real_host(&self.auth, &self.conn)
    }
}

pub fn calc_real_host(auth: &Authentication, conn: &Connection) -> String {
    if auth.auth_type() == &AuthType::Integrated {
        "localhost".to_string()
    } else {
        conn.hostname().to_owned().to_lowercase()
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
            sections: Sections::from_yaml(piggyback)?.unwrap_or(sections.clone()),
        }))
    }

    pub fn hostname(&self) -> &String {
        &self.hostname
    }

    pub fn sections(&self) -> &Sections {
        &self.sections
    }
}

mod trace_tools {
    use std::io::{self, Write};
    use yaml_rust::{Yaml, YamlEmitter};
    #[allow(dead_code)]
    pub fn dump_yaml(yaml: &Yaml) -> String {
        let mut writer = String::new();

        let mut emitter = YamlEmitter::new(&mut writer);
        emitter.dump(yaml).unwrap();
        writer
    }

    #[allow(dead_code)]
    pub fn write_stdout(s: &impl ToString) {
        #[allow(clippy::explicit_write)]
        write!(io::stdout(), "{}", s.to_string()).unwrap();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use yaml_rust::YamlLoader;
    mod data {
        /// copied from tests/files/test-config.yaml
        pub const TEST_CONFIG: &str = r#"
---
mssql:
  main: # mandatory, to be used if no specific config
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
      tls: # optional
        ca: 'C:\path\to\file' # mandatory
        client_certificate: 'C:\path\to\file' # mandatory
      timeout: 5 # optional(default: 5)
    sections: # optional
      always: # optional(default)
        - "instance"
        - "databases"
        - "counters"
        - "blocked_sessions"
        - "transactionlogs"
        - "clusters"
        - "mirroring"
        - "availability_groups"
        - "connections"
      cached: # optional(default)
        - "tablespaces"
        - "datafiles"
        - "backup"
        - "jobs"
      disabled: # optional
        - "someOtherSQL"
      cache_age: 600 # optional(default:600)
    discovery: # optional
      detect: yes # optional(default:yes)
      all: no # optional(default:no) prio 1; ignore include/exclude if yes
      include: ["foo", "bar"] # optional prio 2; use instance even if excluded
      exclude: ["baz"] # optional, prio 3
    mode: "port" # optional(default:"port") - "socket", "port" or "special"
    custom: # optional
      - sid: "INST1" # mandatory
        authentication: # optional, same as above
        connection: # optional,  same as above
        alias: "someApplicationName" # optional
        piggyback: # optional
          hostname: "myPiggybackHost" # mandatory
          sections: # optional, same as above
      - sid: "INST2" # mandatory
  configs:
    - main:
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
        authentication: # mandatory
          username: "f"
          password: "b"
          type: "sql_server"
        connection: # optional
          hostname: "localhost" # optional(default: "localhost")
          timeout: 5 # optional(default: 5)
        discovery: # optional
          detect: yes # optional(default:yes)
  "#;
        pub const AUTHENTICATION_FULL: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "sql_server"
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
  tls:
    ca: 'C:\path\to\file_ca'
    client_certificate: 'C:\path\to\file_client'
  timeout: 341
"#;
        pub const SECTIONS_FULL: &str = r#"
sections:
  always:
    - "aaa"
    - "bbb"
  cached:
    - "ccc"
    - "ddd"
  disabled:
    - "eee"
  cache_age: 900
"#;
        pub const DISCOVERY_FULL: &str = r#"
discovery:
  detect: no
  all: yes
  include: ["a", "b" ]
  exclude: ["c", "d" ]
"#;
        pub const PIGGYBACK_FULL: &str = r#"
piggyback:
  hostname: "piggy_host"
  sections:
    always:
      - "alw1"
      - "alw2"
    cached:
      - "cache1"
      - "cache2"
    disabled:
      - "disabled"
    cache_age: 111
"#;
        pub const INSTANCE: &str = r#"
sid: "INST1"
authentication:
  username: "u1"
connection:
  hostname: "h1"
alias: "a1"
piggyback:
  hostname: "piggy"
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

    fn create_yaml(source: &str) -> Yaml {
        YamlLoader::load_from_str(source).expect("fix test string!")[0].clone()
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
                mode: Mode::Port,
                custom_instances: vec![],
                configs: vec![],
            }
        );
    }

    #[test]
    fn test_config_all() {
        let c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        assert_eq!(c.configs.len(), 2);
        assert_eq!(c.custom_instances.len(), 2);
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
        assert_eq!(a.username(), "foo");
        assert_eq!(a.password(), None);
        #[cfg(windows)]
        assert_eq!(a.auth_type(), &AuthType::Integrated);
        #[cfg(unix)]
        assert_eq!(a.auth_type(), &AuthType::SqlServer);
        assert_eq!(a.access_token(), None);
    }

    #[test]
    fn test_connection_from_yaml() {
        let c = Connection::from_yaml(&create_yaml(data::CONNECTION_FULL))
            .unwrap()
            .unwrap();
        assert_eq!(c.hostname(), "alice");
        assert_eq!(c.fail_over_partner(), Some(&"bob".to_owned()));
        assert_eq!(c.port(), 9999);
        assert_eq!(c.socket(), Some(&PathBuf::from(r"C:\path\to\file_socket")));
        assert_eq!(c.timeout(), Duration::from_secs(341));
        let tls = c.tls().unwrap();
        assert_eq!(tls.ca(), PathBuf::from(r"C:\path\to\file_ca"));
        assert_eq!(
            tls.client_certificate(),
            PathBuf::from(r"C:\path\to\file_client")
        );
    }

    #[test]
    fn test_connection_from_yaml_default() {
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_default())
                .unwrap()
                .unwrap(),
            Connection::default()
        );
        assert_eq!(
            Connection::from_yaml(&create_yaml("nothing: ")).unwrap(),
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
    #[test]
    fn test_sections_from_yaml_full() {
        let s = Sections::from_yaml(&create_yaml(data::SECTIONS_FULL))
            .unwrap()
            .unwrap();
        assert_eq!(s.always(), &vec!["aaa".to_string(), "bbb".to_string()]);
        assert_eq!(s.cached(), &vec!["ccc".to_string(), "ddd".to_string()]);
        assert_eq!(s.disabled(), &vec!["eee".to_string()]);
        assert_eq!(s.cache_age(), 900);
    }

    #[test]
    fn test_sections_filtered() {
        let s = Sections {
            always: vec!["eee".to_string(), "aaa".to_string()],
            cached: vec!["ccc".to_string(), "eee".to_string()],
            disabled: vec!["eee".to_string()],
            cache_age: 900,
        };
        assert_eq!(s.get_filtered_always(), vec!["aaa".to_string()]);
        assert_eq!(s.get_filtered_cached(), vec!["ccc".to_string()]);
    }

    #[test]
    fn test_sections_from_yaml_default() {
        let s = Sections::from_yaml(&create_sections_yaml_default())
            .unwrap()
            .unwrap();
        assert_eq!(s.always(), defaults::SECTIONS_ALWAYS);
        assert_eq!(s.cached(), defaults::SECTIONS_CACHED);
        assert!(s.disabled().is_empty());
        assert_eq!(s.cache_age(), defaults::SECTIONS_CACHE_AGE);
        assert!(Sections::from_yaml(&create_yaml("_sections:\n"))
            .unwrap()
            .is_none());
    }

    fn create_sections_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
sections:
  _nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_discovery_from_yaml_full() {
        let discovery = Discovery::from_yaml(&create_yaml(data::DISCOVERY_FULL)).unwrap();
        assert!(!discovery.detect());
        assert!(discovery.all());
        assert_eq!(discovery.include(), &vec!["a".to_string(), "b".to_string()]);
        assert_eq!(discovery.exclude(), &vec!["c".to_string(), "d".to_string()]);
    }

    #[test]
    fn test_discovery_from_yaml_default() {
        let discovery = Discovery::from_yaml(&create_discovery_yaml_default()).unwrap();
        assert!(discovery.detect());
        assert!(discovery.all());
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
        assert_eq!(
            Mode::from_yaml(&create_yaml("mode: Special")).unwrap(),
            Mode::Special
        );
    }

    #[test]
    fn test_piggyback() {
        let piggyback =
            Piggyback::from_yaml(&create_yaml(data::PIGGYBACK_FULL), &Sections::default())
                .unwrap()
                .unwrap();
        assert_eq!(piggyback.hostname(), "piggy_host");
        let sections = piggyback.sections();
        assert_eq!(
            sections.always(),
            &["alw1", "alw2"].map(str::to_string).to_vec()
        );
        assert_eq!(
            sections.cached(),
            &["cache1", "cache2"].map(str::to_string).to_vec()
        );
        assert_eq!(
            sections.disabled(),
            &["disabled"].map(str::to_string).to_vec()
        );
        assert_eq!(sections.cache_age(), 111);
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
        let instance = CustomInstance::from_yaml(
            &create_yaml(data::INSTANCE),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.sid(), "inst1");
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.conn().hostname(), "localhost");
        assert_eq!(instance.calc_real_host(), "localhost");
        assert_eq!(instance.alias().unwrap(), "a1");
        assert_eq!(instance.piggyback().unwrap().hostname(), "piggy");
        assert_eq!(instance.piggyback().unwrap().sections().cache_age(), 123);
    }

    #[test]
    fn test_config() {
        let c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        assert_eq!(c.instances().len(), 2);
        assert!(c.instances()[0].piggyback().is_some());
        assert_eq!(
            c.instances()[0].piggyback().unwrap().hostname(),
            "myPiggybackHost"
        );
        assert_eq!(c.instances()[0].sid(), "inst1");
        assert_eq!(c.instances()[1].sid(), "inst2");
        assert_eq!(c.mode(), &Mode::Port);
        assert_eq!(
            c.discovery().include(),
            &vec!["foo".to_string(), "bar".to_string()]
        );
        assert_eq!(c.discovery().exclude(), &vec!["baz".to_string()]);
        assert!(!c.discovery().all());
        assert!(c.discovery().detect());
        assert_eq!(c.auth().username(), "foo");
        assert_eq!(c.auth().password().unwrap(), "bar");
        assert_eq!(c.auth().auth_type(), &AuthType::SqlServer);
        assert_eq!(c.auth().access_token().unwrap(), "baz");
        assert_eq!(c.conn().hostname(), "localhost");
        assert_eq!(c.conn().fail_over_partner().unwrap(), "localhost2");
        assert_eq!(c.conn().port(), defaults::CONNECTION_PORT);
        assert_eq!(
            c.conn().socket().unwrap(),
            &PathBuf::from(r"C:\path\to\file")
        );
        assert_eq!(c.conn().tls().unwrap().ca(), Path::new(r"C:\path\to\file"));
        assert_eq!(
            c.conn().tls().unwrap().client_certificate(),
            Path::new(r"C:\path\to\file")
        );
        assert_eq!(
            c.conn().timeout(),
            std::time::Duration::from_secs(defaults::CONNECTION_TIMEOUT)
        );
        assert_eq!(c.sections().always(), defaults::SECTIONS_ALWAYS);
        assert_eq!(c.sections().cached(), defaults::SECTIONS_CACHED);
        assert_eq!(c.sections().disabled(), &vec!["someOtherSQL".to_string()]);
        assert_eq!(c.sections().cache_age(), defaults::SECTIONS_CACHE_AGE);
    }

    #[test]
    fn test_config_discovery() {
        let c = make_detect_config(true, &[], &[]);
        assert!(c.is_instance_allowed(&"weird"));
        let c = make_detect_config(false, &[], &[]);
        assert!(!c.is_instance_allowed(&"weird"));
        let c = make_detect_config(false, &["a", "b"], &["a", "b"]);
        assert!(!c.is_instance_allowed(&"weird"));
        assert!(c.is_instance_allowed(&"a"));
        assert!(c.is_instance_allowed(&"b"));
    }

    fn make_detect_config(all: bool, include: &[&str], exclude: &[&str]) -> Config {
        let source = format!(
            r"---
mssql:
  main:
    authentication:
      username: foo
    discovery:
      detect: true # doesnt matter for us
      all: {}
      include: {include:?}
      exclude: {exclude:?}
    custom:
      - sid: sid1
      - sid: sid2
        connection:
          hostname: ab
",
            if all { "yes" } else { "no" }
        );
        Config::from_string(&source).unwrap().unwrap()
    }

    #[test]
    fn test_calc_effective_host() {
        let conn_to_bar = Connection {
            hostname: "bAr".to_string(),
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

        assert_eq!(calc_real_host(&auth_integrated, &conn_to_bar), "localhost");
        assert_eq!(calc_real_host(&auth_sql_server, &conn_to_bar), "bar");
    }
}
