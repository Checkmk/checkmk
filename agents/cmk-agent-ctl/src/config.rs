// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::cli;
use anyhow::{anyhow, Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::{read_to_string, write};
use std::io;
use std::path::{Path, PathBuf};
use string_enum::StringEnum;

#[derive(StringEnum, PartialEq)]
pub enum ConnectionType {
    /// `push-agent`
    Push,
    /// `pull-agent`
    Pull,
}

pub trait JSONLoader: DeserializeOwned {
    fn new() -> AnyhowResult<Self> {
        Ok(serde_json::from_str("{}")?)
    }

    fn load(path: &Path) -> AnyhowResult<Self> {
        if !path.exists() {
            return Self::new();
        }
        Ok(serde_json::from_str(&read_to_string(path)?)?)
    }
}

pub type AgentLabels = HashMap<String, String>;

#[derive(Deserialize)]
pub struct Credentials {
    pub username: String,
    pub password: String,
}

#[derive(Deserialize)]
pub struct ConfigFromDisk {
    #[serde(default)]
    pub agent_receiver_address: Option<String>,

    #[serde(default)]
    pub credentials: Option<Credentials>,

    #[serde(default)]
    pub root_certificate: Option<String>,

    #[serde(default)]
    pub host_name: Option<String>,

    #[serde(default)]
    pub agent_labels: Option<AgentLabels>,
}

impl JSONLoader for ConfigFromDisk {}

pub enum HostRegistrationData {
    Name(String),
    Labels(AgentLabels),
}

pub struct RegistrationConfig {
    pub agent_receiver_address: String,
    pub credentials: Credentials,
    pub root_certificate: Option<String>,
    pub host_reg_data: HostRegistrationData,
    pub trust_server_cert: bool,
}

impl RegistrationConfig {
    pub fn new(
        config_from_disk: ConfigFromDisk,
        reg_args: cli::RegistrationArgs,
    ) -> AnyhowResult<RegistrationConfig> {
        let agent_receiver_address = reg_args
            .server
            .or(config_from_disk.agent_receiver_address)
            .context("Missing server address")?;
        let credentials =
            if let (Some(username), Some(password)) = (reg_args.user, reg_args.password) {
                Credentials { username, password }
            } else {
                config_from_disk
                    .credentials
                    .context("Missing credentials")?
            };
        let root_certificate = config_from_disk.root_certificate;
        let stored_host_name = config_from_disk.host_name;
        let stored_agent_labels = config_from_disk.agent_labels;
        let host_reg_data = reg_args
            .host_name
            .map(HostRegistrationData::Name)
            .or_else(|| stored_host_name.map(HostRegistrationData::Name))
            .or_else(|| stored_agent_labels.map(HostRegistrationData::Labels))
            .context("Neither hostname nor agent labels found")?;
        Ok(RegistrationConfig {
            agent_receiver_address,
            credentials,
            root_certificate,
            host_reg_data,
            trust_server_cert: reg_args.trust_server_cert,
        })
    }
}

#[derive(Serialize, Deserialize, PartialEq, Debug)]
pub struct Connection {
    #[serde(default)]
    pub uuid: String,

    #[serde(default)]
    pub private_key: String,

    #[serde(default)]
    pub certificate: String,

    #[serde(default)]
    pub root_cert: String,
}

#[derive(Serialize, Deserialize, PartialEq, Debug)]
pub struct RegisteredConnections {
    #[serde(default)]
    pub push: HashMap<String, Connection>,

    #[serde(default)]
    pub pull: HashMap<String, Connection>,

    #[serde(default)]
    pub pull_imported: Vec<Connection>,
}

impl JSONLoader for RegisteredConnections {}

#[derive(PartialEq, Debug)]
pub struct Registry {
    connections: RegisteredConnections,
    path: PathBuf,
}

impl Registry {
    #[cfg(test)]
    pub fn new(connections: RegisteredConnections, path: PathBuf) -> Registry {
        Registry { connections, path }
    }

    #[cfg(test)]
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn from_file(path: &Path) -> AnyhowResult<Registry> {
        Ok(Registry {
            connections: RegisteredConnections::load(path)?,
            path: PathBuf::from(path),
        })
    }

    pub fn save(&self) -> io::Result<()> {
        write(
            &self.path,
            &serde_json::to_string_pretty(&self.connections)?,
        )
    }

    pub fn is_empty(&self) -> bool {
        self.connections.push.is_empty()
            & self.connections.pull.is_empty()
            & self.connections.pull_imported.is_empty()
    }

    pub fn standard_pull_connections(&self) -> impl Iterator<Item = (&String, &Connection)> {
        self.connections.pull.iter()
    }

    pub fn imported_pull_connections(&self) -> impl Iterator<Item = &Connection> {
        self.connections.pull_imported.iter()
    }

    pub fn pull_connections(&self) -> impl Iterator<Item = &Connection> {
        self.connections
            .pull
            .values()
            .chain(self.connections.pull_imported.iter())
    }

    pub fn push_connections(&self) -> impl Iterator<Item = (&String, &Connection)> {
        self.connections.push.iter()
    }

    pub fn register_connection(
        &mut self,
        connection_type: ConnectionType,
        address: &str,
        connection: Connection,
    ) {
        let (insert_connections, remove_connections) = match connection_type {
            ConnectionType::Push => (&mut self.connections.push, &mut self.connections.pull),
            ConnectionType::Pull => (&mut self.connections.pull, &mut self.connections.push),
        };
        remove_connections.remove(address);
        insert_connections.insert(String::from(address), connection);
    }

    pub fn register_imported_connection(&mut self, connection: Connection) {
        self.connections.pull_imported.push(connection);
    }

    pub fn delete_connection(&mut self, connection_id: &str) -> AnyhowResult<()> {
        if self.delete_connection_by_server(connection_id).is_ok()
            || self.delete_connection_by_uuid(connection_id).is_ok()
        {
            return Ok(());
        }
        Err(anyhow!("Connection '{}' not found", connection_id))
    }

    pub fn delete_imported_connection_by_idx(&mut self, idx: usize) -> AnyhowResult<()> {
        if self.connections.pull_imported.len() > idx {
            self.connections.pull_imported.remove(idx);
            return Ok(());
        }
        Err(anyhow!(
            "Imported pull connection with index '{}' not found",
            idx
        ))
    }

    pub fn clear(&mut self) {
        self.connections.push.clear();
        self.connections.pull.clear();
        self.connections.pull_imported.clear();
    }

    fn delete_connection_by_server(&mut self, server: &str) -> AnyhowResult<()> {
        if self.connections.push.remove(server).is_some() {
            println!("Deleted push connection '{}'", server);
            return Ok(());
        }
        if self.connections.pull.remove(server).is_some() {
            println!("Deleted pull connection '{}'", server);
            return Ok(());
        }
        Err(anyhow!("Connection '{}' not found", server))
    }

    fn delete_by_uuid_from_standard_connections(&mut self, uuid: &str) -> AnyhowResult<()> {
        for (conn_type, connections) in vec![
            ("push", &mut self.connections.push),
            ("pull", &mut self.connections.pull),
        ] {
            let mut address_to_delete: Option<String> = None;
            for (address, conn) in connections.iter() {
                if conn.uuid == uuid {
                    address_to_delete = Some(String::from(address));
                    break;
                }
            }
            if let Some(addr) = address_to_delete {
                connections.remove(&addr);
                println!("Deleted {} connection '{}'", conn_type, uuid);
                return Ok(());
            }
        }
        Err(anyhow!("Connection '{}' not found", uuid))
    }

    fn delete_by_uuid_from_imported_connections(&mut self, uuid: &str) -> AnyhowResult<()> {
        let mut idx_to_delete: Option<usize> = None;
        for (idx, imp_pull_conn) in self.imported_pull_connections().enumerate() {
            if imp_pull_conn.uuid == uuid {
                idx_to_delete = Some(idx);
                break;
            }
        }
        if let Some(idx) = idx_to_delete {
            self.connections.pull_imported.remove(idx);
            println!("Deleted imported pull connection '{}'", uuid);
            return Ok(());
        }
        Err(anyhow!("Connection '{}' not found", uuid))
    }

    fn delete_connection_by_uuid(&mut self, uuid: &str) -> AnyhowResult<()> {
        if self.delete_by_uuid_from_standard_connections(uuid).is_ok()
            || self.delete_by_uuid_from_imported_connections(uuid).is_ok()
        {
            return Ok(());
        }
        Err(anyhow!("Connection '{}' not found", uuid))
    }
}

#[cfg(test)]
mod test_registry {
    use super::*;

    fn registry() -> Registry {
        let mut push = std::collections::HashMap::new();
        let mut pull = std::collections::HashMap::new();

        push.insert(
            String::from("push_server:8000"),
            Connection {
                uuid: String::from("uuid-push"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        pull.insert(
            String::from("pull_server:8000"),
            Connection {
                uuid: String::from("uuid-pull"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        Registry {
            connections: RegisteredConnections {
                push,
                pull,
                pull_imported: vec![Connection {
                    uuid: String::from("uuid-imported"),
                    private_key: String::from("private_key"),
                    certificate: String::from("certificate"),
                    root_cert: String::from("root_cert"),
                }],
            },
            path: std::path::PathBuf::from(
                &tempfile::NamedTempFile::new().unwrap().into_temp_path(),
            ),
        }
    }

    fn connection() -> Connection {
        Connection {
            uuid: String::from("abc-123"),
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        }
    }

    #[test]
    fn test_io() {
        let reg = registry();
        assert!(!reg.path.exists());
        reg.save().unwrap();
        assert!(reg.path.exists());
        assert_eq!(reg, Registry::from_file(&reg.path).unwrap());
    }

    #[test]
    fn test_register_push_connection_new() {
        let mut reg = registry();
        reg.register_connection(ConnectionType::Push, "new_server:1234", connection());
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_push_connection_from_pull() {
        let mut reg = registry();
        reg.register_connection(ConnectionType::Push, "pull_server:8000", connection());
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_new() {
        let mut reg = registry();
        reg.register_connection(ConnectionType::Pull, "new_server:1234", connection());
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_from_push() {
        let mut reg = registry();
        reg.register_connection(ConnectionType::Pull, "push_server:8000", connection());
        assert!(reg.connections.push.is_empty());
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_imported_connection() {
        let mut reg = registry();
        reg.register_imported_connection(connection());
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 2);
        assert!(reg.connections.pull_imported[1].uuid == "abc-123");
    }

    #[test]
    fn test_is_empty() {
        let mut reg = registry();
        assert!(!reg.is_empty());
        reg.connections.push.clear();
        assert!(!reg.is_empty());
        reg.connections.pull.clear();
        assert!(!reg.is_empty());
        reg.connections.pull_imported.clear();
        assert!(reg.is_empty());
    }

    #[test]
    fn test_pull_connections() {
        let reg = registry();
        let pull_conns: Vec<&Connection> = reg.pull_connections().collect();
        assert!(pull_conns.len() == 2);
        assert!(pull_conns[0].uuid == "uuid-pull");
        assert!(pull_conns[1].uuid == "uuid-imported");
    }

    #[test]
    fn test_delete_push() {
        for to_delete in ["push_server:8000", "uuid-push"] {
            let mut reg = registry();
            assert!(reg.delete_connection(to_delete).is_ok());
            assert!(reg.connections.push.is_empty());
            assert!(reg.connections.pull.len() == 1);
            assert!(reg.connections.pull_imported.len() == 1);
        }
    }

    #[test]
    fn test_delete_pull() {
        for to_delete in ["pull_server:8000", "uuid-pull"] {
            let mut reg = registry();
            assert!(reg.delete_connection(to_delete).is_ok());
            assert!(reg.connections.push.len() == 1);
            assert!(reg.connections.pull.is_empty());
            assert!(reg.connections.pull_imported.len() == 1);
        }
    }

    #[test]
    fn test_delete_pull_imported() {
        let mut reg = registry();
        assert!(reg.delete_connection("uuid-imported").is_ok());
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.is_empty());
    }

    #[test]
    fn test_delete_missing() {
        let mut reg = registry();
        assert_eq!(
            format!("{}", reg.delete_connection("wiener_schnitzel").unwrap_err()),
            "Connection 'wiener_schnitzel' not found"
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_delete_imported_connection_by_idx_ok() {
        let mut reg = Registry {
            connections: RegisteredConnections {
                push: std::collections::HashMap::new(),
                pull: std::collections::HashMap::new(),
                pull_imported: vec![
                    Connection {
                        uuid: String::from("uuid-imported-1"),
                        private_key: String::from("private_key"),
                        certificate: String::from("certificate"),
                        root_cert: String::from("root_cert"),
                    },
                    Connection {
                        uuid: String::from("uuid-imported-2"),
                        private_key: String::from("private_key"),
                        certificate: String::from("certificate"),
                        root_cert: String::from("root_cert"),
                    },
                ],
            },
            path: std::path::PathBuf::from(
                &tempfile::NamedTempFile::new().unwrap().into_temp_path(),
            ),
        };
        assert!(reg.delete_imported_connection_by_idx(1).is_ok());
        assert!(reg.connections.pull_imported.len() == 1);
        assert!(reg.connections.pull_imported[0].uuid == "uuid-imported-1");
    }

    #[test]
    fn test_delete_delete_imported_connection_by_idx_err() {
        let mut reg = registry();
        assert_eq!(
            format!("{}", reg.delete_imported_connection_by_idx(1).unwrap_err()),
            "Imported pull connection with index '1' not found"
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_clear() {
        let mut reg = registry();
        reg.clear();
        assert!(reg.is_empty());
    }
}
