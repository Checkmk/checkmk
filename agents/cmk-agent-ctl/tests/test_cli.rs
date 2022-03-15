// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;

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

#[tokio::test(flavor = "multi_thread")]
async fn test_dump() -> AnyhowResult<()> {
    let test_dir = tempfile::Builder::new()
        .prefix("cmk_agent_ctl_test_dump-")
        .tempdir()
        .unwrap();
    let test_path = test_dir.path();
    std::fs::create_dir(test_path.join("run"))?;

    let test_agent_output = "some test agent output";
    #[cfg(unix)]
    let agent_socket_address = test_path
        .join("run/check-mk-agent.socket")
        .into_os_string()
        .into_string()
        .unwrap();
    #[cfg(unix)]
    let expected_remote_address = Some("\n");
    #[cfg(windows)]
    let agent_socket_address = "localhost:1997".to_string();
    #[cfg(windows)]
    let expected_remote_address: Option<&str> = None;
    let agent_stream_thread = tokio::spawn(common::agent::one_time_agent_response(
        agent_socket_address,
        test_agent_output,
        expected_remote_address,
    ));

    let mut cmd = Command::cargo_bin(BINARY)?;

    cmd.env("DEBUG_HOME_DIR", test_path.to_str().unwrap())
        .env("DEBUG_WINDOWS_INTERNAL_PORT", "1997")
        .arg("dump")
        .arg("-vv")
        .unwrap()
        .assert()
        .stdout(predicate::str::contains(test_agent_output));

    agent_stream_thread.await??;
    test_dir.close()?;

    Ok(())
}
