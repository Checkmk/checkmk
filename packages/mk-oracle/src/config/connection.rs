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

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use crate::types::{HostName, InstanceName, Port, ServiceName, ServiceType};
use anyhow::Context;
use anyhow::Result;
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

#[derive(PartialEq, Debug, Clone)]
pub enum EngineTag {
    Auto,
    Std,
    SqlPlus,
    Jdbc,
}

impl Default for EngineTag {
    fn default() -> Self {
        Self::Std
    }
}

impl EngineTag {
    fn from_string<T>(value: T) -> Option<Self>
    where
        T: AsRef<str>,
    {
        match value.as_ref() {
            "auto" => Some(Self::Auto),
            "std" => Some(Self::Std),
            "jdbc" => Some(Self::Jdbc),
            "sql_plus" => Some(Self::SqlPlus),
            _ => None,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Connection {
    hostname: HostName,         // "localhost" if not defined
    port: Option<Port>,         // 1521 if not defined
    timeout: Option<u64>,       // 5 if not defined
    tns_admin: Option<PathBuf>, // config dir if not defined
    oracle_local_registry: Option<PathBuf>,
    service_name: Option<ServiceName>,
    instance_name: Option<InstanceName>,
    service_type: Option<ServiceType>,
    engine: EngineTag, // Std if not defined
}

impl Connection {
    pub fn from_connection(
        s: &Connection,
        service_name: &Option<ServiceName>,
        instance_name: &Option<InstanceName>,
    ) -> Self {
        Self {
            hostname: s.hostname.clone(),
            port: s.port.clone(),
            timeout: s.timeout,
            tns_admin: s.tns_admin.clone(),
            oracle_local_registry: s.oracle_local_registry.clone(),
            service_name: if service_name.is_some() {
                service_name.clone()
            } else {
                s.service_name().cloned()
            },
            instance_name: if instance_name.is_some() {
                instance_name.clone()
            } else {
                s.instance_name().cloned()
            },
            service_type: s.service_type.clone(),
            engine: s.engine.clone(),
        }
    }
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let conn = yaml.get(keys::CONNECTION);
        if conn.is_badvalue() {
            return Ok(None);
        }
        Ok(Some(Self {
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
            tns_admin: conn.get_string(keys::TNS_ADMIN).map(PathBuf::from),
            oracle_local_registry: conn
                .get_string(keys::ORACLE_LOCAL_REGISTRY)
                .map(PathBuf::from),
            service_name: conn
                .get_string(keys::SERVICE_NAME)
                .as_deref()
                .map(ServiceName::from),
            service_type: conn.get_string(keys::SERVICE_TYPE).map(ServiceType::from),
            instance_name: conn
                .get_string(keys::INSTANCE_NAME)
                .as_deref()
                .map(InstanceName::from),
            port: conn.get_int::<u16>(keys::PORT).map(Port::from),
            timeout: conn.get_int::<u64>(keys::TIMEOUT),
            engine: {
                let value: String = conn
                    .get_string(keys::ENGINE)
                    .unwrap_or_default()
                    .to_lowercase();
                EngineTag::from_string(value.as_str()).unwrap_or_else(|| {
                    log::info!("Unknown engine '{}'", &value);
                    EngineTag::default()
                })
            },
        }))
    }

    pub fn hostname(&self) -> HostName {
        self.hostname.clone()
    }
    pub fn port(&self) -> Port {
        self.port
            .clone()
            .unwrap_or(Port::from(defaults::CONNECTION_PORT))
    }
    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.timeout.unwrap_or(defaults::CONNECTION_TIMEOUT))
    }
    pub fn tns_admin(&self) -> Option<&PathBuf> {
        self.tns_admin.as_ref()
    }
    pub fn oracle_local_registry(&self) -> Option<&PathBuf> {
        self.oracle_local_registry.as_ref()
    }
    pub fn engine_tag(&self) -> &EngineTag {
        &self.engine
    }
    pub fn service_name(&self) -> Option<&ServiceName> {
        self.service_name.as_ref()
    }
    pub fn service_type(&self) -> Option<&ServiceType> {
        self.service_type.as_ref()
    }
    pub fn instance_name(&self) -> Option<&InstanceName> {
        self.instance_name.as_ref()
    }
    pub fn is_local(&self) -> bool {
        self.hostname() == HostName::from("localhost".to_owned())
            || self.hostname() == HostName::from("127.0.0.1".to_owned())
            || self.hostname() == HostName::from("::1".to_owned())
    }
}

/// This function is used to set the TNS_ADMIN environment variable
/// Location may be changed in the future
pub fn add_tns_admin_to_env(conn: &Connection) {
    let config = std::path::PathBuf::from(std::env::var("MK_CONFDIR").unwrap_or_default());
    if let Some(tns_admin) = conn.tns_admin() {
        let tns_admin = config.join(tns_admin);
        if tns_admin.exists() && tns_admin.is_dir() {
            log::info!("TNS_ADMIN directory '{}' ", tns_admin.display());
            unsafe {
                std::env::set_var("TNS_ADMIN", tns_admin);
            }
        } else {
            log::warn!(
                "TNS_ADMIN directory '{}' does not exist or is not a directory",
                tns_admin.display()
            );
        }
    } else {
        log::info!(
            "No TNS_ADMIN specified, using default path: {}",
            config.display()
        );
        unsafe {
            std::env::set_var("TNS_ADMIN", config);
        }
    }
}

/// Sets up the wallet environment by creating a sqlnet.ora file in MK_CONFDIR with the wallet location.
///
/// This allows wallet authentication without requiring a pre-existing sqlnet.ora file.
/// The default wallet directory is MK_CONFDIR/oracle_wallet.
/// If sqlnet.ora already exists, it will not be overwritten.
pub fn setup_wallet_environment(env_var: Option<String>) -> anyhow::Result<()> {
    let config_dir = std::path::PathBuf::from(
        std::env::var(env_var.unwrap_or("MK_CONFDIR".to_string())).unwrap_or_else(|_| ".".into()),
    );

    let sqlnet_path = config_dir.join("sqlnet.ora");
    if sqlnet_path.exists() {
        log::info!(
            "sqlnet.ora already exists at '{}', skipping creation",
            sqlnet_path.display()
        );
        return Ok(());
    }

    let wallet_path = config_dir.join("oracle_wallet");
    let wallet_display_path = wallet_path
        .canonicalize()
        .unwrap_or_else(|_| wallet_path.clone());

    log::info!(
        "Setting up wallet environment with wallet location: {}",
        wallet_display_path.display()
    );

    let sqlnet_content = format!(
        r#"# Auto-generated by mk-oracle for wallet authentication
NAMES.DIRECTORY_PATH = (TNSNAMES, EZCONNECT)
WALLET_LOCATION = (SOURCE = (METHOD = FILE) (METHOD_DATA = (DIRECTORY = {})))
SQLNET.WALLET_OVERRIDE = TRUE
"#,
        wallet_display_path.display()
    );
    fs::write(&sqlnet_path, &sqlnet_content)
        .with_context(|| format!("Failed to write sqlnet.ora to '{}'", sqlnet_path.display()))?;

    log::info!(
        "Created sqlnet.ora at '{}' with wallet location '{}'",
        sqlnet_path.display(),
        wallet_display_path.display()
    );

    Ok(())
}

impl Default for Connection {
    fn default() -> Self {
        Self {
            hostname: HostName::from(defaults::CONNECTION_HOST_NAME.to_string()),
            oracle_local_registry: None,
            tns_admin: None,
            service_name: None,
            service_type: None,
            instance_name: None,
            port: None,
            timeout: None,
            engine: EngineTag::default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::test_tools::create_yaml;

    mod data {

        pub const CONNECTION_FULL: &str = r#"
connection:
  hostname: "alice"
  port: 9999
  timeout: 341
  tns_admin: "/path/to/oracle/config/files/" # optional, default: agent plugin config folder. Points to the location of sqlnet.ora and tnsnames.ora
  oracle_local_registry: "/etc/oracle/olr.loc" # optional, default: folder of oracle configuration files like oratab
  # not defined in docu, reserved for a future use
  service_name: service_NAME  #
  service_type: dedicated # dedicated or shared
  instance_name: instance_NAME
  engine: std
"#;
    }

    #[test]
    fn test_connection_full() {
        assert_eq!(&InstanceName::from("alice").to_string(), "ALICE");
        assert_eq!(
            &InstanceName::from(&("alice".to_string())).to_string(),
            "ALICE"
        );
        assert_eq!(
            Connection::from_yaml(&create_yaml(data::CONNECTION_FULL))
                .unwrap()
                .unwrap(),
            Connection {
                hostname: HostName::from("alice".to_string()),
                port: Some(Port(9999)),
                timeout: Some(341),
                tns_admin: Some(PathBuf::from("/path/to/oracle/config/files/")),
                oracle_local_registry: Some(PathBuf::from("/etc/oracle/olr.loc")),
                service_name: Some(ServiceName::from("service_NAME")),
                service_type: Some(ServiceType::from("dedicated")),
                instance_name: Some(InstanceName::from("instance_NAME")),
                engine: EngineTag::Std,
            }
        );
    }
    #[test]
    fn test_connection_default() {
        assert_eq!(
            Connection::default(),
            Connection {
                hostname: HostName::from("localhost".to_string()),
                tns_admin: None,
                oracle_local_registry: None,
                service_name: None,
                service_type: None,
                instance_name: None,
                port: None,
                timeout: None,
                engine: EngineTag::default(),
            }
        );
    }
    fn create_connection_with_engine(value: &str) -> String {
        format!(
            r#"
connection:
    hostname: "localhost"
    service_name: "will not be used"
    engine: {value}
"#
        )
    }

    #[test]
    fn test_connection_from_yaml_default() {
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_default())
                .unwrap()
                .unwrap(),
            Connection {
                service_name: Some(ServiceName::from("")),
                ..Default::default()
            }
        );
        assert!(Connection::from_yaml(&create_connection_yaml_no_service_name()).is_ok());
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_empty_host())
                .unwrap()
                .unwrap(),
            Connection::default()
        );
        assert_eq!(
            Connection::from_yaml(&create_connection_yaml_non_empty_host())
                .unwrap()
                .unwrap(),
            Connection {
                hostname: HostName::from("aa".to_string()),
                ..Default::default()
            }
        );
        assert_eq!(
            Connection::from_yaml(&create_yaml("nothing: ")).unwrap(),
            None
        );
    }

    fn create_connection_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
connection:
    hostname: "localhost"
    _nothing: "nothing"
    service_name: ''
"#;
        create_yaml(SOURCE)
    }

    fn create_connection_yaml_no_service_name() -> Yaml {
        const SOURCE: &str = r#"
connection:
    hostname: "localhost"
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
    fn test_connection_engine() {
        let test: Vec<(&str, EngineTag)> = vec![
            ("auto", EngineTag::Auto),
            ("std", EngineTag::Std),
            ("jdbc", EngineTag::Jdbc),
            ("sql_plus", EngineTag::SqlPlus),
            ("unknown", EngineTag::default()),
            ("", EngineTag::default()),
        ];
        for (value, expected) in test {
            let config_text = create_connection_with_engine(value);
            let c = Connection::from_yaml(&create_yaml(&config_text))
                .unwrap()
                .unwrap();
            assert_eq!(c.engine_tag(), &expected, "for value `{value}`");
        }
    }

    #[test]
    fn test_engine_tag() {
        let test: Vec<(&str, Option<EngineTag>)> = vec![
            ("auto", Some(EngineTag::Auto)),
            ("std", Some(EngineTag::Std)),
            ("jdbc", Some(EngineTag::Jdbc)),
            ("sql_plus", Some(EngineTag::SqlPlus)),
            ("unknown", None),
            ("", None),
        ];
        for (value, expected) in test {
            assert_eq!(
                EngineTag::from_string(value),
                expected,
                "for value `{value}`"
            );
        }
    }

    #[test]
    fn test_from_connection() {
        let base = Connection {
            hostname: HostName::from("host1".to_string()),
            port: Some(Port(1234)),
            timeout: Some(10),
            tns_admin: Some(PathBuf::from("/path/to/tns_admin")),
            oracle_local_registry: Some(PathBuf::from("/path/to/olr.loc")),
            service_name: Some(ServiceName::from("service1")),
            instance_name: Some(InstanceName::from("instance1")),
            service_type: Some(ServiceType::from("dedicated")),
            engine: EngineTag::Jdbc,
        };
        let custom = Connection::from_connection(&base, &None, &None);
        assert_eq!(custom, base);

        let custom_service = Some(ServiceName::from("new_service"));
        let custom = Connection::from_connection(&base, &custom_service, &None);
        let mut expected = base.clone();
        expected.service_name = custom_service;
        assert_eq!(custom, expected);

        let custom_instance = Some(InstanceName::from("new_instance"));
        let mut expected = base.clone();
        expected.instance_name = custom_instance.clone();
        let custom = Connection::from_connection(&base, &None, &custom_instance);
        assert_eq!(custom, expected);
    }

    #[test]
    fn test_is_local() {
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
        let conn_1 = Connection {
            hostname: HostName::from("::1".to_string()),
            ..Default::default()
        };
        assert!(conn_127.is_local());
        assert!(conn_local.is_local());
        assert!(conn_1.is_local());
        assert!(!conn_non_local.is_local());
    }
}
