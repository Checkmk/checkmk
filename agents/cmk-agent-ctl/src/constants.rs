// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const VERSION: &str = env!("CARGO_PKG_VERSION");

// CONFIGURATION
pub const DEFAULT_PULL_PORT: &str = "6556";
pub const MAX_CONNECTIONS: usize = 3;
pub const CONNECTION_TIMEOUT: u64 = 20;
#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";
#[cfg(unix)]
pub const UNIX_AGENT_SOCKET: &str = "/run/check-mk-agent.socket";
//TODO(sk): Pass internal port via cmdline
#[cfg(windows)]
#[allow(dead_code)] // TODO(sk): remove after integration will be confirmed
pub const WINDOWS_INTERNAL_PORT: &str = "50001";

// FILES
pub const PAIRING_PRESET_FILE: &str = "cmk-agent-ctl-config.json";
pub const REGISTRY_FILE: &str = "registered_connections.json";
pub const LEGACY_PULL_FILE: &str = "allow-legacy-pull";
pub const CONFIG_FILE: &str = "cmk-agent-ctl.toml";
#[cfg(windows)]
pub const LOG_FILE: &str = "cmk-agent-ctl.log";

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
