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

use crate::types::Sid;
use anyhow::Result;
use regex::Regex;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use sysinfo::System;

/// Regex pattern to match Oracle SID prefixes for PMON processes.
const SID_MASK: &str = r"^(asm_pmon_|ora_pmon_|xe_pmon_|db_pmon_)";

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

/// Finds the oratab file in standard locations.
/// Returns the Result with path to oratab file or error if not found.
pub fn find_oratab_file(oratab_paths: Option<&[&str]>) -> Result<PathBuf> {
    oratab_paths
        .unwrap_or(&["/etc/oratab", "/var/opt/oracle/oratab"])
        .iter()
        .find(|p| Path::new(p).is_file())
        .map(PathBuf::from)
        .ok_or(anyhow::anyhow!("ORA-99999 oratab not found in local mode")) // ORA-99999 is a code from legacy plugin, we keep it for backward compatibility of error handling
}

/// Finds ORACLE_HOME for a given SID by parsing oratab file.
/// Searches for oratab in standard locations (/etc/oratab, /var/opt/oracle/oratab).
/// Comparison of SID is case-insensitive.
/// Returns the Result with optional ORACLE_HOME.
/// None means "SID is not found in oratab", it's not an error, rather misconfiguration.
/// Error means a problem with reading oratab file: lack of Oracle, permissions problem, etc.
pub fn find_oracle_home_from_oratab(
    sid: &Sid,
    oratab_paths: Option<&[&str]>,
) -> Result<Option<PathBuf>> {
    let oratab_path = find_oratab_file(oratab_paths)?;

    let content = std::fs::read_to_string(oratab_path)
        .map_err(|e| anyhow::anyhow!("Failed to read oratab: {}", e))?;

    for l in content.lines() {
        let line = l.split('#').next().unwrap_or("").trim();
        if line.is_empty() {
            continue;
        }

        let parts: Vec<&str> = line.split(':').collect();
        if parts.len() >= 2 && parts[0].eq_ignore_ascii_case(sid.as_ref()) {
            return Ok(Some(PathBuf::from(parts[1])));
        }
    }

    Ok(None)
}

/// Displays detected running sids, their corresponding paths and statuses
/// For example:
/// XE /opt/oracle/product/18c/dbhomeXE OK
/// WORK1 N/A Absent
pub fn print_local_sids() -> Result<String> {
    find_sids_by_processes(None)
        .map(|list| {
            log::info!("Found SIDs: {:?}", list);
            let mut sids: Vec<_> = list.iter().collect();
            sids.sort();
            sids.iter()
                .map(|sid| {
                    let (name, home, status) = find_oracle_home_from_oratab(&Sid::from(*sid), None)
                        .map(|home| {
                            let status = if home.is_some() { "OK" } else { "Absent" }.to_string();
                            (*sid, home, status)
                        })
                        .unwrap_or_else(|e| (*sid, None, e.to_string()));
                    format!(
                        "'{:16}': home={:60} status={:60}",
                        name,
                        home.map(|p| p.display().to_string())
                            .unwrap_or("N/A".to_string()),
                        status
                    )
                })
                .collect::<Vec<_>>()
                .join("\n")
        })
        .inspect_err(|e| {
            log::info!("No SIDs found {e}"); // no SIDs is OK, it's normal for remote monitoring
        })
}
