// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{HostName, InstanceName, Port, ServiceName, ServiceType};

use crate::config::authentication::Authentication;

#[derive(Debug)]
pub struct Target {
    pub host: HostName,
    pub instance: Option<InstanceName>,
    pub service_type: Option<ServiceType>,
    pub service_name: Option<ServiceName>,
    pub port: Port,
    pub auth: Authentication,
}

impl Target {
    pub fn make_connection_string(&self) -> String {
        use std::fmt::Display;

        fn format_entry<T: Display>(instance: &Option<T>, sep: &str) -> String {
            if let Some(inst) = instance {
                format!("{}{}", sep, inst)
            } else {
                String::new()
            }
        }
        if let Some(service_name) = &self.service_name {
            format!(
                "{}:{}/{}{}{}",
                self.host,
                self.port,
                service_name,
                &format_entry(&self.service_type, ":"),
                &format_entry(&self.instance, "/"),
            )
        } else {
            format!(
                "{}:{}{}",
                self.host,
                self.port,
                &format_entry(&self.instance, "/")
            )
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
            instance: Some(InstanceName::from("orcl")),
            service_type: Some(ServiceType::from("dedicated")),
            service_name: Some(ServiceName::from("my_service")),
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML)).unwrap(),
        };
        assert_eq!(
            target.make_connection_string(),
            "localhost:1521/my_service:dedicated/orcl"
        );
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            instance: None,
            service_type: None,
            service_name: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML)).unwrap(),
        };
        assert_eq!(target.make_connection_string(), "localhost:1521");
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            instance: Some(InstanceName::from("orcl")),
            service_type: None,
            service_name: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML)).unwrap(),
        };
        assert_eq!(target.make_connection_string(), "localhost:1521/orcl");
    }
}
