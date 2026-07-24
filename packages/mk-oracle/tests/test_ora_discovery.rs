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

//! SID discovery via oratab / Windows registry. Needs a local Oracle
//! installation, but no database connection.

use mk_oracle::platform::registry::get_instances;

#[test]
fn test_detection_registry() {
    let instances = match get_instances(None) {
        Ok(instances) if !instances.is_empty() => instances,
        _ => {
            eprintln!("Skipping test_detection_registry: no local Oracle installation found");
            return;
        }
    };
    eprintln!("Instances = {:?}", instances);
    for i in instances {
        assert!(!i.name.to_string().is_empty());
        assert!(i.home.is_dir(), "missing ORACLE_HOME dir {:?}", i.home);
        // oratab carries no ORACLE_BASE; only the Windows registry does.
        if let Some(base) = i.base {
            assert!(base.is_dir(), "missing ORACLE_BASE dir {:?}", base);
        }
    }
}
