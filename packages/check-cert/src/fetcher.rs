// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{Context, Result};
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
use openssl::x509::X509;
use std::net::TcpStream;
use std::time::Duration;

pub fn fetch_server_cert(
    server: &str,
    port: &u16,
    timeout: Option<Duration>,
    use_sni: bool,
) -> Result<X509> {
    let stream = TcpStream::connect(format!("{server}:{port}"))?;
    stream.set_read_timeout(timeout)?;
    let mut connector_builder = SslConnector::builder(SslMethod::tls())?;
    connector_builder.set_verify(SslVerifyMode::NONE);
    let connector = connector_builder.build();
    connector
        .configure()
        .context("Cannot configure connection")?
        .use_server_name_indication(use_sni);
    let mut stream = connector.connect(server, stream)?;
    let cert = stream
        .ssl()
        .peer_cert_chain()
        .context("Failed fetching peer cert chain")?
        .iter()
        .next()
        .context("Failed unpacking peer cert chain")?
        .to_owned();
    stream.shutdown()?;
    Ok(cert)
}
