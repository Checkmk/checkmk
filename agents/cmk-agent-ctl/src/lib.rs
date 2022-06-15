// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
pub mod certs;
mod cli;
pub mod config;
mod constants;
#[cfg(windows)]
mod log_ext;
mod misc;
pub mod modes;
mod monitoring_data;
mod setup;
pub mod site_spec;
mod tls_server;
pub mod types;
use anyhow::{anyhow, Context, Result as AnyhowResult};
use config::{JSONLoader, TOMLLoader};
use log::info;
use modes::daemon::daemon;
use modes::delete_connection::{delete, delete_all};
use modes::dump::dump;
use modes::import_connection::import;
use modes::pull::pull;
use modes::push::handle_push_cycle as push;
use modes::registration::{proxy_register, register};
use modes::status::status;

pub use setup::init;

pub fn run_requested_mode(args: cli::Args, paths: setup::PathResolver) -> AnyhowResult<()> {
    agent_socket_operational(&args)?;

    let registration_preset = config::RegistrationPreset::load(&paths.registration_preset_path)?;
    let runtime_config = config::RuntimeConfig::load(&paths.config_path)?;
    let mut registry = config::Registry::from_file(&paths.registry_path)
        .context("Error while loading registered connections.")?;
    let legacy_pull_marker = config::LegacyPullMarker::new(&paths.legacy_pull_path);
    info!(
        "Loaded config from '{:?}', legacy pull '{:?}' {}",
        &paths.config_path,
        legacy_pull_marker,
        if legacy_pull_marker.exists() {
            "exists"
        } else {
            "absent"
        }
    );
    match args {
        cli::Args::Register(reg_args) => {
            register(
                config::RegistrationConfig::new(runtime_config, registration_preset, reg_args)?,
                &mut registry,
            )?;
            legacy_pull_marker.remove().context(
                "Registration successful, but could not delete marker for legacy pull mode",
            )
        }
        cli::Args::Import(import_args) => {
            import(&mut registry, &import_args)?;
            legacy_pull_marker
                .remove()
                .context("Import successful, but could not delete marker for legacy pull mode")
        }
        cli::Args::ProxyRegister(proxy_reg_args) => proxy_register(
            config::RegistrationConfig::new(runtime_config, registration_preset, proxy_reg_args)?,
        ),
        cli::Args::Push(push_args) => push(
            &registry,
            &config::ClientConfig::new(runtime_config, push_args.client_opts),
        ),
        cli::Args::Pull(pull_args) => pull(config::PullConfig::new(
            runtime_config,
            pull_args.pull_opts,
            legacy_pull_marker,
            registry,
        )?),
        cli::Args::Daemon(daemon_args) => daemon(
            registry.clone(),
            config::PullConfig::new(
                runtime_config.clone(),
                daemon_args.pull_opts,
                legacy_pull_marker,
                registry,
            )?,
            config::ClientConfig::new(runtime_config, daemon_args.client_opts),
        ),
        cli::Args::Dump { .. } => dump(),
        cli::Args::Status(status_args) => status(
            &registry,
            &config::PullConfig::new(
                runtime_config.clone(),
                // this will vanish once the Windows agent also uses the toml config
                cli::PullOpts {
                    port: None,
                    #[cfg(windows)]
                    agent_channel: None,
                    allowed_ip: None,
                },
                legacy_pull_marker,
                registry.clone(),
            )?,
            config::ClientConfig::new(runtime_config, status_args.client_opts),
            status_args.json,
            !status_args.no_query_remote,
        ),
        cli::Args::Delete(delete_args) => delete(&mut registry, &delete_args.connection),
        cli::Args::DeleteAll(delete_all_args) => delete_all(
            &mut registry,
            delete_all_args.enable_insecure_connections,
            &legacy_pull_marker,
        ),
    }
}

// This check is currently only useful on Unix. On Windows, the internal agent address can be passed
// on the command line, so we cannot easily check this for any mode.
fn agent_socket_operational(args: &cli::Args) -> AnyhowResult<()> {
    let agent_channel = setup::agent_channel();
    match *args {
        cli::Args::Register { .. } | cli::Args::Import { .. } => {
            match agent_channel.operational() {
                true => Ok(()),
                false => Err(anyhow!(format!(
                    "Something seems wrong with the agent socket ({}), aborting",
                    agent_channel
                ))),
            }
        }
        _ => Ok(()),
    }
}
