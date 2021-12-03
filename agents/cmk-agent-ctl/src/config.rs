// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::cli::Args;
use anyhow::Result as AnyhowResult;
use serde::Deserialize;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::{read_to_string, write};
use std::io;
use std::path::Path;

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

impl ConfigFromDisk {
    fn new() -> AnyhowResult<ConfigFromDisk> {
        Ok(serde_json::from_str("{}")?)
    }

    pub fn load(path: &Path) -> AnyhowResult<ConfigFromDisk> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }

        ConfigFromDisk::new()
    }
}

pub enum HostRegistrationData {
    Name(String),
    Labels(AgentLabels),
}

pub struct Config {
    pub agent_receiver_address: Option<String>,
    pub credentials: Option<Credentials>,
    pub root_certificate: Option<String>,
    pub host_reg_data: Option<HostRegistrationData>,
}

impl Config {
    pub fn new(config_from_disk: ConfigFromDisk, args: Args) -> Config {
        Config {
            agent_receiver_address: args.server.or(config_from_disk.agent_receiver_address),
            credentials: if let (Some(u), Some(p)) = (args.user, args.password) {
                Some(Credentials {
                    username: u,
                    password: p,
                })
            } else {
                config_from_disk.credentials
            },
            root_certificate: config_from_disk.root_certificate,
            host_reg_data: if let Some(hn) = args.host_name.or(config_from_disk.host_name) {
                Some(HostRegistrationData::Name(hn))
            } else {
                config_from_disk
                    .agent_labels
                    .map(HostRegistrationData::Labels)
            },
        }
    }
}

#[derive(Serialize, Deserialize)]
pub struct RegistrationState {
    #[serde(default)]
    pub server_specs: HashMap<String, ServerSpec>,
}

#[derive(Serialize, Deserialize)]
pub struct ServerSpec {
    pub uuid: String,
    pub private_key: String,
    pub certificate: String,
    pub root_cert: String,
}

impl RegistrationState {
    fn new() -> AnyhowResult<RegistrationState> {
        Ok(serde_json::from_str("{}")?)
    }

    pub fn from_file(path: &Path) -> AnyhowResult<RegistrationState> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }

        RegistrationState::new()
    }

    pub fn to_file(&self, path: &Path) -> io::Result<()> {
        write(path, &serde_json::to_string(self)?)
    }
}
