// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::cli;
use super::constants;
#[cfg(unix)]
use anyhow::Context;
use anyhow::Result as AnyhowResult;
#[cfg(unix)]
use nix::unistd;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use structopt::StructOpt;

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
fn determine_paths(user: unistd::User) -> AnyhowResult<PathResolver> {
    Ok(PathResolver::new(&user.dir))
}

#[cfg(windows)]
fn determine_paths() -> AnyhowResult<PathResolver> {
    let program_data_path = std::env::var(constants::ENV_PROGRAM_DATA)
        .unwrap_or_else(|_| String::from("c:\\ProgramData"));
    let home = std::path::PathBuf::from(program_data_path + constants::WIN_AGENT_HOME_DIR);
    Ok(PathResolver::new(&home))
}

#[cfg(unix)]
fn setup(args: &cli::Args) -> AnyhowResult<PathResolver> {
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
