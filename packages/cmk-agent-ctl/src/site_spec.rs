// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config::ClientConfig;
use super::misc::anyhow_error_to_human_readable;
use anyhow::{anyhow, bail, Context, Error as AnyhowError, Result as AnyhowResult};
use log::{debug, info};
use std::fmt::Display;
use std::net::{Ipv4Addr, SocketAddrV6};
use std::str::FromStr;

pub fn parse_port(src: &str) -> AnyhowResult<u16> {
    u16::from_str(src).context(format!(
        "Invalid port number: '{src}'. Not an integer in the range {} - {}.",
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
        if s.starts_with('[') && s.ends_with(']') {
            // we validate with std::net::SocketAddrV6 because std::net::Ipv6Addr::from_str does not accept square brackets
            let spec_with_port_to_be_ignored = Self::from_raw_ipv6_socket_addr(&format!("{s}:0"))
                .map_err(|err| match err {
                IPv6ParsingError::Invalid => anyhow!("'{s}' is not a valid IPv6 address"),
                IPv6ParsingError::ScopeIdentifierSpecified => {
                    anyhow!("IPv6 scope identifiers are currently unsupported")
                }
            })?;
            return Ok(Self {
                server: spec_with_port_to_be_ignored.server,
                port: None,
            });
        }
        if s.starts_with('[') {
            return Self::from_raw_ipv6_socket_addr(s).map_err(|err| match err {
                IPv6ParsingError::Invalid => anyhow!("'{s}' is not a valid IPv6 address with port"),
                IPv6ParsingError::ScopeIdentifierSpecified => {
                    anyhow!("IPv6 scope identifiers are currently unsupported")
                }
            });
        }

        Ok(match s.rsplit_once(':') {
            None => Self {
                server: Self::validate_ipv4_or_hostname(s)?.into(),
                port: None,
            },
            Some((left_of_last_colon, right_of_last_colon)) => Self {
                server: Self::validate_ipv4_or_hostname(left_of_last_colon)?.into(),
                port: Some(parse_port(right_of_last_colon)?),
            },
        })
    }
}

impl ServerSpec {
    fn from_raw_ipv6_socket_addr(raw: &str) -> Result<Self, IPv6ParsingError> {
        let socket_addr_v6 = SocketAddrV6::from_str(raw).map_err(|_| IPv6ParsingError::Invalid)?;
        if raw.contains('%') {
            return Err(IPv6ParsingError::ScopeIdentifierSpecified);
        }
        Ok(Self {
            // we need to keep the square brackets because we want to construct URLs from this
            server: format!("[{}]", socket_addr_v6.ip()),
            port: Some(socket_addr_v6.port()),
        })
    }

    fn validate_ipv4_or_hostname(s: &str) -> AnyhowResult<&str> {
        if Ipv4Addr::from_str(s).is_ok() || hostname_validator::is_valid(s) {
            return Ok(s);
        }
        Err(anyhow!("'{s}' is not a valid IPv4 adress or hostname."))
    }
}

enum IPv6ParsingError {
    Invalid,
    ScopeIdentifierSpecified,
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

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Protocol {
    Https,
    Http,
}

impl Protocol {
    pub fn as_str(&self) -> &'static str {
        match self {
            Protocol::Https => "https",
            Protocol::Http => "http",
        }
    }

    pub fn all() -> [Protocol; 2] {
        [Protocol::Https, Protocol::Http]
    }
}

impl Display for Protocol {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for Protocol {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<Self> {
        match s.to_lowercase().as_str() {
            "https" => Ok(Protocol::Https),
            "http" => Ok(Protocol::Http),
            _ => bail!("Invalid protocol: {}. Must be 'http' or 'https'", s),
        }
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

trait ApiDiscoverer {
    fn site_id(&self) -> &SiteID;
    fn client_config(&self) -> &ClientConfig;
    fn api_endpoint(&self) -> &str;

    fn url(&self, protocol: Protocol) -> AnyhowResult<reqwest::Url> {
        reqwest::Url::parse(&format!(
            "{}://{}/{}{}",
            protocol.as_str(),
            self.site_id().server,
            self.site_id().site,
            self.api_endpoint()
        ))
        .context(format!(
            "Failed to construct URL for {} using server {} and site {}",
            self.api_endpoint(),
            self.site_id().server,
            self.site_id().site,
        ))
    }

    fn build_client(&self) -> reqwest::Result<reqwest::blocking::Client> {
        let mut client_builder = reqwest::blocking::ClientBuilder::new()
            .danger_accept_invalid_certs(!self.client_config().validate_api_cert);
        if !self.client_config().use_proxy {
            client_builder = client_builder.no_proxy();
        }
        client_builder.build()
    }
}

impl ApiDiscoverer for AgentRecvPortDiscoverer<'_> {
    fn site_id(&self) -> &SiteID {
        self.site_id
    }

    fn client_config(&self) -> &ClientConfig {
        self.client_config
    }

    fn api_endpoint(&self) -> &str {
        "/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke"
    }
}

impl AgentRecvPortDiscoverer<'_> {
    fn discover_with_protocol(
        &self,
        client: &reqwest::blocking::Client,
        protocol: Protocol,
    ) -> AnyhowResult<u16> {
        let url = self.url(protocol)?;
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

    pub fn discover(&self) -> AnyhowResult<u16> {
        let client = self.build_client()?;

        for protocol in Protocol::all() {
            match self.discover_with_protocol(&client, protocol) {
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

        bail!(
            "Failed to discover agent receiver port from Checkmk REST API, both with http and https. Run with verbose output to see errors."
        )
    }
}

pub fn discover_protocol(site_id: &SiteID, client_config: &ClientConfig) -> AnyhowResult<Protocol> {
    ProtocolDiscoverer {
        site_id,
        client_config,
    }
    .discover()
}

struct ProtocolDiscoverer<'a> {
    site_id: &'a SiteID,
    client_config: &'a ClientConfig,
}

impl ApiDiscoverer for ProtocolDiscoverer<'_> {
    fn site_id(&self) -> &SiteID {
        self.site_id
    }

    fn client_config(&self) -> &ClientConfig {
        self.client_config
    }

    fn api_endpoint(&self) -> &str {
        "/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke"
    }
}

impl ProtocolDiscoverer<'_> {
    fn test_protocol(
        &self,
        client: &reqwest::blocking::Client,
        protocol: Protocol,
    ) -> AnyhowResult<()> {
        let url = self.url(protocol)?;
        let error_msg = format!("Failed to test protocol {} with {}", protocol, &url);

        client
            .get(url)
            .send()
            .context(error_msg.clone())?
            .error_for_status()
            .context(error_msg)?;

        Ok(())
    }

    pub fn discover(&self) -> AnyhowResult<Protocol> {
        let client = self.build_client()?;

        for protocol in Protocol::all() {
            match self.test_protocol(&client, protocol) {
                Ok(()) => {
                    info!("Successfully discovered protocol: {}", protocol);
                    return Ok(protocol);
                }
                Err(err) => {
                    info!("Failed to connect using {}.", protocol);
                    debug!(
                        "{} error: {:?}",
                        protocol,
                        anyhow_error_to_human_readable(&err)
                    );
                }
            }
        }

        bail!(
            "Failed to discover working protocol for Checkmk site, tried both https and http. Run with verbose output to see errors."
        )
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
    fn test_from_str_valid_ipv4_without_port() {
        assert_eq!(
            ServerSpec::from_str("1.2.3.4").unwrap(),
            ServerSpec {
                server: "1.2.3.4".into(),
                port: None,
            }
        )
    }

    #[test]
    fn test_from_str_invalid_ipv4_without_port() {
        assert!(ServerSpec::from_str("127.0.0.1^")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv4 adress or hostname"))
    }

    #[test]
    fn test_from_str_valid_ipv4_with_valid_port() {
        assert_eq!(
            ServerSpec::from_str("1.2.3.4:40").unwrap(),
            ServerSpec {
                server: "1.2.3.4".into(),
                port: Some(40),
            }
        )
    }

    #[test]
    fn test_from_str_invalid_ipv4_with_valid_port() {
        assert!(ServerSpec::from_str("127.0.0.1^:4000")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv4 adress or hostname"))
    }

    #[test]
    fn test_from_str_valid_ipv4_with_invalid_port() {
        assert!(ServerSpec::from_str("127.0.0.1:a")
            .unwrap_err()
            .to_string()
            .contains("Invalid port number"))
    }

    #[test]
    fn test_from_str_invalid_ipv4_with_invalid_port() {
        assert!(ServerSpec::from_str("127.0.0.1^:a")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv4 adress or hostname"))
    }

    #[test]
    fn test_from_str_valid_hostname_without_port() {
        assert_eq!(
            ServerSpec::from_str("host").unwrap(),
            ServerSpec {
                server: "host".into(),
                port: None,
            }
        )
    }

    #[test]
    fn test_from_str_valid_fqdn_without_port() {
        assert_eq!(
            ServerSpec::from_str("checkmk.server.com").unwrap(),
            ServerSpec {
                server: "checkmk.server.com".into(),
                port: None,
            }
        )
    }

    #[test]
    fn test_from_str_invalid_hostname_without_port() {
        assert!(ServerSpec::from_str("-host")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv4 adress or hostname"))
    }

    #[test]
    fn test_from_str_valid_hostname_with_valid_port() {
        assert_eq!(
            ServerSpec::from_str("host:40").unwrap(),
            ServerSpec {
                server: "host".into(),
                port: Some(40),
            }
        )
    }

    #[test]
    fn test_from_str_valid_fqdn_with_valid_port() {
        assert_eq!(
            ServerSpec::from_str("checkmk.server.com:5678").unwrap(),
            ServerSpec {
                server: "checkmk.server.com".into(),
                port: Some(5678),
            }
        )
    }

    #[test]
    fn test_from_str_invalid_hostname_with_valid_port() {
        assert!(ServerSpec::from_str("-host:4000")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv4 adress or hostname"))
    }

    #[test]
    fn test_from_str_valid_hostname_with_invalid_port() {
        assert!(ServerSpec::from_str("host:a")
            .unwrap_err()
            .to_string()
            .contains("Invalid port number"))
    }

    #[test]
    fn test_from_str_invalid_hostname_with_invalid_port() {
        assert!(ServerSpec::from_str("-host:a")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv4 adress or hostname"))
    }

    #[test]
    fn test_from_str_valid_ipv6_without_port() {
        assert_eq!(
            ServerSpec::from_str("[3a02:87b0:504::2]").unwrap(),
            ServerSpec {
                server: "[3a02:87b0:504::2]".into(),
                port: None,
            }
        )
    }

    #[test]
    fn test_from_str_invalid_ipv6_without_port() {
        assert!(ServerSpec::from_str("[3a02:8!b0:504::2]")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv6 address"))
    }

    #[test]
    fn test_from_str_valid_ipv6_without_port_and_scope_id() {
        assert!(ServerSpec::from_str("[3a02:87b0:504::2%7]")
            .unwrap_err()
            .to_string()
            .contains("IPv6 scope identifiers are currently unsupported"))
    }

    #[test]
    fn test_from_str_valid_ipv6_with_valid_port() {
        assert_eq!(
            ServerSpec::from_str("[3a02:87b0:504::2]:19").unwrap(),
            ServerSpec {
                server: "[3a02:87b0:504::2]".into(),
                port: Some(19)
            }
        )
    }

    #[test]
    fn test_from_str_invalid_ipv6_with_valid_port() {
        assert!(ServerSpec::from_str("[3a02:8!b0:504::2]:19")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv6 address with port"))
    }

    #[test]
    fn test_from_str_valid_ipv6_with_invalid_port() {
        assert!(ServerSpec::from_str("[3a02:87b0:504::2]:a")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv6 address with port"))
    }

    #[test]
    fn test_from_str_invalid_ipv6_with_invalid_port() {
        assert!(ServerSpec::from_str("[3a02:8!b0:504::2]:a")
            .unwrap_err()
            .to_string()
            .contains("not a valid IPv6 address with port"))
    }

    #[test]
    fn test_from_str_valid_ipv6_with_port_and_scope_id() {
        assert!(ServerSpec::from_str("[3a02:87b0:504::2%7]:123")
            .unwrap_err()
            .to_string()
            .contains("IPv6 scope identifiers are currently unsupported"))
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
            .url(Protocol::Http)
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

#[cfg(test)]
mod test_protocol_discoverer {
    use super::*;

    #[test]
    fn test_url() {
        assert_eq!(
            ProtocolDiscoverer {
                site_id: &SiteID {
                    server: String::from("some-server"),
                    site: String::from("some-site"),
                },
                client_config: &ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
            }
            .url(Protocol::Https)
            .unwrap()
            .to_string(),
            "https://some-server/some-site/check_mk/api/1.0/domain-types/internal/actions/discover-receiver/invoke",
        )
    }
}
