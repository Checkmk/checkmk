// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
pub mod certs;
mod cli;
pub mod configuration;
mod constants;
#[cfg(windows)]
mod log_ext;
#[cfg(windows)]
pub mod mailslot_transport;
mod misc;
pub mod modes;
mod monitoring_data;
mod setup;
pub mod site_spec;
mod tls_server;
pub mod types;
mod version;
use anyhow::{bail, Context, Result as AnyhowResult};
use configuration::config;
use configuration::config::TOMLLoaderMissingSafe;
use log::info;
use modes::daemon::daemon;
use modes::delete_connection::{delete, delete_all};
use modes::dump::dump;
use modes::import_connection::import;
use modes::pull::fn_thread;
use modes::push::handle_push_cycle as push;
use modes::registration;
use modes::renew_certificate::renew_certificate;
use modes::status::status;
pub use setup::init;

#[cfg(windows)]
pub use misc::validate_elevation;

pub fn run_requested_mode(cli: cli::Cli, paths: setup::PathResolver) -> AnyhowResult<()> {
    configuration::migrate::migrate_registered_connections(&paths.registry_path)?;
    agent_socket_operational(&cli.mode)?;

    let runtime_config = config::RuntimeConfig::load_missing_safe(&paths.config_path)?;
    let mut registry = config::Registry::from_file(&paths.registry_path).with_context(|| {
        format!(
            "Error while loading registered connections from {:?}.",
            &paths.registry_path
        )
    })?;
    info!(
        "Loaded config from '{:?}', connection registry from '{:?}'",
        &paths.config_path, &paths.registry_path
    );
    match cli.mode {
        cli::Mode::Register(reg_opts) => registration::register_existing(
            &config::RegisterExistingConfig::new(runtime_config, reg_opts)?,
            &mut registry,
        ),
        cli::Mode::RegisterNew(reg_new_opts) => registration::register_new(
            &config::RegisterNewConfig::new(
                config::RegistrationConnectionConfig::new(
                    runtime_config,
                    reg_new_opts.connection_opts,
                )?,
                reg_new_opts.agent_labels_raw.into_iter().collect(),
            )?,
            &mut registry,
        ),
        cli::Mode::ProxyRegister(reg_opts) => registration::proxy_register(
            &config::RegisterExistingConfig::new(runtime_config, reg_opts)?,
        ),
        cli::Mode::Import(import_opts) => import(&mut registry, &import_opts),
        cli::Mode::Push(client_opts) => push(
            &registry,
            &config::ClientConfig::new(runtime_config, client_opts, None),
            &setup::agent_channel(),
        ),
        cli::Mode::Pull(pull_opts) => fn_thread(config::PullConfig::new(
            runtime_config,
            pull_opts,
            registry,
        )?),
        cli::Mode::Daemon(daemon_opts) => daemon(
            &paths.pre_configured_connections_path,
            registry.clone(),
            config::PullConfig::new(runtime_config.clone(), daemon_opts.pull_opts, registry)?,
            config::ClientConfig::new(
                runtime_config,
                daemon_opts.client_opts,
                Some(daemon_opts.reg_client_opts),
            ),
        ),
        cli::Mode::Dump => dump(),
        cli::Mode::Status(status_opts) => status(
            &registry,
            &config::PullConfig::new(
                runtime_config.clone(),
                // this will vanish once the Windows agent also uses the toml config
                cli::PullOpts {
                    port: None,
                    #[cfg(windows)]
                    agent_channel: None,
                },
                registry.clone(),
            )?,
            config::ClientConfig::new(runtime_config, status_opts.client_opts, None),
            status_opts.json,
            !status_opts.no_query_remote,
        ),
        cli::Mode::Delete(delete_opts) => delete(&mut registry, &delete_opts.connection),
        cli::Mode::DeleteAll(delete_all_opts) => {
            delete_all(&mut registry, delete_all_opts.enable_insecure_connections)
        }
        cli::Mode::RenewCertificate(renew_certificate_opts) => renew_certificate(
            registry,
            &renew_certificate_opts.connection_opts.connection,
            config::ClientConfig::new(runtime_config, renew_certificate_opts.client_opts, None),
        ),
    }
}

/// This check is currently only useful on Unix. On Windows, the internal agent address can be passed
/// on the command line, so we cannot easily check this for any mode.
fn agent_socket_operational(mode: &cli::Mode) -> AnyhowResult<()> {
    match mode {
        cli::Mode::Register(_) | cli::Mode::RegisterNew(_) | cli::Mode::Import(_) => {
            let agent_channel = setup::agent_channel();
            if agent_channel.operational() {
                Ok(())
            } else {
                bail!(format!(
                    "Something seems wrong with the agent socket ({agent_channel}), aborting"
                ))
            }
        }
        _ => Ok(()),
    }
}
