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

/// Inject CMK_VERSION into the build as a compile-time env var.
///
/// Bazel builds don't use this: file_from_flag replaces src/version.rs entirely.
/// Cargo builds (AIX, Solaris, Windows) use this to override the fallback version
/// in src/version.rs via option_env!("CMK_VERSION").
///
/// CI sets CMK_VERSION before invoking ./run or run.cmd.
/// Local builds without CMK_VERSION get the hardcoded fallback from version.rs.
fn main() {
    // Rerun build.rs when CMK_VERSION changes, is set, or is removed.
    println!("cargo:rerun-if-env-changed=CMK_VERSION");
    // Inject CMK_VERSION into rustc env so option_env!("CMK_VERSION") picks it up.
    // Cargo tracks this output: recompiles only when the value actually changes.
    if let Ok(v) = std::env::var("CMK_VERSION") {
        // Strip quotes that Windows cmd may inject into env values.
        // For example, '2.6.0'-2026.05.26
        let v = v.replace(['\'', '"'], "");
        if !v.is_empty() {
            println!("cargo:rustc-env=CMK_VERSION={v}");
        }
    }
}
