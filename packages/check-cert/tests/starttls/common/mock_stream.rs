// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::io::{Read, Write};

/// A mock stream that returns responses in sequence for each read.
#[derive(Debug)]
pub struct MockStream {
    responses: Vec<Vec<u8>>,
    write_log: Vec<u8>,
}

impl MockStream {
    pub fn new(responses: Vec<Vec<u8>>) -> Self {
        Self {
            responses,
            write_log: Vec::new(),
        }
    }
}

impl Read for MockStream {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        if self.responses.is_empty() {
            return Ok(0);
        }
        let response = self.responses.remove(0);
        let len = response.len().min(buf.len());
        buf[..len].copy_from_slice(&response[..len]);
        Ok(len)
    }
}

impl Write for MockStream {
    fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
        self.write_log.extend_from_slice(buf);
        Ok(buf.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}
