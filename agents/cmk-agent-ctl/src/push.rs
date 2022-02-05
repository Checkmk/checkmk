// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{agent_receiver_api, config, monitoring_data};
use anyhow::{Context, Result as AnyhowResult};
use log::{debug, info};
use rand::Rng;
use std::sync::{Arc, RwLock};
use std::thread;
use std::time::{Duration, Instant};

fn sleep_randomly() {
    let random_period = rand::thread_rng().gen_range(0..59);
    debug!("Sleeping {}s to avoid DDOSing of sites", random_period);
    thread::sleep(Duration::from_secs(random_period));
}

pub fn push(registry: Arc<RwLock<config::Registry>>) -> AnyhowResult<()> {
    sleep_randomly();
    loop {
        {
            let mut registry_writer = registry.write().unwrap();
            registry_writer.refresh()?;
        }
        let registry_reader = registry.read().unwrap();
        let begin = Instant::now();
        info!("Handling registered push connections");
        handle_push_cycle(&registry_reader)?;
        drop(registry_reader);
        thread::sleep(Duration::from_secs(60).saturating_sub(begin.elapsed()));
    }
}

pub fn handle_push_cycle(registry: &config::Registry) -> AnyhowResult<()> {
    let compressed_mon_data = monitoring_data::compress(
        &monitoring_data::collect().context("Error collecting monitoring data")?,
    )
    .context("Error compressing monitoring data")?;

    for (agent_receiver_address, server_spec) in registry.push_connections() {
        info!("Pushing monitoring data to {}", agent_receiver_address);
        agent_receiver_api::Api::agent_data(
            agent_receiver_address,
            &server_spec.root_cert,
            &server_spec.uuid,
            &server_spec.certificate,
            &monitoring_data::compression_header_info().push,
            &compressed_mon_data,
        )
        .context(format!(
            "Error pushing monitoring data to {}.",
            agent_receiver_address
        ))?
    }
    Ok(())
}
