// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{
    agent_receiver_api::{self, AgentData},
    config, monitoring_data,
};
use anyhow::{Context, Result as AnyhowResult};
use log::{debug, info, warn};
use rand::Rng;
use std::thread;
use std::time::{Duration, Instant};

fn sleep_randomly() {
    let random_period = rand::thread_rng().gen_range(0..59);
    debug!("Sleeping {}s to avoid DDOSing of sites", random_period);
    thread::sleep(Duration::from_secs(random_period));
}

pub fn push(
    mut registry: config::Registry,
    client_config: config::ClientConfig,
) -> AnyhowResult<()> {
    sleep_randomly();
    loop {
        registry.refresh()?;
        let begin = Instant::now();
        if let Err(error) = handle_push_cycle(&registry, &client_config) {
            warn!("Error running push cycle. ({})", error);
        };
        thread::sleep(Duration::from_secs(60).saturating_sub(begin.elapsed()));
    }
}

pub fn handle_push_cycle(
    registry: &config::Registry,
    client_config: &config::ClientConfig,
) -> AnyhowResult<()> {
    if registry.push_is_empty() {
        return Ok(());
    }

    debug!("Handling registered push connections.");

    let compressed_mon_data = monitoring_data::compress(
        &monitoring_data::collect().context("Error collecting agent output")?,
    )
    .context("Error compressing agent output")?;

    for (coordinates, connection) in registry.push_connections() {
        info!("{}: Pushing agent output", coordinates);
        match coordinates.to_url() {
            Ok(url) => {
                if let Err(error) = (agent_receiver_api::Api {
                    use_proxy: client_config.use_proxy,
                })
                .agent_data(
                    &url,
                    connection,
                    &monitoring_data::compression_header_info().push,
                    &compressed_mon_data,
                ) {
                    warn!("{}: Error pushing agent output. ({})", coordinates, error);
                };
            }
            Err(err) => warn!(
                "{}: Failed to construct endpoint URL for pushing. ({})",
                coordinates, err
            ),
        }
    }
    Ok(())
}
