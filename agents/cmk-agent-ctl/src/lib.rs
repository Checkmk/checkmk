// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
use anyhow::{anyhow, Context, Result as AnyhowResult};
use configuration::config;
use configuration::config::TOMLLoaderMissingSafe;
use log::info;
use modes::daemon::daemon;
use modes::delete_connection::{delete, delete_all};
use modes::dump::dump;
use modes::import_connection::import;
use modes::pull::pull;
use modes::push::handle_push_cycle as push;
use modes::registration;
use modes::status::status;
pub use setup::init;

#[cfg(windows)]
pub use misc::validate_elevation;

pub fn run_requested_mode(args: cli::Args, paths: setup::PathResolver) -> AnyhowResult<()> {
    configuration::migrate::migrate_registered_connections(&paths.registry_path)?;
    agent_socket_operational(&args)?;

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
    match args {
        cli::Args::RegisterHostName(reg_args) => registration::register_host_name(
            &config::RegistrationConfigHostName::new(runtime_config, reg_args)?,
            &mut registry,
        ),
        cli::Args::RegisterAgentLabels(reg_args) => registration::register_agent_labels(
            &config::RegistrationConfigAgentLabels::new(
                config::RegistrationConnectionConfig::new(
                    runtime_config,
                    reg_args.connection_args,
                )?,
                reg_args.agent_labels_raw.into_iter().collect(),
            )?,
            &mut registry,
        ),
        cli::Args::ProxyRegister(proxy_reg_args) => registration::proxy_register(
            &config::RegistrationConfigHostName::new(runtime_config, proxy_reg_args)?,
        ),
        cli::Args::Import(import_args) => import(&mut registry, &import_args),
        cli::Args::Push(push_args) => push(
            &registry,
            &config::ClientConfig::new(runtime_config, push_args.client_opts),
            &setup::agent_channel(),
        ),
        cli::Args::Pull(pull_args) => pull(config::PullConfig::new(
            runtime_config,
            pull_args.pull_opts,
            registry,
        )?),
        cli::Args::Daemon(daemon_args) => daemon(
            &paths.pre_configured_connections_path,
            registry.clone(),
            config::PullConfig::new(runtime_config.clone(), daemon_args.pull_opts, registry)?,
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
                },
                registry.clone(),
            )?,
            config::ClientConfig::new(runtime_config, status_args.client_opts),
            status_args.json,
            !status_args.no_query_remote,
        ),
        cli::Args::Delete(delete_args) => delete(&mut registry, &delete_args.connection),
        cli::Args::DeleteAll(delete_all_args) => {
            delete_all(&mut registry, delete_all_args.enable_insecure_connections)
        }
    }
}

// This check is currently only useful on Unix. On Windows, the internal agent address can be passed
// on the command line, so we cannot easily check this for any mode.
fn agent_socket_operational(args: &cli::Args) -> AnyhowResult<()> {
    let agent_channel = setup::agent_channel();
    match *args {
        cli::Args::RegisterHostName { .. }
        | cli::Args::RegisterAgentLabels { .. }
        | cli::Args::Import { .. } => match agent_channel.operational() {
            true => Ok(()),
            false => Err(anyhow!(format!(
                "Something seems wrong with the agent socket ({}), aborting",
                agent_channel
            ))),
        },
        _ => Ok(()),
    }
}
