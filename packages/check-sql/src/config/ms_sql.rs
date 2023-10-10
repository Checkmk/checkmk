// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::yaml::{Get, Yaml};
use anyhow::{anyhow, bail, Context, Result};
use std::path::{Path, PathBuf};

mod keys {
    pub const MSSQL: &str = "mssql";
    pub const STANDARD: &str = "standard";

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

    pub const INSTANCES: &str = "instances";

    pub const SID: &str = "sid";
    pub const ALIAS: &str = "alias";
    pub const PIGGYBACK: &str = "piggyback";
}

mod values {
    /// AuthType::System
    pub const SYSTEM: &str = "system";
    /// AuthType::Windows
    pub const WINDOWS: &str = "windows";
    /// Mode::Port
    pub const PORT: &str = "port";
    /// Mode::Socket
    pub const SOCKET: &str = "socket";
    /// AuthType::Special
    pub const SPECIAL: &str = "special";
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
    pub const DISCOVERY_ALL: bool = true;
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
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let mssql = yaml.get(keys::MSSQL);
        if mssql.is_badvalue() {
            return Ok(None);
        }
        let standard = mssql.get(keys::STANDARD);
        if standard.is_badvalue() {
            bail!("standard key is absent");
        }

        let auth = Authentication::from_yaml(standard)?;
        let conn = Connection::from_yaml(standard)?.unwrap_or_default();
        let sqls = Sqls::from_yaml(standard)?.unwrap_or_default();
        let instances: Result<Vec<Instance>> = mssql
            .get_yaml_vector(keys::INSTANCES)
            .into_iter()
            .map(|v| Instance::from_yaml(&v, &auth, &conn, &sqls))
            .collect();

        Ok(Some(Self {
            auth,
            conn,
            sqls,
            discovery: Discovery::from_yaml(standard)?,
            mode: Mode::from_yaml(standard)?,
            instances: instances?,
        }))
    }
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
            auth_type: AuthType::try_from(auth.get_string(keys::TYPE).as_deref())?,
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
    System,
    Windows,
}

impl TryFrom<Option<&str>> for AuthType {
    type Error = anyhow::Error;

    fn try_from(str: Option<&str>) -> Result<Self> {
        match str.map(str::to_ascii_lowercase).as_deref() {
            Some(values::SYSTEM) | None => Ok(AuthType::System),
            Some(values::WINDOWS) => Ok(AuthType::Windows),
            _ => Err(anyhow!("unsupported auth type")),
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
    timeout: u32,
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
                .unwrap_or_else(|| defaults::CONNECTION_HOST_NAME.to_string()),
            fail_over_partner: conn.get_string(keys::FAIL_OVER_PARTNER),
            port: conn.get_int::<u16>(keys::PORT, defaults::CONNECTION_PORT),
            socket: conn.get_pathbuf(keys::SOCKET),
            tls: ConnectionTls::from_yaml(conn)?,
            timeout: conn.get_int::<u32>(keys::TIMEOUT, defaults::CONNECTION_TIMEOUT),
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

#[derive(PartialEq, Debug, Clone)]
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
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let sqls = yaml.get(keys::SQLS);
        if sqls.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            always: sqls.get_string_vector(keys::ALWAYS, defaults::SQLS_ALWAYS)?,
            cached: sqls.get_string_vector(keys::CACHED, defaults::SQLS_CACHED)?,
            disabled: sqls.get_string_vector(keys::DISABLED, &[])?,
            cache_age: sqls.get_int(keys::CACHE_AGE, defaults::SQLS_CACHE_AGE),
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
            include: discovery.get_string_vector(keys::INCLUDE, &[])?,
            exclude: discovery.get_string_vector(keys::EXCLUDE, &[])?,
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
        Mode::try_from(yaml.get_string(keys::MODE).as_deref())
    }
}

impl TryFrom<Option<&str>> for Mode {
    type Error = anyhow::Error;

    fn try_from(str: Option<&str>) -> Result<Self> {
        match str.map(str::to_ascii_lowercase).as_deref() {
            Some(values::PORT) | None => Ok(Mode::Port),
            Some(values::SOCKET) => Ok(Mode::Socket),
            Some(values::SPECIAL) => Ok(Mode::Special),
            _ => Err(anyhow!("unsupported mode")),
        }
    }
}

#[derive(PartialEq, Debug)]
pub struct Instance {
    sid: String,
    auth: Authentication,
    conn: Connection,
    alias: Option<String>,
    piggyback: Option<Piggyback>,
}

impl Instance {
    pub fn from_yaml(
        yaml: &Yaml,
        auth: &Authentication,
        conn: &Connection,
        sqls: &Sqls,
    ) -> Result<Self> {
        Ok(Self {
            sid: yaml
                .get_string(keys::SID)
                .context("Bad/Missing sid in instance")?,
            auth: Authentication::from_yaml(yaml).unwrap_or(auth.clone()),
            conn: Connection::from_yaml(yaml)?.unwrap_or(conn.clone()),
            alias: yaml.get_string(keys::ALIAS),
            piggyback: Piggyback::from_yaml(yaml, sqls)?,
        })
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
    pub fn alias(&self) -> Option<&String> {
        self.alias.as_ref()
    }
    pub fn piggyback(&self) -> Option<&Piggyback> {
        self.piggyback.as_ref()
    }
}

#[derive(PartialEq, Debug)]
pub struct Piggyback {
    hostname: String,
    sqls: Sqls,
}

impl Piggyback {
    pub fn from_yaml(yaml: &Yaml, sqls: &Sqls) -> Result<Option<Self>> {
        let piggyback = yaml.get(keys::PIGGYBACK);
        if piggyback.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            hostname: piggyback
                .get_string(keys::HOSTNAME)
                .context("Bad/Missing hostname in piggyback")?,
            sqls: Sqls::from_yaml(piggyback)?.unwrap_or(sqls.clone()),
        }))
    }

    pub fn hostname(&self) -> &String {
        &self.hostname
    }

    pub fn sqls(&self) -> &Sqls {
        &self.sqls
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use yaml_rust::YamlLoader;
    /// copied from tests/files/test-config.yaml
    const TEST_CONFIG: &str = r#"
---
mssql:
  standard: # mandatory, to be used if no specific config
    authentication: # mandatory
      username: "foo" # mandatory
      password: "bar" # optional
      type: "system" # optional(default: "system")
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
    sqls: # optional
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
  instances: # optional
    - sid: "INST1" # mandatory
      authentication: # optional, same as above
      connection: # optional,  same as above
      alias: "someApplicationName" # optional
      piggyback: # optional
        hostname: "myPiggybackHost" # mandatory
        sqls: # optional, same as above
    - sid: "INST2" # mandatory
"#;

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
        let c = Connection::from_yaml(&create_connection_yaml_full())
            .unwrap()
            .unwrap();
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
    fn test_sqls_from_yaml_full() {
        let s = Sqls::from_yaml(&create_sqls_yaml_full()).unwrap().unwrap();
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
        let s = Sqls::from_yaml(&create_sqls_yaml_default())
            .unwrap()
            .unwrap();
        assert_eq!(s.always(), defaults::SQLS_ALWAYS.clone());
        assert_eq!(s.cached(), defaults::SQLS_CACHED.clone());
        assert!(s.disabled().is_empty());
        assert_eq!(s.cache_age(), defaults::SQLS_CACHE_AGE);
        assert!(Sqls::from_yaml(&create_yaml("_sqls:\n")).unwrap().is_none());
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

    #[test]
    fn test_piggyback() {
        let piggyback = Piggyback::from_yaml(&create_piggyback_yaml_default(), &Sqls::default())
            .unwrap()
            .unwrap();
        assert_eq!(piggyback.hostname(), "piggy_host");
        let sqls = piggyback.sqls();
        assert_eq!(
            sqls.always(),
            &["alw1", "alw2"].map(str::to_string).to_vec()
        );
        assert_eq!(
            sqls.cached(),
            &["cache1", "cache2"].map(str::to_string).to_vec()
        );
        assert_eq!(sqls.disabled(), &["disabled"].map(str::to_string).to_vec());
        assert_eq!(sqls.cache_age(), 111);
    }

    fn create_piggyback_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
piggyback:
  hostname: "piggy_host"
  sqls:
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
        create_yaml(SOURCE)
    }

    #[test]
    fn test_piggyback_error() {
        assert!(
            Piggyback::from_yaml(&create_piggyback_yaml_no_hostname(), &Sqls::default()).is_err()
        );
        assert_eq!(
            Piggyback::from_yaml(&create_piggyback_yaml_no_sqls(), &Sqls::default())
                .unwrap()
                .unwrap()
                .sqls(),
            &Sqls::default()
        );
    }

    fn create_piggyback_yaml_no_hostname() -> Yaml {
        const SOURCE: &str = r#"
piggyback:
  _hostname: "piggy_host"
  sqls:
    cache_age: 111
"#;
        create_yaml(SOURCE)
    }

    fn create_piggyback_yaml_no_sqls() -> Yaml {
        const SOURCE: &str = r#"
piggyback:
  hostname: "piggy_host"
  _sqls:
    cache_age: 111
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_piggyback_none() {
        assert_eq!(
            Piggyback::from_yaml(&create_yaml("source:\n  xxx"), &Sqls::default()).unwrap(),
            None
        );
    }
    #[test]
    fn test_instance() {
        let instance = Instance::from_yaml(
            &create_instance(),
            &Authentication::default(),
            &Connection::default(),
            &Sqls::default(),
        )
        .unwrap();
        assert_eq!(instance.sid(), "INST1");
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.conn().hostname(), "h1");
        assert_eq!(instance.alias().unwrap(), "a1");
        assert_eq!(instance.piggyback().unwrap().hostname(), "piggy");
        assert_eq!(instance.piggyback().unwrap().sqls().cache_age(), 123);
    }

    fn create_instance() -> Yaml {
        const SOURCE: &str = r#"
    sid: "INST1"
    authentication:
      username: "u1"
    connection:
      hostname: "h1"
    alias: "a1"
    piggyback:
      hostname: "piggy"
      sqls:
        cache_age: 123
"#;
        create_yaml(SOURCE)
    }
    #[test]
    fn test_config() {
        let c = Config::from_yaml(&create_yaml(TEST_CONFIG))
            .unwrap()
            .unwrap();
        assert_eq!(c.instances().len(), 2);
        assert!(c.instances()[0].piggyback().is_some());
        assert_eq!(
            c.instances()[0].piggyback().unwrap().hostname(),
            "myPiggybackHost"
        );
        assert_eq!(c.instances()[0].sid(), "INST1");
        assert_eq!(c.instances()[1].sid(), "INST2");
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
        assert_eq!(c.auth().auth_type(), &AuthType::System);
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
        assert_eq!(c.conn().timeout(), defaults::CONNECTION_TIMEOUT);
        assert_eq!(c.sqls().always(), defaults::SQLS_ALWAYS);
        assert_eq!(c.sqls().cached(), defaults::SQLS_CACHED);
        assert_eq!(c.sqls().disabled(), &vec!["someOtherSQL".to_string()]);
        assert_eq!(c.sqls().cache_age(), defaults::SQLS_CACHE_AGE);
    }
}
