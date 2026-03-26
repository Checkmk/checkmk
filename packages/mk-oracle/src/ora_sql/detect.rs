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

use crate::platform::registry::get_instances;
use crate::types::{LocalInstance, Sid};
use anyhow::Result;
use regex::Regex;
use std::collections::HashSet;
use std::path::PathBuf;
use sysinfo::System;

/// Regex pattern to match Oracle PMON processes and capture the SID.
///
/// Group 1: the prefix (e.g. `ora_pmon_`)
/// Group 2: the SID name (e.g. `TEST19`)
const SID_MASK: &str = r"^(asm_pmon_|ora_pmon_|xe_pmon_|db_pmon_)(.+)";

/// Retrieves local Oracle SIDs from the registry and running processes.
/// On Windows, it checks the registry for Oracle instances and also looks for PMON processes.
pub fn get_local_sid_names() -> Vec<String> {
    let instances = get_instances(None).unwrap_or_default();
    let registry_sids = instances
        .into_iter()
        .map(|i| i.name.to_string())
        .collect::<Vec<String>>();
    let process_sids = find_sids_by_processes(Some(SID_MASK))
        .unwrap_or_default()
        .into_iter()
        .collect::<Vec<String>>();
    registry_sids.into_iter().chain(process_sids).collect()
}

/// Method is similar to `ps -ef | grep <match_string>`
/// May not work on Windows systems
pub fn find_sids_by_processes(match_string: Option<&str>) -> Result<HashSet<String>> {
    let re = Regex::new(match_string.unwrap_or(SID_MASK))?;

    let mut sys = System::new_all();
    sys.refresh_all();

    let result: HashSet<String> = sys
        .processes()
        .values()
        .filter_map(|process| {
            process
                .cmd()
                .last()
                .map(|s| s.to_string_lossy())
                .and_then(|s| s.split(' ').next_back().map(|s| s.to_string()))
                .and_then(|last_param| {
                    re.captures(&last_param)
                        .and_then(|c| c.get(2))
                        .map(|m| m.as_str().to_string())
                })
        })
        .collect();

    Ok(result)
}

/// Finds ORACLE_HOME for a given SID using the platform's instance registry.
/// On Unix: parses oratab (standard locations: /etc/oratab, /var/opt/oracle/oratab).
/// On Windows: queries the Windows registry under SOFTWARE\Oracle.
/// Comparison of SID is case-insensitive.
/// Returns the Result with optional ORACLE_HOME.
/// None means "SID is not found in registry | oratab". It's not an error, rather misconfiguration.
/// Error means a problem with reading registry | oratab file: lack of Oracle, bad permissions, etc.
pub fn find_oracle_home(
    sid: &Sid,
    custom_path: Option<String>, // can be a registry branch for Windows or a path for Linux
) -> Result<Option<PathBuf>> {
    let locals = get_instances(custom_path)?;

    for local in locals {
        if local.name.to_string().eq_ignore_ascii_case(sid.as_ref()) {
            return Ok(Some(local.home));
        }
    }

    Ok(None)
}

fn format_instance_info(
    local_instance: &LocalInstance,
    known_processes: Option<&HashSet<String>>,
) -> String {
    let state = if let Some(processes) = known_processes {
        if processes.contains(&local_instance.name.to_string()) {
            "Run"
        } else {
            "Stop"
        }
    } else {
        "N/A"
    };
    format!(
        "{:16} {:5} {:60} {}",
        local_instance.name,
        state,
        local_instance.home.display(),
        local_instance
            .base
            .as_ref()
            .map(|p| p.display().to_string())
            .unwrap_or_else(|| "N/A".to_string()),
    )
}

fn instance_info_header() -> String {
    format!(
        "{:16} {:5} {:60} {}",
        "SID", "STATE", "ORACLE_HOME", "ORACLE_BASE"
    )
}

pub fn dump_detected_sids() -> String {
    let oracle_processes = if cfg!(windows) {
        None
    } else {
        Some(
            find_sids_by_processes(None)
                .map_err(|e| {
                    log::info!("Error while detecting Oracle processes: {:?}", e);
                })
                .unwrap_or_default(),
        )
    };

    print_detected_sids(&get_instances(None).unwrap_or_default(), oracle_processes)
}

fn print_detected_sids(
    locals: &[LocalInstance],
    oracle_processes: Option<HashSet<String>>,
) -> String {
    let rows = locals
        .iter()
        .map(|local| format_instance_info(local, oracle_processes.as_ref()))
        .collect::<Vec<String>>()
        .join("\n");
    if rows.is_empty() {
        "No local instances found.\n".to_string()
    } else {
        instance_info_header() + "\n" + &rows + "\n"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{InstanceName, LocalInstance};
    use std::path::PathBuf;

    fn make_instance(name: &str, home: &str, base: Option<&str>) -> LocalInstance {
        LocalInstance {
            name: InstanceName::from(name),
            home: PathBuf::from(home),
            base: base.map(PathBuf::from),
        }
    }

    #[test]
    fn test_find_sids_by_processes() {
        let re = Regex::new(SID_MASK).expect("Failed to compile regex");
        let x = re
            .captures("ora_pmon_TEST19")
            .and_then(|c| c.get(2))
            .map(|m| m.as_str().to_string());
        assert_eq!(x, Some("TEST19".to_string()));
    }

    fn parts(inst: LocalInstance, processes: Option<&HashSet<String>>) -> Vec<String> {
        format_instance_info(&inst, processes)
            .split_whitespace()
            .map(str::to_string)
            .collect()
    }

    #[test]
    fn test_format_instance_info_no_processes() {
        let result = parts(make_instance("orcl", "/path/to/ora/home", None), None);
        assert_eq!(result, vec!["ORCL", "N/A", "/path/to/ora/home", "N/A"]);
    }

    #[test]
    fn test_format_instance_info_running() {
        let procs = HashSet::from(["TEST19".to_string()]);
        let result = parts(
            make_instance("TEST19", "/path/to/ora/home", Some("/path/to/ora/base")),
            Some(&procs),
        );
        assert_eq!(
            result,
            vec!["TEST19", "Run", "/path/to/ora/home", "/path/to/ora/base"]
        );
    }

    #[test]
    fn test_format_instance_info_stopped() {
        let result = parts(
            make_instance("TEST19", "/path/to/ora/home", Some("/path/to/ora/base")),
            Some(&HashSet::new()),
        );
        assert_eq!(
            result,
            vec!["TEST19", "Stop", "/path/to/ora/home", "/path/to/ora/base"]
        );
    }

    #[test]
    fn test_format_instance_info_no_base() {
        let result = parts(make_instance("XE", "/path/to/ora/home", None), None);
        assert_eq!(result, vec!["XE", "N/A", "/path/to/ora/home", "N/A"]);
    }

    fn split_row(line: &str) -> Vec<&str> {
        line.split_whitespace().collect()
    }

    /// Empty instance list — even with known processes the output is the "not found" message.
    #[test]
    fn test_print_detected_sids_empty() {
        let procs = HashSet::from(["abc".to_string(), "xyz".to_string()]);
        let result = print_detected_sids(&[], Some(procs));
        assert_eq!(result, "No local instances found.\n");
    }

    /// Windows output: process state is always "N/A" because we don't check processes on Windows, only registry.
    #[test]
    fn test_print_detected_sids_windows() {
        let instances = vec![
            make_instance("TEST19", "/path/to/ora/home", None),
            make_instance("XE", "/path/to/ora/xe", Some("/path/to/ora/base")),
        ];
        let output = print_detected_sids(&instances, None);
        let lines: Vec<&str> = output.lines().collect();
        assert_eq!(
            split_row(lines[1]),
            vec!["TEST19", "N/A", "/path/to/ora/home", "N/A"]
        );
        assert_eq!(
            split_row(lines[2]),
            vec!["XE", "N/A", "/path/to/ora/xe", "/path/to/ora/base"]
        );
    }

    /// Linux output: process has info "Run" or "Stop".
    #[test]
    fn test_print_detected_sids_linux() {
        let instances = vec![
            make_instance("TEST19", "/path/to/ora/home", Some("/path/to/ora/base")),
            make_instance("XE", "/path/to/ora/xe", None),
        ];
        let procs = HashSet::from(["TEST19".to_string()]);
        let output = print_detected_sids(&instances, Some(procs));
        let lines: Vec<&str> = output.lines().collect();
        assert_eq!(
            split_row(lines[1]),
            vec!["TEST19", "Run", "/path/to/ora/home", "/path/to/ora/base"]
        );
        assert_eq!(
            split_row(lines[2]),
            vec!["XE", "Stop", "/path/to/ora/xe", "N/A"]
        );
    }
}
