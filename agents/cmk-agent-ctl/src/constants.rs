// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const VERSION: &str = "2.1.0p3";

// CONFIGURATION
pub const DEFAULT_PULL_PORT: u16 = 6556;
pub const MAX_CONNECTIONS: usize = 3;
pub const CONNECTION_TIMEOUT: u64 = 20;
#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";
#[cfg(unix)]
pub const UNIX_AGENT_SOCKET: &str = "/run/check-mk-agent.socket";
#[cfg(windows)]
pub const WINDOWS_INTERNAL_PORT: &str = "28250";

// FILES
pub const REGISTRATION_PRESET_FILE: &str = "registration_preset.json";
pub const REGISTRY_FILE: &str = "registered_connections.json";
pub const LEGACY_PULL_FILE: &str = "allow-legacy-pull";
pub const CONFIG_FILE: &str = "cmk-agent-ctl.toml";

// DIRS
#[cfg(unix)]
pub const ETC_DIR: &str = "/etc/check_mk";
#[cfg(windows)]
pub const WIN_AGENT_HOME_DIR: &str = "\\checkmk\\agent";

// ENV VARS
pub const ENV_HOME_DIR: &str = "DEBUG_HOME_DIR";
pub const ENV_MAX_CONNECTIONS: &str = "DEBUG_MAX_CONNECTIONS";
pub const ENV_CONNECTION_TIMEOUT: &str = "DEBUG_CONNECTION_TIMEOUT";
#[cfg(windows)]
pub const ENV_WINDOWS_INTERNAL_PORT: &str = "DEBUG_WINDOWS_INTERNAL_PORT";
#[cfg(windows)]
pub const ENV_PROGRAM_DATA: &str = "ProgramData";

// Windows version
// https://en.wikipedia.org/wiki/List_of_Microsoft_Windows_versions
// We support only relative new version of Windows because of Rust toolchain:
// Server 2008 R2 & Windows 7, i.e. 6.1
#[cfg(windows)]
pub const MIN_WIN_VERSION_MAJOR: u64 = 6;
#[cfg(windows)]
pub const MIN_WIN_VERSION_MINOR: u64 = 1;

// Log Rotation default parameters
#[cfg(windows)]
pub mod log {
    use flexi_logger::{Cleanup, Criterion, Naming};
    pub const FILE_MAX_SIZE: Criterion = Criterion::Size(500000);
    pub const FILE_NAMING: Naming = Naming::Numbers;
    pub const FILE_CLEANUP: Cleanup = Cleanup::KeepLogFiles(5);
}
