// Copyright (C) 2025 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

use super::defines::{defaults, keys, values};
use super::section::{Section, SectionKind, Sections};
use super::yaml::{Get, Yaml};
use crate::config::authentication::Authentication;
use crate::config::connection::Connection;
use crate::config::options::Options;
use crate::types::{HostName, InstanceAlias, InstanceName, ServiceName, SqlBindParam};
use anyhow::{anyhow, bail, Context, Result};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use yaml_rust2::YamlLoader;

#[derive(PartialEq, Debug)]
pub struct Config {
    auth: Authentication,
    conn: Connection,
    sections: Sections,
    discovery: Discovery,
    piggyback_host: Option<String>,
    mode: Mode,
    custom_instances: Vec<CustomService>,
    configs: Vec<Config>,
    hash: String,
    options: Options,
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
    pub fn from_string<T: AsRef<str>>(source: T) -> Result<Option<Self>> {
        let r = source.as_ref();

        let y = YamlLoader::load_from_str(r)?;
        y.first()
            .and_then(|e| Config::from_yaml(e).transpose())
            .transpose()
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let root = yaml.get(keys::ORACLE);
        if root.is_badvalue() {
            return Ok(None);
        }
        let default_config = Config::default();

        let config = Config::parse_main_from_yaml(root, &default_config)?;
        match config {
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

        let auth = Authentication::from_yaml(main)?.unwrap_or_else(|| default.auth.clone());
        let conn = Connection::from_yaml(main)?.unwrap_or_else(|| default.conn().clone());
        let options = Options::from_yaml(main)?.unwrap_or_else(|| default.options().clone());
        let discovery = Discovery::from_yaml(main)?.unwrap_or_else(|| default.discovery().clone());
        let section_info = Sections::from_yaml(main, &default.sections)?;

        let mut custom_instances = main
            .get_yaml_vector(keys::INSTANCES)
            .into_iter()
            .map(|v| CustomService::from_yaml(&v, &auth, &conn, &section_info))
            .collect::<Result<Vec<CustomService>>>()?;
        if discovery.detect() {
            let registry_instances =
                get_additional_registry_instances(&custom_instances, &auth, &conn);
            log::info!(
                "Found {} SQL server instances in REGISTRY: [ {} ]",
                registry_instances.len(),
                registry_instances
                    .iter()
                    .map(|i| format!(
                        "{}:{:?}",
                        i.service_name().unwrap_or(&ServiceName::default()),
                        i.conn().port()
                    ))
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
    pub fn instances(&self) -> &Vec<CustomService> {
        &self.custom_instances
    }
    pub fn configs(&self) -> &Vec<Config> {
        &self.configs
    }

    pub fn config_cache_dir(&self) -> String {
        "orasql-".to_owned() + &self.hash
    }

    pub fn product(&self) -> &Sections {
        &self.sections
    }

    pub fn is_instance_allowed(&self, name: &impl AsRef<str>) -> bool {
        self.discovery
            .is_instance_allowed(&InstanceName::from(name.as_ref()))
    }

    pub fn params(&self) -> &Vec<SqlBindParam> {
        self.options.params()
    }
}

fn get_additional_registry_instances(
    _already_found_instances: &[CustomService],
    _auth: &Authentication,
    conn: &Connection,
) -> Vec<CustomService> {
    if !conn.is_local() {
        log::info!("skipping registry instances: the host is not enough localhost");
    }
    log::error!("NOT IMPLEMENTED");

    vec![]
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

    pub fn hostname(&self) -> HostName {
        self.conn().hostname().clone()
    }

    pub fn dump_compact(&self) -> String {
        format!(
            "host: {} port: {} user: {} auth: {:?}",
            self.hostname(),
            self.conn().port(),
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
    pub fn new(detect: bool, include: Vec<String>, exclude: Vec<String>) -> Self {
        Self {
            detect,
            include,
            exclude,
        }
    }
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let discovery = yaml.get(keys::DISCOVERY);
        if discovery.is_badvalue() {
            return Ok(None);
        }
        let detect = discovery.get_bool(keys::DETECT, defaults::DISCOVERY_DETECT);
        let include = discovery
            .get_string_vector(keys::INCLUDE, &[])
            .into_iter()
            .map(|x| x.to_uppercase())
            .collect();
        let exclude = discovery
            .get_string_vector(keys::EXCLUDE, &[])
            .into_iter()
            .map(|x| x.to_uppercase())
            .collect();
        Ok(Some(Self::new(detect, include, exclude)))
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
            values::SPECIAL => Ok(Mode::Special),
            _ => Err(anyhow!("unsupported mode")),
        }
    }
}

#[derive(PartialEq, Debug, Clone, Default)]
pub struct CustomService {
    /// also known as sid
    auth: Authentication,
    conn: Connection,
    alias: Option<InstanceAlias>,
    piggyback: Option<Piggyback>,
}

impl CustomService {
    pub fn new(
        auth: Authentication,
        conn: Connection,
        alias: Option<InstanceAlias>,
        piggyback: Option<Piggyback>,
    ) -> Self {
        Self {
            auth,
            conn,
            alias,
            piggyback,
        }
    }

    pub fn from_yaml(
        yaml: &Yaml,
        main_auth: &Authentication,
        main_conn: &Connection,
        sections: &Sections,
    ) -> Result<Self> {
        Ok(Self::new(
            ensure_auth(yaml, main_auth)?,
            ensure_conn(yaml, main_conn)?,
            yaml.get_string(keys::ALIAS).map(InstanceAlias::from),
            Piggyback::from_yaml(yaml, sections)?,
        ))
    }

    /// may be overridden with a connection value
    pub fn service_name(&self) -> Option<&ServiceName> {
        self.conn.service_name()
    }
    pub fn instance_name(&self) -> Option<&InstanceName> {
        self.conn.instance_name()
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
        calc_real_host(&self.conn)
    }
}

/// Make auth for custom instance using yaml
/// - fallback on main_auth defined in yaml
fn ensure_auth(yaml: &Yaml, main_auth: &Authentication) -> Result<Authentication> {
    Ok(Authentication::from_yaml(yaml)?.unwrap_or(main_auth.clone()))
}

/// Make auth and conn for custom instance using yaml
/// - fallback on main_conn if not defined in yaml
/// - patch service_name and instance_name from yaml if defined
fn ensure_conn(yaml: &Yaml, main_conn: &Connection) -> Result<Connection> {
    let conn = Connection::from_yaml(yaml)?.unwrap_or(main_conn.clone());

    Ok(Connection::from_connection(
        &conn,
        &yaml.get_string(keys::SERVICE_NAME).map(ServiceName::from),
        &yaml.get_string(keys::INSTANCE_NAME).map(InstanceName::from),
    ))
}

pub fn calc_real_host(conn: &Connection) -> HostName {
    if conn.is_local() {
        "localhost".to_string().into()
    } else {
        conn.hostname().clone()
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
    use crate::config::authentication::AuthType;
    use crate::config::{section::SectionKind, yaml::test_tools::create_yaml};
    use crate::types::UseHostClient;
    use crate::types::{MaxConnections, MaxQueries};
    mod data {
        /// copied from tests/files/test-config.yaml
        pub const TEST_CONFIG: &str = r#"
---
oracle:
  main: # mandatory, to be used if no specific config
    options:
      max_connections: 5
      use_host_client: never
      IGNORE_DB_NAME: 13 # wrong value for normal config, just to test params
    authentication:
      username: "foo"
      password: "bar"
      role: "sysdba" # optional, default: empty, values: sysdba, sysasm, ...
      type: "standard" # mandatory, default: "standard", values: standard, wallet
    connection: # optional
      hostname: "localhost2" # optional(default: "localhost")
      service_name: "orcl" # optional
      port: 1521 # optional, default: 1521
      timeout: 11 # optional, default 5
      tns_admin: "/path/to/oracle/config/files/" # optional, default: agent plugin config folder. Points to the location of sqlnet.ora and tnsnames.ora
      oracle_local_registry: "/etc/oracle/olr.loc" # optional, default: folder of oracle configuration files like oratab
    sections: # optional
    - instance: # special section
      affinity: "all" # optional, default: "db", values: "all", "db", "asm"
    - dataguard_stats:
    - locks:
    - logswitches:
    - longactivesessions:
    - performance:
    - processes:
      affinity: "all" # optional, default "db", values: "all", "db", "asm"
    - recovery_area:
    - recovery_status:
    - sessions:
    - systemparameter:
    - undostat:
    - asm_diskgroup:
      is_async: yes
      affinity: "asm" # optional, default: "asm", values: "all", "db", "asm"
    - iostats:
      is_async: yes
    - jobs:
      is_async: yes
    - resumable:
      is_async: yes
    - rman:
      is_async: yes
    - tablespaces:
      is_async: yes
    - tablespaces_xxx:
      is_async: yes
    - tablespaces_xxxz:
      is_async: yes
    - tablespaces_xxxz1222:
      is_async: yes
    cache_age: 501 # optional(default:600)
    piggyback_host: "some_pb_host"
    discovery: # optional
      detect: false # optional(default:yes)
      include: ["foo", "bar", "INST2"] # optional prio 2; use instance even if excluded
      exclude: ["baz"] # optional, prio 3
    mode: "special" # optional(default:"port")
    instances: # optional
      - service_name: "INST1" # mandatory
        authentication: # optional, same as above
        connection: # optional,  same as above
          engine: jdbc
        alias: "someApplicationName" # optional
        piggyback: # optional
          hostname: "myPiggybackHost" # mandatory
          sections: # optional, same as above
      - service_name: "INST2"
        authentication:
          username: "u"
          password: "p"
          type: "standard"
        connection:
          hostname: "local"
          port: 500
          engine: std
  configs:
    - main:
        options:
          max_connections: 11
        authentication: # mandatory
          username: "f" # mandatory
          password: "b"
          type: "standard"
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
          service_name: "will be used"
          timeout: 5 # optional(default: 5)
        piggyback_host: "no"
        discovery: # optional
          detect: yes # optional(default:yes)
    - main:
        authentication: # optional
          username: "f"
          password: "b"
          type: "standard"
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
        pub const CUSTOM_INSTANCE: &str = r#"
service_name: "INST1"
authentication:
  username: "customised"
  type: "standard"
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
        let c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        assert_eq!(c.configs.len(), 3);
    }

    #[test]
    fn test_config_all() {
        let c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        assert_eq!(c.options().max_connections(), MaxConnections::from(5));
        assert_eq!(c.options().use_host_client(), &UseHostClient::Never);
        assert_eq!(c.options().max_queries(), MaxQueries::from(16));
        let auth = c.auth();
        assert_eq!(auth.username(), "foo");
        assert_eq!(auth.password(), Some("bar"));
        let conn = c.conn();
        assert_eq!(conn.hostname(), "localhost2".to_string().into());
        let product = c.product();
        assert_eq!(product.cache_age(), 501);
        assert_eq!(product.sections().len(), 21);
        assert_eq!(c.piggyback_host(), Some("some_pb_host"));
        assert!(!c.discovery().detect);
        let instances = c.instances();
        assert_eq!(instances.len(), 2);
        assert_eq!(c.mode, Mode::Special);
        /*
        mode: "port" # optional(default:"port")
        instances: # optional
        */
    }

    #[test]
    fn test_discovery_from_yaml_full() {
        let discovery = Discovery::from_yaml(&create_yaml(data::DISCOVERY_FULL))
            .unwrap()
            .unwrap();
        assert!(!discovery.detect());
        assert_eq!(discovery.include(), &vec!["A".to_string(), "B".to_string()]);
        assert_eq!(discovery.exclude(), &vec!["C".to_string(), "D".to_string()]);
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
    }

    #[test]
    fn test_mode_from_yaml() {
        assert!(Mode::from_yaml(&create_yaml("mode: Zu")).is_err());
        assert!(Mode::from_yaml(&create_yaml("no_mode: port")).is_err());
    }

    fn as_names(sections: Vec<&Section>) -> Vec<&str> {
        sections.iter().map(|s| s.name().as_str()).collect()
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
        let a = Authentication::from_yaml(&create_yaml(
            r#"
authentication:
    username: "main"
    type: "standard"
  "#,
        ))
        .unwrap()
        .unwrap();
        let instance = CustomService::from_yaml(
            &create_yaml(data::CUSTOM_INSTANCE),
            &a,
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.service_name().unwrap().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "customised");
        assert_eq!(instance.conn().hostname(), "h1".to_string().into());
        assert_eq!(instance.calc_real_host(), "h1".to_string().into());
        assert_eq!(instance.alias(), &Some("a1".to_string().into()));
        assert_eq!(instance.piggyback().unwrap().hostname(), "piggy");
        assert_eq!(instance.piggyback().unwrap().sections().cache_age(), 123);
    }

    #[cfg(windows)]
    #[test]
    fn test_custom_instance_os() {
        pub const INSTANCE_INTEGRATED: &str = r#"
service_name: "INST1"
authentication:
  username: "u1"
  type: "os"
connection:
  hostname: "h1"
"#;
        let instance = CustomService::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.service_name().unwrap().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "");
        assert_eq!(instance.conn().hostname(), "h1".to_string().into());
    }

    #[test]
    fn test_custom_instance_os_default() {
        pub const INSTANCE_OS: &str = r#"
service_name: "INST1"
authentication:
  username: "u1"
  type: "os"
connection:
  port: 5555
"#;
        let instance = CustomService::from_yaml(
            &create_yaml(INSTANCE_OS),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(instance.service_name().unwrap().to_string(), "INST1");
        assert_eq!(instance.auth().username(), "");
        assert_eq!(instance.auth().auth_type(), &AuthType::Os);
        assert_eq!(instance.conn().hostname(), "localhost".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost".to_string().into());
    }

    #[test]
    fn test_custom_instance_remote_default_patch_all() {
        pub const INSTANCE_INTEGRATED: &str = r#"
service_name: "SERVICE_NAME_2"
instance_name: "INSTANCE_NAME_2"
authentication:
  username: "u1"
  password: "pwd"
  type: "standard"
connection:
  hostname: "localhost2"
  service_name: "SERVICE_NAME_3"
  instance_name: "INSTANCE_NAME_3"
"#;
        let instance = CustomService::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(
            instance.service_name().unwrap().to_string(),
            "SERVICE_NAME_2"
        );
        assert_eq!(
            instance.instance_name().unwrap().to_string(),
            "INSTANCE_NAME_2"
        );
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.auth().password().unwrap(), "pwd");
        assert_eq!(instance.auth().auth_type(), &AuthType::Standard);
        assert_eq!(instance.conn().hostname(), "localhost2".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost2".to_string().into());
    }

    #[test]
    fn test_custom_instance_remote_default_patch_connection() {
        pub const INSTANCE_INTEGRATED: &str = r#"
authentication:
  username: "u1"
  password: "pwd"
  type: "standard"
connection:
  hostname: "localhost2"
  service_name: "SERVICE_NAME_3"
  instance_name: "INSTANCE_NAME_3"
"#;
        let instance = CustomService::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(
            instance.service_name().unwrap().to_string(),
            "SERVICE_NAME_3"
        );
        assert_eq!(
            instance.instance_name().unwrap().to_string(),
            "INSTANCE_NAME_3"
        );
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.auth().password().unwrap(), "pwd");
        assert_eq!(instance.auth().auth_type(), &AuthType::Standard);
        assert_eq!(instance.conn().hostname(), "localhost2".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost2".to_string().into());
    }

    #[test]
    fn test_custom_instance_remote_default_same() {
        pub const INSTANCE_INTEGRATED: &str = r#"
authentication:
  username: "u1"
  password: "pwd"
  type: "standard"
connection:
  port: 5555
  service_name: "SERVICE_NAME_1"
"#;
        let instance = CustomService::from_yaml(
            &create_yaml(INSTANCE_INTEGRATED),
            &Authentication::default(),
            &Connection::default(),
            &Sections::default(),
        )
        .unwrap();
        assert_eq!(
            instance.service_name().unwrap().to_string(),
            "SERVICE_NAME_1"
        );
        assert!(instance.instance_name().is_none());
        assert_eq!(instance.auth().username(), "u1");
        assert_eq!(instance.auth().password().unwrap(), "pwd");
        assert_eq!(instance.auth().auth_type(), &AuthType::Standard);
        assert_eq!(instance.conn().hostname(), "localhost".to_string().into());
        assert_eq!(instance.calc_real_host(), "localhost".to_string().into());
    }

    #[test]
    fn test_config() {
        let c = Config::from_string(data::TEST_CONFIG).unwrap().unwrap();
        assert_eq!(c.options().max_connections(), MaxConnections::from(5));
        assert_eq!(c.options().max_queries(), MaxQueries::from(16));
        assert_eq!(c.options().use_host_client(), &UseHostClient::Never);
        assert_eq!(
            c.options().params(),
            &vec![(keys::IGNORE_DB_NAME.to_string(), 13)]
        );
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

    fn make_detect_config(include: &[&str], exclude: &[&str]) -> Config {
        let source = format!(
            r"---
oracle:
  main:
    authentication:
      username: foo
    discovery:
      detect: true # doesn't matter for us
      include: {include:?}
      exclude: {exclude:?}
    instances:
      - service_name: sid1
      - service_name: sid2
        connection:
          hostname: ab
"
        );
        Config::from_string(source).unwrap().unwrap()
    }

    #[test]
    fn test_calc_hash() {
        let c1 = Config::from_string(TEST_CONFIG).unwrap().unwrap();
        let c2 = Config::from_string(TEST_CONFIG.to_string() + "\n# xxx")
            .unwrap()
            .unwrap();
        let c3 = Config::from_string(
            TEST_CONFIG.to_string()
                + r#"
    - main:
        authentication: # mandatory
          username: "f" # mandatory"#,
        )
        .unwrap()
        .unwrap();
        assert_eq!(c1.hash.len(), 16);
        assert_eq!(c1.hash, c2.hash);
        assert_ne!(c1.hash, c3.hash);
    }

    #[test]
    fn test_sections_enabled() {
        const CONFIG: &str = r#"
---
oracle:
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
                .map(|s| (s.name().as_str(), s.kind()))
                .collect::<Vec<(&str, SectionKind)>>(),
            [
                ("instance", SectionKind::Sync),
                ("jobs", SectionKind::Async),
                ("backup", SectionKind::Disabled),
            ]
        );
        // ping the gerrit
        assert_eq!(
            config
                .valid_sections()
                .iter()
                .map(|s| (s.name().as_str(), s.kind()))
                .collect::<Vec<(&str, SectionKind)>>(),
            [
                ("instance", SectionKind::Sync),
                ("jobs", SectionKind::Async),
            ]
        );
    }
}
