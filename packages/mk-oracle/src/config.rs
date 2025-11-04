// Copyright (C) 2025 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

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
