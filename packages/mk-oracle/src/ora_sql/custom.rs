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

use crate::constants::{CONFIG_DIR, RUNTIME_DIR};
use std::path::PathBuf;

pub const ORA_SQL_CUSTOM_SQL_SUB_DIR: &str = "orasql";

/// Main config root with orasql for relative `path:` resolution.
pub fn get_config_sql_dir() -> Option<PathBuf> {
    let path = CONFIG_DIR.join(ORA_SQL_CUSTOM_SQL_SUB_DIR);
    if path.is_dir() {
        Some(path)
    } else {
        None
    }
}

/// Runtime directory with orasql for relative `path:` resolution.
pub fn get_runtime_sql_dir() -> Option<PathBuf> {
    let path = RUNTIME_DIR.join(ORA_SQL_CUSTOM_SQL_SUB_DIR);
    if path.is_dir() {
        Some(path)
    } else {
        None
    }
}

/// Search roots for resolving a relative `path:` value, runtime directory first so it
/// wins on collisions with the config directory.
pub fn get_sql_search_dirs() -> Vec<PathBuf> {
    let mut dirs = Vec::with_capacity(2);
    if let Some(runtime) = get_runtime_sql_dir() {
        dirs.push(runtime);
    }
    if let Some(config) = get_config_sql_dir() {
        dirs.push(config);
    }
    dirs
}
