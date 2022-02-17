// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::types;
use anyhow::Result as AnyhowResult;
use std::{
    path::{Path, PathBuf},
    str::FromStr,
};

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";
//TODO: Pass agent port via cmdline(Windows/Linux) or config(Linux).
pub const AGENT_PORT: &str = "6556";
pub const MAX_CONNECTIONS: usize = 3;
pub const CONNECTION_TIMEOUT: u64 = 20;

//TODO(sk): Pass internal  port via cmdline
#[cfg(windows)]
#[allow(dead_code)] // TODO(sk): remove after integration will be confirmed
pub const WINDOWS_INTERNAL_PORT: &str = "50001";

#[cfg(windows)]
pub const ENV_PROGRAM_DATA: &str = "ProgramData";
#[cfg(windows)]
pub const WIN_AGENT_HOME_DIR: &str = "\\checkmk\\agent";

const PAIRING_PRESET_FILE: &str = "cmk-agent-ctl-config.json";
const REGISTRY_FILE: &str = "registered_connections.json";
const LEGACY_PULL_FILE: &str = "allow-legacy-pull";
#[cfg(unix)]
const ETC_DIR: &str = "/etc/check_mk";
#[cfg(windows)]
const LOG_FILE: &str = "cmk-agent-ctl.log";

pub struct PathResolver {
    pub home_dir: PathBuf,
    pub registration_preset_path: PathBuf,
    pub registry_path: PathBuf,
    pub legacy_pull_path: PathBuf,
    #[cfg(windows)]
    pub log_path: PathBuf,
}

impl PathResolver {
    pub fn new(home_dir: &Path) -> PathResolver {
        #[cfg(unix)]
        let etc_dir = PathBuf::from(ETC_DIR);
        PathResolver {
            home_dir: PathBuf::from(home_dir),
            #[cfg(unix)]
            registration_preset_path: home_dir
                .join(PAIRING_PRESET_FILE)
                .exists_or(etc_dir.join(PAIRING_PRESET_FILE)),
            #[cfg(windows)]
            registration_preset_path: home_dir.join(Path::new(PAIRING_PRESET_FILE)),
            registry_path: home_dir.join(Path::new(REGISTRY_FILE)),
            legacy_pull_path: home_dir.join(Path::new(LEGACY_PULL_FILE)),
            #[cfg(windows)]
            log_path: home_dir.join("log").join(Path::new(LOG_FILE)),
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

pub fn agent_port() -> AnyhowResult<types::Port> {
    types::Port::from_str(AGENT_PORT)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_paths() {
        let home_dir = std::path::Path::new("/a/b/c");
        assert_eq!(PathResolver::new(home_dir).home_dir, home_dir);
    }
}
