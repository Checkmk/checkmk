// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::yaml;
use anyhow::{bail, Context, Result};
use std::path::{Path, PathBuf};
use yaml_rust::Yaml;

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

    pub const INSTANCE_FILTER: &str = "instance_filter";
    pub const DETECT: &str = "detect";
    pub const ALL: &str = "all";
    pub const INCLUDE: &str = "include";
    pub const EXCLUDE: &str = "exclude";
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

    pub const INSTANCE_FILTER_DETECT: &str = "yes";
    pub const INSTANCE_FILTER_ALL: &str = "no";
}

#[derive(PartialEq, Debug)]
pub struct Config {
    auth: Authentication,
    conn: Connection,
    sqls: Sqls,
    instance_filter: InstanceFilter,
    mode: Mode,
    instances: Vec<Instance>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            auth: Authentication::default(),
            conn: Connection::default(),
            sqls: Sqls::default(),
            instance_filter: InstanceFilter::default(),
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
    pub fn instance_filter(&self) -> &InstanceFilter {
        &self.instance_filter
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
        let auth = &yaml[keys::AUTHENTICATION];
        Ok(Self {
            username: auth[keys::USERNAME]
                .as_str()
                .context("bad/absent username")?
                .to_owned(),
            password: auth[keys::PASSWORD].as_str().map(str::to_string),
            auth_type: match auth[keys::TYPE].as_str().unwrap_or(keys::SYSTEM) {
                keys::SYSTEM => AuthType::System,
                keys::WINDOWS => AuthType::Windows,
                _ => bail!("unknown auth type"),
            },
            access_token: auth[keys::ACCESS_TOKEN].as_str().map(str::to_string),
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
        let conn = &yaml[keys::CONNECTION];
        Ok(Self {
            hostname: conn[keys::HOSTNAME]
                .as_str()
                .unwrap_or(defaults::CONNECTION_HOST_NAME)
                .to_owned(),
            fail_over_partner: conn[keys::FAIL_OVER_PARTNER].as_str().map(str::to_string),
            port: conn[keys::PORT]
                .as_i64()
                .map(|v| v as u16)
                .unwrap_or(defaults::CONNECTION_PORT),
            socket: conn[keys::SOCKET].as_str().map(PathBuf::from),
            tls: ConnectionTls::from_yaml(conn)?,
            timeout: conn[keys::TIMEOUT]
                .as_i64()
                .map(|v| v as u32)
                .unwrap_or(defaults::CONNECTION_TIMEOUT),
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
        let tls = &yaml[keys::TLS];
        if tls.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
            ca: tls[keys::CA]
                .as_str()
                .map(PathBuf::from)
                .context("Bad/Missing CA")?,
            client_certificate: tls[keys::CLIENT_CERTIFICATE]
                .as_str()
                .map(PathBuf::from)
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
        let sqls = &yaml[keys::SQLS];
        if sqls.is_badvalue() {
            return Ok(Sqls::default());
        }
        Ok(Self {
            always: get_string_vector(sqls, keys::ALWAYS, defaults::SQLS_ALWAYS)?,
            cached: get_string_vector(sqls, keys::CACHED, defaults::SQLS_CACHED)?,
            disabled: get_string_vector(sqls, keys::DISABLED, &[])?,
            cache_age: sqls[keys::CACHE_AGE]
                .as_i64()
                .map(|v| v as u32)
                .unwrap_or(defaults::SQLS_CACHE_AGE),
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

fn get_string_vector(yaml: &Yaml, key: &str, default: &[&str]) -> Result<Vec<String>> {
    if yaml[key].is_badvalue() {
        Ok(default.iter().map(|&a| str::to_string(a)).collect())
    } else {
        yaml[key]
            .as_vec()
            .unwrap_or(&vec![])
            .iter()
            .map(|v| v.as_str().map(str::to_string).context("Not string"))
            .collect()
    }
}

#[derive(PartialEq, Debug)]
pub struct InstanceFilter {
    detect: String,
    all: String,
    include: Vec<String>,
    exclude: Vec<String>,
}

impl Default for InstanceFilter {
    fn default() -> Self {
        Self {
            detect: defaults::INSTANCE_FILTER_DETECT.to_owned(),
            all: defaults::INSTANCE_FILTER_DETECT.to_owned(),
            include: vec![],
            exclude: vec![],
        }
    }
}

impl InstanceFilter {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let filter = &yaml[keys::INSTANCE_FILTER];
        if filter.is_badvalue() {
            Ok(InstanceFilter::default())
        } else {
            Ok(Self {
                detect: load_assuming_bool(filter, keys::DETECT, defaults::INSTANCE_FILTER_DETECT)?,
                all: load_assuming_bool(filter, keys::ALL, defaults::INSTANCE_FILTER_ALL)?,
                include: get_string_vector(filter, keys::INCLUDE, &[])?,
                exclude: get_string_vector(filter, keys::EXCLUDE, &[])?,
            })
        }
    }
    pub fn detect(&self) -> bool {
        yaml::to_bool(&self.detect).unwrap()
    }
    pub fn all(&self) -> bool {
        yaml::to_bool(&self.all).unwrap()
    }
    pub fn include(&self) -> &Vec<String> {
        &self.include
    }
    pub fn exclude(&self) -> &Vec<String> {
        &self.exclude
    }
}

/// load a string from using key with default.
/// If obtained string is not bool-like -> error
fn load_assuming_bool(yaml: &Yaml, key: &str, default: &str) -> Result<String> {
    Ok(ensure_bool_string(yaml[key].as_str().unwrap_or(default))?.to_string())
}

/// returns error if string is not bool-like
fn ensure_bool_string(value: &str) -> Result<&str> {
    let _ = yaml::to_bool(value)?;
    Ok(value)
}

#[derive(PartialEq, Debug)]
pub enum Mode {
    Port,
    Socket,
    Special,
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
                instance_filter: InstanceFilter::default(),
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
    fn test_instance_filter_from_yaml_full() {
        let filter = InstanceFilter::from_yaml(&create_instance_filter_yaml_full()).unwrap();
        assert!(!filter.detect());
        assert!(filter.all());
        assert_eq!(filter.include(), &vec!["a".to_string(), "b".to_string()]);
        assert_eq!(filter.exclude(), &vec!["c".to_string(), "d".to_string()]);
    }

    fn create_instance_filter_yaml_full() -> Yaml {
        const SOURCE: &str = r#"
instance_filter:
  detect: no
  all: yes
  include: ["a", "b" ]
  exclude: ["c", "d" ]
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_instance_filter_from_yaml_default() {
        let filter = InstanceFilter::from_yaml(&create_instance_filter_yaml_default()).unwrap();
        assert_eq!(
            filter.detect(),
            yaml::to_bool(defaults::INSTANCE_FILTER_DETECT).unwrap()
        );
        assert_eq!(
            filter.all(),
            yaml::to_bool(defaults::INSTANCE_FILTER_ALL).unwrap()
        );
        assert!(filter.include().is_empty());
        assert!(filter.exclude().is_empty());
    }

    fn create_instance_filter_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
instance_filter:
  _nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }
}
