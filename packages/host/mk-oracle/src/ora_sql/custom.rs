// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::constants::CONFIG_DIR;
use std::path::PathBuf;

pub const ORA_SQL_CUSTOM_SQL_SUB_DIR: &str = "orasql";

pub fn get_sql_dir() -> Option<PathBuf> {
    let path = CONFIG_DIR.join(ORA_SQL_CUSTOM_SQL_SUB_DIR);
    if path.is_dir() {
        Some(path)
    } else {
        None
    }
}
