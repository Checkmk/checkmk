// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Test files are compiled to seperate crates, so there
// may be some unused functions in the common module
#![allow(dead_code)]

#[cfg(not(feature = "build_system_bazel"))]
mod common;

#[cfg(feature = "build_system_bazel")]
extern crate common;

#[cfg(unix)]
use anyhow::Result as AnyhowResult;

use common::agent;

use assert_cmd::prelude::OutputAssertExt;
use cmk_agent_ctl::configuration::config;
#[cfg(unix)]
use predicates::prelude::predicate;
use std::fs;
use std::path::Path;

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
            if line.starts_with(format!("  {mode}").as_str()) {
                n_modes_found += 1;
                break;
            }
        }
    }
    n_modes_found == SUPPORTED_MODES.len()
}

#[test]
fn test_help() {
    let output = assert_cmd::Command::new(common::controller_command_path())
        .arg("-h")
        .unwrap();
    let stdout = std::str::from_utf8(&output.stdout).unwrap();
    assert!(stdout.contains("Checkmk agent controller"));
    assert!(test_supported_modes(String::from(stdout)));
    assert_eq!(&output.stderr, b"");
    output.assert().success();
}

#[cfg(unix)]
#[tokio::test(flavor = "multi_thread")]
async fn test_dump() -> AnyhowResult<()> {
    let test_dir = common::setup_test_dir("cmk_agent_ctl_test_dump-");

    let test_agent_output = "some test agent output";
    let agent_socket_address = agent::linux::setup_agent_socket_path(test_dir.path());
    let expected_remote_address = Some("\n");
    let agent_stream_thread = tokio::spawn(agent::linux::one_time_agent_response(
        agent_socket_address,
        test_agent_output,
        expected_remote_address,
    ));

    let mut cmd = assert_cmd::Command::new(common::controller_command_path());

    cmd.env("DEBUG_HOME_DIR", test_dir.path())
        .arg("-vv")
        .arg("dump")
        .unwrap()
        .assert()
        .success()
        .stdout(predicate::str::contains(test_agent_output));

    agent_stream_thread.await??;
    test_dir.close()?;

    Ok(())
}

/// Tests that 'cmk-agent-ctl' errors if it cannot switch to the correct user.
#[cfg(unix)]
#[test]
fn test_fail_become_user() {
    // If the environment variable DEBUG_HOME_DIR is set this test will hang.
    std::env::remove_var("DEBUG_HOME_DIR");
    for mode in SUPPORTED_MODES {
        if mode == "help" {
            continue;
        }
        let mut cmd = assert_cmd::Command::new(common::controller_command_path());
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
        let mut cmd = assert_cmd::Command::new(common::controller_command_path());
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

fn write_legacy_registry(path: impl AsRef<Path>) {
    fs::write(
        path,
        r#"{
        "push": {},
        "pull": {
          "server:8000/site": {
            "uuid": "9a2c4eb5-35f5-4bf7-82c0-e2f2c06215ea",
            "private_key": "private_key",
            "certificate": "certificate",
            "root_cert": "root_cert"
          }
        },
        "pull_imported": []
      }"#,
    )
    .unwrap();
}

#[test]
#[cfg_attr(target_os = "windows", ignore)] // skipped in windows as a flaky
fn test_migration_is_always_triggered() {
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_migration_is_always_triggered");
    let path_registry = test_dir.path().join("registered_connections.json");

    for mode in SUPPORTED_MODES {
        if mode == "help" {
            continue;
        }
        write_legacy_registry(&path_registry);
        assert!(config::Registry::from_file(&path_registry).is_err());
        let mut cmd = assert_cmd::Command::new(common::controller_command_path());
        cmd.timeout(std::time::Duration::from_secs(5))
            .env("DEBUG_HOME_DIR", test_dir.path())
            .arg(mode)
            .args(REQUIRED_ARGUMENTS.get(mode).unwrap_or(&vec![]))
            .assert();
        assert!(config::Registry::from_file(&path_registry).is_ok())
    }
}

fn build_status_command_with_log(
    test_dir: &tempfile::TempDir,
    with_log_file: bool,
) -> assert_cmd::Command {
    let mut cmd = assert_cmd::Command::new(common::controller_command_path());
    cmd.timeout(std::time::Duration::from_secs(5))
        .env("DEBUG_HOME_DIR", test_dir.path())
        .env("MK_LOGDIR", test_dir.path())
        .env(
            "CMK_AGENT_CTL_LOG_TO_FILE",
            if with_log_file { "1" } else { "0" },
        )
        .arg("-vv")
        .arg("status")
        .arg("--no-query-remote");
    cmd
}

#[cfg(windows)]
#[test]
fn test_log_to_file() {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return;
    }

    let test_dir = common::setup_test_dir("cmk-agent-ctl-logging");
    let log_file = test_dir.path().join("cmk-agent-ctl_rCURRENT.log");

    build_status_command_with_log(&test_dir, false).assert();
    assert!(!log_file.exists());
    build_status_command_with_log(&test_dir, true).assert();
    assert!(fs::read_to_string(&log_file)
        .unwrap()
        .contains("Mode status"));
}
