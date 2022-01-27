// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::path::{Path, PathBuf};

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";
//TODO: Pass agent port via cmdline or config.
pub const AGENT_PORT: &str = "6556";

const CONFIG_FILE: &str = "cmk-agent-ctl-config.json";
const REGISTRY_FILE: &str = "registered_connections.json";
const LOG_FILE: &str = "cmk-agent-ctl.log";
const LEGACY_PULL_FILE: &str = "allow-legacy-pull";

pub struct Paths {
    pub home_dir: PathBuf,
    pub config_path: PathBuf,
    pub registry_path: PathBuf,
    pub log_path: PathBuf,
    pub legacy_pull_path: PathBuf,
}

impl Paths {
    pub fn new(home_dir: &Path) -> Paths {
        Paths {
            home_dir: std::path::PathBuf::from(home_dir),
            config_path: home_dir.join(Path::new(CONFIG_FILE)),
            registry_path: home_dir.join(Path::new(REGISTRY_FILE)),
            log_path: home_dir.join(Path::new(LOG_FILE)),
            legacy_pull_path: home_dir.join(Path::new(LEGACY_PULL_FILE)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_paths() {
        let home_dir = std::path::Path::new("/a/b/c");
        assert_eq!(Paths::new(home_dir).home_dir, home_dir);
    }
}
