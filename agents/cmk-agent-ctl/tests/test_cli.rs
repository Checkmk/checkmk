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

fn supported_modes() -> Vec<&'static str> {
    vec![
        "daemon",
        "delete",
        "delete-all",
        "dump",
        "help",
        "import",
        "proxy-register",
        "pull",
        "push",
        "register",
        "status",
    ]
}

fn test_supported_modes(help_stdout: String) -> bool {
    let mut n_modes_found = 0;
    for line in help_stdout.split('\n') {
        for mode in supported_modes() {
            if line.starts_with(format!("    {}", mode).as_str()) {
                n_modes_found += 1;
                break;
            }
        }
    }
    n_modes_found == supported_modes().len()
}

#[test]
fn test_help() {
    let output = Command::cargo_bin(BINARY).unwrap().arg("-h").unwrap();
    let stdout = std::str::from_utf8(&output.stdout).unwrap();
    assert!(stdout.contains("Checkmk agent controller"));
    assert!(test_supported_modes(String::from(stdout)));
    assert_eq!(&output.stderr, b"");
    output.assert().success();
}

#[tokio::test(flavor = "multi_thread")]
async fn test_dump() -> AnyhowResult<()> {
    let test_dir = common::setup_test_dir("cmk_agent_ctl_test_dump-");

    let test_agent_output = "some test agent output";
    #[cfg(unix)]
    let agent_socket_address = common::setup_agent_socket_path(test_dir.path());
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

    cmd.env("DEBUG_HOME_DIR", test_dir.path())
        .env("DEBUG_WINDOWS_INTERNAL_PORT", "1997")
        .arg("dump")
        .arg("-vv")
        .unwrap()
        .assert()
        .success()
        .stdout(predicate::str::contains(test_agent_output));

    agent_stream_thread.await??;
    test_dir.close()?;

    Ok(())
}

#[cfg(unix)]
#[test]
fn test_fail_become_user() {
    for mode in supported_modes() {
        if mode == "help" {
            continue;
        }
        let mut cmd = Command::cargo_bin(BINARY).unwrap();
        let mut cmd = cmd.arg(mode);
        if mode == "delete" {
            cmd = cmd.arg("some-connection");
        }
        let err = cmd.unwrap_err();
        let output = err.as_output().unwrap();
        assert_eq!(output.status.code(), Some(1));
        assert_eq!(output.stdout, b"");
        assert!(std::str::from_utf8(&output.stderr)
            .unwrap()
            .contains("Failed to run as user 'cmk-agent'."));
    }
}

#[cfg(unix)]
#[test]
fn test_fail_socket_missing() {
    let mut modes_allowed = std::collections::HashSet::new();
    modes_allowed.insert("delete");
    modes_allowed.insert("delete-all");
    modes_allowed.insert("proxy-register");
    modes_allowed.insert("status");
    modes_allowed.insert("help");

    for mode in supported_modes() {
        if modes_allowed.contains(mode) {
            continue;
        }
        let mut cmd = Command::cargo_bin(BINARY).unwrap();
        let cmd = cmd.env("DEBUG_HOME_DIR", "whatever").arg(mode);
        let err = cmd.unwrap_err();
        let output = err.as_output().unwrap();
        assert_eq!(output.status.code(), Some(1));
        assert_eq!(output.stdout, b"");
        assert!(std::str::from_utf8(&output.stderr)
            .unwrap()
            .contains("Something seems wrong with the agent socket"));
    }
}
