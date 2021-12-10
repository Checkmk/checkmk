// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::cli;
use anyhow::{Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::{read_to_string, write};
use std::io;
use std::path::{Path, PathBuf};
use string_enum::StringEnum;

#[derive(StringEnum)]
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

#[derive(Serialize, Deserialize)]
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

#[derive(Serialize, Deserialize)]
pub struct RegisteredConnections {
    #[serde(default)]
    pub push: HashMap<String, Connection>,

    #[serde(default)]
    pub pull: HashMap<String, Connection>,

    #[serde(default)]
    pub pull_imported: Vec<Connection>,
}

impl JSONLoader for RegisteredConnections {}
pub struct Registration {
    pub connections: RegisteredConnections,
    pub path: PathBuf,
}

impl Registration {
    pub fn from_file(path: &Path) -> AnyhowResult<Registration> {
        Ok(Registration {
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
        address: String,
        connection: Connection,
    ) -> AnyhowResult<()> {
        let (insert_connections, remove_connections) = match connection_type {
            ConnectionType::Push => (&mut self.connections.push, &mut self.connections.pull),
            ConnectionType::Pull => (&mut self.connections.pull, &mut self.connections.push),
        };
        remove_connections.remove(&address);
        insert_connections.insert(address, connection);
        Ok(())
    }
}
