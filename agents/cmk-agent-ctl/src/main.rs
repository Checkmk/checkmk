// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

mod agent_receiver_api;
mod certs;
mod cli;
mod config;
mod constants;
mod delete_connection;
mod dump;
mod import_connection;
mod monitoring_data;
mod pull;
mod push;
mod registration;
mod setup;
mod site_spec;
mod status;
mod tls_server;
mod types;
use anyhow::{Context, Result as AnyhowResult};
use config::{JSONLoader, TOMLLoader};
use log::{error, info};
use std::sync::mpsc;
use std::thread;

fn daemon(registry: config::Registry, pull_config: config::PullConfig) -> AnyhowResult<()> {
    let (tx_push, rx) = mpsc::channel();
    let tx_pull = tx_push.clone();
    thread::spawn(move || {
        tx_push.send(push::push(registry)).unwrap();
    });
    thread::spawn(move || {
        tx_pull.send(pull::pull(pull_config)).unwrap();
    });

    // We should never receive anything here, unless one of the threads crashed.
    // In that case, this will contain an error that should be propagated.
    rx.recv().unwrap()
}

fn run_requested_mode(args: cli::Args, paths: setup::PathResolver) -> AnyhowResult<()> {
    let registration_preset = config::RegistrationPreset::load(&paths.registration_preset_path)?;
    let config_from_disk = config::ConfigFromDisk::load(&paths.config_path)?;
    let mut registry = config::Registry::from_file(&paths.registry_path)
        .context("Error while loading registered connections.")?;
    let legacy_pull_marker = config::LegacyPullMarker::new(&paths.legacy_pull_path);
    match args {
        cli::Args::Register(reg_args) => {
            registration::register(
                config::RegistrationConfig::new(registration_preset, reg_args)?,
                &mut registry,
            )?;
            legacy_pull_marker.remove().context(
                "Registration successful, but could not delete marker for legacy pull mode",
            )
        }
        cli::Args::Import(import_args) => {
            import_connection::import(&mut registry, &import_args)?;
            legacy_pull_marker
                .remove()
                .context("Import successful, but could not delete marker for legacy pull mode")
        }
        cli::Args::ProxyRegister(proxy_reg_args) => registration::proxy_register(
            config::RegistrationConfig::new(registration_preset, proxy_reg_args)?,
        ),
        cli::Args::Push { .. } => push::handle_push_cycle(&registry),
        cli::Args::Pull(pull_args) => pull::pull(config::PullConfig::new(
            config_from_disk,
            pull_args,
            legacy_pull_marker,
            registry,
        )?),
        cli::Args::Daemon(daemon_args) => daemon(
            registry.clone(),
            config::PullConfig::new(config_from_disk, daemon_args, legacy_pull_marker, registry)?,
        ),
        cli::Args::Dump { .. } => dump::dump(),
        cli::Args::Status(status_args) => status::status(
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
        cli::Args::Delete(delete_args) => {
            delete_connection::delete(&mut registry, &delete_args.connection)
        }
        cli::Args::DeleteAll { .. } => delete_connection::delete_all(&mut registry),
    }
}

fn exit_with_error(err: impl std::fmt::Debug) {
    // In case of an error, we want a non-zero exit code and log the error, which
    // goes to stderr under Unix and to stderr and logfile under Windows.

    // In the future, implementing std::process::Termination looks like the right thing to do.
    // However, this trait is still experimental at the moment. See also
    // https://www.joshmcguigan.com/blog/custom-exit-status-codes-rust/
    error!("{:?}", err);
    std::process::exit(1);
}

fn main() {
    let (args, paths) = match setup::init() {
        Ok(args) => args,
        Err(error) => {
            return exit_with_error(error);
        }
    };

    info!("starting");
    let result = run_requested_mode(args, paths);

    if let Err(error) = &result {
        exit_with_error(error)
    }
}
