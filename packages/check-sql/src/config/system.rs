// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::yaml::{Get, Yaml};
use anyhow::Result;
use yaml_rust::YamlLoader;

mod keys {
    pub const SYSTEM: &str = "system";
    pub const LOGGING: &str = "logging";

    pub const LEVEL: &str = "level";
    pub const MAX_SIZE: &str = "max_size";
    pub const MAX_COUNT: &str = "max_count";
}

mod defaults {
    pub const LOG_LEVEL: log::Level = log::Level::Warn;
    pub const LOG_MAX_SIZE: usize = 1_000_000;
    pub const LOG_MAX_COUNT: usize = 5;
}

#[derive(PartialEq, Debug, Default)]
pub struct SystemConfig {
    logging: Logging,
}

#[derive(PartialEq, Debug)]
pub struct Logging {
    level: log::Level,
    max_size: usize,
    max_count: usize,
}

impl Default for Logging {
    fn default() -> Self {
        Self {
            level: defaults::LOG_LEVEL,
            max_size: defaults::LOG_MAX_SIZE,
            max_count: defaults::LOG_MAX_COUNT,
        }
    }
}

impl Logging {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        use std::str::FromStr;
        let logging = yaml.get(keys::LOGGING);
        Ok(Self {
            level: logging
                .get_string(keys::LEVEL)
                .map(|s| log::Level::from_str(&s))
                .unwrap_or(Ok(defaults::LOG_LEVEL))
                .unwrap_or(defaults::LOG_LEVEL),
            max_size: logging.get_int(keys::MAX_SIZE, defaults::LOG_MAX_SIZE),
            max_count: logging.get_int(keys::MAX_COUNT, defaults::LOG_MAX_COUNT),
        })
    }

    pub fn level(&self) -> log::Level {
        self.level
    }
    pub fn max_size(&self) -> usize {
        self.max_size
    }
    pub fn max_count(&self) -> usize {
        self.max_count
    }
}

impl SystemConfig {
    pub fn from_string(source: &str) -> Result<Self> {
        YamlLoader::load_from_str(source)?
            .get(0)
            .map(SystemConfig::from_yaml)
            .unwrap_or_else(|| Ok(Self::default()))
    }

    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let system: &yaml_rust::Yaml = yaml.get(keys::SYSTEM);
        if system.is_badvalue() {
            return Ok(Self::default());
        }

        let logging = Logging::from_yaml(system).unwrap_or_else(|_| Logging::default());

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
mssql:
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
