// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::io::{Read, Result as IoResult};
use std::os::unix::net::UnixStream;

pub fn collect() -> IoResult<Vec<u8>> {
    let mut mondata: Vec<u8> = vec![];
    UnixStream::connect("/run/check-mk-agent.socket")?.read_to_end(&mut mondata)?;
    Ok(mondata)
}

pub fn compress(data: &[u8]) -> IoResult<Vec<u8>> {
    zstd::encode_all(data, zstd::DEFAULT_COMPRESSION_LEVEL)
}

#[cfg(test)]
mod test_registry {
    use super::*;

    #[test]
    fn test_compress() {
        let compressed_data = compress("abc".as_bytes()).unwrap();
        let decompressed_data = zstd::decode_all(&compressed_data[..]).unwrap();
        assert_eq!("abc", String::from_utf8(decompressed_data).unwrap());
    }
}
