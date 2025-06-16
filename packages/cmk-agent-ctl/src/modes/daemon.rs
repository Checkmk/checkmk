// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config;
use crate::config::JSONLoader;
use crate::misc;
use crate::modes::registration;
use crate::modes::{pull, push, renew_certificate};
use anyhow::Result as AnyhowResult;
use log::{error, info};
use std::sync::mpsc;
use std::thread;

/// Send panic information in log.
/// This is critically important for daemon mode
fn register_panic_handler() {
    let default_panic = std::panic::take_hook();

    std::panic::set_hook(Box::new(move |panic_info| {
        log::error!("Panic in controller '{:?}'", panic_info);
        default_panic(panic_info);
    }));
}

pub fn daemon(
    path_pre_configured_connections: &std::path::Path,
    mut registry: config::Registry,
    pull_config: config::PullConfig,
    client_config: config::ClientConfig,
) -> AnyhowResult<()> {
    register_panic_handler();
    process_pre_configured_connections(
        path_pre_configured_connections,
        &mut registry,
        &client_config,
    );

    // create channels, 3x TX + 1x RX to "synchronize" thread stops on failure
    let (tx_push, rx) = mpsc::channel();
    let tx_pull = tx_push.clone();
    let tx_renew_certificate = tx_push.clone();

    let agent_channel = pull_config.agent_channel.clone();
    let registry_push = registry.clone();
    let client_config_push = client_config.clone();

    thread::spawn(move || {
        tx_push
            .send(push::fn_thread(
                registry_push,
                client_config_push,
                agent_channel,
            ))
            .unwrap();
    });
    thread::spawn(move || {
        tx_pull.send(pull::fn_thread(pull_config)).unwrap();
    });
    thread::spawn(move || {
        tx_renew_certificate
            .send(renew_certificate::fn_thread(registry, client_config))
            .unwrap();
    });

    // We should never receive anything here, unless one of the threads crashed.
    // In that case, this will contain an error that should be propagated.
    rx.recv().unwrap()
}

fn process_pre_configured_connections(
    path_pre_configured_connections: &std::path::Path,
    registry: &mut config::Registry,
    client_config: &config::ClientConfig,
) {
    match config::PreConfiguredConnections::load(path_pre_configured_connections) {
        Ok(pre_configured) => {
            if let Err(err) =
                registration::register_pre_configured(&pre_configured, client_config, registry)
            {
                error!(
                    "Error while processing pre-configured connections: {}",
                    misc::anyhow_error_to_human_readable(&err)
                )
            }
        }
        Err(err) => info!(
            "Could not load pre-configured connections from {:?}: {}",
            path_pre_configured_connections,
            misc::anyhow_error_to_human_readable(&err)
        ),
    }
}
