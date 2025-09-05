// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{HostName, InstanceAlias, InstanceName, Port, ServiceName, ServiceType};

use crate::config::authentication::Authentication;

#[derive(Debug, Clone)]
pub struct Target {
    pub host: HostName,
    pub instance: Option<InstanceName>,
    pub service_type: Option<ServiceType>,
    pub service_name: Option<ServiceName>,
    pub alias: Option<InstanceAlias>,
    pub port: Port,
    pub auth: Authentication,
}

impl Target {
    pub fn make_connection_string(&self, optional_instance: Option<&InstanceName>) -> String {
        use std::fmt::Display;

        fn format_entry<T: Display>(instance: Option<&T>, sep: &str) -> String {
            if let Some(inst) = instance {
                format!("{}{}", sep, inst)
            } else {
                String::new()
            }
        }
        if let Some(alias) = &self.alias {
            log::info!("Using alias connection: {alias}");
            return format!("{}", alias);
        }
        let work_instance = if self.instance.is_some() {
            self.instance.as_ref()
        } else {
            optional_instance
        };

        let conn_string = if let Some(service_name) = &self.service_name {
            format!(
                "{}:{}/{}{}{}",
                self.host,
                self.port,
                service_name,
                &format_entry(self.service_type.as_ref(), ":"),
                &format_entry(work_instance, "/"),
            )
        } else {
            format!(
                "{}:{}{}",
                self.host,
                self.port,
                &format_entry(work_instance, "/")
            )
        };
        log::info!("Using normal connection: {conn_string}");
        conn_string
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
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(
            target.make_connection_string(Some(InstanceName::from("XYZ")).as_ref()),
            "localhost:1521/my_service:dedicated/ORCL"
        );
        assert_eq!(
            target.make_connection_string(None),
            "localhost:1521/my_service:dedicated/ORCL"
        );
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            instance: Some(InstanceName::from("orcl")),
            service_type: Some(ServiceType::from("dedicated")),
            service_name: Some(ServiceName::from("my_service")),
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
            instance: None,
            service_type: None,
            service_name: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(target.make_connection_string(None), "localhost:1521");
        let target = Target {
            host: HostName::from("localhost".to_owned()),
            instance: Some(InstanceName::from("orcl")),
            service_type: None,
            service_name: None,
            alias: None,
            port: Port(1521),
            auth: Authentication::from_yaml(&create_yaml(AUTH_YAML))
                .unwrap()
                .unwrap(),
        };
        assert_eq!(target.make_connection_string(None), "localhost:1521/ORCL");
    }
}
