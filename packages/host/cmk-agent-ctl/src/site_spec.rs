// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config::ClientConfig;
use super::misc::anyhow_error_to_human_readable;
use anyhow::{bail, Context, Error as AnyhowError, Result as AnyhowResult};
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

#[derive(serde::Deserialize, PartialEq, Eq, Debug, Clone)]
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
                    bail!("Failed to split into server and port at ':'");
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

#[derive(
    PartialEq, Eq, Hash, Debug, Clone, serde_with::SerializeDisplay, serde_with::DeserializeFromStr,
)]
pub struct SiteID {
    pub server: String,
    pub site: String,
}

impl FromStr for SiteID {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<SiteID> {
        let components: Vec<&str> = s.split('/').collect();
        if components.len() != 2 {
            bail!("Failed to split into server and site at '/'");
        }
        Ok(SiteID {
            server: components[0].to_owned(),
            site: components[1].to_owned(),
        })
    }
}

impl Display for SiteID {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}/{}", self.server, self.site)
    }
}

pub fn make_site_url(site_id: &SiteID, port: &u16) -> AnyhowResult<reqwest::Url> {
    reqwest::Url::parse(&format!(
        "https://{}:{}/{}",
        site_id.server, port, site_id.site
    ))
    .context(format!(
        "Failed to construct a URL from {site_id} with port {port}",
    ))
}

pub fn discover_receiver_port(site_id: &SiteID, client_config: &ClientConfig) -> AnyhowResult<u16> {
    AgentRecvPortDiscoverer {
        site_id,
        client_config,
    }
    .discover()
}

struct AgentRecvPortDiscoverer<'a> {
    site_id: &'a SiteID,
    client_config: &'a ClientConfig,
}

impl AgentRecvPortDiscoverer<'_> {
    fn url(&self, protocol: &str) -> AnyhowResult<reqwest::Url> {
        reqwest::Url::parse(&format!(
            "{}://{}/{}/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke",
            protocol, self.site_id.server, self.site_id.site,
        ))
        .context(format!(
            "Failed to construct URL for discovering agent receiver port using server {} and site {}",
            self.site_id.server, self.site_id.site,
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

        for protocol in ["https", "http"] {
            match Self::discover_with_protocol(self, &client, protocol) {
                Ok(p) => return Ok(p),
                Err(err) => {
                    info!("Failed to discover agent receiver port using {protocol}.");
                    debug!(
                        "{protocol} error: {:?}",
                        anyhow_error_to_human_readable(&err)
                    );
                }
            };
        }

        bail!("Failed to discover agent receiver port from Checkmk REST API, both with http and https. Run with verbose output to see errors.")
    }
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
mod test_site_id {
    use super::*;

    #[test]
    fn test_to_string() {
        assert_eq!(
            SiteID {
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
            SiteID::from_str("checkmk.server.com/awesome-site").unwrap(),
            SiteID {
                server: String::from("checkmk.server.com"),
                site: String::from("awesome-site"),
            }
        )
    }

    #[test]
    fn test_from_str_error() {
        for erroneous_address in [
            "checkmk.server.com",
            "checkmk.server.com:5678",
            "checkmk.server.com/awesome-site/too-much",
        ] {
            assert!(SiteID::from_str(erroneous_address).is_err())
        }
    }
}

#[cfg(test)]
mod test_agent_recv_port_discoverer {
    use super::*;

    #[test]
    fn test_url() {
        assert_eq!(
            AgentRecvPortDiscoverer {
                site_id: &SiteID {
                    server: String::from("some-server"),
                    site: String::from("some-site"),
                },
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
mod test_make_site_url {
    use super::*;

    #[test]
    fn test_make_site_url() {
        assert_eq!(
            make_site_url(
                &SiteID {
                    server: String::from("some-server"),
                    site: String::from("some-site"),
                },
                &8000,
            )
            .unwrap(),
            reqwest::Url::from_str("https://some-server:8000/some-site").unwrap()
        )
    }
}
