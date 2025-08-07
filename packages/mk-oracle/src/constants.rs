// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::HostName;

use std::path::{Path, PathBuf};
use std::sync::LazyLock;
pub mod log {
    use flexi_logger::Naming;
    pub const FILE_MAX_SIZE: u64 = 500_000;
    pub const FILE_NAMING: Naming = Naming::Numbers;
    pub const FILE_MAX_COUNT: usize = 5;
}

pub const SQL_QUERY_EXTENSION: &str = "sql";

pub mod environment {
    pub const CONFIG_NAME: &str = "oracle.yml";
    pub const CONFIG_DIR_ENV_VAR: &str = "MK_CONFDIR";
    pub const LOG_DIR_ENV_VAR: &str = "MK_LOGDIR";
    pub const TEMP_DIR_ENV_VAR: &str = "MK_TEMPDIR";
    pub const STATE_DIR_ENV_VAR: &str = "MK_STATEDIR";
    pub const VAR_DIR_ENV_VAR: &str = "MK_VARDIR";
}

pub mod sqls {
    pub const DEFAULT_SEPARATOR: char = '|';
    pub const SEPARATOR_DECORATION: &str = "|| '{}' ||";
}

pub const ODBC_CONNECTION_TIMEOUT: u32 = 2;

pub static LOCAL_HOST: LazyLock<HostName> = LazyLock::new(|| "localhost".to_owned().into());

pub static DEFAULT_CONFIG_FILE: LazyLock<PathBuf> = LazyLock::new(|| {
    Path::new(&get_env_value(environment::CONFIG_DIR_ENV_VAR, ".")).join(environment::CONFIG_NAME)
});
pub static CONFIG_DIR: LazyLock<PathBuf> = LazyLock::new(|| Path::new(&get_conf_dir()).to_owned());
pub static ENV_LOG_DIR: LazyLock<Option<PathBuf>> = LazyLock::new(|| {
    std::env::var(environment::LOG_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from)
});
pub static ENV_TEMP_DIR: LazyLock<Option<PathBuf>> = LazyLock::new(|| {
    std::env::var(environment::TEMP_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from)
});
pub static ENV_STATE_DIR: LazyLock<Option<PathBuf>> = LazyLock::new(|| {
    std::env::var(environment::STATE_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from)
});
pub static ENV_VAR_DIR: LazyLock<Option<PathBuf>> = LazyLock::new(|| {
    std::env::var(environment::VAR_DIR_ENV_VAR)
        .ok()
        .map(PathBuf::from)
});

fn get_conf_dir() -> PathBuf {
    Path::new(&get_env_value(environment::CONFIG_DIR_ENV_VAR, ".")).to_owned()
}

pub fn get_env_value(var: &str, on_lack: &str) -> String {
    std::env::var(var).unwrap_or(on_lack.to_string())
}
