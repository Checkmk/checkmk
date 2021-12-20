// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::path::{Path, PathBuf};

#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";

const HOME_DIR: &str = "/var/lib/cmk-agent";
const CONFIG_FILE: &str = "cmk-agent-ctl-config.json";
const REGISTRY_FILE: &str = "registered_connections.json";
const LOG_FILE: &str = "cmk-agent-ctl.log";
const LEGACY_PULL_FILE: &str = "allow-legacy-pull";

pub fn home_dir() -> PathBuf {
    PathBuf::from(HOME_DIR)
}

pub fn config_path() -> PathBuf {
    home_dir().join(Path::new(CONFIG_FILE))
}

pub fn registry_path() -> PathBuf {
    home_dir().join(Path::new(REGISTRY_FILE))
}

pub fn log_path() -> PathBuf {
    home_dir().join(Path::new(LOG_FILE))
}

pub fn legacy_pull_path() -> PathBuf {
    home_dir().join(Path::new(LEGACY_PULL_FILE))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_home_dir() {
        assert_eq!(home_dir().to_string_lossy(), HOME_DIR);
    }

    #[test]
    fn test_config_path() {
        assert!(config_path().ends_with(CONFIG_FILE));
    }

    #[test]
    fn test_registry_path() {
        assert!(registry_path().ends_with(REGISTRY_FILE));
    }

    #[test]
    fn test_log_path() {
        assert!(log_path().ends_with(LOG_FILE));
    }

    #[test]
    fn test_legacy_pull_path() {
        assert!(legacy_pull_path().ends_with(LEGACY_PULL_FILE));
    }
}
