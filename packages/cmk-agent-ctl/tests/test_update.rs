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
    assert_reports_a_missing_configuration(&["update"]);
}

#[test]
fn test_check_only_reports_a_missing_configuration() {
    assert_reports_a_missing_configuration(&["update", "--check-only"]);
}

fn assert_reports_a_missing_configuration(args: &[&str]) {
    if agent::is_elevation_required() {
        println!("Test is skipped, must be in elevated mode");
        return;
    }
    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_update");
    let mut controller = assert_cmd::Command::new(common::controller_command_path());
    // The controller looks for the legacy updater in PATH as well, and the
    // machine that runs the test may have an agent with one installed.
    #[cfg(unix)]
    controller.env("PATH", test_dir.path());

    controller
        .env("DEBUG_HOME_DIR", test_dir.path())
        .args(args)
        .assert()
        .success()
        .stdout(predicate::str::contains(
            "Agent updates are not configured for this host",
        ));

    test_dir.close().unwrap();
}

/// CMK-42015: the legacy updater keeps such a host up to date.
#[cfg(unix)]
#[test]
fn test_update_names_the_legacy_updater_of_a_host_without_configuration() {
    assert_names_the_legacy_updater(&["update"]);
}

/// CMK-42015: the legacy updater keeps such a host up to date.
#[cfg(unix)]
#[test]
fn test_check_only_names_the_legacy_updater_of_a_host_without_configuration() {
    assert_names_the_legacy_updater(&["update", "--check-only"]);
}

#[cfg(unix)]
fn assert_names_the_legacy_updater(args: &[&str]) {
    use std::os::unix::fs::PermissionsExt;

    let test_dir = common::setup_test_dir("cmk-agent-ctl_test_update");
    let legacy_updater = test_dir.path().join("cmk-update-agent");
    std::fs::write(&legacy_updater, "").unwrap();
    std::fs::set_permissions(&legacy_updater, std::fs::Permissions::from_mode(0o755)).unwrap();
    let path = std::env::join_paths(
        std::iter::once(test_dir.path().to_owned())
            .chain(std::env::split_paths(&std::env::var_os("PATH").unwrap())),
    )
    .unwrap();

    assert_cmd::Command::new(common::controller_command_path())
        .env("DEBUG_HOME_DIR", test_dir.path())
        .env("PATH", path)
        .args(args)
        .assert()
        .success()
        .stdout(predicate::str::contains("handled by the legacy updater"));

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
