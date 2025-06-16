// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{
    agent_receiver_api::{self, AgentData},
    config, misc, monitoring_data, site_spec,
    types::AgentChannel,
};
use anyhow::{Context, Result as AnyhowResult};
use log::{debug, info, warn};
use std::thread;
use std::time::{Duration, Instant};

pub fn fn_thread(
    mut registry: config::Registry,
    client_config: config::ClientConfig,
    agent_channel: AgentChannel,
) -> AnyhowResult<()> {
    misc::sleep_randomly();
    loop {
        registry.refresh()?;
        let begin = Instant::now();
        if let Err(error) = handle_push_cycle(&registry, &client_config, &agent_channel) {
            warn!("Error running push cycle. ({})", error);
        };
        thread::sleep(Duration::from_secs(60).saturating_sub(begin.elapsed()));
    }
}

pub fn handle_push_cycle(
    registry: &config::Registry,
    client_config: &config::ClientConfig,
    agent_channel: &AgentChannel,
) -> AnyhowResult<()> {
    if registry.is_push_empty() {
        return Ok(());
    }

    debug!("Handling registered push connections.");

    let compressed_mon_data = monitoring_data::compress(
        &monitoring_data::collect(agent_channel).context("Error collecting agent output")?,
    )
    .context("Error compressing agent output")?;

    for (site_id, connection) in registry.get_push_connections() {
        info!("{site_id} (push): Sending agent output");
        let site_url = site_spec::make_site_url(site_id, &connection.receiver_port)
            .context("Failed to construct URL for pushing data")?;
        if let Err(error) = (agent_receiver_api::Api {
            use_proxy: client_config.use_proxy,
        })
        .agent_data(
            &site_url,
            &connection.trust,
            &monitoring_data::compression_header_info().push,
            &compressed_mon_data,
        ) {
            warn!("{site_url} (push): Error sending agent output. ({error})");
        };
    }
    Ok(())
}
