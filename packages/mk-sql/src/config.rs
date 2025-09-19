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
        let data = yaml::load_from_file(file)?;
        if data.is_empty() {
            bail!("Not yaml document");
        }
        Ok(CheckConfig {
            ms_sql: ms_sql::Config::from_yaml(&data[0])?,
        })
    }

    pub fn load_str(data: &str) -> Result<Self> {
        let data = yaml::load_from_str(data)?;
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
    use lazy_static::lazy_static;
    use std::path::PathBuf;

    lazy_static! {
        static ref YML_MINI_FILE: PathBuf = PathBuf::new()
            .join("tests")
            .join("files")
            .join("test-mini.yml");
        static ref NOT_YAML_FILE: PathBuf = PathBuf::new()
            .join("tests")
            .join("files")
            .join("not-yaml.txt");
        static ref NO_MSSQL_FILE: PathBuf = PathBuf::new()
            .join("tests")
            .join("files")
            .join("no-mssql.yml");
    }

    #[test]
    fn test_check_config() {
        assert!(CheckConfig::load_file(&NOT_YAML_FILE).is_err());
        assert!(CheckConfig::load_file(&NO_MSSQL_FILE)
            .unwrap()
            .ms_sql()
            .is_none());
        assert!(CheckConfig::load_file(&YML_MINI_FILE)
            .unwrap()
            .ms_sql()
            .is_some());
    }
}
