// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use crate::types::{MaxConnections, MaxQueries, SqlBindParam};
use anyhow::Result;

#[derive(PartialEq, Debug, Clone)]
pub struct Options {
    max_connections: MaxConnections,
    max_queries: MaxQueries,
    params: Vec<SqlBindParam>,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            max_connections: defaults::MAX_CONNECTIONS.into(),
            max_queries: defaults::MAX_QUERIES.into(),
            params: vec![(keys::IGNORE_DB_NAME.to_string(), 0)],
        }
    }
}

impl Options {
    pub fn new(max_connections: MaxConnections) -> Self {
        Self {
            max_connections,
            max_queries: defaults::MAX_QUERIES.into(),
            params: vec![(keys::IGNORE_DB_NAME.to_string(), 0)],
        }
    }

    pub fn max_connections(&self) -> MaxConnections {
        self.max_connections.clone()
    }

    pub fn max_queries(&self) -> MaxQueries {
        self.max_queries.clone()
    }

    pub fn params(&self) -> &Vec<SqlBindParam> {
        &self.params
    }
    pub fn from_yaml(yaml: &Yaml) -> Result<Option<Self>> {
        let options = yaml.get(keys::OPTIONS);
        if options.is_badvalue() {
            return Ok(None);
        }

        Ok(Some(Self {
            max_connections: options
                .get_int::<u32>(keys::MAX_CONNECTIONS)
                .unwrap_or_else(|| {
                    log::debug!("no max_connections specified, using default");
                    defaults::MAX_CONNECTIONS
                })
                .into(),
            max_queries: defaults::MAX_QUERIES.into(),
            params: vec![(
                keys::IGNORE_DB_NAME.to_string(),
                options
                    .get_int::<u8>(keys::IGNORE_DB_NAME)
                    .unwrap_or_default(),
            )],
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::test_tools::create_yaml;

    #[test]
    fn test_options_from_yaml() {
        const OPTIONS_YAML: &str = r"
options:   
    max_connections: 100
    IGNORE_DB_NAME: 1
    ";
        let yaml = create_yaml(OPTIONS_YAML);
        let options = Options::from_yaml(&yaml).unwrap().unwrap();
        assert_eq!(options.max_connections(), MaxConnections(100));
        assert_eq!(options.max_queries(), defaults::MAX_QUERIES.into());
        assert_eq!(
            options.params(),
            &vec![(keys::IGNORE_DB_NAME.to_string(), 1)]
        );
    }

    #[test]
    fn test_default_options() {
        let options = Options::default();
        assert_eq!(options.max_connections(), defaults::MAX_CONNECTIONS.into());
        assert_eq!(options.max_queries(), defaults::MAX_QUERIES.into());
        assert_eq!(
            options.params(),
            &vec![(keys::IGNORE_DB_NAME.to_string(), 0)]
        );
    }
}
