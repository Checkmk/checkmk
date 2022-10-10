// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config;
use anyhow::{anyhow, Error as AnyhowError, Result as AnyhowResult};
use serde::Deserialize;
use serde_with::DisplayFromStr;
use std::collections::{HashMap, HashSet};
use std::hash::Hash;
use std::str::FromStr;

#[derive(Deserialize, Default)]
#[allow(dead_code)]
struct RegisteredConnections {
    #[serde(default)]
    push: HashMap<Coordinates, Connection>,

    #[serde(default)]
    pull: HashMap<Coordinates, Connection>,

    #[serde(default)]
    pull_imported: HashSet<Connection>,
}

impl config::JSONLoader for RegisteredConnections {}

#[derive(PartialEq, Eq, Hash, serde_with::DeserializeFromStr)]
struct Coordinates {
    server: String,
    port: u16,
    site: String,
}

impl FromStr for Coordinates {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<Coordinates> {
        let outer_components: Vec<&str> = s.split('/').collect();
        if outer_components.len() != 2 {
            return Err(anyhow!(
                "Failed to split into server address and site at '/'"
            ));
        }
        let server_components: Vec<&str> = outer_components[0].split(':').collect();
        if server_components.len() != 2 {
            return Err(anyhow!("Failed to split into server and port at ':'"));
        }
        Ok(Coordinates {
            server: String::from(server_components[0]),
            port: server_components[1].parse::<u16>()?,
            site: String::from(outer_components[1]),
        })
    }
}

#[serde_with::serde_as]
#[derive(Deserialize)]
#[allow(dead_code)]
struct Connection {
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    private_key: String,
    certificate: String,
    root_cert: String,
}

impl PartialEq for Connection {
    fn eq(&self, other: &Self) -> bool {
        self.uuid == other.uuid
    }
}

impl Eq for Connection {}

impl Hash for Connection {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.uuid.hash(state);
    }
}
