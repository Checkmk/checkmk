// Copyright (C) 2018 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use anyhow::Error as AnyhowError;
use anyhow::Result as AnyhowResult;
#[cfg(unix)]
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufStream};
#[cfg(windows)]
use tokio::io::{AsyncReadExt, AsyncWriteExt};
#[cfg(windows)]
use tokio::net::{TcpListener, TcpStream};
#[cfg(unix)]
use tokio::net::{UnixListener, UnixStream};

pub async fn one_time_agent_response(
    socket_address: String,
    output: &str,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    #[cfg(unix)]
    let socket = UnixListener::bind(socket_address).unwrap();
    #[cfg(windows)]
    let socket = TcpListener::bind(socket_address).await?;
    let (stream, _) = socket.accept().await?;
    agent_response(stream, output.into(), expected_input).await
}

pub async fn agent_response_loop(socket_address: String, output: &str) -> AnyhowResult<()> {
    #[cfg(unix)]
    let socket = UnixListener::bind(socket_address).unwrap();
    #[cfg(windows)]
    let socket = TcpListener::bind(socket_address).await?;
    loop {
        let (stream, _) = socket.accept().await?;
        tokio::spawn(agent_response(stream, output.into(), None));
    }
}

#[cfg(unix)]
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

#[cfg(windows)]
pub async fn agent_response(
    mut stream: TcpStream,
    output: String,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    let mut buf = vec![];
    tokio::time::timeout(tokio::time::Duration::from_secs(1), async {
        loop {
            stream.read_buf(&mut buf).await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
            if !buf.is_empty() {
                return Ok::<(), AnyhowError>(());
            }
        }
    })
    .await
    .unwrap_or(Ok(()))?;

    if let Some(input) = expected_input {
        assert_eq!(String::from_utf8(buf)?, input);
    }

    stream.write_all(output.as_bytes()).await?;
    stream.flush().await?;
    Ok(())
}
