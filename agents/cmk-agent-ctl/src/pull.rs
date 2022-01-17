// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{config, dump, monitoring_data, tls_server};
use anyhow::{Context, Result as AnyhowResult};
use std::io::Write;

const TLS_ID: &[u8] = b"16";

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

    let mon_data = monitoring_data::collect().context("Error collecting monitoring data.")?;
    tls_stream.write_all(&mon_data)?;
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
