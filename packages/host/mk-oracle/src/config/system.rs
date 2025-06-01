// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::yaml::{Get, Yaml};
use crate::utils;
use anyhow::Result;
use std::path::Path;
use yaml_rust2::YamlLoader;

mod keys {
    pub const SYSTEM: &str = "system";
    pub const LOGGING: &str = "logging";

    pub const LEVEL: &str = "level";
    pub const MAX_SIZE: &str = "max_size";
    pub const MAX_COUNT: &str = "max_count";
}

mod defaults {
    use crate::constants;
    pub const LOG_LEVEL: log::Level = log::Level::Info;
    pub const LOG_MAX_SIZE: u64 = constants::log::FILE_MAX_SIZE;
    pub const LOG_MAX_COUNT: usize = constants::log::FILE_MAX_COUNT;
}

#[derive(PartialEq, Debug, Default)]
pub struct SystemConfig {
    logging: Logging,
}

#[derive(PartialEq, Debug, Default, Clone)]
pub struct Logging {
    level: Option<log::Level>,
    max_size: Option<u64>,
    max_count: Option<usize>,
}

impl Logging {
    pub fn from_string(source: &str) -> Result<Option<Self>> {
        YamlLoader::load_from_str(source)?
            .first()
            .and_then(|e| Logging::from_yaml(e).transpose())
            .transpose()
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let logging = yaml.get(keys::LOGGING);
        if logging.is_badvalue() {
            return Ok(None);
        }

        Logging::parse_logging_from_yaml(logging)
    }

    fn parse_logging_from_yaml(logging: &Yaml) -> Result<Option<Self>> {
        use std::str::FromStr;
        let level = logging
            .get_string(keys::LEVEL)
            .and_then(|s| log::Level::from_str(&s).ok());
        let max_size = logging.get_int(keys::MAX_SIZE);
        let max_count = logging.get_int(keys::MAX_COUNT);

        Ok(Some(Self {
            level,
            max_size,
            max_count,
        }))
    }

    pub fn level(&self) -> log::Level {
        self.level.unwrap_or(defaults::LOG_LEVEL)
    }
    pub fn max_size(&self) -> u64 {
        self.max_size.unwrap_or(defaults::LOG_MAX_SIZE)
    }
    pub fn max_count(&self) -> usize {
        self.max_count.unwrap_or(defaults::LOG_MAX_COUNT)
    }
}

impl SystemConfig {
    pub fn load_file(file: &Path) -> Result<Self> {
        match utils::read_file(file) {
            Ok(content) => Self::from_string(&content),
            Err(e) => anyhow::bail!(
                "Can't read file: {}, {e} ",
                // Use relatively complicated  method to print name of the file
                // as it is not possible to use "{file_name:?}": produces to many backslashes
                // in Windows. Probability to NOT decode filename as UTF-8 is nil.
                file.as_os_str().to_str().unwrap_or("")
            ),
        }
    }

    pub fn from_string(source: &str) -> Result<Self> {
        YamlLoader::load_from_str(source)?
            .first()
            .map(SystemConfig::from_yaml)
            .unwrap_or_else(|| Ok(Self::default()))
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let system: &yaml_rust2::Yaml = yaml.get(keys::SYSTEM);
        if system.is_badvalue() {
            return Ok(Self::default());
        }

        let logging = Logging::from_yaml(system)?.unwrap_or_default();

        Ok(Self { logging })
    }
    pub fn logging(&self) -> &Logging {
        &self.logging
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    pub const TEST_CONFIG: &str = r#"
---
system: # optional
  logging: # optional
    level: "trace" # mandatory
    max_size: 1
    max_count: 3
oracle:
  no_matter: ""
"#;
    #[test]
    fn test_system_config() {
        let sys_config = SystemConfig::from_string(TEST_CONFIG).unwrap();
        assert_eq!(sys_config.logging().level(), log::Level::Trace);
        assert_eq!(sys_config.logging().max_size(), 1);
        assert_eq!(sys_config.logging().max_count(), 3);
    }

    #[test]
    fn test_system_config_empty() {
        let sys_config = SystemConfig::from_string("---\n").unwrap();
        assert_eq!(sys_config.logging().level(), defaults::LOG_LEVEL);
        assert_eq!(sys_config.logging().max_size(), defaults::LOG_MAX_SIZE);
        assert_eq!(sys_config.logging().max_count(), defaults::LOG_MAX_COUNT);
    }
}
