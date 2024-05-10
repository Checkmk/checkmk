// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Context, Result};
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
use std::net::{SocketAddr, TcpStream, ToSocketAddrs};
use std::time::Duration;
use typed_builder::TypedBuilder;

#[derive(Debug, TypedBuilder)]
pub struct Config {
    timeout: Option<Duration>,
}

fn to_addr(server: &str, port: u16) -> Result<SocketAddr> {
    let mut addr_iter = format!("{server}:{port}").to_socket_addrs()?;
    addr_iter.next().ok_or(anyhow!("no address"))
}

pub fn fetch_server_cert(server: &str, port: u16, config: Config) -> Result<Vec<Vec<u8>>> {
    let addr = to_addr(server, port)?;
    let stream = match config.timeout {
        None => TcpStream::connect(addr)?,
        Some(dur) => TcpStream::connect_timeout(&addr, dur)?,
    };
    stream.set_read_timeout(config.timeout)?;
    let mut connector_builder = SslConnector::builder(SslMethod::tls())?;
    connector_builder.set_verify(SslVerifyMode::NONE);
    let connector = connector_builder.build();
    connector
        .configure()
        .context("Cannot configure connection")?;
    let mut stream = connector.connect(server, stream)?;
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
