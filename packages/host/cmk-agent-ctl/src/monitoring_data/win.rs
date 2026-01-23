// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{
    mailslot_transport::{self, MailSlotBackend},
    types::AgentChannel,
};
use log::{debug, warn};

use std::net::IpAddr;
use tokio::net::TcpStream;

use std::io::{Error, ErrorKind, Result as IoResult};
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};

/// Absolute max time to wait the agent
const MAX_ANSWER_WAIT_TIME: Duration = Duration::from_secs(180);

#[derive(PartialEq)]
enum ChannelType {
    Ip,
    Mailslot,
}

impl AgentChannel {
    const CHANNEL_MAILSLOT_PREFIX: &'static str = "ms";
    const CHANNEL_IP_PREFIX: &'static str = "ip";
    const CHANNEL_PREFIX_SEPARATOR: char = '/';

    fn split(&self) -> Vec<&str> {
        self.as_ref()
            .split(Self::CHANNEL_PREFIX_SEPARATOR)
            .collect::<Vec<_>>()
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

fn is_error_acceptable(error: &Error) -> bool {
    // special case for Windows related to server/clients with strnage behavior
    error.kind() == std::io::Error::from_raw_os_error(10054).kind()
}

async fn async_collect_from_ip(agent_ip: &str, remote_ip: IpAddr) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    debug!("connect to {}", agent_ip);
    let mut stream = TcpStream::connect(agent_ip).await?;
    stream
        .write_all(format!("{}", remote_ip).as_bytes())
        .await?;
    stream.flush().await?;
    let result = stream.read_to_end(&mut data).await;
    let _ = stream.shutdown().await; // can't return here, error could be ignored
    match result {
        Ok(_) => Ok(data),
        Err(some_err) => {
            if is_error_acceptable(&some_err) {
                debug!("error during receive");
                Ok(data)
            } else {
                Err(some_err)
            }
        }
    }
}

/// Generates correct request for windows agent mailslot
///
/// Attention: must be in sync with windows agent code
fn make_yaml_command(own_mailslot: &str, remote_ip: IpAddr) -> String {
    format!(
        "monitoring_request:\n  text: {} {}\n  id: {}",
        remote_ip,
        own_mailslot,
        std::process::id()
    )
}

/// Sends the command to the agent mailslot and awaits on own mailslot
/// for answer using BIG timeout.
///
/// agent_mailslot - an agent's mailslot(usually services' one).
///
/// remote_ip - an ip from the peer(Site).
///
/// NOTE: uses internally BIG timeout, on the timeout returns empty string with log
async fn async_collect_from_mailslot(agent_mailslot: &str, remote_ip: IpAddr) -> IoResult<Vec<u8>> {
    let own_mailslot = mailslot_transport::build_own_mailslot_name();
    let mut backend =
        MailSlotBackend::new(&own_mailslot).map_err(|e| Error::other(format!("error: {}", e)))?;
    mailslot_transport::send_to_mailslot(
        agent_mailslot,
        mailslot_transport::DataType::Yaml,
        make_yaml_command(backend.used_name(), remote_ip).as_bytes(),
    );
    let value = tokio::time::timeout(MAX_ANSWER_WAIT_TIME, backend.tx.recv())
        .await
        .unwrap_or_else(|e| {
            warn!("Error on receive from channel {:?}", e);
            Some(vec![]) // we return empty string on timeout
        })
        .unwrap_or_default();

    Ok(value)
}

/// Sends the command to the agent channel and awaits
///
/// This is a simple wrapper for Ip and Mailslot channel
pub async fn async_collect(
    agent_channel: &AgentChannel,
    remote_ip: std::net::IpAddr,
) -> IoResult<Vec<u8>> {
    let (ch_type, ch_addr) = agent_channel.parse()?;
    match ch_type {
        ChannelType::Ip => async_collect_from_ip(&ch_addr, remote_ip).await,
        ChannelType::Mailslot => async_collect_from_mailslot(&ch_addr, remote_ip).await,
    }
}

#[tokio::main(flavor = "current_thread")]
async fn collect_from_ip(agent_ip: &str) -> IoResult<Vec<u8>> {
    async_collect_from_ip(agent_ip, IpAddr::from([127, 0, 0, 1])).await
}

#[tokio::main(flavor = "current_thread")]
async fn collect_from_mailslot(mailslot: &str) -> IoResult<Vec<u8>> {
    async_collect_from_mailslot(mailslot, IpAddr::from([127, 0, 0, 1])).await
}

pub fn collect(agent_channel: &AgentChannel) -> IoResult<Vec<u8>> {
    let (ch_type, ch_addr) = agent_channel.parse()?;
    let collector = match ch_type {
        ChannelType::Ip => collect_from_ip,
        ChannelType::Mailslot => collect_from_mailslot,
    };
    collector(&ch_addr)
}

#[cfg(test)]
#[cfg(windows)]
mod tests {
    use crate::mailslot_transport::SERVER_CREATION_TIMEOUT as MAILSLOT_SERVER_TIMEOUT;
    use crate::monitoring_data::win::make_yaml_command;

    use super::{async_collect, AgentChannel, ChannelType};
    use std::fmt;
    use std::io::{ErrorKind, Result as IoResult};
    use std::net::IpAddr;
    use std::time::Duration;

    fn addr() -> IpAddr {
        IpAddr::from([0, 0, 0, 0])
    }
    const EMPTY_DATA: Vec<u8> = vec![];

    impl ChannelType {
        fn to_string_id(&self) -> &str {
            match *self {
                ChannelType::Ip => "Ip",
                ChannelType::Mailslot => "Mailslot",
            }
        }
    }

    impl fmt::Debug for ChannelType {
        fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
            write!(f, "{}", self.to_string_id())
        }
    }

    fn parse_me(s: &str) -> IoResult<(ChannelType, String)> {
        AgentChannel::from(s).parse()
    }

    #[test]
    fn test_address_channel_parse_invalid() {
        for channel in ["", "ms/c/c", "zz/127.0.0.1:x"] {
            assert_eq!(
                parse_me(channel).map_err(|e| e.kind()),
                Err(ErrorKind::InvalidInput)
            );
        }
    }

    #[test]
    fn test_address_channel_parse_valid() {
        for (channel, channel_type) in [
            ("ms/buzz_inc", ChannelType::Mailslot),
            ("ip/buzz_inc", ChannelType::Ip),
            ("buzz_inc", ChannelType::Ip), // legacy
        ] {
            assert_eq!(
                parse_me(channel).unwrap(),
                (channel_type, "buzz_inc".to_string())
            );
        }
    }

    #[test]
    fn test_make_yaml_command() {
        use std::iter::zip;
        let actual: Vec<IpAddr> = vec![
            IpAddr::from([127, 126, 0, 1]),
            IpAddr::from([0, 0, 0, 0, 0, 0xffff, 0xc00a, 0x2ff]),
        ];
        let expected: Vec<&str> = vec!["127.126.0.1", "::ffff:192.10.2.255"];
        zip(actual, expected).for_each(|v| {
            assert_eq!(
                make_yaml_command("mailslot", v.0),
                format!(
                    "monitoring_request:\n  text: {} mailslot\n  id: {}",
                    v.1,
                    std::process::id()
                )
            )
        });
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_async_collect_bad_input() {
        assert_eq!(
            async_collect(&AgentChannel::from(""), addr())
                .await
                .map_err(|e| e.kind()),
            Err(ErrorKind::InvalidInput)
        );
    }

    /// TODO(sk): estimate to move to integration
    #[tokio::test(flavor = "multi_thread")]
    async fn test_async_collect_missing_mailslot() {
        assert_eq!(
            tokio::time::timeout(
                MAILSLOT_SERVER_TIMEOUT + Duration::from_secs(1),
                async_collect(&AgentChannel::from("ms/xxxx"), addr())
            )
            .await
            .unwrap_or_else(|_| Ok(EMPTY_DATA)) // this is semi-OK: timeout
            .unwrap(),
            EMPTY_DATA
        );
    }
}
