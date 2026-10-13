// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The on-disk environment the controller runs in: where its files live for a
//! given deployment layout, selected by [`SetupMode`].

use crate::constants;
use std::path::{Path, PathBuf};

/// Deployment mode of the agent controller, selecting the on-disk directory layout.
pub enum SetupMode {
    /// Classic package deployment: files are deployed in a some system directory:
    /// `/var/lib/cmk-agent`(fixed) for Linux
    /// `%ProgramData%\checkmk\agent` for Windows.
    Classic,
    /// Single directory deployment, Linux only: config and runtime split below the
    /// installation directory.
    #[cfg(unix)]
    SingleDir,
}

pub struct PathResolver {
    pub config_path: PathBuf,
    pub pre_configured_connections_path: PathBuf,
    pub registry_path: PathBuf,

    /// Baked by the site, read-only for the controller.
    pub updater_config_path: PathBuf,

    /// Owned and written by the controller.
    pub updater_state_path: PathBuf,

    /// Part of the installed agent package, read-only for the controller.
    /// In the classic layout on Linux this points outside the controller's own
    /// directory and may be unreadable for the user the controller runs as.
    pub agent_info_path: PathBuf,

    /// Holds a verified agent package until the installer has taken it. Written
    /// by the controller, read by the privileged installer.
    pub updater_package_dir: PathBuf,
}

impl PathResolver {
    /// Resolve the paths of the controller's files for a given deployment mode.
    pub fn new(mode: SetupMode, base_dir: &Path) -> PathResolver {
        match mode {
            SetupMode::Classic => PathResolver::from_home(base_dir),
            #[cfg(unix)]
            SetupMode::SingleDir => PathResolver::from_install(base_dir),
        }
    }

    /// Classic layout: all files live directly in `home_dir`.
    ///
    /// `home_dir` is a fixed system directory:
    /// - `/var/lib/cmk-agent` on Linux
    /// - `%ProgramData%\checkmk\agent` on Windows.
    fn from_home(home_dir: &Path) -> PathResolver {
        PathResolver {
            config_path: home_dir.join(constants::CONFIG_FILE),
            pre_configured_connections_path: home_dir
                .join(constants::PRE_CONFIGURED_CONNECTIONS_FILE),
            registry_path: home_dir.join(constants::REGISTRY_FILE),
            updater_config_path: home_dir.join(constants::UPDATER_CONFIG_FILE),
            updater_state_path: home_dir.join(constants::UPDATER_STATE_FILE),
            agent_info_path: if cfg!(windows) {
                home_dir.join("install").join(constants::AGENT_INFO_FILE)
            } else {
                // The agent info belongs to the agent package, not to the controller's own
                // deployment, so in the classic layout its directory lies outside `home_dir`
                // and has to be guessed here - the agent's real library directory is not
                // knowable to the controller. The guess may also be unreadable for the user
                // the controller runs as. Good enough, because the integrated updater is not
                // officially supported for the classic layout on Linux.
                Path::new("/usr/lib/check_mk_agent").join(constants::AGENT_INFO_FILE)
            },
            // `$MK_LIBDIR/update` on Windows: `MK_LIBDIR` is the agent's user
            // directory (`agents/wnx/src/engine/cfg.cpp`), which is `home_dir`.
            updater_package_dir: home_dir.join(constants::UPDATER_PACKAGE_DIR),
        }
    }

    /// Single directory deployment, Linux only: baked files below `package/config` and
    /// `package/agent`, files owned by the controller below `runtime/controller`, all
    /// relative to `install_dir`.
    #[cfg(unix)]
    fn from_install(install_dir: &Path) -> PathResolver {
        let config_dir = install_dir.join("package/config");
        let runtime_dir = install_dir.join("runtime/controller");
        let agent_dir = install_dir.join("package/agent");
        PathResolver {
            config_path: config_dir.join(constants::CONFIG_FILE),
            pre_configured_connections_path: config_dir
                .join(constants::PRE_CONFIGURED_CONNECTIONS_FILE),
            registry_path: runtime_dir.join(constants::REGISTRY_FILE),
            updater_config_path: config_dir.join(constants::UPDATER_CONFIG_FILE),
            updater_state_path: runtime_dir.join(constants::UPDATER_STATE_FILE),
            agent_info_path: agent_dir.join(constants::AGENT_INFO_FILE),
            updater_package_dir: runtime_dir.join(constants::UPDATER_PACKAGE_DIR),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classic_paths() {
        let home_dir = Path::new("/a/b/c");
        let paths = PathResolver::new(SetupMode::Classic, home_dir);
        assert_eq!(paths.config_path, home_dir.join("cmk-agent-ctl.toml"));
        assert_eq!(
            paths.pre_configured_connections_path,
            home_dir.join("pre_configured_connections.json")
        );
        assert_eq!(
            paths.registry_path,
            home_dir.join("registered_connections.json")
        );
        assert_eq!(
            paths.updater_config_path,
            home_dir.join("cmk-agent-ctl-update.toml")
        );
        assert_eq!(
            paths.updater_state_path,
            home_dir.join("agent-update-state.json")
        );
        // `$MK_LIBDIR/update` on Windows.
        assert_eq!(paths.updater_package_dir, home_dir.join("update"));
        if cfg!(windows) {
            assert_eq!(
                paths.agent_info_path,
                home_dir.join("install").join("checkmk.dat")
            );
        } else {
            // Not below `home_dir`: the classic Linux layout keeps the agent info
            // in a fixed system directory.
            assert_eq!(
                paths.agent_info_path,
                PathBuf::from("/usr/lib/check_mk_agent/agent_info.json")
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn test_single_dir_paths() {
        let install_dir = Path::new("/a/b/c");
        let paths = PathResolver::new(SetupMode::SingleDir, install_dir);
        assert_eq!(
            paths.config_path,
            install_dir.join("package/config/cmk-agent-ctl.toml")
        );
        assert_eq!(
            paths.pre_configured_connections_path,
            install_dir.join("package/config/pre_configured_connections.json")
        );
        assert_eq!(
            paths.registry_path,
            install_dir.join("runtime/controller/registered_connections.json")
        );
        assert_eq!(
            paths.updater_config_path,
            install_dir.join("package/config/cmk-agent-ctl-update.toml")
        );
        assert_eq!(
            paths.updater_state_path,
            install_dir.join("runtime/controller/agent-update-state.json")
        );
        assert_eq!(
            paths.agent_info_path,
            install_dir.join("package/agent/agent_info.json")
        );
        assert_eq!(
            paths.updater_package_dir,
            install_dir.join("runtime/controller/update")
        );
    }
}
