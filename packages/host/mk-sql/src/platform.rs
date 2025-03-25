// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{HostName, InstanceName, Port};

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

#[allow(dead_code)] // NamedPipe is needed on Windows and not Linux.
#[derive(Debug, Clone)]
struct NamedPipe(String);

#[derive(Debug, Clone)]
struct TcpPoint {
    enabled_and_active: bool,
    port: Option<Port>,
    dynamic_port: Option<Port>,
    hostname: HostName,
}
#[derive(Debug, Clone)]
struct Tcp {
    port: Option<Port>,
    dynamic_port: Option<Port>,
    listen_all_ips: bool,
    peers: Vec<TcpPoint>,
}

pub struct PeerTcpInfo {
    pub active: bool,
    pub enabled: bool,
    pub hostname: String,
    pub port: Option<Port>,
    pub dynamic_port: Option<Port>,
}

pub struct HostTcpInfo {
    pub enabled: bool,
    pub listen_on_all_ips: bool,
    pub peers: Vec<PeerTcpInfo>,
}

pub fn get_host_tcp_info() -> HostTcpInfo {
    HostTcpInfo {
        enabled: true,
        listen_on_all_ips: true,
        peers: Vec::new(),
    }
}

#[derive(Debug, Clone)]
pub struct InstanceInfo {
    pub name: InstanceName,
    shared_memory: bool,
    pipe: Option<NamedPipe>,
    tcp: Option<Tcp>,
}

impl Tcp {
    pub fn port(&self) -> Option<Port> {
        if !self.listen_all_ips {
            for peer in &self.peers {
                if peer.port.is_some() && peer.port.as_ref().unwrap().value() != 0 {
                    return peer.port.clone();
                }
                if peer.dynamic_port.is_some() && peer.dynamic_port.as_ref().unwrap().value() != 0 {
                    return peer.dynamic_port.clone();
                }
            }
            return None;
        }

        if self.port.is_some() && self.port.as_ref().unwrap().value() != 0 {
            return self.port.clone();
        }
        if self.dynamic_port.is_some() && self.dynamic_port.as_ref().unwrap().value() != 0 {
            return self.dynamic_port.clone();
        }

        None
    }

    pub fn hostname(&self) -> Option<HostName> {
        if self.listen_all_ips {
            return Some(HostName::from("localhost".to_string()));
        }

        for peer in &self.peers {
            if peer.enabled_and_active {
                return Some(peer.hostname.clone());
            }
        }

        None
    }
}

impl InstanceInfo {
    pub fn final_port(&self) -> Option<Port> {
        if !self.is_tcp() {
            return None;
        }

        self.tcp.as_ref().and_then(|t| t.port().clone())
    }

    pub fn final_host(&self) -> Option<HostName> {
        if !self.is_tcp() {
            return None;
        }

        self.tcp.as_ref().and_then(|t| t.hostname())
    }

    pub fn is_shared_memory(&self) -> bool {
        self.shared_memory
    }

    pub fn is_pipe(&self) -> bool {
        self.pipe.is_some()
    }

    pub fn is_tcp(&self) -> bool {
        self.tcp
            .as_ref()
            .map(|t| t.port().is_some())
            .unwrap_or_default()
    }

    pub fn is_odbc_only(&self) -> bool {
        !self.is_tcp()
    }
}

#[cfg(test)]
mod tests {
    use crate::{
        platform::{InstanceInfo, Tcp},
        types::{InstanceName, Port},
    };

    #[test]
    fn test_instance_final_port() {
        let make_i = |port: Option<u16>, dynamic_port: Option<u16>| InstanceInfo {
            name: InstanceName::from("doesn't-matter".to_owned()),
            shared_memory: false,
            pipe: None,
            tcp: Some(Tcp {
                port: port.map(|p| p.into()),
                dynamic_port: dynamic_port.map(|p| p.into()),
                listen_all_ips: true,
                peers: vec![],
            }),
        };

        let std_port = 1;
        let dyn_port = 2;
        assert_eq!(
            make_i(Some(std_port), None).final_port().unwrap(),
            Port::from(std_port)
        );
        assert_eq!(
            make_i(Some(0), Some(dyn_port)).final_port().unwrap(),
            Port::from(dyn_port)
        );
        assert_eq!(
            make_i(Some(std_port), Some(dyn_port)).final_port().unwrap(),
            Port::from(std_port)
        );
        assert_eq!(
            make_i(None, Some(dyn_port)).final_port().unwrap(),
            Port::from(dyn_port)
        );
        assert_eq!(
            make_i(Some(std_port), Some(0)).final_port().unwrap(),
            Port::from(std_port)
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

    use crate::types::{HostName, InstanceName};
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
        hostname: Option<&HostName>,
        instance: &InstanceName,
        database: Option<&str>,
        driver: Option<&str>,
    ) -> String {
        format!(
            "Driver={{{}}};SERVER={}{};Database={};Integrated Security=SSPI;Trusted_Connection=yes;",
            driver.unwrap_or(&ODBC_DRIVER.clone()),
            hostname.map(|h| h.to_string()).unwrap_or("(local)".to_string()),
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
        use crate::types::{HostName, InstanceName};

        #[test]
        fn test_make_connection_string() {
            assert_eq!( odbc::make_connection_string(
                None,
                &InstanceName::from("SQLEXPRESS_NAME"),
                None,
                None),
                format!("Driver={{{}}};SERVER=(local)\\SQLEXPRESS_NAME;Database=master;Integrated Security=SSPI;Trusted_Connection=yes;", ODBC_DRIVER.clone()));
            assert_eq!(
                odbc::make_connection_string(
                    Some(&HostName::from("host".to_string())),
                    &InstanceName::from("Instance"),
                    Some("db"),
                    Some("driver")),
                "Driver={driver};SERVER=host\\Instance;Database=db;Integrated Security=SSPI;Trusted_Connection=yes;"
            );
            assert_eq!( odbc::make_connection_string(
                Some(&HostName::from("host".to_string())),
                &InstanceName::from("mssqlserver"),
                    None,
                    None),
                    format!("Driver={{{}}};SERVER=host;Database=master;Integrated Security=SSPI;Trusted_Connection=yes;", ODBC_DRIVER.clone()));
        }
    }
}

#[cfg(windows)]
pub mod registry {
    use super::{InstanceInfo, NamedPipe, Tcp, TcpPoint};
    use crate::types::{HostName, InstanceName, Port};
    use std::collections::HashMap;
    use winreg::{enums::HKEY_LOCAL_MACHINE, RegKey};
    const MS_SQL_DEFAULT_BRANCH_LOCATION: &str = r"SOFTWARE\";

    pub fn get_instances(custom_branch: Option<String>) -> Vec<InstanceInfo> {
        let branch = custom_branch.unwrap_or_default() + MS_SQL_DEFAULT_BRANCH_LOCATION;
        let instances_std =
            get_instances_on_key(&(branch.clone() + r"Microsoft\Microsoft SQL Server\"));
        let instances_wow =
            get_instances_on_key(&(branch + r"WOW6432Node\Microsoft\Microsoft SQL Server\"));

        instances_std.into_iter().chain(instances_wow).collect()
    }

    fn get_instances_on_key(sql_key: &str) -> Vec<InstanceInfo> {
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        let result = root_key.open_subkey_with_flags(
            sql_key.to_owned() + r"Instance Names\SQL",
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        );
        if let Err(e) = result {
            let key = sql_key.to_owned() + r"Instance Names\SQL";
            if e.kind() == std::io::ErrorKind::NotFound {
                log::info!("Registry key '{key}' is not found, it's ok");
            } else {
                log::error!("Error opening registry key '{key}': {e:?}",);
            }
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
            .filter_map(|x| get_transport(sql_key, x.0, x.1))
            .collect::<Vec<InstanceInfo>>()
    }

    fn get_shared_memory(sql_key: &str, key_name: &str) -> bool {
        let instance_sm_key = format!(r"{}{}\MSSQLServer\SuperSocketNetLib\Sm", sql_key, key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            instance_sm_key,
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        ) {
            key.get_value::<u32, _>("Enabled").unwrap_or_default() != 0
        } else {
            false
        }
    }

    fn get_pipe(sql_key: &str, key_name: &str) -> Option<String> {
        let instance_pipe_key =
            format!(r"{}{}\MSSQLServer\SuperSocketNetLib\Np", sql_key, key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            instance_pipe_key,
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

    fn _read_tcp_port(key: &RegKey, value: &str) -> u16 {
        key.get_value::<String, _>(value)
            .unwrap_or_default()
            .parse::<u16>()
            .unwrap_or(0)
    }

    fn get_tcp(sql_key: &str, key_name: &str) -> Option<Tcp> {
        let instance_tcp_key =
            format!(r"{}{}\MSSQLServer\SuperSocketNetLib\Tcp", sql_key, key_name);
        let root_key = RegKey::predef(HKEY_LOCAL_MACHINE);
        if let Ok(key) = root_key.open_subkey_with_flags(
            &instance_tcp_key,
            winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
        ) {
            let tcp_enabled: u32 = key.get_value("Enabled").unwrap_or_default();
            if tcp_enabled == 0 {
                return None;
            }
            let ip_all_key = key.open_subkey_with_flags(
                "IPAll",
                winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
            );
            // read ports
            let (port, dynamic_port) = ip_all_key
                .ok()
                .map(|key| {
                    let port: u16 = _read_tcp_port(&key, "TcpPort");
                    let dynamic_port: u16 = _read_tcp_port(&key, "TcpDynamicPorts");
                    (Some(port), Some(dynamic_port))
                })
                .unwrap();
            Some(Tcp {
                port: port.map(Port::from),
                dynamic_port: dynamic_port.map(Port::from),
                listen_all_ips: key
                    .get_value::<u32, _>("ListenOnAllIPs")
                    .unwrap_or_default()
                    != 0,
                peers: _gather_instances(key),
            })
        } else {
            log::error!("Error opening registry key '{instance_tcp_key}'");
            None
        }
    }

    fn _gather_instances(key: RegKey) -> Vec<TcpPoint> {
        let keys = key.enum_keys().filter_map(|x| x.ok());
        keys.filter_map(|k| {
            let ip_key = key.open_subkey_with_flags(
                k,
                winreg::enums::KEY_READ | winreg::enums::KEY_WOW64_64KEY,
            );
            if let Ok(ip_key) = ip_key {
                let dynamic_port = ip_key
                    .get_value::<String, _>("TcpDynamicPorts")
                    .unwrap_or_default();
                let port = ip_key.get_value::<String, _>("TcpPort").unwrap_or_default();
                let hostname = ip_key
                    .get_value::<String, _>("IpAddress")
                    .unwrap_or_default();
                let enabled = ip_key.get_value::<u32, _>("Enabled").unwrap_or_default() != 0;
                let active = ip_key.get_value::<u32, _>("Active").unwrap_or_default() != 0;
                if !enabled || !active {
                    return None;
                }
                Some(TcpPoint {
                    enabled_and_active: enabled && active,
                    hostname: HostName::from(hostname),
                    port: port.parse::<u16>().ok().map(Port::from),
                    dynamic_port: dynamic_port.parse::<u16>().ok().map(Port::from),
                })
            } else {
                None
            }
        })
        .collect()
    }

    fn get_transport(
        sql_key: &str,
        instance_name: &str,
        registry_instance_name: &str,
    ) -> Option<InstanceInfo> {
        let x = InstanceInfo {
            name: InstanceName::from(instance_name.to_owned()),
            shared_memory: get_shared_memory(sql_key, registry_instance_name),
            pipe: get_pipe(sql_key, registry_instance_name).map(NamedPipe),
            tcp: get_tcp(sql_key, registry_instance_name),
        };
        Some(x)
    }

    #[cfg(test)]
    mod tests {
        use std::collections::HashSet;

        use super::get_instances;
        use crate::types::InstanceName;

        /// must be in sync with test files
        /// allowed not be in sync with actual repo branch(may be in future)
        const REPO_NAME: &str = "2.5.0";

        fn obtain_test_instances_registry_branch(test_set_name: &str) -> String {
            format!(
                r"SOFTWARE\checkmk\tests\{}\mk-sql\instances\{}\",
                REPO_NAME, test_set_name
            )
        }

        #[test]
        fn test_get_instances() {
            let custom_branch = obtain_test_instances_registry_branch("test-std");
            let infos = get_instances(Some(custom_branch.to_owned()))
                .into_iter()
                .filter(|i| {
                    i.name != InstanceName::from("SQLEXPRESS_OLD")
                        && i.name != InstanceName::from("SQLBAD")
                })
                .collect::<Vec<_>>();
            assert_eq!(infos.len(), 3usize);
        }

        #[test]
        fn test_get_host_tcp_info() {
            let custom_branch = obtain_test_instances_registry_branch("test-not-all");
            let infos = get_instances(Some(custom_branch.to_owned()))
                .into_iter()
                .map(|i| i.tcp)
                .collect::<Vec<_>>();
            assert_eq!(infos.len(), 2usize);
            assert_eq!(infos[0].as_ref().unwrap().port().unwrap().value(), 1433);
            assert_eq!(infos[1].as_ref().unwrap().port().unwrap().value(), 1433);
            let host_name_set = infos
                .into_iter()
                .map(|i| i.unwrap().hostname().unwrap().to_string())
                .collect::<HashSet<_>>();
            assert_eq!(
                host_name_set,
                ["192.168.125.175", "192.168.121.170"]
                    .into_iter()
                    .map(|s| s.to_string())
                    .collect::<HashSet<_>>()
            );
        }
    }
}

#[cfg(unix)]
pub mod registry {
    use super::InstanceInfo;
    pub fn get_instances(_custom_branch: Option<String>) -> Vec<InstanceInfo> {
        vec![]
    }
    #[cfg(test)]
    mod tests {
        use super::get_instances;
        #[test]
        fn test_get_instances() {
            assert!(get_instances(None).is_empty());
        }
    }
}
