// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::starttls::stream_io::{read_bytes, write_bytes};
use anyhow::{anyhow, Result};
use std::io::{Read, Write};

// https://www.postgresql.org/docs/current/protocol-message-formats.html#PROTOCOL-MESSAGE-FORMATS-SSLREQUEST
const POSTGRES_SSL_REQUEST: [u8; 8] = [
    0x00, 0x00, 0x00, 0x08, // Length of the message: 8 bytes
    0x04, 0xD2, 0x16, 0x2F, // SSLRequest code: 0x04D2 = 1234. 0x162F = 5679
];
const POSTGRES_SSL_RESPONSE_LENGTH: usize = 1;
const POSTGRES_SSL_YES: u8 = b'S';
const POSTGRES_SSL_NO: u8 = b'N';

/// Performs the PostgreSQL SSLRequest handshake (STARTTLS equivalent) as per protocol documentation.
/// https://www.postgresql.org/docs/current/protocol-flow.html#PROTOCOL-FLOW-SSL
/// Returns Ok(()) if the server supports SSL (responds with 'S'), otherwise returns an error.
pub fn perform<T: Read + Write>(stream: &mut T) -> Result<()> {
    // Send SSLRequest message
    write_bytes(stream, &POSTGRES_SSL_REQUEST)?;

    let response = PostgresSslResponse::parse(&read_bytes(stream, POSTGRES_SSL_RESPONSE_LENGTH)?)?;

    match response {
        PostgresSslResponse::SslSupported => Ok(()),
        PostgresSslResponse::SslNotSupported => {
            Err(anyhow!("PostgreSQL server does not support SSL (STARTTLS)"))
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
enum PostgresSslResponse {
    SslSupported,
    SslNotSupported,
}

impl PostgresSslResponse {
    fn parse(response: &[u8]) -> Result<Self> {
        if response.len() != POSTGRES_SSL_RESPONSE_LENGTH {
            // Avoid displaying this error message to the user,
            // because the server has not been authenticated yet (CVE-2024-10977).
            return Err(anyhow!("Unexpected response length: {}", response.len()));
        }
        match response[0] {
            POSTGRES_SSL_YES => Ok(PostgresSslResponse::SslSupported),
            POSTGRES_SSL_NO => Ok(PostgresSslResponse::SslNotSupported),
            // Avoid displaying this error message to the user,
            // because the server has not been authenticated yet (CVE-2024-10977).
            _ => Err(anyhow!("Invalid response byte")),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_postgres_ssl_response_parse_supported() {
        let resp = PostgresSslResponse::parse(b"S").unwrap();
        assert_eq!(resp, PostgresSslResponse::SslSupported);
    }

    #[test]
    fn test_postgres_ssl_response_parse_not_supported() {
        let resp = PostgresSslResponse::parse(b"N").unwrap();
        assert_eq!(resp, PostgresSslResponse::SslNotSupported);
    }

    #[test]
    fn test_postgres_ssl_response_parse_invalid_length() {
        let err = PostgresSslResponse::parse(b"SN");
        assert_eq!(
            err.unwrap_err().to_string(),
            "Unexpected response length: 2"
        );
    }

    #[test]
    fn test_postgres_ssl_response_parse_invalid_byte() {
        let err = PostgresSslResponse::parse(b"X");
        assert_eq!(err.unwrap_err().to_string(), "Invalid response byte");
    }
}
