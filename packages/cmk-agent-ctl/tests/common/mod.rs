// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub mod agent;
pub mod certs;
use assert_cmd::Command;
#[cfg(windows)]
pub use is_elevated;

pub fn setup_test_dir(prefix: &str) -> tempfile::TempDir {
    tempfile::Builder::new().prefix(prefix).tempdir().unwrap()
}

#[cfg(unix)]
pub fn setup_agent_socket_path(home_dir: &std::path::Path) -> String {
    std::fs::create_dir(home_dir.join("run")).unwrap();
    home_dir
        .join("run/check-mk-agent.socket")
        .to_str()
        .unwrap()
        .to_string()
}

pub fn controller_command() -> Command {
    Command::cargo_bin("cmk-agent-ctl").unwrap()
}
