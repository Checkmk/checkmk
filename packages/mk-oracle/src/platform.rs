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
        let lowercased = home.to_string_lossy().to_lowercase();
        let trimmed = lowercased.trim_end_matches('\\');
        PathBuf::from(if trimmed.ends_with(':') {
            lowercased.as_str() // usually "C:\"
        } else {
            trimmed
        })
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
    const ORACLE_BRANCH: &str = r"SOFTWARE\Oracle";

    /// Reading these keys does not need admin rights, unlike asking the
    /// service control manager.
    #[cfg(windows)]
    const SERVICES_BRANCH: &str = r"SYSTEM\CurrentControlSet\Services";

    #[cfg(any(windows, test))]
    const SERVICE_PREFIXES: [&str; 2] = ["OracleASMService", "OracleService"];

    /// The binary both `OracleService*` and `OracleASMService*` run.
    #[cfg(any(windows, test))]
    const INSTANCE_BINARY: &str = "oracle.exe";

    /// Returns the SID of an instance service: `OracleServiceORCL` gives
    /// `ORCL`, `OracleASMService+ASM` gives `+ASM`. Every other Oracle
    /// service, such as the listener or the job scheduler, gives `None`.
    #[cfg(any(windows, test))]
    fn sid_from_service_name(service: &str) -> Option<&str> {
        SERVICE_PREFIXES
            .iter()
            .find_map(|prefix| {
                service
                    .get(..prefix.len())
                    .filter(|head| head.eq_ignore_ascii_case(prefix))
                    .and_then(|_| service.get(prefix.len()..))
            })
            .filter(|sid| !sid.is_empty())
    }

    /// Returns the `ORACLE_HOME` of a service `ImagePath`, which looks like
    /// `"<home>\bin\oracle.exe" <SID>`, where the quotes and the SID may be
    /// missing. Anchoring on `\bin\` rather than on the quotes also gets the
    /// home out of an unquoted path with spaces, and requiring the binary to
    /// be `bin\oracle.exe` keeps a service that only shares the name prefix
    /// from becoming an instance. A path that does not match is rejected
    /// instead of guessed at: a wrong home would send every later client
    /// lookup to the wrong installation, while a rejected one only leaves the
    /// SID to the home keys.
    #[cfg(any(windows, test))]
    fn home_from_image_path(image_path: &str) -> Option<PathBuf> {
        const BIN_DIR: &str = r"\bin\";

        let lowercased = image_path.to_ascii_lowercase();
        let bin = lowercased.rfind(BIN_DIR)?;
        // To be sure it is Oracle, not smth strange
        if !lowercased[bin + BIN_DIR.len()..].starts_with(INSTANCE_BINARY) {
            return None;
        }
        let home = image_path[..bin].trim().trim_start_matches('"');
        (!home.is_empty()).then(|| PathBuf::from(home))
    }

    /// Returns one entry per SID.
    ///
    /// Both sources can name a SID twice: an upgrade leaves the old home's
    /// `ORACLE_SID` in place, and a SID served by an `OracleService` and an
    /// `OracleASMService` alike has two service keys. The first entry of a SID
    /// wins, and services come first: the service knows the home the instance
    /// really runs from, so a home key is used only for a SID that has no
    /// service. `InstanceName` upper-cases, which makes the comparison case
    /// insensitive, as Oracle treats SIDs.
    #[cfg(any(windows, test))]
    fn merge_instances(
        home_keys: Vec<LocalInstance>,
        services: Vec<LocalInstance>,
    ) -> Vec<LocalInstance> {
        use std::collections::HashSet;

        let mut seen: HashSet<InstanceName> = HashSet::new();
        let mut merged: Vec<LocalInstance> = services
            .into_iter()
            .filter(|service| seen.insert(service.name.clone()))
            .map(|service| LocalInstance {
                // ORACLE_BASE belongs to the home, not to the SID, so any home
                // key of that home has the right one.
                base: home_keys
                    .iter()
                    .find(|key| super::home_key(&key.home) == super::home_key(&service.home))
                    .and_then(|key| key.base.clone()),
                ..service
            })
            .collect();
        merged.extend(
            home_keys
                .into_iter()
                .filter(|key| seen.insert(key.name.clone())),
        );
        merged
    }

    /// Returns the `ORACLE_SID` of every home key. `ORACLE_BASE` is optional.
    /// Some homes do not have it, and it is not needed to reach an instance.
    #[cfg(windows)]
    fn instances_from_home_keys(oracle: &winreg::RegKey) -> Vec<LocalInstance> {
        oracle
            .enum_keys()
            .filter_map(|key| key.ok())
            .filter_map(|key| oracle.open_subkey(key).ok())
            .filter_map(|home| {
                let value = |name: &str| -> String { home.get_value(name).unwrap_or_default() };
                let (oracle_home, sid) = (value("ORACLE_HOME"), value("ORACLE_SID"));
                if oracle_home.is_empty() || sid.is_empty() {
                    return None;
                }
                let base = value("ORACLE_BASE");
                Some(LocalInstance {
                    name: InstanceName::from(sid.as_str()),
                    home: PathBuf::from(oracle_home),
                    base: (!base.is_empty()).then(|| PathBuf::from(base)),
                })
            })
            .collect()
    }

    /// Returns every SID that has a service. A home key gives only the
    /// default SID of its home, so this finds the databases created into an
    /// existing home as well. The legacy `mk_oracle.ps1` reads the same list
    /// with `Get-Service`.
    #[cfg(windows)]
    fn instances_from_services(services: &winreg::RegKey) -> Vec<LocalInstance> {
        services
            .enum_keys()
            .filter_map(|key| key.ok())
            .filter_map(|service| {
                let sid = sid_from_service_name(&service)?.to_string();
                let image_path: String = services
                    .open_subkey(&service)
                    .and_then(|key| key.get_value("ImagePath"))
                    .map_err(|e| log::info!("Cannot read ImagePath of {service}: {e}"))
                    .ok()?;
                let Some(home) = home_from_image_path(&image_path) else {
                    log::info!("Cannot derive ORACLE_HOME of {service} from {image_path:?}");
                    return None;
                };
                Some(LocalInstance {
                    name: InstanceName::from(sid.as_str()),
                    home,
                    // Filled in from the home keys by merge_instances.
                    base: None,
                })
            })
            .collect()
    }

    /// Returns the instances Windows knows about: the `ORACLE_SID` of every
    /// Oracle home key plus every instance service. Both sources are needed. A
    /// database created into an existing home has no home key of its own, and
    /// a home key can name a SID whose service is gone. Keeping the home keys
    /// also means this never reports less than it did before the service scan
    /// was added.
    #[cfg(windows)]
    pub fn get_instances(custom_branch: Option<String>) -> Result<Vec<LocalInstance>> {
        use winreg::{enums::HKEY_LOCAL_MACHINE, RegKey};

        let branch = custom_branch.unwrap_or_else(|| ORACLE_BRANCH.to_string());
        let hklm = RegKey::predef(HKEY_LOCAL_MACHINE);
        let homes = instances_from_home_keys(&hklm.open_subkey(branch)?);
        let services = match hklm.open_subkey(SERVICES_BRANCH) {
            Ok(key) => instances_from_services(&key),
            Err(e) => {
                log::warn!("Cannot enumerate {SERVICES_BRANCH}: {e}");
                Vec::new()
            }
        };
        Ok(merge_instances(homes, services))
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

    #[cfg(test)]
    mod tests {
        use super::{
            home_from_image_path, merge_instances, sid_from_service_name, InstanceName,
            LocalInstance,
        };
        use std::path::PathBuf;

        /// `From<&str>` upper-cases, as both registry sources do.
        fn instance(name: &str, home: &str) -> LocalInstance {
            LocalInstance {
                name: InstanceName::from(name),
                home: PathBuf::from(home),
                base: None,
            }
        }

        fn instance_with_base(name: &str, home: &str, base: &str) -> LocalInstance {
            LocalInstance {
                base: Some(PathBuf::from(base)),
                ..instance(name, home)
            }
        }

        #[test]
        fn test_sid_from_service_name() {
            assert_eq!(sid_from_service_name("OracleServiceORCL"), Some("ORCL"));
            assert_eq!(sid_from_service_name("OracleASMService+ASM"), Some("+ASM"));
            // Registry key names are case-insensitive.
            assert_eq!(sid_from_service_name("ORACLESERVICEorcl"), Some("orcl"));
        }

        #[test]
        fn test_sid_from_service_name_skips_services_without_an_instance() {
            for service in [
                "OracleOraDB19Home1TNSListener",
                "OracleJobSchedulerORCL",
                "OracleVssWriterORCL",
                "OracleRemExecServiceV2",
                "OracleService",
                "OracleASMService",
                "Dhcp",
                "",
            ] {
                assert_eq!(sid_from_service_name(service), None, "{service}");
            }
        }

        #[test]
        fn test_home_from_image_path() {
            let home = Some(PathBuf::from(r"C:\app\oracle\product\19.0.0\dbhome_1"));
            for image_path in [
                r#""C:\app\oracle\product\19.0.0\dbhome_1\bin\oracle.exe" ORCL"#,
                r#""C:\app\oracle\product\19.0.0\dbhome_1\bin\oracle.exe""#,
                r"C:\app\oracle\product\19.0.0\dbhome_1\bin\oracle.exe ORCL",
                r"C:\app\oracle\product\19.0.0\dbhome_1\bin\oracle.exe",
                r"  C:\app\oracle\product\19.0.0\dbhome_1\BIN\ORACLE.EXE  ",
            ] {
                assert_eq!(home_from_image_path(image_path), home, "{image_path}");
            }
        }

        /// An unquoted path with spaces is ambiguous, but the `bin` directory
        /// still ends the home.
        #[test]
        fn test_home_from_image_path_of_a_home_with_spaces() {
            let home = Some(PathBuf::from(r"C:\Program Files\oracle\dbhome_1"));
            for image_path in [
                r#""C:\Program Files\oracle\dbhome_1\bin\oracle.exe" ORCL"#,
                r"C:\Program Files\oracle\dbhome_1\bin\oracle.exe ORCL", // doubtful example
            ] {
                assert_eq!(home_from_image_path(image_path), home, "{image_path}");
            }
        }

        #[test]
        fn test_home_from_image_path_rejects_a_path_outside_bin() {
            for image_path in [
                r"C:\app\oracle\dbhome_1\oracle.exe",
                r"oracle.exe",
                r#""" ORCL"#,
                "",
                "   ",
            ] {
                assert_eq!(home_from_image_path(image_path), None, "{image_path:?}");
            }
        }

        /// A service that only shares the name prefix must not become an
        /// instance, and neither must a binary nested below `bin`.
        #[test]
        fn test_home_from_image_path_rejects_another_binary() {
            for image_path in [
                r"C:\vendor\bin\vendor.exe",
                r#""C:\vendor\bin\vendor.exe" ORCL"#,
                r"C:\app\oracle\dbhome_1\bin\tnslsnr.exe LISTENER",
                r"C:\app\oracle\dbhome_1\bin\subdir\oracle.exe ORCL",
                r"C:\app\oracle\dbhome_1\bin\",
            ] {
                assert_eq!(home_from_image_path(image_path), None, "{image_path:?}");
            }
        }

        #[test]
        fn test_merge_instances_lists_every_sid_once() {
            let merged = merge_instances(
                vec![instance("ORCL", r"C:\home_1")],
                // A second database in the same home has no home key.
                vec![
                    instance("orcl", r"C:\home_1"),
                    instance("PROD", r"C:\home_1"),
                ],
            );

            assert_eq!(
                merged,
                vec![
                    instance("ORCL", r"C:\home_1"),
                    instance("PROD", r"C:\home_1"),
                ]
            );
        }

        /// OracleServiceXE and OracleASMServiceXE would both name the SID XE.
        #[test]
        fn test_merge_instances_dedups_services() {
            let merged = merge_instances(
                vec![],
                vec![instance("XE", r"C:\home_1"), instance("xe", r"C:\home_2")],
            );

            assert_eq!(merged, vec![instance("XE", r"C:\home_1")]);
        }

        /// An upgrade leaves the old home's ORACLE_SID in place. The service
        /// says which home the instance runs from now.
        #[test]
        fn test_merge_instances_prefers_the_service_home_over_a_stale_home_key() {
            let merged = merge_instances(
                vec![
                    instance_with_base("ORCL", r"C:\home_12c", r"C:\base_12c"),
                    instance_with_base("ORCL", r"C:\home_19c", r"C:\base_19c"),
                ],
                vec![instance("ORCL", r"C:\home_19c")],
            );

            assert_eq!(
                merged,
                vec![instance_with_base("ORCL", r"C:\home_19c", r"C:\base_19c")]
            );
        }

        /// If ORACLE_BASE exists for ORACLE_HOME, add it.
        #[test]
        fn test_merge_instances_takes_the_base_of_the_home() {
            let merged = merge_instances(
                vec![instance_with_base("ORCL", r"C:\home_1", r"C:\base_1")],
                vec![instance("PROD", r"C:\home_1")],
            );

            assert_eq!(
                merged,
                vec![
                    instance_with_base("PROD", r"C:\home_1", r"C:\base_1"),
                    instance_with_base("ORCL", r"C:\home_1", r"C:\base_1"),
                ]
            );
        }

        #[test]
        fn test_merge_instances_has_no_base_for_an_unknown_home() {
            let merged = merge_instances(
                vec![instance_with_base("ORCL", r"C:\home_12c", r"C:\base_12c")],
                vec![instance("ORCL", r"C:\home_19c")],
            );

            assert_eq!(merged, vec![instance("ORCL", r"C:\home_19c")]);
        }

        /// Without a service there is nothing better than the first home key.
        #[test]
        fn test_merge_instances_dedups_home_keys() {
            let merged = merge_instances(
                vec![
                    instance("OrCL", r"C:\home_12c"),
                    instance("oRcl", r"C:\home_19c"),
                    instance("TEST", r"C:\home_19c"),
                ],
                vec![],
            );

            assert_eq!(
                merged,
                vec![
                    instance("ORCL", r"C:\home_12c"),
                    instance("TEST", r"C:\home_19c"),
                ]
            );
        }

        #[test]
        fn test_merge_instances_of_nothing() {
            assert!(merge_instances(vec![], vec![]).is_empty());
        }
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

    /// The home keys and the services spell the same home differently.
    #[cfg(windows)]
    #[test]
    fn test_home_key_ignores_a_trailing_separator() {
        assert_eq!(
            home_key(Path::new(r"C:\app\oracle\dbhome_1\")),
            home_key(Path::new(r"C:\app\oracle\dbhome_1"))
        );
        assert_eq!(home_key(Path::new(r"C:\")), PathBuf::from(r"c:\"));
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
