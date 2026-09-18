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

use crate::types::{LocalInstance, Sid};
use anyhow::Result;
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

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

/// The name of this node, as the operating system reports it.
///
/// This calls POSIX `gethostname` through `libc` rather than using the
/// `gethostname` crate. That crate reaches the same call through `rustix`,
/// whose libc backend also references `sethostname`, which AIX does not have,
/// so it fails to build there. We only ever read the name.
#[cfg(unix)]
pub fn node_name() -> Option<String> {
    let mut buf = [0 as libc::c_char; 256];
    // SAFETY: buf is a valid, writable array of exactly the length passed on.
    if unsafe { libc::gethostname(buf.as_mut_ptr(), buf.len()) } != 0 {
        log::warn!("gethostname failed");
        return None;
    }
    // gethostname may leave the name untruncated and unterminated when it fills
    // the buffer, so stop at the first NUL or at the end, whichever comes first.
    let bytes: Vec<u8> = buf
        .iter()
        .take_while(|&&c| c != 0)
        .map(|&c| c as u8)
        .collect();
    String::from_utf8(bytes)
        .ok()
        .filter(|name| !name.is_empty())
}

#[cfg(windows)]
pub fn node_name() -> Option<String> {
    std::env::var("COMPUTERNAME")
        .ok()
        .filter(|name| !name.is_empty())
}

pub fn get_local_instances() -> Result<Vec<LocalInstance>> {
    registry::get_instances(None)
}

pub fn home_key(home: &Path) -> PathBuf {
    if cfg!(windows) {
        PathBuf::from(home.to_string_lossy().to_lowercase())
    } else {
        home.to_path_buf()
    }
}

/// The SIDs each `ORACLE_HOME` owns, upper-cased: [`get_local_instances`]
/// inverted. Keys are [`home_key`], so a lookup has to use it too.
pub fn get_oracle_home_sids(instances: &[LocalInstance]) -> HashMap<PathBuf, HashSet<Sid>> {
    let mut homes: HashMap<PathBuf, HashSet<Sid>> = HashMap::new();
    for instance in instances {
        // `Sid::from` keeps the case, so fold it here: Oracle compares SIDs
        // case-insensitively, and names differing only in case must collapse.
        let sid = Sid::from(instance.name.to_string().to_uppercase().as_str());
        homes
            .entry(home_key(&instance.home))
            .or_default()
            .insert(sid);
    }
    homes
}

pub mod registry {
    use std::path::PathBuf;

    use super::LocalInstance;
    use crate::types::InstanceName;
    use anyhow::Result;

    #[cfg(windows)]
    pub fn get_instances(custom_branch: Option<String>) -> Result<Vec<LocalInstance>> {
        use winreg::{enums::*, RegKey};

        let custom_branch = custom_branch.unwrap_or_else(|| "SOFTWARE\\Oracle".to_string());

        // Open the branch, e.g. HKEY_LOCAL_MACHINE\SOFTWARE
        let handle = RegKey::predef(HKEY_LOCAL_MACHINE);
        let oracle = handle.open_subkey(custom_branch)?;

        let instances: Vec<LocalInstance> = oracle
            .enum_keys()
            .filter_map(|k| k.ok())
            .filter_map(|k| {
                if let Ok(candidate) = oracle.open_subkey(k) {
                    let values = ["ORACLE_HOME", "ORACLE_BASE", "ORACLE_SID"]
                        .iter()
                        .map(|&key| candidate.get_value(key).unwrap_or_default())
                        .collect::<Vec<String>>();

                    if values.iter().all(|v| !v.is_empty()) {
                        Some(LocalInstance {
                            name: InstanceName::from(values[2].as_str()),
                            home: PathBuf::from(values[0].as_str()),
                            base: Some(PathBuf::from(values[1].as_str())),
                        })
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect::<Vec<LocalInstance>>();
        Ok(instances)
    }

    /// Finds the oratab file in standard locations.
    /// Returns the Result with path to oratab file or error if not found.
    pub fn find_oratab_file(oratab_paths: Option<&[&str]>) -> Result<PathBuf> {
        use std::path::Path;

        if cfg!(windows) {
            Err(anyhow::anyhow!(
                "ORA-99999 oratab is not supported on Windows"
            )) // ORA-99999 is a code from legacy plugin, we keep it for backward compatibility of error handling
        } else {
            oratab_paths
                .unwrap_or(&["/etc/oratab", "/var/opt/oracle/oratab"])
                .iter()
                .find(|p| Path::new(p).is_file())
                .map(PathBuf::from)
                .ok_or(anyhow::anyhow!("ORA-99999 oratab not found in local mode"))
            // ORA-99999 is a code from legacy plugin, we keep it for backward compatibility of error handling
        }
    }

    #[cfg(unix)]
    pub fn get_instances(custom_path: Option<String>) -> Result<Vec<LocalInstance>> {
        let maybe_path = custom_path.as_deref().map(|p| vec![p]);
        let oratab_path = find_oratab_file(maybe_path.as_deref())?;

        let content = std::fs::read_to_string(oratab_path)
            .map_err(|e| anyhow::anyhow!("Failed to read oratab: {}", e))?;

        let all = content
            .lines()
            .filter_map(|l| {
                let line = l.split('#').next().unwrap_or("").trim();
                if line.is_empty() {
                    return None;
                }

                let parts: Vec<&str> = line.split(':').collect();
                if parts.len() >= 3 {
                    Some(LocalInstance {
                        name: InstanceName::from(parts[0].trim()),
                        home: PathBuf::from(parts[1].trim()),
                        base: None, // oratab does not contain base information, we set it to None
                    })
                } else {
                    None
                }
            })
            .collect::<Vec<LocalInstance>>();
        Ok(all)
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
    use super::{get_oracle_home_sids, home_key};
    use crate::types::{InstanceName, LocalInstance, Sid};
    use std::path::Path;
    use std::path::PathBuf;

    /// `From<String>` keeps the case, unlike `From<&str>`, so the name reaches
    /// the function exactly as spelled here.
    fn instance(name: &str, home: &str) -> LocalInstance {
        LocalInstance {
            name: InstanceName::from(name.to_string()),
            home: PathBuf::from(home),
            base: None,
        }
    }

    #[test]
    fn test_get_oracle_home_sids() {
        let homes = get_oracle_home_sids(&[
            instance("xe", "/opt/oracle/21c"),
            instance("free", "/opt/oracle/21c"),
            instance("XE", "/opt/oracle/21c"),
            instance("sid19", "/opt/oracle/19c"),
        ]);

        assert_eq!(homes.len(), 2);
        assert_eq!(
            homes[&PathBuf::from("/opt/oracle/21c")],
            ["XE", "FREE"].into_iter().map(Sid::from).collect()
        );
        assert_eq!(
            homes[&PathBuf::from("/opt/oracle/19c")],
            ["SID19"].into_iter().map(Sid::from).collect()
        );
        assert!(get_oracle_home_sids(&[]).is_empty());
    }

    /// Windows spells one directory in several cases; Unix does not.
    #[test]
    fn test_get_oracle_home_sids_folds_the_home_case_on_windows() {
        let homes = get_oracle_home_sids(&[
            instance("XE", r"C:\app\oracle\dbhome_1"),
            instance("FREE", r"c:\app\oracle\DBHOME_1"),
        ]);

        if cfg!(windows) {
            assert_eq!(homes.len(), 1, "one directory, one entry: {homes:?}");
            let key = home_key(Path::new(r"C:\APP\Oracle\dbhome_1"));
            assert_eq!(homes[&key].len(), 2, "both sids land in it");
        } else {
            assert_eq!(homes.len(), 2, "case names two directories on unix");
        }
    }

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
