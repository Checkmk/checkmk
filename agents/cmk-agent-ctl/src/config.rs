// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{cli, site_spec};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::{metadata, read_to_string, write};
use std::io;
use std::path::{Path, PathBuf};
use std::time::SystemTime;
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
    pub site_spec: Option<site_spec::SiteSpec>,

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
    pub coordinates: site_spec::Coordinates,
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
        let coordinates = match reg_args
            .site_address
            .or(config_from_disk.site_spec)
            .context("Site address not specified")?
        {
            site_spec::SiteSpec::Complete(coord) => coord,
            site_spec::SiteSpec::Incomplete(inc_coord) => {
                site_spec::Coordinates::from_incomplete_coordinates(inc_coord)?
            }
        };

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
            coordinates,
            credentials,
            root_certificate,
            host_reg_data,
            trust_server_cert: reg_args.trust_server_cert,
        })
    }
}

#[derive(Serialize, Deserialize, PartialEq, Debug, Clone)]
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

#[derive(Serialize, Deserialize, PartialEq, Debug, Clone)]
pub struct RegisteredConnections {
    #[serde(default)]
    pub push: HashMap<site_spec::Coordinates, Connection>,

    #[serde(default)]
    pub pull: HashMap<site_spec::Coordinates, Connection>,

    #[serde(default)]
    pub pull_imported: Vec<Connection>,
}

impl JSONLoader for RegisteredConnections {}

fn mtime(path: &Path) -> AnyhowResult<Option<SystemTime>> {
    Ok(if path.exists() {
        Some(metadata(&path)?.modified()?)
    } else {
        None
    })
}
#[derive(PartialEq, Debug, Clone)]
pub struct Registry {
    connections: RegisteredConnections,
    path: PathBuf,
    last_reload: Option<SystemTime>,
}

impl Registry {
    #[cfg(test)]
    pub fn new(connections: RegisteredConnections, path: PathBuf) -> AnyhowResult<Registry> {
        let last_reload = mtime(&path)?;
        Ok(Registry {
            connections,
            path,
            last_reload,
        })
    }

    #[cfg(test)]
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn from_file(path: &Path) -> AnyhowResult<Registry> {
        Ok(Registry {
            connections: RegisteredConnections::load(path)?,
            path: PathBuf::from(path),
            last_reload: mtime(path)?,
        })
    }

    pub fn refresh(&mut self) -> AnyhowResult<bool> {
        match (mtime(&self.path)?, self.last_reload) {
            (Some(now), Some(then)) => {
                match now.duration_since(then) {
                    Ok(time) if time.is_zero() => Ok(false),
                    _ => {
                        // This also covers Err(_), which means "negative time".
                        // This may occur due to clock adjustments.
                        // Force reload in this case.
                        self.reload()?;
                        Ok(true)
                    }
                }
            }

            (None, Some(_)) => {
                self.reload()?;
                Ok(true)
            }

            _ => Ok(false),
        }
    }

    pub fn save(&self) -> io::Result<()> {
        write(
            &self.path,
            &serde_json::to_string_pretty(&self.connections)?,
        )
    }

    pub fn pull_is_empty(&self) -> bool {
        self.connections.pull.is_empty() & self.connections.pull_imported.is_empty()
    }

    pub fn push_is_empty(&self) -> bool {
        self.connections.push.is_empty()
    }

    pub fn is_empty(&self) -> bool {
        self.push_is_empty() & self.pull_is_empty()
    }

    pub fn standard_pull_connections(
        &self,
    ) -> impl Iterator<Item = (&site_spec::Coordinates, &Connection)> {
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

    pub fn push_connections(&self) -> impl Iterator<Item = (&site_spec::Coordinates, &Connection)> {
        self.connections.push.iter()
    }

    pub fn register_connection(
        &mut self,
        connection_type: ConnectionType,
        coordinates: &site_spec::Coordinates,
        connection: Connection,
    ) {
        let (insert_connections, remove_connections) = match connection_type {
            ConnectionType::Push => (&mut self.connections.push, &mut self.connections.pull),
            ConnectionType::Pull => (&mut self.connections.pull, &mut self.connections.push),
        };
        remove_connections.remove(coordinates);
        insert_connections.insert(coordinates.clone(), connection);
    }

    pub fn register_imported_connection(&mut self, connection: Connection) {
        self.connections.pull_imported.push(connection);
    }

    pub fn delete_standard_connection(
        &mut self,
        coordinates: &site_spec::Coordinates,
    ) -> AnyhowResult<()> {
        if self.connections.push.remove(coordinates).is_some() {
            println!("Deleted push connection '{}'", coordinates);
            return Ok(());
        }
        if self.connections.pull.remove(coordinates).is_some() {
            println!("Deleted pull connection '{}'", coordinates);
            return Ok(());
        }
        Err(anyhow!("Connection '{}' not found", coordinates))
    }

    pub fn delete_imported_connection(&mut self, idx: usize) -> AnyhowResult<()> {
        if self.connections.pull_imported.len() > idx {
            self.connections.pull_imported.remove(idx);
            return Ok(());
        }
        Err(anyhow!(
            "Imported pull connection with index {} not found",
            idx
        ))
    }

    pub fn clear(&mut self) {
        self.connections.push.clear();
        self.connections.pull.clear();
        self.connections.pull_imported.clear();
    }

    fn reload(&mut self) -> AnyhowResult<()> {
        self.connections = RegisteredConnections::load(&self.path)?;
        self.last_reload = mtime(&self.path)?;
        Ok(())
    }
}

#[cfg(test)]
mod test_registry {
    use super::*;
    use std::str::FromStr;

    fn registry() -> Registry {
        let mut push = std::collections::HashMap::new();
        let mut pull = std::collections::HashMap::new();

        push.insert(
            site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            Connection {
                uuid: String::from("uuid-push"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        pull.insert(
            site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            Connection {
                uuid: String::from("uuid-pull"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        let path =
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path());
        let last_reload = mtime(&path).unwrap();
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
            path,
            last_reload,
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
        assert!(reg.last_reload.is_none());

        reg.save().unwrap();
        assert!(reg.path.exists());
        let new_reg = Registry::from_file(&reg.path).unwrap();
        assert_eq!(reg.connections, new_reg.connections);
        assert_eq!(reg.path, new_reg.path);
        assert!(new_reg.last_reload.is_some());
    }

    #[test]
    fn test_register_push_connection_new() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Push,
            &site_spec::Coordinates::from_str("new_server:1234/new-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_push_connection_from_pull() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Push,
            &site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_new() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Pull,
            &site_spec::Coordinates::from_str("new_server:1234/new-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_from_push() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Pull,
            &site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            connection(),
        );
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
        let mut reg = registry();
        assert!(reg
            .delete_standard_connection(
                &site_spec::Coordinates::from_str("server:8000/push-site").unwrap()
            )
            .is_ok());
        assert!(reg.connections.push.is_empty());
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_pull() {
        let mut reg = registry();
        assert!(reg
            .delete_standard_connection(
                &site_spec::Coordinates::from_str("server:8000/pull-site").unwrap()
            )
            .is_ok());
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_missing() {
        let mut reg = registry();
        assert_eq!(
            format!(
                "{}",
                reg.delete_standard_connection(
                    &site_spec::Coordinates::from_str("wiener_schnitzel:8000/pommes").unwrap()
                )
                .unwrap_err()
            ),
            "Connection 'wiener_schnitzel:8000/pommes' not found"
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_imported_connection_by_idx_ok() {
        let path =
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path());
        let last_reload = mtime(&path).unwrap();
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
            path,
            last_reload,
        };
        assert!(reg.delete_imported_connection(1).is_ok());
        assert!(reg.connections.pull_imported.len() == 1);
        assert!(reg.connections.pull_imported[0].uuid == "uuid-imported-1");
    }

    #[test]
    fn test_delete_imported_connection_by_idx_err() {
        let mut reg = registry();
        assert_eq!(
            format!("{}", reg.delete_imported_connection(1).unwrap_err()),
            "Imported pull connection with index 1 not found"
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
