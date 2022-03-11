// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;

#[cfg(unix)]
use anyhow::Result as AnyhowResult;
use assert_cmd::{prelude::OutputAssertExt, Command};
use predicates::prelude::predicate;

const BINARY: &str = "cmk-agent-ctl";

#[test]
fn test_help() {
    let mut cmd = Command::cargo_bin(BINARY).unwrap();
    cmd.arg("-h")
        .unwrap()
        .assert()
        .stdout(predicate::str::contains("Checkmk agent controller"));
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_dump() -> AnyhowResult<()> {
    let test_dir = tempfile::Builder::new()
        .prefix("cmk_agent_ctl_test_dump-")
        .tempdir()
        .unwrap();
    let test_path = test_dir.path();
    std::fs::create_dir(test_path.join("run"))?;

    let test_agent_output = "some test agent output";
    let socket_addr = test_path.join("run/check-mk-agent.socket");
    let agent_stream_thread = tokio::spawn(tokio::time::timeout(
        tokio::time::Duration::from_secs(1),
        common::unix::agent_socket(socket_addr, test_agent_output, Some("\n")),
    ));

    let mut cmd = Command::cargo_bin(BINARY)?;

    cmd.env("DEBUG_HOME_DIR", test_path.to_str().unwrap())
        .arg("dump")
        .arg("-vv")
        .unwrap()
        .assert()
        .stdout(predicate::str::contains(test_agent_output));

    agent_stream_thread.await???;
    test_dir.close()?;

    Ok(())
}
