// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::types;
use anyhow::{anyhow, Context, Error as AnyhowError, Result as AnyhowResult};
use std::fmt::Display;
use std::str::FromStr;

#[derive(
    PartialEq,
    std::cmp::Eq,
    std::hash::Hash,
    Debug,
    Clone,
    serde_with::SerializeDisplay,
    serde_with::DeserializeFromStr,
)]
pub struct Coordinates {
    pub server: String,
    pub port: types::Port,
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
            port: server_components[1].parse::<types::Port>()?,
            site: String::from(outer_components[1]),
        })
    }
}

impl Display for Coordinates {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}/{}", self.server, self.port, self.site)
    }
}

impl std::convert::TryFrom<IncompleteCoordinates> for Coordinates {
    type Error = AnyhowError;

    fn try_from(incomplete_coordinates: IncompleteCoordinates) -> AnyhowResult<Self> {
        Ok(Coordinates {
            port: Coordinates::port_from_checkmk_rest_api(&incomplete_coordinates)
                .context("Failed to query agent receiver port from Checkmk REST API")?,
            server: incomplete_coordinates.server,
            site: incomplete_coordinates.site,
        })
    }
}

impl Coordinates {
    pub fn to_url(&self) -> AnyhowResult<reqwest::Url> {
        reqwest::Url::parse(&format!(
            "https://{}:{}/{}",
            &self.server, &self.port, &self.site
        ))
        .context(format!("Failed to convert {} into a URL", &self))
    }

    fn port_from_checkmk_rest_api(
        incomplete_coordinates: &IncompleteCoordinates,
    ) -> AnyhowResult<types::Port> {
        let url = format!(
            "http://{}/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke",
            incomplete_coordinates,
        );
        let error_msg = format!("Failed to discover agent receiver port from {}", url);
        reqwest::blocking::get(&url)
            .context(error_msg.clone())?
            .text()
            .context(error_msg.clone())?
            .parse::<types::Port>()
            .context(error_msg)
    }
}

#[derive(PartialEq, Debug, serde::Deserialize)]
pub struct IncompleteCoordinates {
    server: String,
    site: String,
}

impl FromStr for IncompleteCoordinates {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<Self> {
        let components: Vec<&str> = s.split('/').collect();
        if components.len() != 2 {
            return Err(anyhow!("Failed to split into server and site at '/'"));
        }
        Ok(IncompleteCoordinates {
            server: String::from(components[0]),
            site: String::from(components[1]),
        })
    }
}

impl Display for IncompleteCoordinates {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}/{}", self.server, self.site)
    }
}

#[derive(PartialEq, Debug, serde::Deserialize)]
#[serde(untagged)]
pub enum SiteSpec {
    Incomplete(IncompleteCoordinates),
    Complete(Coordinates),
}

impl FromStr for SiteSpec {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<SiteSpec> {
        if s.contains(':') {
            return Ok(SiteSpec::Complete(Coordinates::from_str(s)?));
        }
        Ok(SiteSpec::Incomplete(IncompleteCoordinates::from_str(s)?))
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
                port: types::Port::from_str("8002").unwrap(),
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
                port: types::Port::from_str("5678").unwrap(),
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

    #[test]
    fn test_to_url() {
        assert_eq!(
            &Coordinates::from_str("my.server.something:7893/cool-site")
                .unwrap()
                .to_url()
                .unwrap()
                .to_string(),
            "https://my.server.something:7893/cool-site"
        )
    }
}

#[cfg(test)]
mod test_incomplete_coordinates {
    use super::*;

    #[test]
    fn test_to_string() {
        assert_eq!(
            IncompleteCoordinates {
                server: String::from("my-server"),
                site: String::from("my-site"),
            }
            .to_string(),
            "my-server/my-site"
        )
    }

    #[test]
    fn test_from_str_ok() {
        assert_eq!(
            IncompleteCoordinates::from_str("checkmk.server.com/awesome-site").unwrap(),
            IncompleteCoordinates {
                server: String::from("checkmk.server.com"),
                site: String::from("awesome-site"),
            }
        )
    }

    #[test]
    fn test_from_str_error() {
        for erroneous_address in ["checkmk.server.com", "checkmk.server.com/a/b"] {
            assert!(IncompleteCoordinates::from_str(erroneous_address).is_err())
        }
    }
}

#[cfg(test)]
mod test_site_spec {
    use super::*;

    #[test]
    fn test_from_str_complete() {
        assert_eq!(
            SiteSpec::from_str("server:8000/site").unwrap(),
            SiteSpec::Complete(Coordinates {
                server: String::from("server"),
                port: types::Port::from_str("8000").unwrap(),
                site: String::from("site"),
            })
        )
    }

    #[test]
    fn test_from_str_incomplete() {
        assert_eq!(
            SiteSpec::from_str("server/site").unwrap(),
            SiteSpec::Incomplete(IncompleteCoordinates {
                server: String::from("server"),
                site: String::from("site"),
            })
        )
    }
}
