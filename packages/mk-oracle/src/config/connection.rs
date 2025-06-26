// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use crate::types::{HostName, InstanceName, Port, ServiceName, ServiceType};
use anyhow::Result;
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
    hostname: HostName,
    service_name: Option<ServiceName>,
    service_type: Option<ServiceType>,
    instance: Option<InstanceName>,
    port: Port,
    timeout: u64,
    engine: EngineTag,
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
            service_name: conn.get_string(keys::SERVICE_NAME).map(ServiceName::from),
            service_type: conn.get_string(keys::SERVICE_TYPE).map(ServiceType::from),
            instance: conn.get_string(keys::INSTANCE).map(InstanceName::from),
            port: Port(conn.get_int::<u16>(keys::PORT).unwrap_or_else(|| {
                log::debug!("no port specified, using default");
                defaults::CONNECTION_PORT
            })),
            timeout: conn.get_int::<u64>(keys::TIMEOUT).unwrap_or_else(|| {
                log::debug!("no timeout specified, using default");
                defaults::CONNECTION_TIMEOUT
            }),
            engine: {
                let value: String = conn
                    .get_string(keys::ENGINE)
                    .unwrap_or_default()
                    .to_lowercase();
                EngineTag::from_string(value.as_str()).unwrap_or_else(|| {
                    log::error!("Unknown engine '{}'", &value);
                    EngineTag::default()
                })
            },
        }))
    }

    pub fn hostname(&self) -> HostName {
        self.hostname.clone()
    }
    pub fn port(&self) -> Port {
        self.port.clone()
    }
    pub fn timeout(&self) -> Duration {
        Duration::from_secs(self.timeout)
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
    pub fn instance(&self) -> Option<&InstanceName> {
        self.instance.as_ref()
    }
    pub fn is_local(&self) -> bool {
        self.hostname() == HostName::from("localhost".to_owned())
            || self.hostname() == HostName::from("127.0.0.1".to_owned())
            || self.hostname() == HostName::from("::1".to_owned())
    }
}

impl Default for Connection {
    fn default() -> Self {
        Self {
            hostname: HostName::from(defaults::CONNECTION_HOST_NAME.to_string()),
            service_name: None,
            service_type: None,
            instance: None,
            port: Port(defaults::CONNECTION_PORT),
            timeout: defaults::CONNECTION_TIMEOUT,
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
  service_name: service_NAME 
  service_type: service_TYPE
  instance: instance_NAME # mandatory
  port: 9999
  timeout: 341
  engine: std
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
                service_name: Some(ServiceName::from("service_NAME")),
                service_type: Some(ServiceType::from("service_TYPE")),
                instance: Some(InstanceName::from("instance_NAME")),
                port: Port(9999),
                timeout: 341,
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
                service_name: None,
                service_type: None,
                instance: None,
                port: Port(1521),
                timeout: 5,
                engine: EngineTag::default(),
            }
        );
    }
    fn create_connection_with_engine(value: &str) -> String {
        format!(
            r#"
connection:
    hostname: "localhost"
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
}
