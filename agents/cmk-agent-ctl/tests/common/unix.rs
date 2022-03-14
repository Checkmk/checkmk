// Copyright (C) 2018 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::path::Path;

use anyhow::Result as AnyhowResult;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufStream};
use tokio::net::{UnixListener, UnixStream};

pub async fn agent_call<P>(
    agent_socket_path: P,
    output: &str,
    expected_input: Option<&str>,
) -> AnyhowResult<()>
where
    P: AsRef<Path>,
{
    let unix_socket = tokio::net::UnixListener::bind(agent_socket_path).unwrap();
    let (unix_stream, _) = unix_socket.accept().await?;
    agent_response(unix_stream, output.into(), expected_input).await
}

pub async fn agent_loop(unix_socket: UnixListener, output: &str) -> AnyhowResult<()> {
    loop {
        let (unix_stream, _) = unix_socket.accept().await?;
        tokio::spawn(agent_response(unix_stream, output.into(), None));
    }
}

async fn agent_response(
    unix_stream: UnixStream,
    output: String,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    let mut buffered_stream = BufStream::new(unix_stream);
    let mut buf = String::new();
    buffered_stream.read_line(&mut buf).await?;

    if let Some(input) = expected_input {
        assert_eq!(buf, input);
    }

    buffered_stream.write_all(output.as_bytes()).await?;
    buffered_stream.flush().await?;
    Ok(())
}
