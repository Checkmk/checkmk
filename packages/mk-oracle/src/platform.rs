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

use crate::types::InstanceName;
use anyhow::Result;
use std::path::PathBuf;

pub struct Block {
    pub headline: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

impl Block {
    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn first(&self) -> Option<&Vec<String>> {
        self.rows.first()
    }
    pub fn last(&self) -> Option<&Vec<String>> {
        self.rows.last()
    }

    pub fn get_value_by_name(&self, row: &[String], idx: &str) -> String {
        if let Some(index) = self.headline.iter().position(|r| r == idx) {
            row.get(index).cloned()
        } else {
            None
        }
        .unwrap_or_default()
    }

    pub fn get_bigint_by_name(&self, row: &[String], idx: &str) -> String {
        self.get_value_by_name(row, idx)
            .parse::<i64>()
            .unwrap_or_default()
            .to_string()
    }

    pub fn get_first_row_column(&self, column: usize) -> Option<String> {
        self.rows.first().and_then(|r| r.get(column)).cloned()
    }
}

pub fn get_row_value_by_idx(row: &[String], idx: usize) -> String {
    row.get(idx).cloned().unwrap_or_default()
}

#[derive(Debug, Clone)]
pub struct InstanceInfo {
    pub name: InstanceName,
    pub home: PathBuf,
    pub base: PathBuf,
}

pub fn get_local_instances() -> Result<Vec<InstanceInfo>> {
    registry::get_instances(None)
}

pub mod registry {
    #[cfg(windows)]
    use winreg::{enums::*, RegKey};

    use super::InstanceInfo;
    #[cfg(windows)]
    use super::InstanceName;
    use anyhow::Result;
    #[cfg(windows)]
    pub fn get_instances(_custom_branch: Option<String>) -> Result<Vec<InstanceInfo>> {
        use std::path::PathBuf;

        // Open the branch, e.g. HKEY_LOCAL_MACHINE\SOFTWARE
        let handle = RegKey::predef(HKEY_LOCAL_MACHINE);
        let oracle = handle.open_subkey("SOFTWARE\\Oracle")?;

        let instances: Vec<InstanceInfo> = oracle
            .enum_keys()
            .filter_map(|k| k.ok())
            .filter_map(|k| {
                if let Ok(candidate) = oracle.open_subkey(k) {
                    let values = ["ORACLE_HOME", "ORACLE_BASE", "ORACLE_SID"]
                        .iter()
                        .map(|&key| candidate.get_value(key).unwrap_or_default())
                        .collect::<Vec<String>>();

                    if values.iter().all(|v| !v.is_empty()) {
                        Some(InstanceInfo {
                            name: InstanceName::from(values[2].as_str()),
                            home: PathBuf::from(values[0].as_str()),
                            base: PathBuf::from(values[1].as_str()),
                        })
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect::<Vec<InstanceInfo>>();
        Ok(instances)
    }

    #[cfg(unix)]
    pub fn get_instances(_custom_branch: Option<String>) -> Result<Vec<InstanceInfo>> {
        Ok(vec![])
    }
}

#[cfg(windows)]
pub mod path_var {
    use std::env;
    use std::ffi::OsString;
    use std::fs;
    use std::path::{Path, PathBuf};

    fn split_paths_var(var: &str) -> Vec<PathBuf> {
        match env::var_os(var) {
            Some(v) => env::split_paths(&v).collect(),
            None => Vec::new(),
        }
    }

    fn is_file(p: &Path) -> bool {
        fs::metadata(p).map(|m| m.is_file()).unwrap_or(false)
    }

    /// Rough equivalent of `where <name>` on Windows: search PATH.
    /// Returns *all* matches in PATH order.
    pub fn which(name: &str) -> Vec<PathBuf> {
        let mut results = Vec::<PathBuf>::new();

        let candidate = Path::new(name);

        let path_dirs = split_paths_var("PATH");

        let mut try_add = |p: PathBuf| {
            // De-dup (case-insensitive-ish): Windows paths are case-insensitive.
            // Keep first occurrence (PATH order).
            let p_norm = p.to_string_lossy().to_ascii_uppercase();
            if results
                .iter()
                .any(|x| x.to_string_lossy().to_ascii_uppercase() == p_norm)
            {
                return;
            }
            if is_file(&p) {
                results.push(p);
            }
        };

        for dir in path_dirs {
            try_add(dir.join(candidate));
        }

        results
    }

    /// remove from the patth all paths where target exe is found
    pub fn patch_path_var(name: &str) -> OsString {
        let mut results = Vec::<OsString>::new();

        let candidate = Path::new(name);

        let path_dirs: Vec<OsString> = split_paths_var("PATH")
            .into_iter()
            .map(|p| p.into_os_string())
            .collect();

        let mut check_for_skip = |p: OsString, f: &Path| {
            let p_norm = p.to_string_lossy().to_ascii_uppercase();
            if results
                .iter()
                .any(|x| x.to_string_lossy().to_ascii_uppercase() == p_norm)
            {
                return;
            }
            if !is_file(&PathBuf::from(p.clone()).join(f)) {
                results.push(p);
            }
        };

        for dir in path_dirs {
            check_for_skip(dir, candidate);
        }

        results.join(&OsString::from(";"))
    }
}

#[cfg(unix)]
pub mod path_var {
    use std::ffi::OsString;
    use std::path::PathBuf;

    // not required on unix systems
    pub fn which(_name: &str) -> Vec<PathBuf> {
        vec![]
    }
    pub fn patch_path_var(_name: &str) -> OsString {
        std::env::var_os("PATH").unwrap_or_default()
    }
}

#[cfg(test)]
mod tests {
    #[cfg(windows)]
    #[test]
    fn test_which() {
        use super::path_var::which;
        use std::path::PathBuf;

        let results = which("kernel32.dll");
        assert_eq!(
            results[0],
            PathBuf::from("C:\\Windows\\system32\\kernel32.dll")
        );
    }

    #[cfg(windows)]
    #[test]
    fn test_patch_path() {
        use super::path_var::patch_path_var;

        let patched_path = patch_path_var("kernel32.dll");
        assert!(!patched_path
            .into_string()
            .unwrap()
            .contains("C:\\Windows\\system32"));
    }
    #[cfg(unix)]
    #[test]
    fn test_which() {
        use super::path_var::which;

        let results = which("bash");
        assert!(results.is_empty());
    }

    #[cfg(unix)]
    #[test]
    fn test_patch_path() {
        use super::path_var::patch_path_var;

        let patched_path = patch_path_var("kernel32.dll");
        assert_eq!(
            patched_path.into_string().unwrap(),
            std::env::var_os("PATH").unwrap().into_string().unwrap()
        );
    }
}
