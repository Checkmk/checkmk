// Copyright (C) 2026 Checkmk GmbH
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

//! Detection of Oracle Grid Infrastructure, which covers both a full cluster
//! running Oracle Clusterware and a single node running Oracle Restart.
//!
//! A node that runs Grid Infrastructure keeps a pointer file called
//! `olr.loc`. That file names the installation directory of Grid
//! Infrastructure in a `crs_home=` line. Two things follow from a Grid home
//! that the rest of the plugin uses. The listener of such a node binds the
//! node address rather than the loopback address. And the Grid home ships a
//! client library, which matters on a node where `oratab` is not maintained.

use std::fs;
use std::path::{Path, PathBuf};

/// Where `olr.loc` lives when the operator does not configure a path.
/// Legacy `mk_oracle` probes the first entry, legacy `mk_oracle_crs` adds the
/// second one for Solaris.
const STANDARD_LOCATIONS: &[&str] = &["/etc/oracle/olr.loc", "/var/opt/oracle/olr.loc"];

/// Grid Infrastructure as found on this node.
///
/// A value exists only when the Grid home read from `olr.loc` is a directory.
/// Legacy `mk_oracle` applies the same condition before it treats a node as a
/// Grid Infrastructure node.
#[derive(PartialEq, Debug, Clone)]
pub struct GridInfrastructure {
    local_registry: PathBuf,
    crs_home: PathBuf,
}

impl GridInfrastructure {
    /// A configured path wins over the standard locations. Pointing the
    /// configuration at a path that does not exist therefore switches Grid
    /// Infrastructure handling off, which is what legacy `mk_oracle`
    /// documents for `OLRLOC`.
    pub fn detect(configured: Option<&Path>) -> Option<Self> {
        Self::detect_in(configured, STANDARD_LOCATIONS)
    }

    /// Same as [`Self::detect`] with the standard locations supplied by the
    /// caller, which lets a test point them at a temporary directory.
    pub fn detect_in(configured: Option<&Path>, standard_locations: &[&str]) -> Option<Self> {
        let local_registry = match configured {
            Some(path) => path.to_path_buf(),
            None => standard_locations
                .iter()
                .map(PathBuf::from)
                .find(|p| p.is_file())?,
        };

        if !local_registry.is_file() {
            log::info!(
                "No Oracle Local Registry at '{}': not a Grid Infrastructure node",
                local_registry.display()
            );
            return None;
        }

        let content = fs::read_to_string(&local_registry)
            .map_err(|e| {
                log::warn!(
                    "Failed to read Oracle Local Registry '{}': {e}",
                    local_registry.display()
                )
            })
            .ok()?;

        let Some(crs_home) = parse_crs_home(&content) else {
            log::warn!(
                "No crs_home entry in Oracle Local Registry '{}'",
                local_registry.display()
            );
            return None;
        };

        if !crs_home.is_dir() {
            log::warn!(
                "Grid home '{}' from '{}' is not a directory",
                crs_home.display(),
                local_registry.display()
            );
            return None;
        }

        log::info!(
            "Grid Infrastructure detected: home '{}' from '{}'",
            crs_home.display(),
            local_registry.display()
        );
        Some(Self {
            local_registry,
            crs_home,
        })
    }

    pub fn local_registry(&self) -> &Path {
        &self.local_registry
    }

    pub fn crs_home(&self) -> &Path {
        &self.crs_home
    }
}

/// Extracts the Grid home from the content of `olr.loc`.
/// Skips empty lines, comments and unparseable lines. First match wins.
fn parse_crs_home(content: &str) -> Option<PathBuf> {
    content
        .lines()
        .filter_map(|line| {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                return None;
            }
            let (key, value) = line.split_once('=')?;
            if key.trim() == "crs_home" {
                let value = value.trim();
                if !value.is_empty() {
                    return Some(PathBuf::from(value));
                }
            }
            None
        })
        .next()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_crs_home() {
        assert_eq!(
            parse_crs_home("crs_home=/u01/app/19.0.0/grid"),
            Some(PathBuf::from("/u01/app/19.0.0/grid"))
        );
        assert_eq!(parse_crs_home(""), None);
        assert_eq!(parse_crs_home("# comment\n"), None);
        assert_eq!(parse_crs_home("crs_home="), None);
        assert_eq!(
            parse_crs_home("olrconfig_loc=/etc/oracle/olr\ncrs_home=/grid"),
            Some(PathBuf::from("/grid"))
        );
        assert_eq!(
            parse_crs_home("crs_home=/first\ncrs_home=/second"),
            Some(PathBuf::from("/first"))
        );
        assert_eq!(
            parse_crs_home("badline\ncrs_home=/ok"),
            Some(PathBuf::from("/ok"))
        );
    }

    #[test]
    fn test_detect_none_without_registry_file() {
        assert!(GridInfrastructure::detect_in(None, &["/no/such/olr.loc"]).is_none());
        assert!(GridInfrastructure::detect_in(Some(Path::new("/no/such/olr.loc")), &[]).is_none());
    }
}
