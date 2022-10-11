// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]
mod common;

use anyhow::Result as AnyhowResult;
use assert_cmd::prelude::OutputAssertExt;
use predicates::prelude::predicate;

const SUPPORTED_MODES: [&str; 12] = [
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
    "register-new",
    "status",
];

lazy_static::lazy_static! {
    static ref REQUIRED_ARGUMENTS: std::collections::HashMap<&'static str, Vec<&'static str>> = {
        std::collections::HashMap::from([
            ("delete", vec!["some-connection"]),
            ("register", vec!["-s", "server", "-i", "site", "-U", "user", "-H", "host"]),
            ("proxy-register", vec!["-s", "server", "-i", "site", "-U", "user", "-H", "host"]),
            ("register-new", vec!["-s", "server", "-i", "site", "-U", "user"]),
        ])
    };
}

fn test_supported_modes(help_stdout: String) -> bool {
    let mut n_modes_found = 0;
    for line in help_stdout.split('\n') {
        for mode in SUPPORTED_MODES {
            if line.starts_with(format!("  {}", mode).as_str()) {
                n_modes_found += 1;
                break;
            }
        }
    }
    n_modes_found == SUPPORTED_MODES.len()
}

#[test]
fn test_help() {
    let output = common::controller_command().arg("-h").unwrap();
    let stdout = std::str::from_utf8(&output.stdout).unwrap();
    assert!(stdout.contains("Checkmk agent controller"));
    assert!(test_supported_modes(String::from(stdout)));
    assert_eq!(&output.stderr, b"");
    output.assert().success();
}

/// Generates `random` port in the range 30'000..32'000
/// The reason is to avoid re-using expiring ports which may make troubles
/// if we are testing too often
/// `/ 4` - in windows PID is multiple of 4
fn get_pseudo_random_port() -> u16 {
    (std::process::id() / 4 % 2_000u32) as u16 + 30_000u16
}

#[tokio::test(flavor = "multi_thread")]
async fn test_dump() -> AnyhowResult<()> {
    #[cfg(windows)]
    if !is_elevated::is_elevated() {
        // SK: There is no better method to avoid annoying failures if your
        // IDE is not elevated. Do not worry, that you may occasionally do not
        // test something - the testing script will require elevation in any case.
        println!("Test is skipped, must be in elevated mode");
        return Ok(());
    }
    let port = get_pseudo_random_port();
    let test_dir = common::setup_test_dir("cmk_agent_ctl_test_dump-");

    let test_agent_output = "some test agent output";
    #[cfg(unix)]
    let agent_socket_address = common::setup_agent_socket_path(test_dir.path());
    #[cfg(unix)]
    let expected_remote_address = Some("\n");
    #[cfg(windows)]
    let agent_socket_address = format!("localhost:{}", &port);
    #[cfg(windows)]
    let expected_remote_address: Option<&str> = None;
    let agent_stream_thread = tokio::spawn(common::agent::one_time_agent_response(
        agent_socket_address,
        test_agent_output,
        expected_remote_address,
    ));

    let mut cmd = common::controller_command();

    cmd.env("DEBUG_HOME_DIR", test_dir.path())
        .env("DEBUG_WINDOWS_INTERNAL_PORT", port.to_string())
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
    for mode in SUPPORTED_MODES {
        if mode == "help" {
            continue;
        }
        let mut cmd = common::controller_command();
        let err = cmd
            .arg(mode)
            .args(REQUIRED_ARGUMENTS.get(mode).unwrap_or(&vec![]))
            .unwrap_err();
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
    let error_message_socket = "Something seems wrong with the agent socket";

    for mode in SUPPORTED_MODES {
        let mut cmd = common::controller_command();
        let output_res = cmd
            .timeout(std::time::Duration::from_secs(1))
            .env("DEBUG_HOME_DIR", "whatever")
            .arg(mode)
            .args(REQUIRED_ARGUMENTS.get(mode).unwrap_or(&vec![]))
            .ok();

        match mode {
            // these commands are expected to fail due to missing socket
            "register" | "register-new" | "import" => {
                let err = output_res.unwrap_err();
                let stderr = std::str::from_utf8(&err.as_output().unwrap().stderr).unwrap();
                assert!(stderr.contains(error_message_socket));
            }
            // for other failing commands, we make sure that the failure is *not* due to the socket
            _ => {
                if let Err(err) = output_res {
                    let stderr = std::str::from_utf8(&err.as_output().unwrap().stderr).unwrap();
                    assert!(!stderr.contains(error_message_socket));
                }
            }
        }
    }
}
