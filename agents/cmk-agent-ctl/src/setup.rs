// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(unix)]
use super::types;
use super::{cli, constants};
#[cfg(unix)]
use anyhow::Context;
use anyhow::Result as AnyhowResult;
use log::debug;
#[cfg(unix)]
use nix::unistd;
use std::env;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use structopt::StructOpt;

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
    pub registration_preset_path: PathBuf,
    pub registry_path: PathBuf,
    pub legacy_pull_path: PathBuf,
    #[cfg(windows)]
    pub log_path: PathBuf,
}

#[cfg(unix)]
impl PathResolver {
    pub fn new(home_dir: &Path) -> PathResolver {
        let etc_dir = PathBuf::from(constants::ETC_DIR);
        PathResolver {
            home_dir: PathBuf::from(home_dir),
            config_path: home_dir
                .join(constants::CONFIG_FILE)
                .exists_or(etc_dir.join(constants::CONFIG_FILE)),
            registration_preset_path: home_dir
                .join(constants::PAIRING_PRESET_FILE)
                .exists_or(etc_dir.join(constants::PAIRING_PRESET_FILE)),
            registry_path: home_dir.join(Path::new(constants::REGISTRY_FILE)),
            legacy_pull_path: home_dir.join(Path::new(constants::LEGACY_PULL_FILE)),
        }
    }
}

#[cfg(windows)]
impl PathResolver {
    pub fn new(home_dir: &Path) -> PathResolver {
        PathResolver {
            home_dir: PathBuf::from(home_dir),
            config_path: home_dir.join(Path::new(constants::CONFIG_FILE)),
            registration_preset_path: home_dir.join(Path::new(constants::PAIRING_PRESET_FILE)),
            registry_path: home_dir.join(Path::new(constants::REGISTRY_FILE)),
            legacy_pull_path: home_dir.join(Path::new(constants::LEGACY_PULL_FILE)),
            log_path: home_dir.join("log").join(Path::new(constants::LOG_FILE)),
        }
    }
}
trait ExistsOr {
    fn exists_or(self, other_path: PathBuf) -> PathBuf;
}

impl ExistsOr for PathBuf {
    fn exists_or(self, other_path: PathBuf) -> PathBuf {
        self.exists().then(|| self).unwrap_or(other_path)
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
pub fn agent_socket() -> types::AgentChannel {
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
fn agent_port() -> String {
    match env::var(constants::ENV_WINDOWS_INTERNAL_PORT) {
        Err(_) => String::from(constants::WINDOWS_INTERNAL_PORT),
        Ok(port) => {
            debug!("Using debug WINDOWS_INTERNAL_PORT: {}", port);
            port
        }
    }
}

#[cfg(windows)]
pub fn agent_channel() -> String {
    format!("localhost:{}", agent_port())
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
        .rotate(
            constants::log::FILE_MAX_SIZE,
            constants::log::FILE_NAMING,
            constants::log::FILE_CLEANUP,
        )
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
fn determine_paths(user: unistd::User) -> AnyhowResult<PathResolver> {
    Ok(PathResolver::new(&user.dir))
}

#[cfg(windows)]
fn determine_paths() -> AnyhowResult<PathResolver> {
    // Alternative home dir can be passed for testing/debug reasons
    if let Ok(debug_home_dir) = std::env::var(constants::ENV_HOME_DIR) {
        debug!("Using debug HOME_DIR: {}", debug_home_dir);
        return Ok(PathResolver::new(&PathBuf::from(debug_home_dir)));
    }

    // Normal/prod home dir
    let program_data_path = std::env::var(constants::ENV_PROGRAM_DATA)
        .unwrap_or_else(|_| String::from("c:\\ProgramData"));
    let home = PathBuf::from(program_data_path + constants::WIN_AGENT_HOME_DIR);
    Ok(PathResolver::new(&home))
}

#[cfg(unix)]
fn setup(args: &cli::Args) -> AnyhowResult<PathResolver> {
    if let Err(err) = init_logging(&args.logging_level()) {
        io::stderr()
            .write_all(format!("Failed to initialize logging: {:?}", err).as_bytes())
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
fn setup(args: &cli::Args) -> AnyhowResult<PathResolver> {
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

pub fn init() -> AnyhowResult<(cli::Args, PathResolver)> {
    if !is_os_supported() {
        eprintln!("This OS is unsupported");
        std::process::exit(1);
    }
    // Parse args as first action to directly exit from --help or malformatted arguments
    let args = cli::Args::from_args();
    let paths = setup(&args)?;
    Ok((args, paths))
}

#[cfg(test)]
mod tests {
    use super::*;

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
