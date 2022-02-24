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
mod site_spec;
mod status;
mod tls_server;
mod types;
use anyhow::{Context, Result as AnyhowResult};
use config::{JSONLoader, TOMLLoader};
use log::{error, info};
#[cfg(unix)]
use nix::unistd;
use std::io::{self, Write};
use std::sync::mpsc;
use std::thread;
use structopt::StructOpt;

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

#[cfg(unix)]
fn init_logging(level: &str) -> Result<flexi_logger::LoggerHandle, flexi_logger::FlexiLoggerError> {
    flexi_logger::Logger::try_with_env_or_str(level)?
        .log_to_stderr()
        .format(flexi_logger::default_format)
        .start()
}

#[cfg(windows)]
fn init_logging(
    level: &str,
    path: &std::path::Path,
    duplicate_level: flexi_logger::Duplicate,
) -> Result<flexi_logger::LoggerHandle, flexi_logger::FlexiLoggerError> {
    flexi_logger::Logger::try_with_env_or_str(level)?
        .log_to_file(flexi_logger::FileSpec::try_from(path)?) // critically important for daemon mode
        .append()
        .format(flexi_logger::detailed_format)
        .duplicate_to_stderr(duplicate_level)
        .start()
}

#[cfg(unix)]
fn become_user(username: &str) -> AnyhowResult<unistd::User> {
    let user = unistd::User::from_name(username)?.context(format!(
        "Could not find dedicated Checkmk agent user {}",
        username
    ))?;

    unistd::setgid(user.gid).context(format!(
        "Failed to set group id {} corresponding to user {}",
        user.gid, user.name,
    ))?;
    unistd::setuid(user.uid).context(format!(
        "Failed to set user id {} corresponding to user {}",
        user.uid, user.name,
    ))?;
    Ok(user)
}

#[cfg(unix)]
fn determine_paths(user: unistd::User) -> AnyhowResult<constants::PathResolver> {
    Ok(constants::PathResolver::new(&user.dir))
}

#[cfg(windows)]
fn determine_paths() -> AnyhowResult<constants::PathResolver> {
    let program_data_path = std::env::var(constants::ENV_PROGRAM_DATA)
        .unwrap_or_else(|_| String::from("c:\\ProgramData"));
    let home = std::path::PathBuf::from(program_data_path + constants::WIN_AGENT_HOME_DIR);
    Ok(constants::PathResolver::new(&home))
}

#[cfg(unix)]
fn setup(args: &cli::Args) -> AnyhowResult<constants::PathResolver> {
    if let Err(err) = init_logging(&args.logging_level()) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", err).as_bytes())
            .unwrap_or(());
    }
    become_user(constants::CMK_AGENT_USER).context(format!(
        "Failed to run as user '{}'. Please execute with sufficient permissions (maybe try 'sudo').",
        constants::CMK_AGENT_USER,
    )).and_then(determine_paths)
}

#[cfg(windows)]
fn setup(args: &cli::Args) -> AnyhowResult<constants::PathResolver> {
    let paths = determine_paths()?;
    let duplicate_level = if let cli::Args::Daemon(_) = args {
        flexi_logger::Duplicate::None
    } else {
        flexi_logger::Duplicate::All
    };
    if let Err(err) = init_logging(&args.logging_level(), &paths.log_path, duplicate_level) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", err).as_bytes())
            .unwrap_or(());
    }
    Ok(paths)
}

fn init() -> AnyhowResult<(cli::Args, constants::PathResolver)> {
    // Parse args as first action to directly exit from --help or malformatted arguments
    let args = cli::Args::from_args();
    let paths = setup(&args)?;
    Ok((args, paths))
}

fn run_requested_mode(args: cli::Args, paths: constants::PathResolver) -> AnyhowResult<()> {
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
        cli::Args::RegisterSurrogatePull(surr_pull_reg_args) => {
            registration::register_surrogate_pull(config::RegistrationConfig::new(
                registration_preset,
                surr_pull_reg_args,
            )?)
        }
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
    let (args, paths) = match init() {
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

#[cfg(windows)]
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_windows_paths() {
        let p = determine_paths().unwrap();
        let home = String::from("C:\\ProgramData") + constants::WIN_AGENT_HOME_DIR;
        assert_eq!(p.home_dir, std::path::PathBuf::from(&home));
        assert_eq!(
            p.registration_preset_path,
            std::path::PathBuf::from(&home).join("cmk-agent-ctl-config.json")
        );
        assert_eq!(
            p.registry_path,
            std::path::PathBuf::from(&home).join("registered_connections.json")
        );
        assert_eq!(
            p.log_path,
            std::path::PathBuf::from(&home)
                .join("log")
                .join("cmk-agent-ctl.log")
        );
        assert_eq!(
            p.legacy_pull_path,
            std::path::PathBuf::from(&home).join("allow-legacy-pull")
        );
    }
}
