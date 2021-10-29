// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::cli::Args;
use super::uuid::make as make_uuid;
use serde::Deserialize;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::{read_to_string, write};
use std::io;
use std::path::Path;

#[derive(Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub marcv_addresses: Option<Vec<String>>,

    #[serde(default)]
    pub uuid: Option<String>,

    #[serde(default)]
    pub package_name: Option<String>,

    #[serde(default)]
    pub root_certificate: Option<String>,
}

impl Config {
    fn empty_config() -> Config {
        return serde_json::from_str("{}").unwrap();
    }

    pub fn from_file(path: &Path) -> io::Result<Config> {
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
            root_certificate: winner.root_certificate.or(loser.root_certificate),
        };
    }

    pub fn from_args(args: Args) -> Config {
        return Config {
            marcv_addresses: args.server,
            uuid: None,
            package_name: args.package_name,
            root_certificate: None,
        };
    }
}

#[derive(Serialize, Deserialize)]
pub struct RegistrationState {
    #[serde(default = "make_uuid")]
    pub uuid: String,
    #[serde(default)]
    pub server_specs: HashMap<String, ServerSpec>,
}

#[derive(Serialize, Deserialize)]
pub struct ServerSpec {
    pub client_chain: String,
    pub root_cert: String,
}

impl RegistrationState {
    fn empty_state() -> RegistrationState {
        return serde_json::from_str("{}").unwrap();
    }

    pub fn from_file(path: &Path) -> io::Result<RegistrationState> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }
        return Ok(RegistrationState::empty_state());
    }

    pub fn to_file(self, path: &Path) -> io::Result<()> {
        write(path, &serde_json::to_string(&self)?)
    }
}
