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
mod monitoring_data;
mod pull;
mod registration;
mod status;
mod tls_server;
use anyhow::{Context, Result as AnyhowResult};
use config::JSONLoader;
use log::error;
#[cfg(unix)]
use nix::unistd;
use std::io::{self, Write};
use std::path::Path;
use structopt::StructOpt;

fn push(registry: config::Registry) -> AnyhowResult<()> {
    let compressed_mon_data = monitoring_data::compress(
        &monitoring_data::collect().context("Error collecting monitoring data")?,
    )
    .context("Error compressing monitoring data")?;

    for (agent_receiver_address, server_spec) in registry.push_connections() {
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

fn init_logging(path: &Path) -> AnyhowResult<()> {
    flexi_logger::Logger::try_with_env_or_str("error")?
        .log_to_file(flexi_logger::FileSpec::try_from(path)?)
        .append()
        .format(flexi_logger::detailed_format)
        .start()
        .unwrap();
    Ok(())
}

#[cfg(unix)]
fn become_user(user: &unistd::User) -> AnyhowResult<()> {
    unistd::setgid(user.gid).context(format!(
        "Failed to set group id {} corresponding to user {}",
        user.gid, user.name,
    ))?;
    unistd::setuid(user.uid).context(format!(
        "Failed to set user id {} corresponding to user {}",
        user.uid, user.name,
    ))?;
    Ok(())
}

#[cfg(unix)]
fn user_setup(username: &str) -> AnyhowResult<constants::Paths> {
    let user = unistd::User::from_name(username)?.context(format!(
        "Could not find dedicated Checkmk agent user {}",
        username
    ))?;

    if let Err(error) = become_user(&user) {
        return Err(error.context(format!(
            "Failed to become dedicated Checkmk agent user {}",
            user.name,
        )));
    }

    Ok(constants::Paths::new(&user.dir))
}

fn init() -> AnyhowResult<(cli::Args, constants::Paths)> {
    // Parse args as first action to directly exit from --help or malformatted arguments
    let args = cli::Args::from_args();

    let paths = match user_setup(constants::CMK_AGENT_USER) {
        Ok(paths) => paths,
        Err(err) => return Err(err),
    };

    if let Err(error) = init_logging(&paths.log_path) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", error).as_bytes())
            .unwrap_or(());
    }

    Ok((args, paths))
}

fn run_requested_mode(args: cli::Args, paths: constants::Paths) -> AnyhowResult<()> {
    let stored_config = config::ConfigFromDisk::load(&paths.config_path)?;
    let mut registry = config::Registry::from_file(&paths.registry_path)
        .context("Error while loading registered connections.")?;
    match args {
        cli::Args::Register(reg_args) => {
            registration::register(
                config::RegistrationConfig::new(stored_config, reg_args)?,
                &mut registry,
            )?;
            pull::disallow_legacy_pull(&paths.legacy_pull_path).context(
                "Registration successful, but could not delete marker for legacy pull mode",
            )
        }
        cli::Args::RegisterSurrogatePull(surr_pull_reg_args) => {
            registration::register_surrogate_pull(config::RegistrationConfig::new(
                stored_config,
                surr_pull_reg_args,
            )?)
        }
        cli::Args::Push { .. } => push(registry),
        cli::Args::Pull { .. } => pull::pull(&registry, &paths.legacy_pull_path),
        cli::Args::Dump { .. } => dump::dump(),
        cli::Args::Status(status_args) => status::status(registry, status_args.json),
        cli::Args::Delete(delete_args) => {
            delete_connection::delete(&mut registry, &delete_args.connection)
        }
        cli::Args::DeleteAll { .. } => delete_connection::delete_all(&mut registry),
    }
}

fn main() -> AnyhowResult<()> {
    let (args, paths) = match init() {
        Ok(args) => args,
        Err(error) => {
            // Do not log errors which occured for example when trying to become the cmk-agent user,
            // otherwise, the log file ownership might be messed up
            return Err(error);
        }
    };

    let result = run_requested_mode(args, paths);

    if let Err(error) = &result {
        error!("{:?}", error)
    }

    result
}
