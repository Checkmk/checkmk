// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use assert_cmd::{prelude::OutputAssertExt, Command};
use predicates::prelude::*;

const BINARY: &str = "cmk-agent-ctl";

#[test]
fn test_help() {
    let mut cmd = Command::cargo_bin(BINARY).unwrap();
    cmd.arg("-h")
        .unwrap()
        .assert()
        .stdout(predicate::str::contains("Checkmk agent controller"));
}
