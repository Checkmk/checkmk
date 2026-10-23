// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
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

use predicates::prelude::*;

#[test]
fn test_update_reports_a_missing_configuration() {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return;
    }
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_update");

    assert_cmd::Command::new(common::controller_command_path())
        .env("DEBUG_HOME_DIR", test_dir.path())
        .arg("update")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Agent updates are not configured for this host",
        ));

    test_dir.close().unwrap();
}

#[test]
fn test_check_only_reports_a_missing_configuration() {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return;
    }
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_update");

    assert_cmd::Command::new(common::controller_command_path())
        .env("DEBUG_HOME_DIR", test_dir.path())
        .args(["update", "--check-only"])
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Agent updates are not configured for this host",
        ));

    test_dir.close().unwrap();
}

/// `activated` gates the daemon only: `update` runs its cycle regardless.
#[test]
fn test_update_runs_while_updates_are_deactivated() {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return;
    }
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_update");
    std::fs::write(
        test_dir.path().join("cmk-agent-ctl-update.toml"),
        "activated = false\ninterval = 60\nsignature_keys = []\n",
    )
    .unwrap();

    assert_cmd::Command::new(common::controller_command_path())
        .env("DEBUG_HOME_DIR", test_dir.path())
        .arg("update")
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "No agent update is possible for this host",
        ));

    test_dir.close().unwrap();
}

/// A configuration that cannot be read is a failure, not "nothing to do".
#[test]
fn test_update_exits_with_1_on_a_broken_configuration() {
    assert_exits_with_1_on_a_broken_configuration(&["update"]);
}

#[test]
fn test_check_only_exits_with_1_on_a_broken_configuration() {
    assert_exits_with_1_on_a_broken_configuration(&["update", "--check-only"]);
}

fn assert_exits_with_1_on_a_broken_configuration(args: &[&str]) {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return;
    }
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_update");
    std::fs::write(
        test_dir.path().join("cmk-agent-ctl-update.toml"),
        "activated = \"yes\"\n",
    )
    .unwrap();

    // Every mode warns about the broken file, so only the final ERROR tells.
    assert_cmd::Command::new(common::controller_command_path())
        .env("DEBUG_HOME_DIR", test_dir.path())
        .args(args)
        .assert()
        .code(1)
        .stderr(
            predicate::str::is_match(r"ERROR .*Failed to load the updater configuration").unwrap(),
        );

    test_dir.close().unwrap();
}
