// Copyright (C) 2018 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;

use assert_cmd::{prelude::OutputAssertExt, Command};
use predicates::prelude::*;

#[tokio::test(flavor = "multi_thread")]
async fn test_status_ok() {
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_status");

    #[cfg(unix)]
    {
        tokio::spawn(common::agent::agent_response_loop(
            common::setup_agent_socket_path(test_dir.path()),
            String::from("some-agent-output"),
        ));
    }

    let mut cmd = Command::cargo_bin("cmk-agent-ctl").unwrap();
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
    let mut cmd = Command::cargo_bin("cmk-agent-ctl").unwrap();
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
