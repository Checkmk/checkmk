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
use std::fs;
use std::io::{self, Write};
use std::path::Path;
use structopt::StructOpt;

fn push(registry: config::Registry) -> AnyhowResult<()> {
    let compressed_mon_data = monitoring_data::compress(
        &monitoring_data::collect().context("Error collecting monitoring data")?,
    )
    .context("Error compressing monitoring data")?;

    for (agent_receiver_address, server_spec) in registry.push_connections() {
        agent_receiver_api::agent_data(
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

fn ensure_home_directory(path: &Path) -> io::Result<()> {
    if !path.exists() {
        fs::create_dir_all(path)?;
    }
    Ok(())
}

#[cfg(unix)]
fn try_sanitize_home_dir_ownership(home_dir: &Path, user: &str) {
    if let Err(error) = sanitize_home_dir_ownership(home_dir, user).context(format!(
        "Failed to recursively set ownership of {} to {}",
        home_dir.display(),
        user
    )) {
        io::stderr()
            .write_all(format!("{:?}", error).as_bytes())
            .unwrap_or(());
        error!("{:?}", error)
    };
}

#[cfg(unix)]
fn sanitize_home_dir_ownership(home_dir: &Path, user: &str) -> AnyhowResult<()> {
    if !unistd::Uid::current().is_root() {
        return Ok(());
    }
    let cmk_agent_user =
        unistd::User::from_name(user)?.context(format!("Could not find user {}", user))?;
    let cmk_agent_group =
        unistd::Group::from_name(user)?.context(format!("Could not find group {}", user))?;
    Ok(recursive_chown(
        home_dir,
        Some(cmk_agent_user.uid),
        Some(cmk_agent_group.gid),
    )?)
}

#[cfg(unix)]
fn recursive_chown(
    dir: &Path,
    uid: Option<unistd::Uid>,
    gid: Option<unistd::Gid>,
) -> io::Result<()> {
    unistd::chown(dir, uid, gid)?;
    for entry in fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_dir() {
            recursive_chown(&path, uid, gid)?;
        } else {
            unistd::chown(&path, uid, gid)?;
        }
    }
    Ok(())
}

fn init() -> cli::Args {
    // Parse args as first action to directly exit from --help or malformatted arguments
    let args = cli::Args::from_args();

    // TODO: Decide: Check if running as cmk-agent or root, and abort otherwise?
    if let Err(error) = ensure_home_directory(&constants::home_dir()) {
        panic!(
            "Cannot go on: Missing cmk-agent home directory and failed to create it: {}",
            error
        );
    }

    if let Err(error) = init_logging(&constants::log_path()) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", error).as_bytes())
            .unwrap_or(());
    }

    args
}

fn run_requested_mode(args: cli::Args) -> AnyhowResult<()> {
    let stored_config = config::ConfigFromDisk::load(&constants::config_path())?;
    let mut registry = config::Registry::from_file(&constants::registry_path())
        .context("Error while loading registered connections.")?;
    match args {
        cli::Args::Register(reg_args) => {
            registration::register(
                config::RegistrationConfig::new(stored_config, reg_args)?,
                registry,
            )?;
            pull::disallow_legacy_pull(&constants::legacy_pull_path()).context(
                "Registration successful, but could not delete marker for legacy pull mode",
            )
        }
        cli::Args::Push { .. } => push(registry),
        cli::Args::Pull { .. } => pull::pull(&registry, &constants::legacy_pull_path()),
        cli::Args::Dump { .. } => dump::dump(),
        cli::Args::Status(status_args) => status::status(registry, status_args.json),
        cli::Args::Delete(delete_args) => {
            delete_connection::delete(&mut registry, &delete_args.connection)
        }
        cli::Args::DeleteAll { .. } => delete_connection::delete_all(&mut registry),
    }
}

fn main() -> AnyhowResult<()> {
    let args = init();

    let result = run_requested_mode(args);

    if let Err(error) = &result {
        error!("{:?}", error)
    }

    #[cfg(unix)]
    try_sanitize_home_dir_ownership(&constants::home_dir(), constants::CMK_AGENT_USER);

    result
}
