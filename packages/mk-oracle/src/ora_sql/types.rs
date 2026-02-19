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

use crate::types::{
    ConnectionStringType, DescriptorSid, HostName, InstanceAlias, InstanceName, Port, ServiceName,
    ServiceType, Sid,
};

use crate::config::{authentication::Authentication, target::TargetId};

#[derive(Debug, Clone)]
pub struct Target {
    pub host: HostName,
    pub port: Port,
    pub auth: Authentication,

    pub target_id: TargetId,
}

impl Target {
    pub fn service_name(&self) -> Option<&ServiceName> {
        self.target_id.service_name()
    }

    pub fn instance_name(&self) -> Option<&InstanceName> {
        self.target_id.instance_name()
    }

    pub fn descriptor_sid(&self) -> Option<&DescriptorSid> {
        self.target_id.descriptor_sid()
    }

    pub fn standalone_sid(&self) -> Option<&Sid> {
        self.target_id.standalone_sid()
    }

    pub fn alias(&self) -> Option<&InstanceAlias> {
        self.target_id.alias()
    }

    pub fn service_type(&self) -> Option<&ServiceType> {
        self.target_id.service_type()
    }
}

impl Target {
    pub fn make_connection_string(
        &self,
        use_instance: Option<&InstanceName>,
        conn_type: ConnectionStringType,
    ) -> Option<String> {
        match &self.target_id {
            TargetId::Alias(alias) => {
                log::info!("Using alias connection: {}", alias);
                Some(alias.to_string())
            }

            TargetId::NoId => {
                log::warn!("Target is not defined");
                None
            }

            TargetId::Sid(_) => match conn_type {
                ConnectionStringType::EzConnect => {
                    log::error!("Sid target doesn't support ez connection strings");
                    None
                }
                ConnectionStringType::Tns => Some(self.make_tns_connect_string(None)),
            },

            TargetId::Descriptor(_) => match conn_type {
                ConnectionStringType::EzConnect => Some(self.make_ez_connect_string(use_instance)),
                ConnectionStringType::Tns => Some(self.make_tns_connect_string(use_instance)),
            },
        }
    }

    fn make_ez_connect_string(&self, use_instance: Option<&InstanceName>) -> String {
        use std::fmt::Display;

        fn format_entry<T: Display>(optional_value: Option<&T>, sep: &str) -> String {
            if let Some(value) = optional_value {
                format!("{}{}", sep, value)
            } else {
                String::new()
            }
        }

        let instance_name = if use_instance.is_some() {
            use_instance
        } else {
            self.instance_name()
        };

        if let Some(service_name) = self.service_name() {
            let conn_string = format!(
                "{}:{}/{}{}{}",
                self.host,
                self.port,
                service_name,
                &format_entry(self.service_type(), ":"),
                &format_entry(instance_name, "/"),
            );
            log::info!("Using normal connection: {conn_string}");
            conn_string
        } else {
            let conn_string = format!("{}:{}", self.host, self.port);
            log::info!("Using simple connection: {conn_string}");
            conn_string
        }
    }

    fn make_tns_connect_string(&self, use_instance: Option<&InstanceName>) -> String {
        let instance_name = if use_instance.is_some() {
            use_instance
        } else {
            self.instance_name()
        };

        let mut connect_data_parts = Vec::new();

        let server = self
            .service_type()
            .map(|st| st.to_string().to_uppercase())
            .unwrap_or_else(|| "DEDICATED".to_string());
        connect_data_parts.push(format!("(SERVER = {})", server));

        if let Some(service_name) = self.service_name() {
            connect_data_parts.push(format!("(SERVICE_NAME = {})", service_name));
            if let Some(inst_name) = instance_name {
                connect_data_parts.push(format!("(INSTANCE_NAME = {})", inst_name));
            }
            if let Some(sid) = self.descriptor_sid() {
                connect_data_parts.push(format!("(SID = {})", sid));
            }
        } else if let Some(sid) = self.standalone_sid() {
            connect_data_parts.push(format!("(SID = {})", sid));
        } else {
            log::warn!("Insufficient information to build TNS connection string");
        }

        let connect_data = connect_data_parts.join(" ");

        let conn_string = format!(
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = {})(PORT = {})) (CONNECT_DATA = {}))",
            self.host, self.port, connect_data
        );

        conn_string
    }

    pub fn display_name(&self) -> String {
        self.target_id.display_name().to_uppercase()
    }

    pub fn is_defined(&self) -> bool {
        !matches!(self.target_id, TargetId::NoId)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::authentication::Authentication;
    use crate::config::target::TargetIdBuilder;
    use crate::config::yaml::test_tools::create_yaml;
    use crate::types::HostName;

    const AUTH_YAML: &str = r"
authentication:
    username: 'user'
    password: 'pass'
    type: 'standard'";

    #[test]
    fn test_make_connection_string_service_type_instance() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("my_service")))
                .service_type(Some(&ServiceType::from("dedicated")))
                .instance_name(Some(&InstanceName::from("orcl")))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target
                .make_connection_string(
                    Some(InstanceName::from("XYZ")).as_ref(),
                    ConnectionStringType::EzConnect
                )
                .unwrap(),
            "localhost:1521/my_service:dedicated/XYZ"
        );
        assert_eq!(
            target
                .make_connection_string(None, ConnectionStringType::EzConnect)
                .unwrap(),
            "localhost:1521/my_service:dedicated/ORCL"
        );
    }

    #[test]
    fn test_make_connection_string_all() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("my_service")))
                .service_type(Some(&ServiceType::from("dedicated")))
                .instance_name(Some(&InstanceName::from("orcl")))
                .alias(Some(&InstanceAlias::from("my_alias".to_string())))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target
                .make_connection_string(
                    Some(InstanceName::from("XYZ")).as_ref(),
                    ConnectionStringType::EzConnect
                )
                .unwrap(),
            "my_alias"
        );
        assert_eq!(
            target
                .make_connection_string((None).as_ref(), ConnectionStringType::EzConnect)
                .unwrap(),
            "my_alias"
        );
    }

    #[test]
    fn test_make_connection_string_empty() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new().build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert!(target
            .make_connection_string(None, ConnectionStringType::EzConnect)
            .is_none());
    }

    #[test]
    fn test_make_connection_string_service() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("oRcl")))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target
                .make_connection_string(None, ConnectionStringType::EzConnect)
                .unwrap(),
            "localhost:1521/oRcl"
        );
    }

    fn make_target(
        service_name: Option<&ServiceName>,
        instance_name: Option<&InstanceName>,
        sid: Option<&Sid>,
        alias: Option<&InstanceAlias>,
    ) -> Target {
        Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(service_name)
                .instance_name(instance_name)
                .sid(sid.map(|s| s.to_string()).as_deref())
                .alias(alias)
                .build(),
            port: Port(1521),
            auth: Authentication::default(),
        }
    }
    #[test]
    fn test_get_display_name() {
        let service_name = ServiceName::from("service");
        let instance_name = InstanceName::from("instance");
        let sid = Sid::from("sid");
        let alias = InstanceAlias::from("alias".to_string());

        let full =
            make_target(Some(&service_name), Some(&instance_name), None, None).display_name();
        assert_eq!(full, "INSTANCE");
        let service = make_target(Some(&service_name), None, None, None).display_name();
        assert_eq!(service, "SERVICE");
        let undefined = make_target(None, None, None, None).display_name();
        assert_eq!(undefined, "UNDEFINED");
        assert_eq!(
            make_target(Some(&service_name), Some(&instance_name), Some(&sid), None).display_name(),
            "INSTANCE"
        );
        assert_eq!(
            make_target(Some(&service_name), None, Some(&sid), None).display_name(),
            "SERVICE"
        );
        assert_eq!(
            make_target(None, None, Some(&sid), None).display_name(),
            "SID"
        );
        assert_eq!(
            make_target(
                Some(&service_name),
                Some(&instance_name),
                None,
                Some(&alias)
            )
            .display_name(),
            "ALIAS"
        );
    }

    #[test]
    fn test_is_defined() {
        let service_name = ServiceName::from("service");
        let instance_name = InstanceName::from("instance");
        let sid = Sid::from("sid");
        let alias = InstanceAlias::from("alias".to_string());
        assert!(!make_target(None, None, None, None).is_defined());
        assert!(!make_target(None, Some(&instance_name), None, None).is_defined());
        assert!(make_target(Some(&service_name), None, None, None).is_defined());
        assert!(make_target(None, None, Some(&sid), None).is_defined());
        assert!(make_target(None, None, None, Some(&alias)).is_defined());
    }

    #[test]
    fn test_make_tns_connection_string_service_instance() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("FREE.test")))
                .service_type(Some(&ServiceType::from("dedicated")))
                .instance_name(Some(&InstanceName::from("FREE")))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns).unwrap(),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = FREE.test) (INSTANCE_NAME = FREE)))"
        );
    }

    #[test]
    fn test_make_tns_connection_string_service() {
        let service_name = Some(ServiceName::from("ORCL"));
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(service_name.as_ref())
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns).unwrap(),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = ORCL)))"
        );
    }

    #[test]
    fn test_make_tns_connection_string_instance() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .instance_name(Some(&InstanceName::from("orcl")))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert!(target
            .make_connection_string(None, ConnectionStringType::Tns)
            .is_none());
    }

    #[test]
    fn test_make_tns_connection_string_all() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("my_service")))
                .service_type(Some(&ServiceType::from("dedicated")))
                .instance_name(Some(&InstanceName::from("orcl")))
                .alias(Some(&InstanceAlias::from("my_alias".to_string())))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target
                .make_connection_string(None, ConnectionStringType::Tns)
                .unwrap(),
            "my_alias"
        );
    }

    #[test]
    fn test_make_tns_connection_string_service_type_instance() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("ORCL")))
                .service_type(Some(&ServiceType::from("shared")))
                .instance_name(Some(&InstanceName::from("inst1")))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(Some(InstanceName::from("INST2")).as_ref(), ConnectionStringType::Tns).unwrap(),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = SHARED) (SERVICE_NAME = ORCL) (INSTANCE_NAME = INST2)))"
        );
    }

    #[test]
    fn test_make_tns_connection_string_sid() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new().sid(Some("ORCL")).build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns).unwrap(),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SID = ORCL)))"
        );
    }

    #[test]
    fn test_make_tns_connection_string_service_sid() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("MY_SERVICE")))
                .sid(Some("ORCL"))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns).unwrap(),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = MY_SERVICE) (SID = ORCL)))"
        );
    }

    #[test]
    fn test_make_tns_connection_string_service_instance_sid() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            target_id: TargetIdBuilder::new()
                .service_name(Some(&ServiceName::from("MY_SERVICE")))
                .instance_name(Some(&InstanceName::from("INST")))
                .sid(Some("ORCL"))
                .build(),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns).unwrap(),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = MY_SERVICE) (INSTANCE_NAME = INST) (SID = ORCL)))"
        );
    }
}
