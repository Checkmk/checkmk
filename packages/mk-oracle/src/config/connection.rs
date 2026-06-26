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
use crate::types::{HostName, Port};
use anyhow::Context;
use anyhow::Result;
use std::fs;
use std::path::PathBuf;
use std::time::Duration;

#[derive(PartialEq, Debug, Clone, Default)]
pub enum EngineTag {
    Auto,
    #[default]
    Std,
    SqlPlus,
    Jdbc,
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
    crs_home: Option<PathBuf>,
    crsctl_bin: Option<PathBuf>,
    engine: EngineTag, // Std if not defined
}

/// Parse olr.loc file content and extract `crs_home` path.
///
/// Skips empty lines, comments, and unparseable lines. First match wins.
fn parse_crs_home(content: &str) -> Option<PathBuf> {
    content
        .lines()
        .filter_map(|line| {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                return None;
            }
            let (key, value) = line.split_once('=')?;
            if key.trim() == "crs_home" {
                let value = value.trim();
                if !value.is_empty() {
                    return Some(PathBuf::from(value));
                }
            }
            None
        })
        .next()
}

impl Connection {
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let conn = yaml.get(keys::CONNECTION);
        if conn.is_badvalue() {
            return Ok(None);
        }
        let oracle_local_registry = conn
            .get_string(keys::ORACLE_LOCAL_REGISTRY)
            .map(PathBuf::from);

        let crs_home = oracle_local_registry
            .as_ref()
            .filter(|p| p.exists())
            .and_then(|p| {
                fs::read_to_string(p)
                    .map_err(|e| log::warn!("Failed to read olr.loc '{}': {}", p.display(), e))
                    .ok()
            })
            .and_then(|content| parse_crs_home(&content));

        let crsctl_bin = crs_home
            .as_ref()
            .map(|home| home.join("bin").join("crsctl"));

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
            oracle_local_registry,
            crs_home,
            crsctl_bin,
            port: conn.get_int::<u16>(keys::PORT).map(Port::from),
            timeout: conn.get_int::<u64>(keys::TIMEOUT),
            engine: {
                let value: String = conn
                    .get_string(keys::ENGINE)
                    .unwrap_or_default()
                    .to_lowercase();
                EngineTag::from_string(value.as_str()).unwrap_or_else(|| {
                    log::info!("Engine is not set, fallback to default");
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
    pub fn crs_home(&self) -> Option<&PathBuf> {
        self.crs_home.as_ref()
    }
    pub fn crsctl_bin(&self) -> Option<&PathBuf> {
        self.crsctl_bin.as_ref()
    }
    pub fn engine_tag(&self) -> &EngineTag {
        &self.engine
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
            crs_home: None,
            crsctl_bin: None,
            tns_admin: None,
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

        pub const CONNECTION_WITH_SID: &str = r#"
connection:
  hostname: "localhost"
  port: 1521
  sid: FREE
"#;
    }

    #[test]
    fn test_connection_full() {
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
                engine: EngineTag::Std,
                ..Default::default()
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
                crs_home: None,
                crsctl_bin: None,
                port: None,
                timeout: None,
                engine: EngineTag::default(),
            }
        );
    }

    #[test]
    fn test_connection_with_only_sid() {
        let conn = Connection::from_yaml(&create_yaml(data::CONNECTION_WITH_SID))
            .unwrap()
            .unwrap();
        assert_eq!(conn.hostname(), HostName::from("localhost".to_string()));
        assert_eq!(conn.port(), Port(1521));
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
            Connection::default()
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

    #[test]
    fn test_parse_crs_home() {
        assert_eq!(
            parse_crs_home("crs_home=/u01/app/19.0.0/grid"),
            Some(PathBuf::from("/u01/app/19.0.0/grid"))
        );
        assert_eq!(parse_crs_home(""), None);
        assert_eq!(parse_crs_home("# comment\n"), None);
        assert_eq!(parse_crs_home("crs_home="), None);
        assert_eq!(
            parse_crs_home("olrconfig_loc=/etc/oracle/olr\ncrs_home=/grid"),
            Some(PathBuf::from("/grid"))
        );
        assert_eq!(
            parse_crs_home("crs_home=/first\ncrs_home=/second"),
            Some(PathBuf::from("/first"))
        );
        assert_eq!(
            parse_crs_home("badline\ncrs_home=/ok"),
            Some(PathBuf::from("/ok"))
        );
    }

    #[test]
    fn test_connection_crs_home_none_when_no_olr_file() {
        let conn = Connection::from_yaml(&create_yaml(data::CONNECTION_FULL))
            .unwrap()
            .unwrap();
        assert!(conn.crs_home().is_none());
        assert!(conn.crsctl_bin().is_none());
    }
}
