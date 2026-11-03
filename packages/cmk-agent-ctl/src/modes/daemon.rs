// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::certs::trusted_cas;
use crate::config;
use crate::config::JSONLoader;
use crate::environment::PathResolver;
use crate::misc;
use crate::modes::{pull, push, renew_certificate};
use crate::modes::{registration, update};
use crate::updater::{self, PythonUpdater};
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
    paths: PathResolver,
    mut registry: config::Registry,
    pull_config: config::PullConfig,
    client_config: config::ClientConfig,
    updater_registration: config::UpdaterRegistration,
    python_updater: Option<PythonUpdater>,
) -> AnyhowResult<()> {
    register_panic_handler();
    let baked_cas = trusted_cas::load_baked_cas(&paths.trusted_cas_path);
    // Connections that are already registered are covered here, connections created below get the
    // baked CAs handed to the registration.
    trusted_cas::trust_baked_cas(&baked_cas, &mut registry);
    process_pre_configured_connections(
        &paths,
        &mut registry,
        &client_config,
        updater_registration,
        python_updater.as_ref(),
        &baked_cas,
    );

    // create channels, 3x TX + 1x RX to "synchronize" thread stops on failure
    let (tx_push, rx) = mpsc::channel();
    let tx_pull = tx_push.clone();
    let tx_renew_certificate = tx_push.clone();
    let tx_update = tx_push.clone();

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

    let reg_copy = registry.clone();
    let config_clone = client_config.clone();
    thread::spawn(move || {
        tx_renew_certificate
            .send(renew_certificate::fn_thread(reg_copy, config_clone))
            .unwrap();
    });

    thread::spawn(move || {
        tx_update
            .send(update::fn_thread(paths, registry, client_config))
            .unwrap();
    });

    // We should never receive anything here, unless one of the threads crashed.
    // In that case, this will contain an error that should be propagated.
    rx.recv().unwrap()
}

fn process_pre_configured_connections(
    paths: &PathResolver,
    registry: &mut config::Registry,
    client_config: &config::ClientConfig,
    updater_registration: config::UpdaterRegistration,
    python_updater: Option<&PythonUpdater>,
    baked_cas: &trusted_cas::BakedCAs,
) {
    match config::PreConfiguredConnections::load(&paths.pre_configured_connections_path) {
        Ok(pre_configured) => {
            if let Err(err) = registration::register_pre_configured(
                &pre_configured,
                client_config,
                registry,
                baked_cas,
            )
            .and_then(|added_connections| {
                updater::after_connection_changes(
                    paths,
                    &added_connections,
                    &updater_registration,
                    python_updater,
                    registry,
                )
            }) {
                error!(
                    "Error while processing pre-configured connections: {}",
                    misc::anyhow_error_to_human_readable(&err)
                )
            }
        }
        Err(err) => info!(
            "Could not load pre-configured connections from {:?}: {}",
            paths.pre_configured_connections_path,
            misc::anyhow_error_to_human_readable(&err)
        ),
    }
}
