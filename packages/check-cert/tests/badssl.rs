// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// Integration tests, run with `cargo test -- --ignored`

use assert_cmd::Command;
use assertor::*;
use std::process::Output;

fn cmd(host: &str) -> Command {
    let mut cmd = Command::cargo_bin("check_cert").unwrap();
    cmd.args(["--url", host]);
    cmd
}

fn stdout(out: Result<Output, std::io::Error>) -> String {
    String::from_utf8(out.unwrap().stdout).unwrap()
}

fn failure(reason: &str) -> String {
    format!("Certificate chain verification failed: {reason} (!)")
}

#[test]
#[ignore]
fn test_expired() {
    let mut cmd = cmd("expired.badssl.com");
    assert_that!(stdout(cmd.output())).contains(failure("certificate has expired"));
}

#[test]
#[ignore]
fn test_wrong_host() {
    #[allow(unused_variables, unused_mut)]
    let mut cmd = cmd("wrong.host.badssl.com");

    todo!("should fail");
}

#[test]
#[ignore]
fn test_self_signed() {
    let mut cmd = cmd("self-signed.badssl.com");
    assert_that!(stdout(cmd.output())).contains(failure("self-signed certificate"));
}

#[test]
#[ignore]
fn test_allow_self_signed() {
    let mut cmd = cmd("self-signed.badssl.com");
    cmd.arg("--allow-self-signed");

    assert_that!(stdout(cmd.output()))
        .contains("Certificate chain verification OK: self-signed certificate");
}

#[test]
#[ignore]
fn test_untrusted_root() {
    let mut cmd = cmd("self-signed.badssl.com");

    assert_that!(stdout(cmd.output())).contains(failure("self-signed certificate"));
}

#[test]
#[ignore]
fn test_revoked() {
    let mut cmd = cmd("revoked.badssl.com");

    assert_that!(stdout(cmd.output())).contains("certificate has expired");
}

#[test]
#[ignore]
fn test_pinning_test() {
    #[allow(unused_variables, unused_mut)]
    let mut cmd = cmd("pinning-test.badssl.com");

    todo!("should fail");
}
