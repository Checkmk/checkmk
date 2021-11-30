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

#[derive(Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub agent_receiver_address: Option<String>,

    #[serde(default)]
    pub package_name: Option<String>,

    #[serde(default)]
    pub credentials: Option<String>,

    #[serde(default)]
    pub root_certificate: Option<String>,

    #[serde(default)]
    pub host_name: Option<String>,
}

impl Config {
    fn empty_config() -> AnyhowResult<Config> {
        Ok(serde_json::from_str("{}")?)
    }

    pub fn from_file(path: &Path) -> AnyhowResult<Config> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }

        Config::empty_config()
    }

    pub fn merge_two_configs(loser: Config, winner: Config) -> Config {
        Config {
            agent_receiver_address: winner
                .agent_receiver_address
                .or(loser.agent_receiver_address),
            package_name: winner.package_name.or(loser.package_name),
            credentials: winner.credentials.or(loser.credentials),
            root_certificate: winner.root_certificate.or(loser.root_certificate),
            host_name: winner.host_name.or(loser.host_name),
        }
    }

    pub fn from_args(args: Args) -> Config {
        return Config {
            agent_receiver_address: args.server,
            package_name: args.package_name,
            credentials: if let (Some(u), Some(p)) = (args.user, args.password) {
                Some(format!("{} {}", &u, &p))
            } else {
                None
            },
            root_certificate: None,
            host_name: args.host_name,
        };
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
    fn empty_state() -> AnyhowResult<RegistrationState> {
        Ok(serde_json::from_str("{}")?)
    }

    pub fn from_file(path: &Path) -> AnyhowResult<RegistrationState> {
        if path.exists() {
            return Ok(serde_json::from_str(&read_to_string(path)?)?);
        }

        RegistrationState::empty_state()
    }

    pub fn to_file(&self, path: &Path) -> io::Result<()> {
        write(path, &serde_json::to_string(self)?)
    }
}
