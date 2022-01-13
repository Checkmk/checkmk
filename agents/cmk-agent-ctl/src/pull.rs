// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{config, dump, monitoring_data, tls_server};
use anyhow::{Context, Result as AnyhowResult};
use std::io::Write;

const TLS_ID: &[u8] = b"16";
const HEADER_VERSION: &[u8] = b"\x00\x00";

pub fn pull(registry: &config::Registry, legacy_pull_marker: &std::path::Path) -> AnyhowResult<()> {
    if is_legacy_pull(&registry, legacy_pull_marker) {
        return dump::dump();
    }

    let mut stream = tls_server::IoStream::new();

    stream.write_all(TLS_ID)?;
    stream.flush()?;

    let mut tls_connection = tls_server::tls_connection(registry.pull_connections())
        .context("Could not initialize TLS.")?;
    let mut tls_stream = tls_server::tls_stream(&mut tls_connection, &mut stream);

    tls_stream.write_all(&encode_data_for_transport(
        &monitoring_data::collect().context("Error collecting monitoring data.")?,
    )?)?;
    tls_stream.flush()?;

    disallow_legacy_pull(legacy_pull_marker).context("Just provided agent data via TLS, but legacy pull mode is still allowed, and could not delete marker")?;
    Ok(())
}

fn is_legacy_pull(registry: &config::Registry, legacy_pull_marker: &std::path::Path) -> bool {
    if !legacy_pull_marker.exists() {
        return false;
    }
    if !registry.is_empty() {
        return false;
    }
    true
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
