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
    println!("cargo:rerun-if-env-changed=CMK_VERSION");
    eprintln!("[build.rs] ============================");
    match std::env::var("CMK_VERSION") {
        Ok(v) => {
            eprintln!("[build.rs] CMK_VERSION is set to: '{v}'");
            println!("cargo:warning=CMK_VERSION is set to: '{v}'");
            let v = v.replace(['\'', '"'], "");
            if !v.is_empty() {
                println!("cargo:rustc-env=CMK_VERSION={v}");
            } else {
                eprintln!("[build.rs] CMK_VERSION is empty after stripping quotes");
                println!("cargo:warning=CMK_VERSION is empty after stripping quotes");
            }
        }
        Err(e) => {
            eprintln!("[build.rs] CMK_VERSION is NOT set: {e}");
            println!("cargo:warning=CMK_VERSION is NOT set: {e}");
        }
    }
    eprintln!("[build.rs] ============================");
}
