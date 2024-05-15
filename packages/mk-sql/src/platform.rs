// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{InstanceName, Port};

#[derive(Debug)]
pub struct InstanceInfo {
    pub name: InstanceName,
    port: Option<Port>,
    dynamic_port: Option<Port>,
    shared_memory: bool,
    pipe: Option<String>,
}

impl InstanceInfo {
    pub fn final_port(&self) -> Option<&Port> {
        self.dynamic_port
            .as_ref()
            .filter(|p| p.0 != 0)
            .or(self.port.as_ref())
            .filter(|p| p.0 != 0)
    }

    pub fn is_shared_memory(&self) -> bool {
        self.shared_memory
    }

    pub fn is_pipe(&self) -> bool {
        self.pipe.is_some()
    }
}

#[cfg(test)]
mod tests {
    use crate::{
        platform::InstanceInfo,
        types::{InstanceName, Port},
    };

    #[test]
    fn test_instance_final_port() {
        let make_i = |port: Option<u16>, dynamic_port: Option<u16>| InstanceInfo {
            name: InstanceName::from("AAA".to_owned()),
            port: port.map(|p| p.into()),
            dynamic_port: dynamic_port.map(|p| p.into()),
            shared_memory: false,
            pipe: None,
        };

        let std_port = 1;
        let dyn_port = 2;
        assert_eq!(
            make_i(Some(std_port), None).final_port().unwrap(),
            &Port::from(std_port)
        );
        assert_eq!(
            make_i(Some(std_port), Some(dyn_port)).final_port().unwrap(),
            &Port::from(dyn_port)
        );
        assert_eq!(
            make_i(Some(std_port), Some(dyn_port)).final_port().unwrap(),
            &Port::from(dyn_port)
        );
        assert_eq!(
            make_i(Some(std_port), Some(0)).final_port().unwrap(),
            &Port::from(std_port)
        );
        assert!(make_i(Some(0), Some(0)).final_port().is_none());
    }
}

#[cfg(windows)]
pub mod odbc {
    use anyhow::Result;
    use odbc_api::{
        buffers::{ColumnarBuffer, TextColumn, TextRowSet},
        ConnectionOptions, Cursor, Environment, ResultSetMetadata,
    };

    use crate::types::InstanceName;

    /// creates a local connection string for the ODBC driver
    /// always SSPI and Trusted connection
    pub fn make_connection_string(
        instance: &InstanceName,
        database: Option<&str>,
        driver: Option<&str>,
    ) -> String {
        format!(
            "Driver={};SERVER=(local)\\{};Initial Catalog={};Integrated Security=SSPI;Trusted_Connection=yes;",
            driver.unwrap_or("{ODBC Driver 17 for SQL Server}"),
            instance,
            database.unwrap_or("master")
        )
    }

    pub struct Block {
        pub headline: Vec<String>,
        pub rows: Vec<Vec<String>>,
    }

    type BufferType = ColumnarBuffer<TextColumn<u8>>;

    pub fn execute(connection_string: &str, query: &str) -> Result<Vec<Block>> {
        let env = Environment::new()?;

        let conn =
            env.connect_with_connection_string(connection_string, ConnectionOptions::default())?;

        if let Some(mut cursor) = conn.execute(query, ())? {
            const BATCH_SIZE: usize = 5000;
            let mut blocks: Vec<Block> = Vec::new();

            let headline = cursor.column_names()?.collect::<Result<_, _>>()?;
            let mut buffers = TextRowSet::for_cursor(BATCH_SIZE, &mut cursor, Some(4096))?;
            let mut row_set_cursor = cursor.bind_buffer(&mut buffers)?;

            let mut rows: Vec<Vec<String>> = Vec::new();
            while let Some(batch) = row_set_cursor.fetch()? {
                rows.extend(process_batch(batch));
            }
            blocks.push(Block { headline, rows });

            if let Ok((cursor, _buffer)) = row_set_cursor.unbind() {
                if let Ok(Some(mut c)) = cursor.more_results() {
                    let headline = c.column_names()?.collect::<Result<_, _>>()?;
                    let mut rows: Vec<Vec<String>> = Vec::new();
                    let mut row_set_cursor = c.bind_buffer(&mut buffers)?;
                    while let Some(batch) = row_set_cursor.fetch()? {
                        rows.extend(process_batch(batch));
                    }
                    blocks.push(Block { headline, rows });
                }
            }
            return Ok(blocks);
        }

        Ok(vec![])
    }

    pub fn process_batch(batch: &BufferType) -> Vec<Vec<String>> {
        let mut rows: Vec<Vec<String>> = Vec::new();
        for row in 0..batch.num_rows() {
            let row: Vec<String> = (0..batch.num_cols())
                .map(|col_index| {
                    batch
                        .at_as_str(col_index, row)
                        .unwrap_or_default()
                        .unwrap_or_default()
                        .to_string()
                })
                .collect();
            rows.push(row);
        }
        rows
    }

    #[cfg(test)]
    mod tests {
        use crate::platform::odbc;
        use crate::types::InstanceName;

        #[test]
        fn test_make_connection_string() {
            assert_eq!(
                odbc::make_connection_string(
                    &InstanceName::from("SQLEXPRESS_NAME".to_string()),
                    None,
                    None
                ),
                "Driver={ODBC Driver 17 for SQL Server};SERVER=(local)\\SQLEXPRESS_NAME;Initial Catalog=master;Integrated Security=SSPI;Trusted_Connection=yes;"
            );
            assert_eq!(
                odbc::make_connection_string(
                    &InstanceName::from("Instance".to_string()),
                    Some("db"),
                    Some("driver"),
                ),
                "Driver=driver;SERVER=(local)\\Instance;Initial Catalog=db;Integrated Security=SSPI;Trusted_Connection=yes;"
            );
        }
    }
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

    fn get_instances_on_key(sql_key: &str) -> Vec<InstanceInfo> {
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

    fn get_sm(sql_key: &str, key_name: &str) -> bool {
        let instance_sm_key = format!(r"{}\MSSQLServer\SuperSocketNetLib\Sm", key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            sql_key.to_owned() + &instance_sm_key,
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        ) {
            let shared_memory: u32 = key.get_value("Enabled").unwrap_or_default();
            shared_memory != 0
        } else {
            false
        }
    }

    fn get_pipe(sql_key: &str, key_name: &str) -> Option<String> {
        let instance_sm_key = format!(r"{}\MSSQLServer\SuperSocketNetLib\Np", key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            sql_key.to_owned() + &instance_sm_key,
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        ) {
            let pipe_enabled: u32 = key.get_value("Enabled").unwrap_or_default();
            if pipe_enabled != 0 {
                key.get_value("PipeName").ok()
            } else {
                None
            }
        } else {
            None
        }
    }

    fn get_info(sql_key: &str, name: &str, key_name: &str) -> Option<InstanceInfo> {
        let instance_name = name;
        let instance_tcp_ip_all_key =
            format!(r"{}\MSSQLServer\SuperSocketNetLib\Tcp\IPAll", key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            sql_key.to_owned() + &instance_tcp_ip_all_key,
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
                shared_memory: get_sm(sql_key, key_name),
                pipe: get_pipe(sql_key, key_name),
            })
        } else {
            log::warn!("cannot open key: {}", instance_tcp_ip_all_key);
            None
        }
    }
    #[cfg(test)]
    mod tests {
        use super::get_instances;
        #[test]
        fn test_get_instances() {
            let infos = get_instances();
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
