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

use crate::types::{HostName, InstanceAlias, InstanceName, Port, ServiceName, ServiceType};

use crate::config::authentication::Authentication;

#[derive(Debug, Clone)]
pub struct Target {
    pub host: HostName,
    pub service_name: Option<ServiceName>,
    pub service_type: Option<ServiceType>,
    pub instance_name: Option<InstanceName>,
    pub alias: Option<InstanceAlias>,
    pub port: Port,
    pub auth: Authentication,
}

impl Target {
    pub fn make_connection_string(&self, use_instance: Option<&InstanceName>) -> String {
        use std::fmt::Display;

        fn format_entry<T: Display>(optional_value: Option<&T>, sep: &str) -> String {
            if let Some(value) = optional_value {
                format!("{}{}", sep, value)
            } else {
                String::new()
            }
        }
        if let Some(alias) = &self.alias {
            log::info!("Using alias connection: {alias}");
            return format!("{}", alias);
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
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::authentication::Authentication;
    use crate::config::yaml::test_tools::create_yaml;
    use crate::types::HostName;

    #[test]
    fn test_make_connection_string() {
        const AUTH_YAML: &str = r"
authentication:
    username: 'user'
    password: 'pass'
    type: 'standard'";
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("my_service")),
            service_type: Some(ServiceType::from("dedicated")),
            instance_name: Some(InstanceName::from("orcl")),
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(Some(InstanceName::from("XYZ")).as_ref()),
            "localhost:1521/my_service:dedicated/XYZ"
        );
        assert_eq!(
            target.make_connection_string(None),
            "localhost:1521/my_service:dedicated/ORCL"
        );
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("my_service")),
            service_type: Some(ServiceType::from("dedicated")),
            instance_name: Some(InstanceName::from("orcl")),
            alias: Some(InstanceAlias::from("my_alias".to_string())),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(Some(InstanceName::from("XYZ")).as_ref()),
            "my_alias"
        );
        assert_eq!(target.make_connection_string((None).as_ref()), "my_alias");
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: None,
            service_type: None,
            instance_name: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(target.make_connection_string(None), "localhost:1521");
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            service_name: Some(ServiceName::from("oRcl")),
            service_type: None,
            instance_name: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(target.make_connection_string(None), "localhost:1521/oRcl");
    }
}
