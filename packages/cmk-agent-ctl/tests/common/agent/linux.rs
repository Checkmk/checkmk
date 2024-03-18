// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufStream};
use tokio::net::{UnixListener, UnixStream};

pub async fn one_time_agent_response(
    socket_address: String,
    output: &str,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    let socket = UnixListener::bind(socket_address).unwrap();
    let (stream, _) = socket.accept().await?;
    agent_response(stream, output.into(), expected_input).await
}

pub async fn agent_response_loop(socket_address: String, output: String) -> AnyhowResult<()> {
    let socket = UnixListener::bind(socket_address).unwrap();
    loop {
        let (stream, _) = socket.accept().await?;
        tokio::spawn(agent_response(stream, output.clone(), None));
    }
}

pub async fn agent_response(
    stream: UnixStream,
    output: String,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    let mut buffered_stream = BufStream::new(stream);
    let mut buf = String::new();
    buffered_stream.read_line(&mut buf).await?;

    if let Some(input) = expected_input {
        assert_eq!(buf, input);
    }

    buffered_stream.write_all(output.as_bytes()).await?;
    buffered_stream.flush().await?;
    Ok(())
}

pub fn setup_agent_socket_path(home_dir: &std::path::Path) -> String {
    std::fs::create_dir(home_dir.join("run")).unwrap();
    home_dir
        .join("run/check-mk-agent.socket")
        .to_str()
        .unwrap()
        .to_string()
}

pub fn is_elevation_required() -> bool {
    false
}

/// On Linux returns true always: this is initial behavior and subject to change in the future
/// with consequent merge both functions into one
pub fn is_port_available(_port: u16) -> bool {
    true
}
