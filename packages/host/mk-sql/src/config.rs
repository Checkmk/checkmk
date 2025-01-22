// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod defines;
pub mod ms_sql;
pub mod section;
pub mod system;
pub mod yaml;
use anyhow::{bail, Result};
use std::path::Path;

/// Contains config to check database(MS SQL)
#[derive(Default, Debug, PartialEq)]
pub struct CheckConfig {
    ms_sql: Option<ms_sql::Config>,
}

impl CheckConfig {
    pub fn load_file(file: &Path) -> Result<Self> {
        CheckConfig::load_vec_yaml(yaml::load_from_file(file)?)
    }
    pub fn load_str(content: &str) -> Result<Self> {
        CheckConfig::load_vec_yaml(yaml::load_from_str(content)?)
    }

    fn load_vec_yaml(data: Vec<yaml::Yaml>) -> Result<Self> {
        if data.is_empty() {
            bail!("Not yaml document");
        }
        Ok(CheckConfig {
            ms_sql: ms_sql::Config::from_yaml(&data[0])?,
        })
    }

    pub fn ms_sql(&self) -> Option<&ms_sql::Config> {
        self.ms_sql.as_ref()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    static YML_MINI_FILE: &str = include_str!("../tests/files/test-mini.yml");
    static NOT_YAML_FILE: &str = include_str!("../tests/files/not-yaml.yml");
    static NO_MSSQL_FILE: &str = include_str!("../tests/files/no-mssql.yml");

    #[test]
    fn test_check_config() {
        assert!(CheckConfig::load_str(NOT_YAML_FILE).is_err());
        assert!(CheckConfig::load_str(NO_MSSQL_FILE)
            .unwrap()
            .ms_sql()
            .is_none());
        assert!(CheckConfig::load_str(YML_MINI_FILE)
            .unwrap()
            .ms_sql()
            .is_some());
    }
}
