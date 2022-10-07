// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::AgentChannel;
use std::io::{Read, Result as IoResult, Write};

use std::os::unix::net::UnixStream;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::UnixStream as AsyncUnixStream;

pub async fn async_collect(
    agent_channel: &AgentChannel,
    remote_ip: std::net::IpAddr,
) -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    let mut agent_stream = AsyncUnixStream::connect(agent_channel).await?;
    agent_stream
        .write_all(format!("{}\n", remote_ip).as_bytes())
        .await?;
    agent_stream.read_to_end(&mut mondata).await?;
    Ok(mondata)
}

pub fn collect(agent_channel: &AgentChannel) -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    let mut agent_stream = UnixStream::connect(agent_channel)?;
    agent_stream.write_all("\n".as_bytes())?; // No remote IP, signalize agent to continue and collect
    agent_stream.read_to_end(&mut mondata)?;
    Ok(mondata)
}
