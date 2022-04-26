// Copyright (C) 2018 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use assert_cmd::{prelude::OutputAssertExt, Command};
use predicates::prelude::predicate;

#[test]
fn test_status_ok() {
    let mut cmd = Command::cargo_bin("cmk-agent-ctl").unwrap();
    cmd.env("DEBUG_HOME_DIR", "/hurz/barz")
        .arg("status")
        .unwrap()
        .assert()
        .success()
        .stdout(predicate::str::contains("No connections"));
}
