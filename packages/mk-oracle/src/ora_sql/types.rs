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
    ConnectionStringType, HostName, InstanceAlias, InstanceName, Port, ServiceName, ServiceType,
    Sid,
};

use crate::config::authentication::Authentication;

#[derive(Debug, Clone)]
pub struct Target {
    pub host: HostName,
    pub service_name: Option<ServiceName>,
    pub service_type: Option<ServiceType>,
    pub instance_name: Option<InstanceName>,
    pub sid: Option<Sid>,
    pub alias: Option<InstanceAlias>,
    pub port: Port,
    pub auth: Authentication,
}

impl Target {
    pub fn make_connection_string(
        &self,
        use_instance: Option<&InstanceName>,
        conn_type: ConnectionStringType,
    ) -> String {
        if let Some(alias) = &self.alias {
            log::info!("Using alias connection: {alias}");
            return format!("{}", alias);
        }

        match conn_type {
            ConnectionStringType::EzConnect => self.make_ezconnect_string(use_instance),
            ConnectionStringType::Tns => self.make_tns_string(use_instance),
        }
    }

    fn make_ezconnect_string(&self, use_instance: Option<&InstanceName>) -> String {
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
            self.instance_name.as_ref()
        };

        if let Some(service_name) = &self.service_name {
            let conn_string = format!(
                "{}:{}/{}{}{}",
                self.host,
                self.port,
                service_name,
                &format_entry(self.service_type.as_ref(), ":"),
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

    fn make_tns_string(&self, use_instance: Option<&InstanceName>) -> String {
        let instance_name = if use_instance.is_some() {
            use_instance
        } else {
            self.instance_name.as_ref()
        };

        let mut connect_data_parts = Vec::new();

        let server = self
            .service_type
            .as_ref()
            .map(|st| st.to_string().to_uppercase())
            .unwrap_or_else(|| "DEDICATED".to_string());
        connect_data_parts.push(format!("(SERVER = {})", server));

        if let Some(sid) = &self.sid {
            connect_data_parts.push(format!("(SID = {})", sid));
        }

        if let Some(service_name) = &self.service_name {
            connect_data_parts.push(format!("(SERVICE_NAME = {})", service_name));
        }

        if let Some(inst_name) = instance_name {
            connect_data_parts.push(format!("(INSTANCE_NAME = {})", inst_name));
        }

        let connect_data = connect_data_parts.join(" ");

        let conn_string = format!(
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = {})(PORT = {})) (CONNECT_DATA = {}))",
            self.host, self.port, connect_data
        );

        conn_string
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::authentication::Authentication;
    use crate::config::yaml::test_tools::create_yaml;
    use crate::types::HostName;

    const AUTH_YAML: &str = r"
authentication:
    username: 'user'
    password: 'pass'
    type: 'standard'";

    #[test]
    fn test_make_connection_string() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("my_service")),
            service_type: Some(ServiceType::from("dedicated")),
            instance_name: Some(InstanceName::from("orcl")),
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(
                Some(InstanceName::from("XYZ")).as_ref(),
                ConnectionStringType::EzConnect
            ),
            "localhost:1521/my_service:dedicated/XYZ"
        );
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::EzConnect),
            "localhost:1521/my_service:dedicated/ORCL"
        );
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("my_service")),
            service_type: Some(ServiceType::from("dedicated")),
            instance_name: Some(InstanceName::from("orcl")),
            sid: None,
            alias: Some(InstanceAlias::from("my_alias".to_string())),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(
                Some(InstanceName::from("XYZ")).as_ref(),
                ConnectionStringType::EzConnect
            ),
            "my_alias"
        );
        assert_eq!(
            target.make_connection_string((None).as_ref(), ConnectionStringType::EzConnect),
            "my_alias"
        );
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: None,
            service_type: None,
            instance_name: None,
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::EzConnect),
            "localhost:1521"
        );
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("oRcl")),
            service_type: None,
            instance_name: None,
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::EzConnect),
            "localhost:1521/oRcl"
        );
    }

    #[test]
    fn test_make_tns_connection_string() {
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("FREE.test")),
            service_type: Some(ServiceType::from("dedicated")),
            instance_name: Some(InstanceName::from("FREE")),
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = FREE.test) (INSTANCE_NAME = FREE)))"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("ORCL")),
            service_type: None,
            instance_name: None,
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SERVICE_NAME = ORCL)))"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: None,
            service_type: None,
            instance_name: Some(InstanceName::from("orcl")),
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (INSTANCE_NAME = ORCL)))"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("my_service")),
            service_type: Some(ServiceType::from("dedicated")),
            instance_name: Some(InstanceName::from("orcl")),
            sid: None,
            alias: Some(InstanceAlias::from("my_alias".to_string())),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "my_alias"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("ORCL")),
            service_type: Some(ServiceType::from("shared")),
            instance_name: Some(InstanceName::from("inst1")),
            sid: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(Some(InstanceName::from("INST2")).as_ref(), ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = SHARED) (SERVICE_NAME = ORCL) (INSTANCE_NAME = INST2)))"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: None,
            service_type: None,
            instance_name: None,
            sid: Some(Sid::from("ORCL")),
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SID = ORCL)))"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("MY_SERVICE")),
            service_type: None,
            instance_name: None,
            sid: Some(Sid::from("ORCL")),
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SID = ORCL) (SERVICE_NAME = MY_SERVICE)))"
        );

        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("MY_SERVICE")),
            service_type: None,
            instance_name: Some(InstanceName::from("INST")),
            sid: Some(Sid::from("ORCL")),
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(None, ConnectionStringType::Tns),
            "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = localhost)(PORT = 1521)) (CONNECT_DATA = (SERVER = DEDICATED) (SID = ORCL) (SERVICE_NAME = MY_SERVICE) (INSTANCE_NAME = INST)))"
        );
    }
}
