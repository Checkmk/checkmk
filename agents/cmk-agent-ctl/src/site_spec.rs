// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Context, Error as AnyhowError, Result as AnyhowResult};
use std::fmt::Display;
use std::str::FromStr;

#[derive(PartialEq, Debug, serde::Deserialize)]
pub struct Coordinates {
    pub server: String,
    pub port: usize,
    pub site: String,
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
            port: server_components[1]
                .parse::<usize>()
                .context("Port is not a non-negative integer")?,
            site: String::from(outer_components[1]),
        })
    }
}

impl Display for Coordinates {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}/{}", self.server, self.port, self.site)
    }
}

#[cfg(test)]
mod test_coordinates {
    use super::*;

    #[test]
    fn test_to_string() {
        assert_eq!(
            Coordinates {
                server: String::from("my-server"),
                port: 8002,
                site: String::from("my-site"),
            }
            .to_string(),
            "my-server:8002/my-site"
        )
    }

    #[test]
    fn test_from_str_ok() {
        assert_eq!(
            Coordinates::from_str("checkmk.server.com:5678/awesome-site").unwrap(),
            Coordinates {
                server: String::from("checkmk.server.com"),
                port: 5678,
                site: String::from("awesome-site"),
            }
        )
    }

    #[test]
    fn test_from_str_error() {
        for erroneous_address in [
            "checkmk.server.com",
            "checkmk.server.com:5678",
            "checkmk.server.com:5678:site",
            "checkmk.server.com/5678:site",
            "5678:site",
            "checkmk.server.com:5678/awesome-site/too-much",
        ] {
            assert!(Coordinates::from_str(erroneous_address).is_err())
        }
    }
}
