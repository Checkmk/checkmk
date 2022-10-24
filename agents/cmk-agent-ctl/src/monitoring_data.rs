// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{setup, types};
#[cfg(windows)]
use log::debug;

#[cfg(windows)]
use async_std::net::TcpStream as AsyncTcpStream;
#[cfg(windows)]
use async_std::prelude::*;
#[cfg(windows)]
use std::io::Error;
#[cfg(windows)]
use std::net::IpAddr;

use std::io::{Result as IoResult, Write};

#[cfg(unix)]
use std::io::Read;
#[cfg(unix)]
use std::os::unix::net::UnixStream;
#[cfg(unix)]
use tokio::io::{AsyncReadExt, AsyncWriteExt};
#[cfg(unix)]
use tokio::net::UnixStream as AsyncUnixStream;

#[cfg(windows)]
fn is_error_acceptable(error: &Error) -> bool {
    // special case for Windows related to server/clients with strange behavior
    error.kind() == Error::from_raw_os_error(10054).kind()
}

// TODO(sk): add logging and unit testing(using local server)
#[cfg(windows)]
async fn async_collect_from_ip(
    agent_channel: &types::AgentChannel,
    remote_ip: IpAddr,
) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    debug!("connect to {}", agent_channel.as_ref());
    let mut stream = AsyncTcpStream::connect(agent_channel.as_ref()).await?;
    stream
        .write_all(format!("{}", remote_ip).as_bytes())
        .await?;
    stream.flush().await?;
    let result = stream.read_to_end(&mut data).await;
    let _ = stream.shutdown(std::net::Shutdown::Both); // can't return here, error could be ignored
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

#[cfg(windows)]
pub async fn async_collect(
    agent_channel: &types::AgentChannel,
    remote_ip: std::net::IpAddr,
) -> IoResult<Vec<u8>> {
    async_collect_from_ip(agent_channel, remote_ip).await
}

#[cfg(windows)]
fn collect_from_ip(agent_channel: &types::AgentChannel) -> IoResult<Vec<u8>> {
    async_std::task::block_on(async_collect_from_ip(
        agent_channel,
        IpAddr::from([127, 0, 0, 1]),
    ))
}

#[cfg(windows)]
pub fn collect() -> IoResult<Vec<u8>> {
    collect_from_ip(&setup::agent_channel())
}

#[cfg(unix)]
pub async fn async_collect(
    agent_channel: &types::AgentChannel,
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

#[cfg(unix)]
pub fn collect() -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    let mut agent_stream = UnixStream::connect(setup::agent_channel())?;
    agent_stream.write_all("\n".as_bytes())?; // No remote IP, signalize agent to continue and collect
    agent_stream.read_to_end(&mut mondata)?;
    Ok(mondata)
}

pub fn compress(data: &[u8]) -> IoResult<Vec<u8>> {
    let mut zlib_enc = flate2::write::ZlibEncoder::new(Vec::new(), flate2::Compression::default());
    zlib_enc.write_all(data)?;
    zlib_enc.finish()
}

pub struct CompressionHeaderInfo {
    pub push: String,
    pub pull: Vec<u8>,
}

pub fn compression_header_info() -> CompressionHeaderInfo {
    CompressionHeaderInfo {
        push: String::from("zlib"),
        pull: b"\x01".to_vec(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Read;

    #[test]
    fn test_compress() {
        let input_str = "abc";
        let compressed_data = compress(input_str.as_bytes()).unwrap();
        let mut zlib_dec = flate2::read::ZlibDecoder::new(&compressed_data[..]);
        let mut decompressed_str = String::new();
        zlib_dec.read_to_string(&mut decompressed_str).unwrap();
        assert_eq!(input_str, decompressed_str);
    }
}
