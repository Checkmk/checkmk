// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{setup, types};
use log::debug;

use async_std::net::TcpStream as AsyncTcpStream;
use async_std::prelude::*;
use std::net::IpAddr;
use std::net::TcpStream as StdTcpStream;

use std::io::{Error, ErrorKind, Read, Result as IoResult};

#[derive(PartialEq)]
enum ChannelType {
    Ip,
    Mailslot,
}

impl types::AgentChannel {
    const CHANNEL_MAILSLOT_PREFIX: &'static str = "ms";
    const CHANNEL_IP_PREFIX: &'static str = "ip";
    const CHANNEL_PREFIX_SEPARATOR: char = '/';

    fn split(&self) -> Vec<&str> {
        return self
            .as_ref()
            .split(Self::CHANNEL_PREFIX_SEPARATOR)
            .collect::<Vec<_>>();
    }

    /// Parse windows agent channel as a pattern"type/address"
    /// where
    ///     type is either "ms" or "ip"
    ///     address is arbitrary string
    fn parse(&self) -> IoResult<(ChannelType, String)> {
        let split = self.split();
        // Legacy case support: agent_channel is "localhost:28250"
        if split.len() == 1 && !split[0].is_empty() {
            return Ok((ChannelType::Ip, split[0].to_string()));
        }
        if split.len() != 2 {
            return Err(Error::new(
                ErrorKind::InvalidInput,
                format!("Malformed agent channel: '{}'", self.as_ref()),
            ));
        }
        let addr = split[1].to_string();
        match split[0] {
            Self::CHANNEL_MAILSLOT_PREFIX => Ok((ChannelType::Mailslot, addr)),
            Self::CHANNEL_IP_PREFIX => Ok((ChannelType::Ip, addr)),
            _ => Err(Error::new(
                ErrorKind::InvalidInput,
                format!(
                    "Unknown agent channel type: '{}' for addr '{}'",
                    split[0], addr
                ),
            )),
        }
    }
}

// TODO(sk): add logging and unit testing(using local server)
async fn async_collect_from_ip(agent_ip: &str, remote_ip: IpAddr) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    debug!("connect to {}", agent_ip);
    let mut stream = AsyncTcpStream::connect(agent_ip).await?;
    stream
        .write_all(format!("{}", remote_ip).as_bytes())
        .await?;
    stream.flush().await?;
    stream.read_to_end(&mut data).await?;
    stream.shutdown(std::net::Shutdown::Both)?;
    debug!("obtained from win-agent {} bytes", data.len());
    Ok(data)
}

// TODO(sk): add logging and unit testing(using local server)
async fn async_collect_from_mailslot(_mailslot: &str, _remote_ip: IpAddr) -> IoResult<Vec<u8>> {
    let data: Vec<u8> = vec![];
    // TODO(sk): send command to mailslot & wait for result on own slot
    Ok(data)
}

pub async fn async_collect(
    agent_channel: &types::AgentChannel,
    remote_ip: std::net::IpAddr,
) -> IoResult<Vec<u8>> {
    let (ch_type, ch_addr) = agent_channel.parse()?;
    match ch_type {
        ChannelType::Ip => async_collect_from_ip(&ch_addr, remote_ip).await,
        ChannelType::Mailslot => async_collect_from_mailslot(&ch_addr, remote_ip).await,
    }
}

fn collect_from_ip(agent_ip: &str) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    StdTcpStream::connect(agent_ip)?.read_to_end(&mut data)?;
    Ok(data)
}

fn collect_from_mailslot(_mailslot: &str) -> IoResult<Vec<u8>> {
    let data: Vec<u8> = vec![];
    // TODO(sk): send command to mailslot & wait for result on own slot
    Ok(data)
}

// TODO(sk) : change function signature on collect(types::AgentChannel)
// do not use config/default/setup implicitly: testing difficult, code non-readable
pub fn collect() -> IoResult<Vec<u8>> {
    let (ch_type, ch_addr) = setup::agent_channel().parse()?;
    match ch_type {
        ChannelType::Ip => collect_from_ip(&ch_addr),
        ChannelType::Mailslot => collect_from_mailslot(&ch_addr),
    }
}

#[cfg(test)]
#[cfg(windows)]
mod tests {
    use super::{async_collect, types, ChannelType};
    use std::fmt;
    use std::io::{ErrorKind, Result as IoResult};
    use std::net::IpAddr;

    fn addr() -> IpAddr {
        IpAddr::from([0, 0, 0, 0])
    }
    const EMPTY_DATA: Vec<u8> = vec![];

    impl fmt::Debug for ChannelType {
        fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
            match *self {
                ChannelType::Ip => write!(f, "Ip"),
                ChannelType::Mailslot => write!(f, "Mailslot"),
            }
        }
    }

    fn parse_me(s: &str) -> IoResult<(ChannelType, String)> {
        types::AgentChannel::from(s).parse()
    }

    #[test]
    fn test_address_channel_parse() {
        assert_eq!(
            parse_me("").map_err(|e| e.kind()),
            Err(ErrorKind::InvalidInput)
        );
        assert_eq!(
            parse_me("ms/c/c").map_err(|e| e.kind()),
            Err(ErrorKind::InvalidInput)
        );
        assert_eq!(
            parse_me("zz/127.0.0.1:x").map_err(|e| e.kind()),
            Err(ErrorKind::InvalidInput)
        );
        assert_eq!(
            parse_me("ms/buzz_inc").unwrap(),
            (ChannelType::Mailslot, "buzz_inc".to_string())
        );
        assert_eq!(
            parse_me("ip/buzz_inc").unwrap(),
            (ChannelType::Ip, "buzz_inc".to_string())
        );
        assert_eq!(
            parse_me("buzz_inc").unwrap(),
            (ChannelType::Ip, "buzz_inc".to_string())
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_async_collect_bad_input() {
        assert_eq!(
            async_collect(&types::AgentChannel::from(""), addr())
                .await
                .map_err(|e| e.kind()),
            Err(ErrorKind::InvalidInput)
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_async_collect_missing_mailslot() {
        assert_eq!(
            async_collect(&types::AgentChannel::from("ms/xxxx"), addr())
                .await
                .unwrap(),
            EMPTY_DATA
        );
    }
}
