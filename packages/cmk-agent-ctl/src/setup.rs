// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use super::misc;
use super::{cli, constants, types};
#[cfg(unix)]
use anyhow::Context;
use anyhow::Result as AnyhowResult;
use clap::Parser;
#[cfg(windows)]
use flexi_logger::FileSpec;
use log::debug;
#[cfg(windows)]
use log::info;
#[cfg(unix)]
use nix::unistd;
use std::env;
use std::env::ArgsOs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};

// TODO(sk): estimate to move in constants
#[cfg(windows)]
fn to_version(major: &u64, minor: &u64) -> u64 {
    major * 100 + minor
}

fn is_os_supported() -> bool {
    #[cfg(windows)]
    {
        let info = os_info::get();
        match info.version() {
            os_info::Version::Semantic(major, minor, _patch) => {
                to_version(major, minor)
                    >= to_version(
                        &constants::MIN_WIN_VERSION_MAJOR,
                        &constants::MIN_WIN_VERSION_MINOR,
                    )
            }
            _ => false,
        }
    }

    #[cfg(unix)]
    true
}

pub struct PathResolver {
    pub home_dir: PathBuf,
    pub config_path: PathBuf,
    pub pre_configured_connections_path: PathBuf,
    pub registry_path: PathBuf,
}

#[cfg(unix)]
impl PathResolver {
    pub fn new(home_dir: &Path) -> PathResolver {
        PathResolver {
            home_dir: PathBuf::from(home_dir),
            config_path: home_dir.join(constants::CONFIG_FILE),
            pre_configured_connections_path: home_dir
                .join(constants::PRE_CONFIGURED_CONNECTIONS_FILE),
            registry_path: home_dir.join(Path::new(constants::REGISTRY_FILE)),
        }
    }
}

#[cfg(windows)]
impl PathResolver {
    pub fn new(home_dir: &Path) -> PathResolver {
        PathResolver {
            home_dir: PathBuf::from(home_dir),
            config_path: home_dir.join(Path::new(constants::CONFIG_FILE)),
            pre_configured_connections_path: home_dir
                .join(Path::new(constants::PRE_CONFIGURED_CONNECTIONS_FILE)),
            registry_path: home_dir.join(Path::new(constants::REGISTRY_FILE)),
        }
    }
}

pub fn connection_timeout() -> u64 {
    match env::var(constants::ENV_CONNECTION_TIMEOUT) {
        Err(_) => constants::CONNECTION_TIMEOUT,
        Ok(timeout) => {
            let max = timeout.parse().unwrap();
            debug!("Using debug value for CONNECTION_TIMEOUT: {}", max);
            max
        }
    }
}

pub fn max_connections() -> usize {
    match env::var(constants::ENV_MAX_CONNECTIONS) {
        Err(_) => constants::MAX_CONNECTIONS,
        Ok(max) => {
            let max = max.parse().unwrap();
            debug!("Using debug value for MAX_CONNECTIONS: {}", max);
            max
        }
    }
}

#[cfg(unix)]
pub fn agent_channel() -> types::AgentChannel {
    match env::var(constants::ENV_HOME_DIR) {
        Err(_) => constants::UNIX_AGENT_SOCKET.into(),
        Ok(home_dir) => {
            let sock = PathBuf::from(home_dir).join(
                PathBuf::from(constants::UNIX_AGENT_SOCKET)
                    .strip_prefix("/")
                    .unwrap(),
            );
            debug!("Using debug UNIX socket: {:?}", &sock);
            sock.into()
        }
    }
}

#[cfg(windows)]
pub fn agent_channel() -> types::AgentChannel {
    use crate::mailslot_transport;
    types::AgentChannel::from(
        format!("ms/{}", mailslot_transport::service_mailslot_name()).as_ref(),
    )
}

#[cfg(unix)]
fn init_logging(level: &str) -> Result<flexi_logger::LoggerHandle, flexi_logger::FlexiLoggerError> {
    flexi_logger::Logger::try_with_env_or_str(level)?
        .log_to_stderr()
        .format(flexi_logger::default_format)
        .start()
}

#[cfg(windows)]
fn make_log_file_spec() -> FileSpec {
    FileSpec::default()
        .directory(env::var(constants::ENV_AGENT_LOG_DIR).unwrap_or_else(|_| ".".to_owned()))
        .suppress_timestamp()
        .basename("cmk-agent-ctl")
}

#[cfg(windows)]
fn init_logging(
    level: &str,
    duplicate_level: flexi_logger::Duplicate,
) -> Result<flexi_logger::LoggerHandle, flexi_logger::FlexiLoggerError> {
    let mut logger = flexi_logger::Logger::try_with_env_or_str(level)?;

    logger = match duplicate_level {
        flexi_logger::Duplicate::None => {
            logger.log_to_writer(crate::log_ext::make_mailslot_logger(level))
        }
        _ => logger.log_to_stderr(),
    };
    if env::var(constants::ENV_LOG_TO_FILE).unwrap_or_default() == "1" {
        logger = logger.log_to_file(make_log_file_spec());
    }
    logger
        .append()
        .format(flexi_logger::detailed_format)
        .rotate(
            constants::log::FILE_MAX_SIZE,
            constants::log::FILE_NAMING,
            constants::log::FILE_CLEANUP,
        )
        .start()
}

#[cfg(unix)]
fn become_user(username: &str) -> AnyhowResult<unistd::User> {
    let target_user = unistd::User::from_name(username)?.context(format!(
        "Could not find dedicated Checkmk agent user {username}"
    ))?;

    // If we already are the right user, return early. Otherwise, eg. setting the supplementary
    // group ids will fail due to insufficient permissions.
    if target_user.uid == unistd::getuid() {
        return Ok(target_user);
    }

    unistd::setgroups(&[target_user.gid]).context(format!(
        "Failed to set supplementary group id {} corresponding to user {}",
        target_user.gid, target_user.name,
    ))?;
    unistd::setgid(target_user.gid).context(format!(
        "Failed to set group id {} corresponding to user {}",
        target_user.gid, target_user.name,
    ))?;
    unistd::setuid(target_user.uid).context(format!(
        "Failed to set user id {} corresponding to user {}",
        target_user.uid, target_user.name,
    ))?;

    Ok(target_user)
}

#[cfg(unix)]
fn determine_paths(user: unistd::User) -> AnyhowResult<PathResolver> {
    Ok(PathResolver::new(&user.dir))
}

#[cfg(windows)]
fn determine_paths() -> AnyhowResult<PathResolver> {
    // Alternative home dir can be passed for testing/debug reasons
    if let Ok(debug_home_dir) = std::env::var(constants::ENV_HOME_DIR) {
        info!("Using debug HOME_DIR: {}", debug_home_dir);
        return Ok(PathResolver::new(&PathBuf::from(debug_home_dir)));
    }

    // Normal/prod home dir
    let program_data_path = std::env::var(constants::ENV_PROGRAM_DATA)
        .unwrap_or_else(|_| String::from("c:\\ProgramData"));
    let home = PathBuf::from(program_data_path + constants::WIN_AGENT_HOME_DIR);
    Ok(PathResolver::new(&home))
}

#[cfg(unix)]
fn setup(cli: &cli::Cli) -> AnyhowResult<PathResolver> {
    if let Err(err) = init_logging(&cli.logging_level()) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {err:?}").as_bytes())
            .unwrap_or(());
    }

    match env::var(constants::ENV_HOME_DIR) {
        // Alternative home dir can be passed for testing/debug reasons
        Ok(debug_home_dir) => {
            debug!("Skipping to change user and using debug HOME_DIR: {}", debug_home_dir);
            Ok(PathResolver::new(Path::new(&debug_home_dir)))
        },
        // Normal/prod home dir
        Err(_) => become_user(constants::CMK_AGENT_USER).context(format!(
                "Failed to run as user '{}'. Please execute with sufficient permissions (maybe try 'sudo').",
                constants::CMK_AGENT_USER,
            )).and_then(determine_paths),
    }
}

#[cfg(windows)]
fn setup(cli: &cli::Cli) -> AnyhowResult<PathResolver> {
    let paths = determine_paths()?;
    let duplicate_level = if let cli::Mode::Daemon(_) = cli.mode {
        flexi_logger::Duplicate::None
    } else {
        flexi_logger::Duplicate::All
    };
    if let Err(err) = init_logging(&cli.logging_level(), duplicate_level) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", err).as_bytes())
            .unwrap_or(());
    }
    Ok(paths)
}

pub fn init(args: ArgsOs) -> AnyhowResult<(cli::Cli, PathResolver)> {
    if !is_os_supported() {
        eprintln!("This OS is unsupported");
        std::process::exit(1);
    }
    // Parse args as first action to directly exit from --help or malformatted arguments
    let cli = cli::Cli::parse_from(args);
    #[cfg(windows)]
    misc::validate_elevation()?;

    let paths = setup(&cli)?;
    Ok((cli, paths))
}

#[cfg(test)]
mod tests {
    use super::*;

    // build
    #[test]
    fn test_paths() {
        let home_dir = std::path::Path::new("/a/b/c");
        assert_eq!(PathResolver::new(home_dir).home_dir, home_dir);
    }

    #[cfg(windows)]
    #[test]
    fn test_windows_paths() {
        let p = determine_paths().unwrap();
        let home = String::from("C:\\ProgramData") + constants::WIN_AGENT_HOME_DIR;
        assert_eq!(p.home_dir, std::path::PathBuf::from(&home));
        assert_eq!(
            p.pre_configured_connections_path,
            std::path::PathBuf::from(&home).join("pre_configured_connections.json")
        );
        assert_eq!(
            p.registry_path,
            std::path::PathBuf::from(&home).join("registered_connections.json")
        );
    }

    #[cfg(windows)]
    #[test]
    fn test_make_log_file_spec() {
        assert_eq!(
            make_log_file_spec().as_pathbuf(None).to_str().unwrap(),
            ".\\cmk-agent-ctl.log".to_owned()
        )
    }
}
