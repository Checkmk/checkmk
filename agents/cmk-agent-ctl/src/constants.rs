// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
pub const DEFAULT_AGENT_PORT: &str = "6556";
pub const MAX_CONNECTIONS: usize = 3;
pub const CONNECTION_TIMEOUT: u64 = 20;
pub const PAIRING_PRESET_FILE: &str = "cmk-agent-ctl-config.json";
pub const REGISTRY_FILE: &str = "registered_connections.json";
pub const LEGACY_PULL_FILE: &str = "allow-legacy-pull";
pub const CONFIG_FILE: &str = "cmk-agent-ctl.toml";
#[cfg(unix)]
pub const CMK_AGENT_USER: &str = "cmk-agent";
#[cfg(unix)]
pub const ETC_DIR: &str = "/etc/check_mk";
#[cfg(unix)]
pub const AGENT_SOCKET: &str = "/run/check-mk-agent.socket";
//TODO(sk): Pass internal  port via cmdline
#[cfg(windows)]
#[allow(dead_code)] // TODO(sk): remove after integration will be confirmed
pub const WINDOWS_INTERNAL_PORT: &str = "50001";
#[cfg(windows)]
pub const ENV_PROGRAM_DATA: &str = "ProgramData";
#[cfg(windows)]
pub const WIN_AGENT_HOME_DIR: &str = "\\checkmk\\agent";
#[cfg(windows)]
pub const LOG_FILE: &str = "cmk-agent-ctl.log";
