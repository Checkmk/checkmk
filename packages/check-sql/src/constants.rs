// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use lazy_static::lazy_static;
use std::path::{Path, PathBuf};
pub mod log {
    use flexi_logger::{Cleanup, Criterion, Naming};
    pub const FILE_MAX_SIZE: Criterion = Criterion::Size(100000);
    pub const FILE_NAMING: Naming = Naming::Numbers;
    pub const FILE_CLEANUP: Cleanup = Cleanup::KeepLogFiles(5);
}

pub mod environment {
    pub const CONFIG_NAME: &str = "check-sql.yml";
    pub const CONFIG_DIR_ENV_VAR: &str = "MK_CONFDIR";
}

lazy_static! {
    pub static ref DEFAULT_CONFIG_FILE: PathBuf =
        Path::new(&get_env_value(environment::CONFIG_DIR_ENV_VAR, "."))
            .join(environment::CONFIG_NAME);
}

fn get_env_value(var: &str, on_lack: &str) -> String {
    std::env::var(var).unwrap_or(on_lack.to_string())
}
