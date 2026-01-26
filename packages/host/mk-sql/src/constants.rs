// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub const VERSION: &str = "2.4.0p21";
use crate::types::HostName;

use lazy_static::lazy_static;
use std::path::{Path, PathBuf};
pub mod log {
    use flexi_logger::Naming;
    pub const FILE_MAX_SIZE: u64 = 500_000;
    pub const FILE_NAMING: Naming = Naming::Numbers;
    pub const FILE_MAX_COUNT: usize = 5;
}

pub const SQL_QUERY_EXTENSION: &str = "sql";

pub mod environment {
    pub const CONFIG_NAME: &str = "mk-sql.yml";
    pub const CONFIG_DIR_ENV_VAR: &str = "MK_CONFDIR";
    pub const LOG_DIR_ENV_VAR: &str = "MK_LOGDIR";
    pub const TEMP_DIR_ENV_VAR: &str = "MK_TEMPDIR";
    pub const STATE_DIR_ENV_VAR: &str = "MK_STATEDIR";
    pub const VAR_DIR_ENV_VAR: &str = "MK_VARDIR";
}

pub const ODBC_CONNECTION_TIMEOUT: u32 = 2;

lazy_static! {
    pub static ref LOCAL_HOST: HostName = "localhost".to_owned().into();
    pub static ref DEFAULT_CONFIG_FILE: PathBuf =
        Path::new(&get_env_value(environment::CONFIG_DIR_ENV_VAR, "."))
            .join(environment::CONFIG_NAME);
    pub static ref CONFIG_DIR: PathBuf = Path::new(&get_conf_dir()).to_owned();
    pub static ref ENV_LOG_DIR: Option<PathBuf> = std::env::var(environment::LOG_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from);
    pub static ref ENV_TEMP_DIR: Option<PathBuf> = std::env::var(environment::TEMP_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from);
    pub static ref ENV_STATE_DIR: Option<PathBuf> = std::env::var(environment::STATE_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from);
    pub static ref ENV_VAR_DIR: Option<PathBuf> = std::env::var(environment::VAR_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from);
}

fn get_conf_dir() -> PathBuf {
    Path::new(&get_env_value(environment::CONFIG_DIR_ENV_VAR, ".")).to_owned()
}

pub fn get_env_value(var: &str, on_lack: &str) -> String {
    std::env::var(var).unwrap_or(on_lack.to_string())
}

#[cfg(test)]
pub mod tests {
    use crate::types::InstanceName;
    use std::collections::HashSet;
    pub fn expected_instances_in_config() -> HashSet<InstanceName> {
        [
            "MSSQLSERVER",
            "SQLEXPRESS_NAME",
            "SQLEXPRESS_WOW",
            "INST1", // in text
            "INST2", // in text
        ]
        .iter()
        .map(|&s| InstanceName::from(s))
        .collect()
    }
}
