// Copyright (C) 2018 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to separate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]

#[cfg(not(feature = "build_system_bazel"))]
mod common;

#[cfg(feature = "build_system_bazel")]
extern crate common;

use common::agent;

use assert_cmd::prelude::OutputAssertExt;
use predicates::prelude::*;

#[cfg(windows)]
#[test]
fn test_environment() {
    // it seems we need this flag to properly link openssl on Windows
    let env_value = std::env::var("CFLAGS")
        .map_err(|e| anyhow::anyhow!("{e}"))
        .unwrap();
    assert_eq!(env_value, "-DNDEBUG");
}

#[tokio::test(flavor = "multi_thread")]
async fn test_status_ok() {
    if agent::is_elevation_required() {
        // SK: There is no better method to avoid annoying failures if your
        // IDE/shell is not elevated. The testing script in CI  will require
        // elevation in any case.
        println!("Test is skipped, must be in elevated mode");
        return;
    }
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_status");

    #[cfg(unix)]
    {
        tokio::spawn(agent::linux::agent_response_loop(
            agent::linux::setup_agent_socket_path(test_dir.path()),
            String::from("some-agent-output"),
        ));
    }

    let mut cmd = assert_cmd::Command::new(common::controller_command_path());
    cmd.env("DEBUG_HOME_DIR", test_dir.path())
        .arg("status")
        .unwrap()
        .assert()
        .success()
        .stdout(
            predicate::str::contains("No connections")
                .and(predicate::str::contains("Agent socket: operational")),
        );

    test_dir.close().unwrap();
}

#[cfg(unix)]
#[test]
fn test_status_socket_down() {
    let mut cmd = assert_cmd::Command::new(common::controller_command_path());
    cmd.env("DEBUG_HOME_DIR", "/hurz/barz")
        .arg("status")
        .unwrap()
        .assert()
        .success()
        .stdout(
            predicate::str::contains("No connections")
                .and(predicate::str::contains("Agent socket: inoperational (!!)")),
        );
}
