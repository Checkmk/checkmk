// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod agent;
pub mod certs;
use std::path;

#[cfg(not(feature = "build_system_bazel"))]
pub fn controller_command_path() -> path::PathBuf {
    assert_cmd::cargo::cargo_bin("cmk-agent-ctl")
}

#[cfg(feature = "build_system_bazel")]
pub fn controller_command_path() -> path::PathBuf {
    let mut path = std::env::current_dir().unwrap();
    path.push("packages");
    path.push("cmk-agent-ctl");
    path.push("cmk-agent-ctl");
    assert!(path.is_file());
    path
}

pub fn setup_test_dir(prefix: &str) -> tempfile::TempDir {
    tempfile::Builder::new().prefix(prefix).tempdir().unwrap()
}
