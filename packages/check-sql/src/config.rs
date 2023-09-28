// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod ms_sql;
mod yaml;
use ms_sql::MsSql;
use std::path::Path;

/// Contains config to check database(MS SQL)
pub struct CheckConfig {
    _ms_sql: Option<MsSql>,
}

impl CheckConfig {
    pub fn load_file(file: &Path) -> anyhow::Result<Self> {
        let _ = yaml::load_from_file(file);
        Ok(CheckConfig {
            _ms_sql: Some(MsSql {}),
        })
    }
}
