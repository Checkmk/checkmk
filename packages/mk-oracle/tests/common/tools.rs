// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{self, Result};
use mk_oracle::config::authentication::Role;

pub const ORA_ENDPOINT_ENV_VAR_LOCAL: &str = "CI_ORA1_DB_TEST";
// pub const ORA_ENDPOINT_ENV_VAR_EXT: &str = "CI_ORA2_DB_TEST";
// See ticket CMK-23904 for details on the format of this environment variable.
// CI_ORA1_DB_TEST=ora1.lan.tribe29.net:system:ABcd#1234:1521:XE:sysdba:_:_:_
#[allow(dead_code)]
#[derive(Debug)]
pub struct SqlDbEndpoint {
    pub host: String,
    pub user: String,
    pub pwd: String,
    pub port: u16,
    pub instance: String,
    pub role: Option<Role>,
}

impl SqlDbEndpoint {
    pub fn from_env(endpoint_var: &str) -> Result<Self> {
        let env_value =
            std::env::var(endpoint_var).map_err(|e| anyhow::anyhow!("{e}: {endpoint_var}"))?;
        let parts: Vec<&str> = env_value.split(':').collect();
        if parts.len() < 6 {
            anyhow::bail!("Invalid format for {}", endpoint_var);
        }
        Ok(Self {
            host: parts[0].to_string(),
            user: parts[1].to_string(),
            pwd: parts[2].to_string(),
            port: parts[3]
                .parse()
                .map_err(|_| anyhow::anyhow!("Wrong/malformed port number in {}", endpoint_var))?,
            instance: parts[4].to_string(),
            role: Role::new(parts[5]),
        })
    }
}
