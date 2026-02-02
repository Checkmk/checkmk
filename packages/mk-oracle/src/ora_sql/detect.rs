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

use anyhow::Result;
use regex::Regex;
use std::collections::HashSet;
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
