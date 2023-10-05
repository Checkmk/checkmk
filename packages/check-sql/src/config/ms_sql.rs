// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::yaml::{Get, Yaml};
use anyhow::{anyhow, bail, Context, Result};
use std::path::{Path, PathBuf};

mod keys {
    pub const AUTHENTICATION: &str = "authentication";
    pub const USERNAME: &str = "username";
    pub const PASSWORD: &str = "password";
    pub const TYPE: &str = "type";
    pub const ACCESS_TOKEN: &str = "access_token";
    pub const SYSTEM: &str = "system";
    pub const WINDOWS: &str = "windows";

    pub const CONNECTION: &str = "connection";
    pub const HOSTNAME: &str = "hostname";
    pub const FAIL_OVER_PARTNER: &str = "failoverpartner";
    pub const TLS: &str = "tls";
    pub const PORT: &str = "port";
    pub const SOCKET: &str = "socket";
    pub const TIMEOUT: &str = "timeout";
    pub const CA: &str = "ca";
    pub const CLIENT_CERTIFICATE: &str = "client_certificate";

    pub const SQLS: &str = "sqls";
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
}

mod defaults {
    pub const CONNECTION_HOST_NAME: &str = "localhost";
    pub const CONNECTION_PORT: u16 = 1433;
    pub const CONNECTION_TIMEOUT: u32 = 5;
    pub const SQLS_CACHE_AGE: u32 = 600;
    pub const SQLS_ALWAYS: &[&str] = &[
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
    pub const SQLS_CACHED: &[&str] = &["tablespaces", "datafiles", "backup", "jobs"];

    pub const DISCOVERY_DETECT: bool = true;
    pub const DISCOVERY_ALL: bool = false;
}

#[derive(PartialEq, Debug)]
pub struct Config {
    auth: Authentication,
    conn: Connection,
    sqls: Sqls,
    discovery: Discovery,
    mode: Mode,
    instances: Vec<Instance>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            auth: Authentication::default(),
            conn: Connection::default(),
            sqls: Sqls::default(),
            discovery: Discovery::default(),
            mode: Mode::Port,
            instances: vec![],
        }
    }
}

impl Config {
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }
    pub fn conn(&self) -> &Connection {
        &self.conn
    }
    pub fn sqls(&self) -> &Sqls {
        &self.sqls
    }
    pub fn discovery(&self) -> &Discovery {
        &self.discovery
    }
    pub fn mode(&self) -> &Mode {
        &self.mode
    }
    pub fn instances(&self) -> &Vec<Instance> {
        &self.instances
    }
}

#[derive(PartialEq, Debug)]
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
            auth_type: AuthType::System,
            access_token: None,
        }
    }
}
impl Authentication {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let auth = yaml.get(keys::AUTHENTICATION);
        Ok(Self {
            username: auth
                .get_string(keys::USERNAME)
                .context("bad/absent username")?,
            password: auth.get_string(keys::PASSWORD),
            auth_type: match auth.get_string(keys::TYPE).as_deref() {
                Some(keys::SYSTEM) | None => AuthType::System,
                Some(keys::WINDOWS) => AuthType::Windows,
                _ => bail!("unknown auth type"),
            },
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

#[derive(PartialEq, Debug)]
pub enum AuthType {
    System,
    Windows,
}

#[derive(PartialEq, Debug)]
pub struct Connection {
    hostname: String,
    fail_over_partner: Option<String>,
    port: u16,
    socket: Option<PathBuf>,
    tls: Option<ConnectionTls>,
    timeout: u32,
}

impl Connection {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let conn = yaml.get(keys::CONNECTION);
        Ok(Self {
            hostname: conn
                .get_string(keys::HOSTNAME)
                .unwrap_or_else(|| defaults::CONNECTION_HOST_NAME.to_string()),
            fail_over_partner: conn.get_string(keys::FAIL_OVER_PARTNER),
            port: conn.get_int::<u16>(keys::PORT, defaults::CONNECTION_PORT),
            socket: conn.get_pathbuf(keys::SOCKET),
            tls: ConnectionTls::from_yaml(conn)?,
            timeout: conn.get_int::<u32>(keys::TIMEOUT, defaults::CONNECTION_TIMEOUT),
        })
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
    pub fn socket(&self) -> Option<&PathBuf> {
        self.socket.as_ref()
    }
    pub fn tls(&self) -> Option<&ConnectionTls> {
        self.tls.as_ref()
    }
    pub fn timeout(&self) -> u32 {
        self.timeout
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

#[derive(PartialEq, Debug)]
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

#[derive(PartialEq, Debug)]
pub struct Sqls {
    always: Vec<String>,
    cached: Vec<String>,
    disabled: Vec<String>,
    cache_age: u32,
}

impl Default for Sqls {
    fn default() -> Self {
        Self {
            always: defaults::SQLS_ALWAYS
                .iter()
                .map(|s| s.to_string())
                .collect(),
            cached: defaults::SQLS_CACHED
                .iter()
                .map(|s| s.to_string())
                .collect(),
            disabled: vec![],
            cache_age: defaults::SQLS_CACHE_AGE,
        }
    }
}

impl Sqls {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let sqls = yaml.get(keys::SQLS);
        if sqls.is_badvalue() {
            return Ok(Sqls::default());
        }
        Ok(Self {
            always: sqls.get_string_vector(keys::ALWAYS, defaults::SQLS_ALWAYS)?,
            cached: sqls.get_string_vector(keys::CACHED, defaults::SQLS_CACHED)?,
            disabled: sqls.get_string_vector(keys::DISABLED, &[])?,
            cache_age: sqls.get_int(keys::CACHE_AGE, defaults::SQLS_CACHE_AGE),
        })
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
            Ok(Discovery::default())
        } else {
            Ok(Self {
                detect: discovery.get_bool(keys::DETECT, defaults::DISCOVERY_DETECT)?,
                all: discovery.get_bool(keys::ALL, defaults::DISCOVERY_ALL)?,
                include: discovery.get_string_vector(keys::INCLUDE, &[])?,
                exclude: discovery.get_string_vector(keys::EXCLUDE, &[])?,
            })
        }
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
        Mode::try_from(yaml.get_string(keys::MODE).as_deref())
    }
}

impl TryFrom<Option<&str>> for Mode {
    type Error = anyhow::Error;

    fn try_from(str: Option<&str>) -> Result<Self> {
        match str.map(str::to_ascii_lowercase).as_deref() {
            Some("port") | None => Ok(Mode::Port),
            Some("socket") => Ok(Mode::Socket),
            Some("special") => Ok(Mode::Special),
            _ => Err(anyhow!("unsupported mode")),
        }
    }
}

#[derive(PartialEq, Debug)]
pub struct Instance {
    name: String,
    auth: Authentication,
    conn: Option<Connection>,
    alias: String,
    piggyback: Option<Piggyback>,
}

impl Instance {
    pub fn name(&self) -> &String {
        &self.name
    }
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }
    pub fn conn(&self) -> Option<&Connection> {
        self.conn.as_ref()
    }
    pub fn alias(&self) -> &String {
        &self.alias
    }
    pub fn piggyback(&self) -> Option<&Piggyback> {
        self.piggyback.as_ref()
    }
}

#[derive(PartialEq, Debug)]
pub struct Piggyback {
    hostname: String,
    sqls: Option<Sqls>,
}

impl Piggyback {
    pub fn hostname(&self) -> &String {
        &self.hostname
    }

    pub fn sqls(&self) -> Option<&Sqls> {
        self.sqls.as_ref()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use yaml_rust::YamlLoader;

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
                sqls: Sqls::default(),
                discovery: Discovery::default(),
                mode: Mode::Port,
                instances: vec![],
            }
        );
    }

    #[test]
    fn test_authentication_from_yaml() {
        let a = Authentication::from_yaml(&create_authentication_yaml_full()).unwrap();
        assert_eq!(a.username(), "foo");
        assert_eq!(a.password(), Some(&"bar".to_owned()));
        assert_eq!(a.auth_type(), &AuthType::Windows);
        assert_eq!(a.access_token(), Some(&"baz".to_owned()));
    }

    fn create_authentication_yaml_full() -> Yaml {
        const SOURCE: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "windows"
  access_token: "baz"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_authentication_from_yaml_empty() {
        assert!(Authentication::from_yaml(&create_yaml(r"authentication:")).is_err());
    }

    #[test]
    fn test_authentication_from_yaml_no_username() {
        assert!(Authentication::from_yaml(&create_yaml(
            r#"
authentication:
  _username: 'aa'
"#
        ))
        .is_err());
    }

    #[test]
    fn test_authentication_from_yaml_mini() {
        let a = Authentication::from_yaml(&create_authentication_yaml_mini()).unwrap();
        assert_eq!(a.username(), "foo");
        assert_eq!(a.password(), None);
        assert_eq!(a.auth_type(), &AuthType::System);
        assert_eq!(a.access_token(), None);
    }

    fn create_authentication_yaml_mini() -> Yaml {
        const SOURCE: &str = r#"
authentication:
  username: "foo"
  _password: "bar"
  _type: "system"
  _access_token: "baz"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_connection_from_yaml() {
        let c = Connection::from_yaml(&create_connection_yaml_full()).unwrap();
        assert_eq!(c.hostname(), "alice");
        assert_eq!(c.fail_over_partner(), Some(&"bob".to_owned()));
        assert_eq!(c.port(), 9999);
        assert_eq!(c.socket(), Some(&PathBuf::from(r"C:\path\to\file_socket")));
        assert_eq!(c.timeout(), 341);
        let tls = c.tls().unwrap();
        assert_eq!(tls.ca(), PathBuf::from(r"C:\path\to\file_ca"));
        assert_eq!(
            tls.client_certificate(),
            PathBuf::from(r"C:\path\to\file_client")
        );
    }

    fn create_connection_yaml_full() -> Yaml {
        const SOURCE: &str = r#"
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
        create_yaml(SOURCE)
    }

    #[test]
    fn test_connection_from_yaml_default() {
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_default()).unwrap(),
            Connection::default()
        );
        assert_eq!(
            Connection::from_yaml(&create_yaml("nothing: ")).unwrap(),
            Connection::default()
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
    fn test_sqls_from_yaml_full() {
        let s = Sqls::from_yaml(&create_sqls_yaml_full()).unwrap();
        assert_eq!(s.always(), &vec!["aaa".to_string(), "bbb".to_string()]);
        assert_eq!(s.cached(), &vec!["ccc".to_string(), "ddd".to_string()]);
        assert_eq!(s.disabled(), &vec!["eee".to_string()]);
        assert_eq!(s.cache_age(), 900);
    }

    fn create_sqls_yaml_full() -> Yaml {
        const SOURCE: &str = r#"
sqls:
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
        create_yaml(SOURCE)
    }

    #[test]
    fn test_sqls_from_yaml_default() {
        let s = Sqls::from_yaml(&create_sqls_yaml_default()).unwrap();
        assert_eq!(s.always(), defaults::SQLS_ALWAYS.clone());
        assert_eq!(s.cached(), defaults::SQLS_CACHED.clone());
        assert!(s.disabled().is_empty());
        assert_eq!(s.cache_age(), defaults::SQLS_CACHE_AGE);
        assert_eq!(s, Sqls::from_yaml(&create_yaml("_sqls:\n")).unwrap());
    }

    fn create_sqls_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
sqls:
  _nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_discovery_from_yaml_full() {
        let discovery = Discovery::from_yaml(&create_discovery_yaml_full()).unwrap();
        assert!(!discovery.detect());
        assert!(discovery.all());
        assert_eq!(discovery.include(), &vec!["a".to_string(), "b".to_string()]);
        assert_eq!(discovery.exclude(), &vec!["c".to_string(), "d".to_string()]);
    }

    fn create_discovery_yaml_full() -> Yaml {
        const SOURCE: &str = r#"
discovery:
  detect: no
  all: yes
  include: ["a", "b" ]
  exclude: ["c", "d" ]
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_discovery_from_yaml_default() {
        let discovery = Discovery::from_yaml(&create_discovery_yaml_default()).unwrap();
        assert_eq!(discovery.detect(), defaults::DISCOVERY_DETECT);
        assert_eq!(discovery.all(), defaults::DISCOVERY_ALL);
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
        assert!(Mode::try_from(Some("a")).is_err());
        assert_eq!(Mode::try_from(None).unwrap(), Mode::Port);
        assert_eq!(Mode::try_from(Some("poRt")).unwrap(), Mode::Port);
        assert_eq!(Mode::try_from(Some("soCKET")).unwrap(), Mode::Socket);
        assert_eq!(Mode::try_from(Some("SPecial")).unwrap(), Mode::Special);
    }

    #[test]
    fn test_mode_from_yaml() {
        assert!(Mode::from_yaml(&create_yaml("mode: Zu")).is_err());
        assert_eq!(
            Mode::from_yaml(&create_yaml("mode: Special")).unwrap(),
            Mode::Special
        );
    }
}
