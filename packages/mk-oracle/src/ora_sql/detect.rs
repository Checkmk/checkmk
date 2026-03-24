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
use crate::types::Sid;
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

#[cfg(windows)]
fn dump_local_instances() -> String {
    use crate::platform::get_local_instances;

    let instances = get_local_instances().unwrap_or_else(|e| {
        log::error!("{:?}", e);
        vec![]
    });
    let rows = instances
        .iter()
        .map(|i| {
            format!(
                "{:16} {:60} {:60}",
                i.name,
                i.home.display().to_string(),
                i.base
                    .as_deref()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| "N/A".to_string())
            )
        })
        .collect::<Vec<String>>()
        .join("\n");
    let header = format!("{:16} {:60} {:60}", "SID", "ORACLE_HOME", "ORACLE_BASE");

    format!(
        "{}\n{}\nTotal instances found: {}\n",
        header,
        rows,
        instances.len()
    )
}

pub fn dump_detected_sids() -> Result<String> {
    #[cfg(windows)]
    return Ok(dump_local_instances());
    #[cfg(not(windows))]
    return find_sids_by_processes(None)
        .map(|list| {
            log::info!("Found SIDs: {:?}", list);
            list.iter().cloned().collect::<Vec<_>>().join("\n") + "\n"
        })
        .or_else(|e| {
            log::info!("Error while detecting SIDs: {:?}", e);
            anyhow::bail!(e)
        });
}

#[cfg(test)]
mod tests {
    use crate::ora_sql::detect::SID_MASK;
    use regex::Regex;

    #[test]
    fn test_find_sids_by_processes() {
        let re = Regex::new(SID_MASK).expect("Failed to compile regex");
        let x = re
            .captures("ora_pmon_TEST19")
            .and_then(|c| c.get(2))
            .map(|m| m.as_str().to_string());
        assert_eq!(x, Some("TEST19".to_string()));
    }
}
