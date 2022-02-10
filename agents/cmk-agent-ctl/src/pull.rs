// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{config, monitoring_data, tls_server};
use anyhow::{Context, Result as AnyhowResult};
use log::info;
use tokio::io::AsyncWriteExt;
use tokio::net::{TcpListener, TcpStream};
use tokio_rustls::TlsAcceptor;

const TLS_ID: &[u8] = b"16";
const HEADER_VERSION: &[u8] = b"\x00\x00";

#[tokio::main(flavor = "current_thread")]
pub async fn pull(
    registry: config::Registry,
    legacy_pull_marker: std::path::PathBuf,
    port: String,
) -> AnyhowResult<()> {
    let listener = TcpListener::bind(format!("0.0.0.0:{}", port)).await?;
    let mut pull_config = PullConfiguration::new(registry, legacy_pull_marker)?;

    loop {
        let (stream, addr) = listener
            .accept()
            .await
            .context("Failed accepting pull connection")?;
        info!("{}: Handling pull request", addr);

        pull_config.refresh()?;

        tokio::spawn(handle_pull_request(
            stream,
            pull_config.legacy_pull,
            pull_config.tls_acceptor(),
        ));
    }
}

struct PullConfiguration {
    legacy_pull: bool,
    tls_acceptor: TlsAcceptor,
    registry: config::Registry,
    legacy_pull_marker: std::path::PathBuf,
}

impl PullConfiguration {
    pub fn new(
        registry: config::Registry,
        legacy_pull_marker: std::path::PathBuf,
    ) -> AnyhowResult<Self> {
        Ok(PullConfiguration {
            legacy_pull: is_legacy_pull(&registry, &legacy_pull_marker),
            tls_acceptor: tls_server::tls_acceptor(registry.pull_connections())
                .context("Could not initialize TLS.")?,
            registry,
            legacy_pull_marker,
        })
    }

    pub fn refresh(&mut self) -> AnyhowResult<()> {
        if self.registry.refresh()? {
            self.tls_acceptor = tls_server::tls_acceptor(self.registry.pull_connections())
                .context("Could not initialize TLS.")?;
            self.legacy_pull = is_legacy_pull(&self.registry, &self.legacy_pull_marker);
        };
        Ok(())
    }

    pub fn tls_acceptor(&self) -> TlsAcceptor {
        self.tls_acceptor.clone()
    }
}

fn is_legacy_pull(registry: &config::Registry, legacy_pull_marker: &std::path::Path) -> bool {
    if legacy_pull_marker.exists() {
        return false;
    }
    if !registry.is_empty() {
        return false;
    }
    true
}

async fn handle_pull_request(
    mut stream: TcpStream,
    is_legacy_pull: bool,
    tls_acceptor: TlsAcceptor,
) -> AnyhowResult<()> {
    let mon_data = monitoring_data::async_collect()
        .await
        .context("Error collecting monitoring data.")?;

    if is_legacy_pull {
        stream.write_all(&mon_data).await?;
        return Ok(());
    }

    stream.write_all(TLS_ID).await?;
    stream.flush().await?;

    let mut tls_stream = tls_acceptor.accept(stream).await?;

    tls_stream
        .write_all(&encode_data_for_transport(&mon_data)?)
        .await?;
    tls_stream.flush().await?;
    Ok(())
}

pub fn disallow_legacy_pull(legacy_pull_marker: &std::path::Path) -> std::io::Result<()> {
    if !legacy_pull_marker.exists() {
        return Ok(());
    }

    std::fs::remove_file(legacy_pull_marker)
}

fn encode_data_for_transport(raw_agent_output: &[u8]) -> AnyhowResult<Vec<u8>> {
    let mut encoded_data = HEADER_VERSION.to_vec();
    encoded_data.append(&mut monitoring_data::compression_header_info().pull);
    encoded_data.append(
        &mut monitoring_data::compress(raw_agent_output)
            .context("Error compressing monitoring data")?,
    );
    Ok(encoded_data)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_data_for_transport() {
        let mut expected_result = b"\x00\x00\x01".to_vec();
        expected_result.append(&mut monitoring_data::compress(b"abc").unwrap());
        assert_eq!(encode_data_for_transport(b"abc").unwrap(), expected_result);
    }
}
