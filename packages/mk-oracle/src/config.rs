// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod authentication;
pub mod connection;
pub mod defines;
mod options;
pub mod ora_sql;
pub mod section;
pub mod system;
pub mod yaml;

use anyhow::{bail, Result};
use std::path::Path;

/// Contains config to check Oracle database
#[derive(Default, Debug, PartialEq)]
pub struct OracleConfig {
    ora_sql: Option<ora_sql::Config>,
}

impl OracleConfig {
    pub fn load_file(file: &Path) -> Result<Self> {
        OracleConfig::load_vec_yaml(yaml::load_from_file(file)?)
    }
    pub fn load_str(content: &str) -> Result<Self> {
        OracleConfig::load_vec_yaml(yaml::load_from_str(content)?)
    }

    fn load_vec_yaml(data: Vec<yaml::Yaml>) -> Result<Self> {
        if data.is_empty() {
            bail!("Not yaml document");
        }
        Ok(OracleConfig {
            ora_sql: ora_sql::Config::from_yaml(&data[0])?,
        })
    }

    pub fn ora_sql(&self) -> Option<&ora_sql::Config> {
        self.ora_sql.as_ref()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    static YML_MINI_FILE: &str = include_str!("../tests/files/test-mini.yml");
    static NOT_YAML_FILE: &str = include_str!("../tests/files/not-yaml.yml");
    static NOT_ORA_SQL_FILE: &str = include_str!("../tests/files/not-ora_sql.yml");

    #[test]
    fn test_check_config() {
        assert!(OracleConfig::load_str(NOT_YAML_FILE).is_err());
        assert!(OracleConfig::load_str(NOT_ORA_SQL_FILE)
            .unwrap()
            .ora_sql()
            .is_none());
        assert!(OracleConfig::load_str(YML_MINI_FILE)
            .unwrap()
            .ora_sql()
            .is_some());
    }
}
