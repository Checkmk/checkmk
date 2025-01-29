// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod agent;
pub mod certs;
use assert_cmd::Command;

pub fn setup_test_dir(prefix: &str) -> tempfile::TempDir {
    tempfile::Builder::new().prefix(prefix).tempdir().unwrap()
}

pub fn controller_command() -> Command {
    Command::cargo_bin("cmk-agent-ctl").unwrap()
}
