// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::cli::Args;
use serde::Deserialize;
use serde::Serialize;
use std::fs::{read_to_string, write};
use std::io::Result;
use std::path::Path;

#[derive(Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub marcv_addresses: Option<Vec<String>>,

    #[serde(default)]
    pub uuid: Option<String>,

    #[serde(default)]
    pub package_name: Option<String>,
}

impl Config {
    fn empty_config() -> Config {
        return serde_json::from_str("{}").unwrap();
    }

    pub fn from_file(path: &Path) -> Result<Config> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }
        return Ok(Config::empty_config());
    }

    pub fn merge_two_configs(loser: Config, winner: Config) -> Config {
        return Config {
            marcv_addresses: winner.marcv_addresses.or(loser.marcv_addresses),
            uuid: winner.uuid.or(loser.uuid),
            package_name: winner.package_name.or(loser.package_name),
        };
    }

    pub fn from_args(args: Args) -> Config {
        return Config {
            marcv_addresses: args.server,
            uuid: None,
            package_name: args.package_name,
        };
    }
}

#[derive(Serialize, Deserialize)]
pub struct RegistrationState {
    #[serde(default)]
    pub server_specs: Vec<ServerSpec>,
}

#[derive(Serialize, Deserialize)]
pub struct ServerSpec {
    pub marcv_address: String,
    pub uuid: String,
    pub private_key: String,
    pub client_cert: String,
}

impl RegistrationState {
    fn empty_state() -> RegistrationState {
        return serde_json::from_str("{}").unwrap();
    }

    pub fn from_file(path: &Path) -> Result<RegistrationState> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }
        return Ok(RegistrationState::empty_state());
    }

    pub fn to_file(self, path: &Path) -> Result<()> {
        return write(path, &serde_json::to_string(&self)?);
    }

    pub fn add_server_spec(&mut self, server_spec: ServerSpec) {
        self.server_specs.push(server_spec)
    }
}
