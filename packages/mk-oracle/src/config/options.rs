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
            _ => build_path(s).map(UseHostClient::Path),
        }
    }
}

/// Expand environment variables in `some` and return the result if it is an absolute path.
///
/// Returns `None` if the expanded string is not absolute (e.g. the variable is undefined
/// and the literal fallback is relative, or the value itself is not an absolute path).
fn build_path(some: &str) -> Option<String> {
    if !some.contains(std::path::MAIN_SEPARATOR)
        && !some.contains('/') // windows users might use '/' as a separator
        && !some.starts_with('$')
    {
        log::warn!("use_host_client: '{some}' is not a good path");
        return None;
    }
    match shellexpand::env(some) {
        Err(e) => {
            log::warn!(
                "use_host_client: can't expand path '{}', ignoring path {:?}",
                e.var_name,
                some
            );
            None
        }
        Ok(p) => {
            let p = p.into_owned();
            if std::path::Path::new(&p).is_absolute() {
                Some(p)
            } else {
                log::warn!("use_host_client: expanded path {p:?} is not absolute, ignoring");
                None
            }
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
        #[cfg(not(windows))]
        assert_eq!(
            UseHostClient::from_str("/p").unwrap(),
            UseHostClient::Path("/p".to_string())
        );
        #[cfg(windows)]
        assert!(UseHostClient::from_str("/p").is_none());
        assert!(UseHostClient::from_str("trash").is_none());
    }

    #[test]
    fn test_build_path_invalid() {
        // Rejected on all platforms: no MAIN_SEPARATOR and doesn't start with '$'
        assert_eq!(build_path(""), None);
        assert_eq!(build_path("trash"), None);

        // Contains '/' so passes the guard, but fails is_absolute() — rejected on all platforms
        assert_eq!(build_path("relative/path"), None);

        // Windows-style backslash paths: no '/' on Linux so guard fires → None;
        // on Windows '\' IS MAIN_SEPARATOR so guard passes and is_absolute() → Some.
        #[cfg(not(windows))]
        {
            assert_eq!(build_path("C:\\Program Files"), None);
            assert_eq!(build_path("d:\\oracle"), None);
        }
        #[cfg(windows)]
        {
            assert_eq!(
                build_path("C:\\Program Files"),
                Some("C:\\Program Files".to_string())
            );
            assert_eq!(build_path("d:\\oracle"), Some("d:\\oracle".to_string()));
            // Unix-style path on Windows is supported but will be rejected as non root
            assert_eq!(build_path("/some/path"), None);
        }
    }

    #[cfg(not(windows))]
    #[test]
    fn test_build_path_expand_env_var() {
        // Paths starting with '$' pass the guard (with or without separators after the var name).
        let Some(val) = std::env::var("HOME").ok() else {
            return; // HOME not set in this environment — skip
        };
        assert_eq!(build_path("$HOME"), Some(val.clone()));
        assert_eq!(build_path("/base/${HOME}"), Some(format!("/base/{val}")));
        assert_eq!(
            build_path("/u01/$HOME/lib"),
            Some(format!("/u01/{val}/lib"))
        );
    }

    #[cfg(windows)]
    #[test]
    fn test_build_path_expand_env_var() {
        // Paths starting with '$' pass the guard (with or without separators after the var name).
        let Some(val) = std::env::var("SYSTEMROOT").ok() else {
            return; // SYSTEMROOT not set in this environment — skip
        };
        assert_eq!(build_path("$SYSTEMROOT"), Some(val.clone()));
        assert_eq!(build_path("C:\\${SYSTEMROOT}"), Some(format!("C:\\{val}")));
        assert_eq!(
            build_path("C:\\$SYSTEMROOT\\lib"),
            Some(format!("C:\\{val}\\lib"))
        );
    }

    #[test]
    fn test_build_path_expand_undefined_var() {
        // Undefined variable: shellexpand returns Err, a warning is logged, and build_path yields None
        assert_eq!(build_path("$UNDEFINED_VAR_12345"), None);
    }

    #[test]
    fn test_build_path_expand_to_relative() {
        // Variable expands successfully but to a relative path: a warning is logged and None is returned
        unsafe { std::env::set_var("_MK_TEST_RELATIVE_PATH", "relative/oracle/lib") };
        assert_eq!(build_path("$_MK_TEST_RELATIVE_PATH"), None);
        unsafe { std::env::remove_var("_MK_TEST_RELATIVE_PATH") };
    }

    #[test]
    fn test_build_path_separator_guard() {
        // Path contains MAIN_SEPARATOR but does not start with '$':
        // the guard fires and None is returned without invoking shellexpand
        let sep = std::path::MAIN_SEPARATOR;
        assert_eq!(build_path(&format!("relative{sep}oracle{sep}lib")), None);
    }
}
