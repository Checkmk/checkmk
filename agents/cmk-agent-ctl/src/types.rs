// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{Context, Error as AnyhowError, Result as AnyhowResult};
use serde::Deserialize;

pub type AgentLabels = std::collections::HashMap<String, String>;

#[derive(PartialEq, std::cmp::Eq, std::hash::Hash, Debug, Clone, Deserialize)]
pub struct Port(u16);

impl std::str::FromStr for Port {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<Port> {
        Ok(Port(s.parse::<u16>().context(format!(
            "Port is not an integer in the range {} - {}",
            u16::MIN,
            u16::MAX
        ))?))
    }
}

impl std::fmt::Display for Port {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[cfg(test)]
mod test_port {
    use std::str::FromStr;

    use super::*;

    #[test]
    fn test_from_str() {
        assert_eq!(Port::from_str("8999").unwrap(), Port(8999));
        assert!(Port::from_str("kjgsdfljhg").is_err());
        assert!(Port::from_str("-10").is_err());
        assert!(Port::from_str("99999999999999999999").is_err());
    }

    #[test]
    fn test_to_string() {
        assert_eq!(Port(8999).to_string(), "8999");
    }
}

#[derive(serde::Deserialize, Clone)]
pub struct OptPwdCredentials {
    pub username: String,
    pub password: Option<String>,
}

pub struct Credentials {
    pub username: String,
    pub password: String,
}

impl std::convert::TryFrom<OptPwdCredentials> for Credentials {
    type Error = AnyhowError;

    fn try_from(opt_pwd_credentials: OptPwdCredentials) -> AnyhowResult<Self> {
        Ok(Self {
            password: match opt_pwd_credentials.password {
                Some(pwd) => pwd,
                None => Self::prompt_password(&opt_pwd_credentials.username)?,
            },
            username: opt_pwd_credentials.username,
        })
    }
}

impl Credentials {
    fn prompt_password(user: &str) -> AnyhowResult<String> {
        eprintln!();
        rpassword::prompt_password_stderr(&format!("Please enter password for '{}'\n> ", user))
            .context("Failed to obtain API password")
    }
}
