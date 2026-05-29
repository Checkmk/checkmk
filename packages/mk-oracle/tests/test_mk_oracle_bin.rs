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

use assert_cmd::Command;
use mk_oracle::version::VERSION;
use std::ffi::OsString;
use std::sync::OnceLock;

static BIN_COMMAND_PATH: OnceLock<OsString> = OnceLock::new();

#[cfg(not(feature = "build_system_bazel"))]
fn bin_command_path_impl() -> OsString {
    let path = assert_cmd::cargo::cargo_bin("mk-oracle");
    assert!(path.is_file());
    path.into()
}

#[cfg(feature = "build_system_bazel")]
fn bin_command_path_impl() -> OsString {
    let cwd = std::env::current_dir().unwrap();
    let relative_path: std::path::PathBuf = ["packages", "mk-oracle", "mk-oracle"].iter().collect();
    let path = cwd.join(relative_path);
    assert!(path.is_file());
    path.into()
}

fn run_bin() -> Command {
    let bin_command_path = BIN_COMMAND_PATH.get_or_init(bin_command_path_impl);
    Command::new(bin_command_path)
}

#[test]
fn test_version() {
    let output = run_bin().arg("--version").ok().unwrap();
    let stdout = String::from_utf8(output.stdout).unwrap();
    let expected = format!("mk-oracle {VERSION}\n");
    assert_eq!(stdout, expected, "Unexpected version output");

    if let Ok(cmk_version) = std::env::var("CMK_VERSION") {
        assert_eq!(
            stdout,
            format!("mk-oracle {cmk_version}\n"),
            "Binary version doesn't match CMK_VERSION env var"
        );
    }
}
