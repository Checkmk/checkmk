// Copyright (C) 2018 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result as AnyhowResult;
use std::path::PathBuf;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufStream};
use tokio::net::UnixListener;

pub async fn agent_stream(
    unix_socket: UnixListener,
    output: &str,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    let (unix_stream, _) = unix_socket.accept().await?;
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

pub async fn agent_socket(
    socket_addr: PathBuf,
    output: &str,
    expected_input: Option<&str>,
) -> AnyhowResult<()>
where
{
    let unix_socket = UnixListener::bind(&socket_addr)?;
    agent_stream(unix_socket, output, expected_input).await
}
