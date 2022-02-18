// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{cli, constants, site_spec, types};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde::Serialize;
use serde_with::DisplayFromStr;
use std::collections::HashMap;
use std::fs::{metadata, read_to_string, write};
use std::io;
use std::path::{Path, PathBuf};
use std::str::FromStr;
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

pub trait TOMLLoader: DeserializeOwned {
    fn new() -> AnyhowResult<Self> {
        Ok(toml::from_str("")?)
    }

    fn load(path: &Path) -> AnyhowResult<Self> {
        if !path.exists() {
            return Self::new();
        }
        Ok(toml::from_str(&read_to_string(path)?)?)
    }
}

#[derive(Deserialize)]
pub struct RegistrationPreset {
    #[serde(default)]
    site_spec: Option<site_spec::SiteSpec>,

    #[serde(default)]
    credentials: Option<types::OptPwdCredentials>,

    #[serde(default)]
    root_certificate: Option<String>,

    #[serde(default)]
    host_name: Option<String>,

    #[serde(default)]
    agent_labels: Option<types::AgentLabels>,
}

impl JSONLoader for RegistrationPreset {}

pub enum HostRegistrationData {
    Name(String),
    Labels(types::AgentLabels),
}

pub struct RegistrationConfig {
    pub coordinates: site_spec::Coordinates,
    pub opt_pwd_credentials: types::OptPwdCredentials,
    pub root_certificate: Option<String>,
    pub host_reg_data: HostRegistrationData,
    pub trust_server_cert: bool,
}

impl RegistrationConfig {
    pub fn new(
        preset: RegistrationPreset,
        reg_args: cli::RegistrationArgs,
    ) -> AnyhowResult<RegistrationConfig> {
        let coordinates = match reg_args
            .site_address
            .or(preset.site_spec)
            .context("Site address not specified")?
        {
            site_spec::SiteSpec::Complete(coord) => coord,
            site_spec::SiteSpec::Incomplete(inc_coord) => {
                site_spec::Coordinates::try_from(inc_coord)?
            }
        };
        let opt_pwd_credentials = match reg_args.user {
            Some(username) => types::OptPwdCredentials {
                username,
                password: reg_args.password,
            },
            None => preset.credentials.context("Missing credentials")?,
        };
        let root_certificate = preset.root_certificate;
        let stored_host_name = preset.host_name;
        let stored_agent_labels = preset.agent_labels;
        let host_reg_data = reg_args
            .host_name
            .map(HostRegistrationData::Name)
            .or_else(|| stored_host_name.map(HostRegistrationData::Name))
            .or_else(|| stored_agent_labels.map(HostRegistrationData::Labels))
            .context("Neither hostname nor agent labels found")?;
        Ok(RegistrationConfig {
            coordinates,
            opt_pwd_credentials,
            root_certificate,
            host_reg_data,
            trust_server_cert: reg_args.trust_server_cert,
        })
    }
}

#[derive(Deserialize)]
pub struct ConfigFromDisk {
    #[serde(default)]
    allowed_ip: Option<Vec<String>>,

    #[serde(default)]
    pull_port: Option<types::Port>,
}

impl TOMLLoader for ConfigFromDisk {}

pub struct PullConfig {
    pub allowed_ip: Vec<String>,
    pub port: types::Port,
}

impl PullConfig {
    pub fn new(
        config_from_disk: ConfigFromDisk,
        pull_args: cli::PullArgs,
    ) -> AnyhowResult<PullConfig> {
        let allowed_ip = pull_args
            .allowed_ip
            .or(config_from_disk.allowed_ip)
            .unwrap_or_default();
        let port = pull_args
            .port
            .or(config_from_disk.pull_port)
            .unwrap_or(types::Port::from_str(constants::DEFAULT_AGENT_PORT)?);
        Ok(PullConfig { allowed_ip, port })
    }
}

#[serde_with::serde_as]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Connection {
    #[serde_as(as = "DisplayFromStr")]
    pub uuid: uuid::Uuid,
    pub private_key: String,
    pub certificate: String,
    pub root_cert: String,
}

impl std::cmp::PartialEq for Connection {
    fn eq(&self, other: &Self) -> bool {
        self.uuid == other.uuid
    }
}

impl std::cmp::Eq for Connection {}

impl std::hash::Hash for Connection {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.uuid.hash(state);
    }
}

impl std::borrow::Borrow<uuid::Uuid> for Connection {
    fn borrow(&self) -> &uuid::Uuid {
        &self.uuid
    }
}

#[derive(Serialize, Deserialize, PartialEq, Debug, Clone)]
pub struct RegisteredConnections {
    #[serde(default)]
    pub push: HashMap<site_spec::Coordinates, Connection>,

    #[serde(default)]
    pub pull: HashMap<site_spec::Coordinates, Connection>,

    #[serde(default)]
    pub pull_imported: std::collections::HashSet<Connection>,
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
                    Ok(time) if time.is_zero() => {
                        // No change.
                        Ok(false)
                    }
                    _ => {
                        // This also covers Err(_), which means "negative time".
                        // This may occur due to clock adjustments.
                        // Force reload in this case.
                        // Otherwise, we have a regular posive duration, which means
                        // that our registration was touched.
                        self.reload()?;
                        Ok(true)
                    }
                }
            }

            (None, None) => {
                // Still no file there -> No change.
                Ok(false)
            }

            _ => {
                // File was deleted or is new
                self.reload()?;
                Ok(true)
            }
        }
    }

    pub fn save(&self) -> io::Result<()> {
        write(
            &self.path,
            &serde_json::to_string_pretty(&self.connections)?,
        )
    }

    pub fn pull_standard_is_empty(&self) -> bool {
        self.connections.pull.is_empty()
    }

    pub fn pull_imported_is_empty(&self) -> bool {
        self.connections.pull_imported.is_empty()
    }

    pub fn pull_is_empty(&self) -> bool {
        self.pull_standard_is_empty() & self.pull_imported_is_empty()
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
        self.connections.pull_imported.insert(connection);
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

    pub fn delete_imported_connection(&mut self, uuid: &uuid::Uuid) -> AnyhowResult<()> {
        if self.connections.pull_imported.remove(uuid) {
            println!("Deleted imported connection '{}'", uuid);
            return Ok(());
        };
        Err(anyhow!(
            "Imported pull connection with UUID {} not found",
            uuid
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
        let mut pull_imported = std::collections::HashSet::new();

        push.insert(
            site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            Connection {
                uuid: uuid::Uuid::new_v4(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        pull.insert(
            site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            Connection {
                uuid: uuid::Uuid::new_v4(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        pull_imported.insert(Connection {
            uuid: uuid::Uuid::new_v4(),
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });

        let path =
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path());
        let last_reload = mtime(&path).unwrap();
        Registry {
            connections: RegisteredConnections {
                push,
                pull,
                pull_imported,
            },
            path,
            last_reload,
        }
    }

    fn connection() -> Connection {
        Connection {
            uuid: uuid::Uuid::new_v4(),
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
        let conn = connection();
        let uuid = conn.uuid;
        reg.register_imported_connection(conn);
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 2);
        assert!(reg.connections.pull_imported.contains(&uuid));
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
        assert!(
            pull_conns[0]
                == reg
                    .connections
                    .pull
                    .get(&site_spec::Coordinates::from_str("server:8000/pull-site").unwrap())
                    .unwrap()
        );
        assert!(reg.connections.pull_imported.contains(pull_conns[1]));
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
    fn test_delete_imported_connection_ok() {
        let uuid_first_imported = uuid::Uuid::new_v4();
        let uuid_second_imported = uuid::Uuid::new_v4();
        let mut reg = registry();
        reg.connections.pull_imported.clear();
        reg.register_imported_connection(Connection {
            uuid: uuid_first_imported,
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });
        reg.register_imported_connection(Connection {
            uuid: uuid_second_imported,
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });
        assert!(reg.delete_imported_connection(&uuid_first_imported).is_ok());
        assert!(reg.connections.pull_imported.len() == 1);
        assert!(reg
            .connections
            .pull_imported
            .contains(&uuid_second_imported));
    }

    #[test]
    fn test_delete_imported_connection_err() {
        let mut reg = registry();
        let uuid = uuid::Uuid::new_v4();
        assert_eq!(
            format!("{}", reg.delete_imported_connection(&uuid).unwrap_err()),
            format!("Imported pull connection with UUID {} not found", uuid),
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
