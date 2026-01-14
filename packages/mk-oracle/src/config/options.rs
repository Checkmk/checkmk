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

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use crate::types::{MaxConnections, MaxQueries, SqlBindParam, UseHostClient};
use anyhow::Result;

impl Default for UseHostClient {
    fn default() -> Self {
        UseHostClient::from_str(defaults::USE_HOST_CLIENT).unwrap()
    }
}

impl UseHostClient {
    fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "always" => Some(UseHostClient::Always),
            "never" => Some(UseHostClient::Never),
            "auto" => Some(UseHostClient::Auto),
            _ if s.starts_with('/') || s.contains('\\') => Some(UseHostClient::Path(s.to_string())),
            _ => None,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Options {
    max_connections: MaxConnections,
    max_queries: MaxQueries,
    use_host_client: UseHostClient,
    params: Vec<SqlBindParam>,
    threads: usize,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            max_connections: defaults::MAX_CONNECTIONS.into(),
            max_queries: defaults::MAX_QUERIES.into(),
            use_host_client: UseHostClient::default(),
            params: vec![(keys::IGNORE_DB_NAME.to_string(), 0)],
            threads: 1,
        }
    }
}

impl Options {
    pub fn new(max_connections: MaxConnections) -> Self {
        Self {
            max_connections,
            max_queries: defaults::MAX_QUERIES.into(),
            use_host_client: UseHostClient::default(),
            params: vec![(keys::IGNORE_DB_NAME.to_string(), 0)],
            threads: 1,
        }
    }

    pub fn max_connections(&self) -> MaxConnections {
        self.max_connections.clone()
    }

    pub fn max_queries(&self) -> MaxQueries {
        self.max_queries.clone()
    }

    pub fn use_host_client(&self) -> &UseHostClient {
        &self.use_host_client
    }

    pub fn params(&self) -> &Vec<SqlBindParam> {
        &self.params
    }

    pub fn threads(&self) -> usize {
        self.threads
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
            use_host_client: UseHostClient::from_str(
                options
                    .get_string(keys::USE_HOST_CLIENT)
                    .unwrap_or_default()
                    .as_str(),
            )
            .unwrap_or_default(),
            params: vec![(
                keys::IGNORE_DB_NAME.to_string(),
                options
                    .get_int::<u8>(keys::IGNORE_DB_NAME)
                    .unwrap_or_default(),
            )],
            threads: 1,
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
    use_host_client: always
    IGNORE_DB_NAME: 1
    ";
        let yaml = create_yaml(OPTIONS_YAML);
        let options = Options::from_yaml(&yaml).unwrap().unwrap();
        assert_eq!(options.max_connections(), MaxConnections(100));
        assert_eq!(options.use_host_client(), &UseHostClient::Always);
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
        assert_eq!(options.use_host_client(), &UseHostClient::default());
        assert_eq!(options.max_queries(), defaults::MAX_QUERIES.into());
        assert_eq!(
            options.params(),
            &vec![(keys::IGNORE_DB_NAME.to_string(), 0)]
        );
    }
    #[test]
    fn test_default_use_host_client() {
        assert_eq!(UseHostClient::default(), UseHostClient::Auto);
    }
    #[test]
    fn test_use_host_client_parser() {
        assert_eq!(
            UseHostClient::from_str("always").unwrap(),
            UseHostClient::Always
        );
        assert_eq!(
            UseHostClient::from_str("never").unwrap(),
            UseHostClient::Never
        );
        assert_eq!(
            UseHostClient::from_str("auto").unwrap(),
            UseHostClient::Auto
        );
        assert_eq!(
            UseHostClient::from_str("/p").unwrap(),
            UseHostClient::Path("/p".to_string())
        );
        assert_eq!(
            UseHostClient::from_str("c:\\P").unwrap(),
            UseHostClient::Path("c:\\P".to_string())
        );
        assert!(UseHostClient::from_str("trash").is_none());
    }
}
