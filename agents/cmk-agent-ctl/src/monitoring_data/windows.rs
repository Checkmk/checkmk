// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{setup, types};
use log::debug;

use async_std::net::TcpStream as AsyncTcpStream;
use async_std::prelude::*;
use std::net::TcpStream as StdTcpStream;

use std::io::{Read, Result as IoResult};

// TODO(sk): add logging and unit testing(using local server)
async fn async_collect_from_ip(
    agent_channel: &types::AgentChannel,
    remote_ip: std::net::IpAddr,
) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    debug!("connect to {}", agent_channel.as_ref());
    let mut stream = AsyncTcpStream::connect(agent_channel.as_ref()).await?;
    stream
        .write_all(format!("{}", remote_ip).as_bytes())
        .await?;
    stream.flush().await?;
    stream.read_to_end(&mut data).await?;
    stream.shutdown(std::net::Shutdown::Both)?;
    debug!("obtained from win-agent {} bytes", data.len());
    Ok(data)
}

pub async fn async_collect(
    agent_channel: &types::AgentChannel,
    remote_ip: std::net::IpAddr,
) -> IoResult<Vec<u8>> {
    async_collect_from_ip(agent_channel, remote_ip).await
}

fn collect_from_ip(agent_channel: &types::AgentChannel) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    StdTcpStream::connect(agent_channel.as_ref())?.read_to_end(&mut data)?;
    Ok(data)
}

pub fn collect() -> IoResult<Vec<u8>> {
    collect_from_ip(&setup::agent_channel())
}
