// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::io::{Read, Result as IoResult, Write};
use std::net::TcpStream;

#[cfg(unix)]
use std::os::unix::net::UnixStream;

// TODO(sk): add logging and unit testing(using local server)
#[cfg(windows)]
fn collect_from_ip(agent_ip: &str) -> IoResult<Vec<u8>> {
    let mut data: Vec<u8> = vec![];
    TcpStream::connect(agent_ip)?.read_to_end(&mut data)?;
    Ok(data)
}

#[cfg(windows)]
pub fn collect() -> IoResult<Vec<u8>> {
    collect_from_ip("localhost:6556")
}

#[cfg(unix)]
pub fn collect() -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    UnixStream::connect("/run/check-mk-agent.socket")?.read_to_end(&mut mondata)?;
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
