// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{InstanceName, Port};

#[derive(Debug)]
pub struct InstanceInfo {
    pub name: InstanceName,
    pub port: Option<Port>,
    pub dynamic_port: Option<Port>,
}

#[cfg(windows)]
pub mod registry {
    use super::InstanceInfo;
    use crate::types::{InstanceName, Port};
    use std::collections::HashMap;
    use winreg::{enums::HKEY_LOCAL_MACHINE, RegKey};

    pub fn get_instances() -> Vec<InstanceInfo> {
        let instances_std = get_instances_on_key(r"SOFTWARE\Microsoft\Microsoft SQL Server\");
        let instances_wow =
            get_instances_on_key(r"SOFTWARE\WOW6432Node\Microsoft\Microsoft SQL Server\");

        instances_std.into_iter().chain(instances_wow).collect()
    }

    pub fn get_instances_on_key(sql_key: &str) -> Vec<InstanceInfo> {
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        let result = root_key.open_subkey_with_flags(
            sql_key.to_owned() + r"Instance Names\SQL",
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        );
        if let Err(e) = result {
            log::error!("Failed to open registry key: {:?}", e);
            return vec![];
        }
        let names_map: HashMap<String, String> = result
            .expect("Impossible")
            .enum_values()
            .filter_map(|x| x.ok())
            .map(|x| (x.0, format!("{}", x.1)))
            .collect();

        names_map
            .iter()
            .filter_map(|x| get_info(sql_key, x.0, x.1))
            .collect::<Vec<InstanceInfo>>()
    }

    fn get_info(sql_key: &str, name: &str, key_name: &str) -> Option<InstanceInfo> {
        let instance_name = name;
        let instance_key = format!(r"{}\MSSQLServer\SuperSocketNetLib\Tcp\IPAll", key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            sql_key.to_owned() + &instance_key,
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        ) {
            let port: Option<String> = key.get_value("TcpPort").ok();
            let dynamic_port: Option<String> = key.get_value("TcpDynamicPorts").ok();
            Some(InstanceInfo {
                name: InstanceName::from(instance_name.to_owned()),
                port: port.and_then(|s| s.parse::<u16>().ok()).map(Port::from),
                dynamic_port: dynamic_port
                    .and_then(|s| s.parse::<u16>().ok())
                    .map(Port::from),
            })
        } else {
            log::warn!("cannot open key: {}", instance_key);
            None
        }
    }
    #[cfg(test)]
    mod tests {
        use super::get_instances;
        #[test]
        fn test_get_instances() {
            let infos = get_instances();
            eprintln!("{:?}", infos);
            assert_eq!(infos.len(), 3usize);
        }
    }
}

#[cfg(unix)]
pub mod registry {
    use super::InstanceInfo;
    pub fn get_instances() -> Vec<InstanceInfo> {
        vec![]
    }
    #[cfg(test)]
    mod tests {
        use super::get_instances;
        #[test]
        fn test_get_instances() {
            assert!(get_instances().is_empty());
        }
    }
}
