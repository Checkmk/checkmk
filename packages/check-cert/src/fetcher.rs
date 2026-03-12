// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Context, Result};
use log::{debug, info};
use openssl::base64::encode_block;
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
use std::env;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::time::Duration;
use typed_builder::TypedBuilder;

use crate::starttls;

#[derive(Debug, Clone, clap::ValueEnum)]
pub enum ConnectionType {
    #[value(name = "tls")]
    Tls,
    #[value(name = "smtp_starttls")]
    SmtpStarttls,
    #[value(name = "postgres_starttls")]
    PostgresStarttls,
    #[value(name = "imap_starttls")]
    ImapStarttls,
    #[value(name = "ldap_starttls")]
    LdapStarttls,
}

#[derive(Debug, Clone, TypedBuilder)]
pub struct ProxyAuth {
    username: String,
    password: String,
}

#[derive(Debug, Clone, TypedBuilder)]
pub struct ProxyConfig {
    url: String,
    port: u16,
    auth: Option<ProxyAuth>,
}

impl ProxyConfig {
    pub fn to_addr(&self) -> Result<SocketAddr> {
        to_addr(&self.url, self.port)
    }
}

#[derive(Debug, TypedBuilder)]
pub struct Config {
    timeout: Option<Duration>,
    connection_type: ConnectionType,
    proxy: Option<ProxyConfig>,
}

fn to_addr(server: &str, port: u16) -> Result<SocketAddr> {
    let mut addr_iter = format!("{server}:{port}").to_socket_addrs()?;
    addr_iter.next().ok_or(anyhow!("no address"))
}

fn strip_url_protocol(url: &str) -> &str {
    url.find("://").map(|pos| &url[pos + 3..]).unwrap_or(url)
}

pub fn fetch_server_cert(server: &str, port: u16, config: Config) -> Result<Vec<Vec<u8>>> {
    let addr = config
        .proxy
        .clone()
        .map_or(to_addr(server, port), |proxy| {
            to_addr(strip_url_protocol(&proxy.url), proxy.port)
        })?;
    let mut stream = match config.timeout {
        None => {
            debug!("Connecting to {}:{}", server, port);
            TcpStream::connect(addr)?
        }
        Some(dur) => {
            debug!("Connecting to {}:{} with timeout {:?}", server, port, dur);
            TcpStream::connect_timeout(&addr, dur)?
        }
    };
    debug!("TCP connection established");
    stream.set_read_timeout(config.timeout)?;
    if config.proxy.is_some() {
        info!("Setting up proxy connection...");
        build_proxy_stream(&mut stream, config.proxy.unwrap().auth, server, port)?;
    };
    stream.set_read_timeout(config.timeout)?;

    match config.connection_type {
        ConnectionType::Tls => debug!("Using TLS connection"),
        ConnectionType::SmtpStarttls => starttls::smtp::perform(&mut stream, server)?,
        ConnectionType::PostgresStarttls => starttls::postgres::perform(&mut stream)?,
        ConnectionType::ImapStarttls => starttls::imap::perform(&mut stream)?,
        ConnectionType::LdapStarttls => starttls::ldap::perform(&mut stream)?,
    };

    let mut connector_builder = SslConnector::builder(SslMethod::tls())?;
    connector_builder.set_verify(SslVerifyMode::NONE);
    let connector = connector_builder.build();
    connector
        .configure()
        .context("Cannot configure connection")?;
    let mut stream = connector.connect(server, stream)?;

    // Send EHLO again for SMTP STARTTLS to comply with RFC 3207
    if let ConnectionType::SmtpStarttls = config.connection_type {
        debug!("Sending EHLO after TLS connection...");
        starttls::smtp::send_ehlo(&mut stream, server)?;
    }

    let chain = stream
        .ssl()
        .peer_cert_chain()
        .context("Failed fetching peer cert chain")?
        .iter()
        .flat_map(|x509| x509.to_der())
        .collect::<Vec<_>>();
    stream.shutdown()?;
    Ok(chain)
}

fn build_proxy_stream<T: Read + Write>(
    stream: &mut T,
    proxy_auth: Option<ProxyAuth>,
    server: &str,
    port: u16,
) -> Result<()> {
    let mut connect_req = format!("CONNECT {server}:{port} HTTP/1.1\r\nHost: {server}:{port}\r\n");
    if let Some(ProxyAuth { username, password }) = proxy_auth {
        let auth = encode_block(format!("{username}:{password}").as_bytes());
        connect_req.push_str(&format!("Proxy-Authorization: Basic {auth}\r\n"));
    }
    connect_req.push_str("\r\n");
    stream.write_all(connect_req.as_bytes())?;
    stream.flush()?;

    let mut reader = BufReader::new(stream);
    let mut status_line = String::new();
    reader.read_line(&mut status_line)?;
    if !status_line.starts_with("HTTP/1.1 200") {
        return Err(anyhow!("Proxy CONNECT failed: {status_line}"));
    }
    // Drain remaining response headers until the blank line
    loop {
        let mut line = String::new();
        reader.read_line(&mut line)?;
        if line == "\r\n" || line == "\n" || line.is_empty() {
            break;
        }
    }
    Ok(())
}

pub fn proxy_from_env(hostname: &str) -> Option<ProxyConfig> {
    // Respect no_proxy / NO_PROXY before looking up a proxy
    if let Ok(no_proxy) = env::var("no_proxy").or_else(|_| env::var("NO_PROXY")) {
        if matches_no_proxy(hostname, &no_proxy) {
            return None;
        }
    }

    // Prefer https_proxy for TLS connections, fall back to http_proxy
    let proxy_url = env::var("https_proxy")
        .or_else(|_| env::var("HTTPS_PROXY"))
        .or_else(|_| env::var("http_proxy"))
        .or_else(|_| env::var("HTTP_PROXY"))
        .ok()?;

    if proxy_url.is_empty() {
        return None;
    }

    let result = parse_proxy_env_var(&proxy_url);
    if result.is_none() {
        log::warn!("Could not parse proxy URL from environment: {proxy_url:?}");
    }
    result
}

fn matches_no_proxy(hostname: &str, no_proxy: &str) -> bool {
    let hostname_lower = hostname.to_lowercase();
    for pattern in no_proxy.split(',') {
        let pattern = pattern.trim();
        if pattern.is_empty() {
            continue;
        }
        if pattern == "*" {
            return true;
        }
        let pattern_lower = pattern.trim_start_matches('.').to_lowercase();
        if hostname_lower == pattern_lower || hostname_lower.ends_with(&format!(".{pattern_lower}"))
        {
            return true;
        }
    }
    false
}

fn parse_proxy_env_var(proxy_url: &str) -> Option<ProxyConfig> {
    // Strip scheme (http://, https://, etc.)
    let without_scheme = proxy_url
        .find("://")
        .map(|pos| &proxy_url[pos + 3..])
        .unwrap_or(proxy_url);

    // Split auth from host:port at the last '@'
    let (auth_opt, hostport) = if let Some(at_pos) = without_scheme.rfind('@') {
        (
            Some(&without_scheme[..at_pos]),
            &without_scheme[at_pos + 1..],
        )
    } else {
        (None, without_scheme)
    };

    // Strip trailing path (e.g. "/" in "http://proxy:8080/")
    let hostport = hostport.split('/').next().unwrap_or(hostport);

    // Parse host:port - use rfind to correctly handle IPv6 addresses like [::1]:8080
    let (host, port) = if let Some(colon_pos) = hostport.rfind(':') {
        let host = &hostport[..colon_pos];
        let port: u16 = hostport[colon_pos + 1..].parse().ok()?;
        (host, port)
    } else {
        log::warn!("Could not find parse the environment proxy. Port is missing.");
        return None;
    };

    let auth = auth_opt.and_then(|auth| {
        let colon_pos = auth.find(':')?;
        Some(
            ProxyAuth::builder()
                .username(auth[..colon_pos].to_string())
                .password(auth[colon_pos + 1..].to_string())
                .build(),
        )
    });

    Some(
        ProxyConfig::builder()
            .url(host.to_string())
            .port(port)
            .auth(auth)
            .build(),
    )
}

#[cfg(test)]
mod test_strip_url_protocol {
    use crate::fetcher::strip_url_protocol;

    #[test]
    fn test_strip_http() {
        assert_eq!(
            strip_url_protocol("http://example.com/url"),
            "example.com/url"
        );
    }

    #[test]
    fn test_strip_https() {
        assert_eq!(
            strip_url_protocol("https://example.com/url"),
            "example.com/url"
        );
    }

    #[test]
    fn test_strip_ftp() {
        assert_eq!(
            strip_url_protocol("ftp://example.com/url"),
            "example.com/url"
        );
    }

    #[test]
    fn test_no_strip() {
        assert_eq!(strip_url_protocol("example.com/url"), "example.com/url");
    }
}

#[cfg(test)]
mod test_parse_proxy_env_var {
    use super::parse_proxy_env_var;

    #[test]
    fn test_proxy_with_port_and_scheme() {
        let cfg = parse_proxy_env_var("http://proxy.example.com:8080").unwrap();
        assert_eq!(cfg.url, "proxy.example.com");
        assert_eq!(cfg.port, 8080);
        assert!(cfg.auth.is_none());
    }

    #[test]
    fn test_proxy_with_credentials() {
        let cfg = parse_proxy_env_var("http://user:secret@proxy.example.com:8080").unwrap();
        assert_eq!(cfg.url, "proxy.example.com");
        assert_eq!(cfg.port, 8080);
        let auth = cfg.auth.unwrap();
        assert_eq!(auth.username, "user");
        assert_eq!(auth.password, "secret");
    }

    #[test]
    fn test_proxy_without_port_returns_none() {
        assert!(parse_proxy_env_var("http://proxy.example.com").is_none());
    }

    #[test]
    fn test_empty_proxy_url_returns_none() {
        assert!(parse_proxy_env_var("").is_none());
    }
}

#[cfg(test)]
mod test_matches_no_proxy {
    use super::matches_no_proxy;

    #[test]
    fn test_wildcard_bypasses_all() {
        assert!(matches_no_proxy("example.com", "*"));
    }

    #[test]
    fn test_exact_match() {
        assert!(matches_no_proxy("example.com", "example.com"));
    }

    #[test]
    fn test_subdomain_matches_dot_pattern() {
        assert!(matches_no_proxy("sub.example.com", ".example.com"));
    }

    #[test]
    fn test_no_match() {
        assert!(!matches_no_proxy("other.com", "example.com"));
    }
}
