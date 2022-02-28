// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::constants;
#[cfg(windows)]
use log::debug;

#[cfg(windows)]
use async_std::net::TcpStream as AsyncTcpStream;
#[cfg(windows)]
use async_std::prelude::*;
#[cfg(windows)]
use std::net::TcpStream as StdTcpStream;

use std::io::{Read, Result as IoResult, Write};

#[cfg(unix)]
use std::os::unix::net::UnixStream;
#[cfg(unix)]
use tokio::io::{AsyncReadExt, AsyncWriteExt};
#[cfg(unix)]
use tokio::net::UnixStream as AsyncUnixStream;

// TODO(sk): add logging and unit testing(using local server)
#[cfg(windows)]
async fn async_collect_from_ip(agent_ip: &str) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    debug!("connect to {}", agent_ip);
    AsyncTcpStream::connect(agent_ip)
        .await?
        .read_to_end(&mut data)
        .await?;
    debug!("delivered {}", data.len());
    Ok(data)
}

// TODO(sk): Deliver the remote ip to Windows agent to satisfy logwatch requirements
#[cfg(windows)]
pub async fn async_collect(_remote_ip: std::net::IpAddr) -> IoResult<Vec<u8>> {
    let peer = format!("localhost:{}", constants::WINDOWS_INTERNAL_PORT);
    async_collect_from_ip(&peer).await
}

#[cfg(windows)]
fn collect_from_ip(agent_ip: &str) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    StdTcpStream::connect(agent_ip)?.read_to_end(&mut data)?;
    Ok(data)
}

#[cfg(windows)]
pub fn collect() -> IoResult<Vec<u8>> {
    let peer = format!("localhost:{}", constants::WINDOWS_INTERNAL_PORT);
    collect_from_ip(&peer)
}

#[cfg(unix)]
pub async fn async_collect(remote_ip: std::net::IpAddr) -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    let mut agent_stream = AsyncUnixStream::connect(constants::AGENT_SOCKET).await?;
    agent_stream
        .write_all(format!("{}\n", remote_ip).as_bytes())
        .await?;
    agent_stream.read_to_end(&mut mondata).await?;
    Ok(mondata)
}

#[cfg(unix)]
pub fn collect() -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    let mut agent_stream = UnixStream::connect("/run/check-mk-agent.socket")?;
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
