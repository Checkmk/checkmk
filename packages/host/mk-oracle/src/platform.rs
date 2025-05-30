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
