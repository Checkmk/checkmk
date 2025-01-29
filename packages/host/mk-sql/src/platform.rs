// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{InstanceName, Port};

pub struct Block {
    pub headline: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

impl Block {
    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn first(&self) -> Option<&Vec<String>> {
        self.rows.first()
    }
    pub fn last(&self) -> Option<&Vec<String>> {
        self.rows.last()
    }

    pub fn get_value_by_name(&self, row: &[String], idx: &str) -> String {
        if let Some(index) = self.headline.iter().position(|r| r == idx) {
            row.get(index).cloned()
        } else {
            None
        }
        .unwrap_or_default()
    }

    pub fn get_bigint_by_name(&self, row: &[String], idx: &str) -> String {
        self.get_value_by_name(row, idx)
            .parse::<i64>()
            .unwrap_or_default()
            .to_string()
    }

    pub fn get_first_row_column(&self, column: usize) -> Option<String> {
        self.rows.first().and_then(|r| r.get(column)).cloned()
    }
}

pub fn get_row_value_by_idx(row: &[String], idx: usize) -> String {
    row.get(idx).cloned().unwrap_or_default()
}

#[derive(Debug, PartialEq, Clone)]
pub enum Transport {
    Tcp,
    NamedPipe,
    SharedMemory,
}

#[derive(Debug, Clone)]
pub struct InstanceInfo {
    pub name: InstanceName,
    port: Option<Port>,
    dynamic_port: Option<Port>,
    pipe: Option<String>,
    transports: Vec<Transport>,
}

impl InstanceInfo {
    pub fn final_port(&self) -> Option<&Port> {
        if !self.is_tcp() {
            return None;
        }
        self.dynamic_port
            .as_ref()
            .filter(|p| p.value() != 0)
            .or(self.port.as_ref())
            .filter(|p| p.value() != 0)
    }

    pub fn is_shared_memory(&self) -> bool {
        self.transports.contains(&Transport::SharedMemory)
    }

    pub fn is_pipe(&self) -> bool {
        self.transports.contains(&Transport::NamedPipe) && self.pipe.is_some()
    }

    pub fn is_tcp(&self) -> bool {
        self.transports.contains(&Transport::Tcp)
    }

    pub fn is_odbc_only(&self) -> bool {
        !self.transports.is_empty() && !self.is_tcp()
    }
}

#[cfg(test)]
mod tests {
    use crate::{
        platform::{InstanceInfo, Transport},
        types::{InstanceName, Port},
    };

    #[test]
    fn test_instance_final_port() {
        let make_i = |port: Option<u16>, dynamic_port: Option<u16>| InstanceInfo {
            name: InstanceName::from("AAA".to_owned()),
            port: port.map(|p| p.into()),
            dynamic_port: dynamic_port.map(|p| p.into()),
            pipe: None,
            transports: vec![Transport::Tcp],
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
    use super::Block;
    use anyhow::Result;
    use odbc_api::{
        buffers::{ColumnarBuffer, TextColumn, TextRowSet},
        ConnectionOptions, Cursor, Environment, ResultSetMetadata,
    };

    const ODBC_DRIVER_LIST: &str = "Get-OdbcDriver -Name '* SQL Server' -Platform 32-Bit | Format-Table -HideTableHeaders -Property Name";

    use crate::types::InstanceName;
    lazy_static::lazy_static! {
        pub static ref ODBC_DRIVER: String = gather_odbc_drivers().last().unwrap_or(&"".to_string()).clone();
    }

    pub fn gather_odbc_drivers() -> Vec<String> {
        match run_powershell_command(ODBC_DRIVER_LIST) {
            Ok(output) => {
                let output_text = std::str::from_utf8(&output.stdout)
                    .map(|s| s.to_string())
                    .unwrap_or_default();
                output_text
                    .split('\n')
                    .map(|s| s.to_string().replace('\r', ""))
                    .filter(|s| !s.is_empty())
                    .collect::<Vec<String>>()
            }
            Err(e) => {
                log::error!("Failed to gather ODBC drivers: {:?}", e);
                vec![]
            }
        }
    }

    fn run_powershell_command(command: &str) -> std::io::Result<std::process::Output> {
        std::process::Command::new("powershell")
            .args(["-Command", command])
            .output()
    }

    /// creates a local connection string for the ODBC driver
    /// always SSPI and Trusted connection
    pub fn make_connection_string(
        instance: &InstanceName,
        database: Option<&str>,
        driver: Option<&str>,
    ) -> String {
        format!(
            "Driver={{{}}};SERVER=(local){};Database={};Integrated Security=SSPI;Trusted_Connection=yes;",
            driver.unwrap_or(&ODBC_DRIVER.clone()),
            if instance.to_string().to_uppercase() == *"MSSQLSERVER" {
                "".to_string()
            } else {
                format!("\\{}", instance)
            },
            database.unwrap_or("master")
        )
    }

    type BufferType = ColumnarBuffer<TextColumn<u8>>;

    // TODO(sk): make it ASYNC!
    pub fn execute(
        connection_string: &str,
        query: &str,
        timeout: Option<u32>,
    ) -> Result<Vec<Block>> {
        let env = Environment::new()?;

        log::info!("Connecting with string {}", connection_string);

        let conn = env.connect_with_connection_string(
            connection_string,
            ConnectionOptions {
                login_timeout_sec: timeout,
                ..Default::default()
            },
        )?;

        // TODO(sk): replace execute with execute_polling
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

            if let Ok((cursor, mut _buffer)) = row_set_cursor.unbind() {
                if let Ok(Some(mut c)) = cursor.more_results() {
                    let headline = c.column_names()?.collect::<Result<_, _>>()?;
                    let mut buffers = TextRowSet::for_cursor(BATCH_SIZE, &mut c, Some(4096))?;
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
        use crate::platform::odbc::{self, ODBC_DRIVER};
        use crate::types::InstanceName;

        #[test]
        fn test_make_connection_string() {
            assert_eq!( odbc::make_connection_string(
                &InstanceName::from("SQLEXPRESS_NAME"),
                None,
                None),
                format!("Driver={{{}}};SERVER=(local)\\SQLEXPRESS_NAME;Database=master;Integrated Security=SSPI;Trusted_Connection=yes;", ODBC_DRIVER.clone()));
            assert_eq!(
                odbc::make_connection_string(
                    &InstanceName::from("Instance"),
                    Some("db"),
                    Some("driver")),
                "Driver={driver};SERVER=(local)\\Instance;Database=db;Integrated Security=SSPI;Trusted_Connection=yes;"
            );
            assert_eq!( odbc::make_connection_string(
                    &InstanceName::from("mssqlserver"),
                    None,
                    None),
                    format!("Driver={{{}}};SERVER=(local);Database=master;Integrated Security=SSPI;Trusted_Connection=yes;", ODBC_DRIVER.clone()));
        }
    }
}

#[cfg(windows)]
pub mod registry {
    use super::{InstanceInfo, Transport};
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

    fn get_transport(
        sql_key: &str,
        registry_instance_name: &str,
        transport_key: &str,
        flag_names: &[&str],
    ) -> bool {
        let instance_key = format!(
            r"{}\MSSQLServer\SuperSocketNetLib\{}",
            registry_instance_name, transport_key
        );
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            sql_key.to_owned() + &instance_key,
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        ) {
            flag_names.iter().all(|flag| {
                let on: u32 = key.get_value(flag).unwrap_or_default();
                on != 0
            })
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

    fn get_enabled_transports(sql_key: &str, key_name: &str) -> Vec<Transport> {
        let mut transports = vec![];
        if get_transport(sql_key, key_name, "Tcp", &["Enabled", "ListenOnAllIPs"]) {
            transports.push(Transport::Tcp);
        }
        if get_transport(sql_key, key_name, "Sm", &["Enabled"]) {
            transports.push(Transport::SharedMemory);
        }
        if get_transport(sql_key, key_name, "Np", &["Enabled"]) {
            transports.push(Transport::NamedPipe);
        }
        transports
    }

    fn get_info(
        sql_key: &str,
        instance_name: &str,
        registry_instance_name: &str,
    ) -> Option<InstanceInfo> {
        let instance_tcp_ip_all_key = format!(
            r"{}\MSSQLServer\SuperSocketNetLib\Tcp\IPAll",
            registry_instance_name
        );
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
                pipe: get_pipe(sql_key, registry_instance_name),
                transports: get_enabled_transports(sql_key, registry_instance_name),
            })
        } else {
            log::warn!("cannot open key: {}", instance_tcp_ip_all_key);
            None
        }
    }
    #[cfg(test)]
    mod tests {
        use super::get_instances;
        use crate::types::InstanceName;
        #[test]
        fn test_get_instances() {
            let infos = get_instances()
                .into_iter()
                .filter(|i| {
                    i.name != InstanceName::from("SQLEXPRESS_OLD")
                        && i.name != InstanceName::from("SQLBAD")
                })
                .collect::<Vec<_>>();
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
