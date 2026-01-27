// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.
use anyhow::{anyhow, Result};
use std::io::{BufRead, Read, Write};

const MAX_RESPONSE_SIZE: usize = 8192;
pub const MAX_LINE_SIZE: usize = 2048;

/// Read a single line from a BufRead stream (up to and including the newline terminator).
/// Uses the BufRead trait's read_line method which reads exactly one line.
/// The BufReader may buffer additional data, so the same reader should be reused for subsequent reads.
/// Limits the maximum number of bytes read to MAX_LINE_SIZE to prevent DoS attacks.
pub fn read_line<R: BufRead>(reader: &mut R) -> Result<String> {
    let mut line = String::new();

    let bytes_read = reader.take(MAX_LINE_SIZE as u64).read_line(&mut line)?;

    if bytes_read == 0 {
        return Err(anyhow!("Unexpected end of stream while reading line"));
    }

    if bytes_read >= MAX_LINE_SIZE {
        return Err(anyhow!(
            "Maximum line size of {} bytes reached when reading",
            MAX_LINE_SIZE
        ));
    }

    Ok(line)
}

/// Read stream until no more data is available or the maximum response size is reached.
pub fn read<T: Read>(stream: &mut T) -> Result<String> {
    let mut buf = vec![0u8; MAX_RESPONSE_SIZE];
    let read_bytes = stream.read(&mut buf)?;
    if read_bytes >= MAX_RESPONSE_SIZE {
        return Err(anyhow!("Response too large"));
    }
    let response = String::from_utf8_lossy(&buf[..read_bytes]).to_string();
    Ok(response)
}

pub fn read_bytes<T: Read>(stream: &mut T, size: usize) -> Result<Vec<u8>> {
    if size > MAX_RESPONSE_SIZE {
        return Err(anyhow!("Requested read size too large"));
    }
    let mut buf = vec![0u8; size];
    let mut nbytes = 0;

    while nbytes < size {
        let bytes_read = stream.read(&mut buf[nbytes..])?;
        if bytes_read == 0 {
            return Err(anyhow!(
                "Unexpected end of stream: expected {} bytes, but only got {} bytes",
                size,
                nbytes
            ));
        }
        nbytes += bytes_read;
    }

    Ok(buf)
}

pub fn write<T: Write>(stream: &mut T, data: &str) -> Result<()> {
    stream.write_all(data.as_bytes())?;
    Ok(())
}

pub fn write_bytes<T: Write>(stream: &mut T, data: &[u8]) -> Result<()> {
    stream.write_all(data)?;
    Ok(())
}
