// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use anyhow::Result as AnyhowResult;
use assert_cmd::{prelude::OutputAssertExt, Command};
use predicates::prelude::*;
use std::io::{BufRead, BufReader, Write};

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
#[test]
fn test_dump() -> AnyhowResult<()> {
    let test_dir = tempfile::tempdir().unwrap().into_path();
    std::fs::create_dir(test_dir.join("run"))?;
    let unix_socket =
        std::os::unix::net::UnixListener::bind(test_dir.join("run/check-mk-agent.socket"))?;

    let agent_stream_thread = std::thread::spawn(move || -> AnyhowResult<()> {
        let (unix_stream, _) = unix_socket.accept()?;
        let mut buf_reader = BufReader::new(unix_stream);
        let mut buf = String::new();
        buf_reader.read_line(&mut buf)?;

        assert_eq!(buf, "\n");

        let mut unix_stream = buf_reader.into_inner();
        unix_stream.write_all(b"some test agent output")?;
        unix_stream.flush()?;
        Ok(())
    });

    let mut cmd = Command::cargo_bin(BINARY)?;

    cmd.env("DEBUG_HOME_DIR", test_dir.to_str().unwrap())
        .arg("dump")
        .arg("-vv")
        .unwrap()
        .assert()
        .stdout(predicate::str::contains("some test agent output"));

    agent_stream_thread.join().unwrap()?;

    Ok(())
}
