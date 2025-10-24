// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Context, Result};
use openssl::base64::encode_block;
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
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
    #[value(name = "proxy_tls")]
    ProxyTls,
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

pub fn fetch_server_cert(server: &str, port: u16, config: Config) -> Result<Vec<Vec<u8>>> {
    let addr = config
        .proxy
        .clone()
        .map_or(to_addr(server, port), |p| p.to_addr())?;
    let mut stream = match config.timeout {
        None => TcpStream::connect(addr)?,
        Some(dur) => TcpStream::connect_timeout(&addr, dur)?,
    };
    stream.set_read_timeout(config.timeout)?;
    if let ConnectionType::ProxyTls = config.connection_type {
        build_proxy_stream(&mut stream, config.proxy.unwrap().auth, server, port)?;
    };
    stream.set_read_timeout(config.timeout)?;

    match config.connection_type {
        ConnectionType::Tls | ConnectionType::ProxyTls => (),
        ConnectionType::SmtpStarttls => starttls::smtp::perform(&mut stream, server)?,
        ConnectionType::PostgresStarttls => starttls::postgres::perform(&mut stream)?,
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
    let mut response = String::new();
    reader.read_line(&mut response)?;
    if !response.starts_with("HTTP/1.1 200") {
        return Err(anyhow!("Proxy CONNECT failed: {response}"));
    }
    Ok(())
}
