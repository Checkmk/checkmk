// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config::ClientConfig;
use super::misc::anyhow_error_to_human_readable;
use anyhow::{anyhow, Context, Error as AnyhowError, Result as AnyhowResult};
use log::{debug, info};
use std::fmt::Display;
use std::str::FromStr;

pub fn parse_port(src: &str) -> AnyhowResult<u16> {
    u16::from_str(src).context(format!(
        "Port is not an integer in the range {} - {}",
        u16::MIN,
        u16::MAX
    ))
}

#[derive(serde::Deserialize, PartialEq, Debug)]
pub struct ServerSpec {
    pub server: String,

    #[serde(default)]
    pub port: Option<u16>,
}

impl FromStr for ServerSpec {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<Self> {
        match s.contains(':') {
            true => {
                let components: Vec<&str> = s.split(':').collect();
                if components.len() != 2 {
                    return Err(anyhow!("Failed to split into server and port at ':'"));
                }
                Ok(Self {
                    server: String::from(components[0]),
                    port: Some(parse_port(components[1])?),
                })
            }
            false => Ok(Self {
                server: String::from(s),
                port: None,
            }),
        }
    }
}

#[derive(serde::Deserialize)]
pub struct PresetSiteSpec {
    #[serde(flatten)]
    pub server_spec: ServerSpec,

    pub site: String,
}

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
    pub port: u16,
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
            port: server_components[1].parse::<u16>()?,
            site: String::from(outer_components[1]),
        })
    }
}

impl Display for Coordinates {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}/{}", self.server, self.port, self.site)
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
}

struct AgentRecvPortDiscoverer<'a> {
    server: &'a str,
    site: &'a str,
    client_config: &'a ClientConfig,
}

impl<'a> AgentRecvPortDiscoverer<'a> {
    fn url(&self, protocol: &str) -> AnyhowResult<reqwest::Url> {
        reqwest::Url::parse(&format!(
            "{}://{}/{}/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke",
            protocol, self.server, self.site,
        ))
        .context(format!(
            "Failed to construct URL for discovering agent receiver port using server {} and site {}",
            self.server, self.site,
        ))
    }

    fn discover_with_protocol(
        &self,
        client: &reqwest::blocking::Client,
        protocol: &str,
    ) -> AnyhowResult<u16> {
        let url = Self::url(self, protocol)?;
        let error_msg = format!("Failed to discover agent receiver port from {}", &url);
        client
            .get(url)
            .send()
            .context(error_msg.clone())?
            .text()
            .context(error_msg.clone())?
            .parse::<u16>()
            .context(error_msg)
    }

    fn build_client(&self) -> reqwest::Result<reqwest::blocking::Client> {
        let mut client_builder = reqwest::blocking::ClientBuilder::new()
            .danger_accept_invalid_certs(!self.client_config.validate_api_cert);
        if !self.client_config.use_proxy {
            client_builder = client_builder.no_proxy();
        }
        client_builder.build()
    }

    pub fn discover(&self) -> AnyhowResult<u16> {
        let client = self.build_client()?;

        match Self::discover_with_protocol(self, &client, "https") {
            Ok(p) => return Ok(p),
            Err(err) => {
                info!("Failed to discover agent receiver port using https, trying http.");
                debug!("https error {:?}", anyhow_error_to_human_readable(&err));
            }
        };

        match Self::discover_with_protocol(self, &client, "http") {
            Ok(p) => return Ok(p),
            Err(err) => {
                info!("Failed to discover agent receiver port using http.");
                debug!("http error {:?}", anyhow_error_to_human_readable(&err));
            }
        };

        Err(anyhow!("Failed to discover agent receiver port from Checkmk REST API, both with http and https. Run with verbose output to see errors."))
    }
}

pub fn make_coordinates(
    server: &str,
    port: Option<u16>,
    site: &str,
    client_config: &ClientConfig,
) -> AnyhowResult<Coordinates> {
    Ok(Coordinates {
        server: String::from(server),
        port: match port {
            Some(p) => p,
            None => AgentRecvPortDiscoverer {
                server,
                site,
                client_config,
            }
            .discover()?,
        },
        site: String::from(site),
    })
}

#[cfg(test)]
mod test_parse_port {
    use super::*;

    #[test]
    fn test() {
        assert_eq!(parse_port("8999").unwrap(), 8999);
        assert!(parse_port("kjgsdfljhg").is_err());
        assert!(parse_port("-10").is_err());
        assert!(parse_port("99999999999999999999").is_err());
    }
}

#[cfg(test)]
mod test_server_spec {
    use super::*;

    #[test]
    fn test_from_str_with_port() {
        assert_eq!(
            ServerSpec::from_str("server:8000").unwrap(),
            ServerSpec {
                server: String::from("server"),
                port: Some(u16::from_str("8000").unwrap()),
            }
        )
    }

    #[test]
    fn test_from_str_without_port() {
        assert_eq!(
            ServerSpec::from_str("server.123").unwrap(),
            ServerSpec {
                server: String::from("server.123"),
                port: None,
            }
        )
    }

    #[test]
    fn test_from_str_error() {
        assert!(ServerSpec::from_str("checkmk.server.com:5678:123").is_err())
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
                port: u16::from_str("8002").unwrap(),
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
                port: u16::from_str("5678").unwrap(),
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
mod test_agent_recv_port_discoverer {
    use super::*;

    #[test]
    fn test_url() {
        assert_eq!(
            AgentRecvPortDiscoverer {
                server: "some-server",
                site: "some-site",
                client_config: &ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
            }
            .url("http")
            .unwrap()
            .to_string(),
            "http://some-server/some-site/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke",
        )
    }
}

#[cfg(test)]
mod test_make_coordinates {
    use super::*;

    #[test]
    fn test_with_port() {
        assert_eq!(
            make_coordinates(
                "some-server",
                Some(8000),
                "some-site",
                &ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                }
            )
            .unwrap(),
            Coordinates {
                server: String::from("some-server"),
                port: 8000,
                site: String::from("some-site")
            }
        )
    }
}
