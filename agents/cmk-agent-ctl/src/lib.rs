// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
pub mod certs;
mod cli;
pub mod config;
mod constants;
pub mod modes;
mod monitoring_data;
mod setup;
pub mod site_spec;
mod tls_server;
pub mod types;
use anyhow::{Context, Result as AnyhowResult};
use config::{JSONLoader, TOMLLoader};

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
    let registration_preset = config::RegistrationPreset::load(&paths.registration_preset_path)?;
    let config_from_disk = config::ConfigFromDisk::load(&paths.config_path)?;
    let mut registry = config::Registry::from_file(&paths.registry_path)
        .context("Error while loading registered connections.")?;
    let legacy_pull_marker = config::LegacyPullMarker::new(&paths.legacy_pull_path);
    match args {
        cli::Args::Register(reg_args) => {
            register(
                config::RegistrationConfig::new(registration_preset, reg_args)?,
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
            config::RegistrationConfig::new(registration_preset, proxy_reg_args)?,
        ),
        cli::Args::Push { .. } => push(&registry),
        cli::Args::Pull(pull_args) => pull(config::PullConfig::new(
            config_from_disk,
            pull_args,
            legacy_pull_marker,
            registry,
        )?),
        cli::Args::Daemon(daemon_args) => daemon(
            registry.clone(),
            config::PullConfig::new(config_from_disk, daemon_args, legacy_pull_marker, registry)?,
        ),
        cli::Args::Dump { .. } => dump(),
        cli::Args::Status(status_args) => status(
            &registry,
            &config::PullConfig::new(
                config_from_disk,
                // this will vanish once the Windows agent also uses the toml config
                cli::PullArgs {
                    port: None,
                    allowed_ip: None,
                    logging_opts: status_args.logging_opts,
                },
                legacy_pull_marker,
                registry.clone(),
            )?,
            status_args.json,
        ),
        cli::Args::Delete(delete_args) => delete(&mut registry, &delete_args.connection),
        cli::Args::DeleteAll { .. } => delete_all(&mut registry),
    }
}
