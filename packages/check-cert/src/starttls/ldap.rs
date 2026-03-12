// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::starttls::stream_io::write_bytes;
use anyhow::{anyhow, Result};
use der_parser::ber::{
    ber_read_element_header, parse_ber_enum, parse_ber_integer, Class, Length, Tag,
};
use log::{debug, info};
use std::io::{Read, Write};

const MAX_RESPONSE_SIZE: usize = 4096;

// LDAP STARTTLS Extended Operation Request (RFC 2830 / RFC 4511)
//
// LDAPMessage ::= SEQUENCE {
//   messageID INTEGER (1),
//   protocolOp ExtendedRequest [APPLICATION 23] {
//     requestName [0] "1.3.6.1.4.1.1466.20037"
//   }
// }
const STARTTLS_REQUEST: &[u8] = &[
    0x30, 0x1d, // SEQUENCE, length 29
    0x02, 0x01, 0x01, // INTEGER messageID = 1
    0x77, 0x18, // APPLICATION 23 (ExtendedRequest), length 24
    0x80, 0x16, // [0] requestName, length 22
    // "1.3.6.1.4.1.1466.20037"
    0x31, 0x2e, 0x33, 0x2e, 0x36, 0x2e, 0x31, 0x2e, 0x34, 0x2e, 0x31, 0x2e, 0x31, 0x34, 0x36, 0x36,
    0x2e, 0x32, 0x30, 0x30, 0x33, 0x37,
];

const RESULT_SUCCESS: u8 = 0;

// APPLICATION 23 tag for LDAP ExtendedResponse (0x78 = class:Application, constructed, tag:24)
const TAG_EXTENDED_RESPONSE: Tag = Tag(24);

/// Performs the LDAP STARTTLS handshake on the given stream according to RFC 2830 / RFC 4511.
pub fn perform<T: Read + Write>(stream: &mut T) -> Result<()> {
    info!("Starting LDAP STARTTLS handshake");

    debug!("Sending LDAP STARTTLS Extended Operation request");
    write_bytes(stream, STARTTLS_REQUEST)?;

    debug!("Reading LDAP STARTTLS response");
    let response = read_response(stream)?;
    let result_code = parse_starttls_response(&response)?;

    if result_code != RESULT_SUCCESS {
        return Err(anyhow!(
            "LDAP STARTTLS failed: server returned result code {}",
            result_code
        ));
    }

    info!("LDAP STARTTLS handshake completed successfully");
    Ok(())
}

fn read_response<T: Read>(stream: &mut T) -> Result<Vec<u8>> {
    let mut buf = vec![0u8; MAX_RESPONSE_SIZE + 1];
    let n = stream.read(&mut buf)?;
    if n == 0 {
        return Err(anyhow!("Empty response from LDAP server"));
    }
    if n > MAX_RESPONSE_SIZE {
        return Err(anyhow!("LDAP response too large"));
    }
    buf.truncate(n);
    Ok(buf)
}

/// Parse an LDAP ExtendedResponse and return the resultCode.
fn parse_starttls_response(data: &[u8]) -> Result<u8> {
    // Parse outer LDAPMessage SEQUENCE
    let (rest, header) = ber_read_element_header(data)
        .map_err(|e| anyhow!("LDAPMessage SEQUENCE: failed to read header: {}", e))?;
    if header.tag() != Tag::Sequence {
        return Err(anyhow!(
            "Expected LDAPMessage SEQUENCE tag 0x{:02x}, got 0x{:02x}",
            Tag::Sequence.0,
            header.tag().0,
        ));
    }
    let msg_len = match header.length() {
        Length::Definite(l) => l,
        Length::Indefinite => return Err(anyhow!("LDAPMessage SEQUENCE has indefinite length")),
    };
    if rest.len() < msg_len {
        return Err(anyhow!("LDAPMessage body truncated"));
    }
    let msg_body = &rest[..msg_len];

    // Skip messageID INTEGER
    let (msg_body, _) =
        parse_ber_integer(msg_body).map_err(|_| anyhow!("Failed to parse messageID INTEGER"))?;

    if msg_body.is_empty() {
        return Err(anyhow!("No protocolOp in LDAPMessage"));
    }

    // Parse ExtendedResponse [APPLICATION 24]
    let (ext_rest, ext_header) = ber_read_element_header(msg_body)
        .map_err(|_| anyhow!("Failed to read ExtendedResponse header"))?;
    if ext_header.class() != Class::Application || ext_header.tag() != TAG_EXTENDED_RESPONSE {
        return Err(anyhow!(
            "Expected ExtendedResponse [APPLICATION 24], got class {:?} tag {:?}",
            ext_header.class(),
            ext_header.tag(),
        ));
    }
    let ext_len = match ext_header.length() {
        Length::Definite(l) => l,
        Length::Indefinite => return Err(anyhow!("ExtendedResponse has indefinite length")),
    };
    if ext_rest.len() < ext_len {
        return Err(anyhow!("ExtendedResponse body truncated"));
    }
    let ext_body = &ext_rest[..ext_len];

    // Parse resultCode ENUMERATED (first field in ExtendedResponse)
    let (_, enum_obj) =
        parse_ber_enum(ext_body).map_err(|_| anyhow!("Failed to parse resultCode ENUMERATED"))?;
    let val = enum_obj
        .as_u64()
        .map_err(|_| anyhow!("resultCode is not a valid ENUMERATED"))?;

    if val > u8::MAX as u64 {
        return Err(anyhow!(
            "Unexpected resultCode ENUMERATED length: value {} exceeds 1 byte (expected 1)",
            val
        ));
    }

    Ok(val as u8)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_success_response() -> Vec<u8> {
        vec![
            0x30, 0x0c, // SEQUENCE, length 12
            0x02, 0x01, 0x01, // INTEGER messageID = 1
            0x78, 0x07, // APPLICATION 24 (ExtendedResponse), length 7
            0x0a, 0x01, 0x00, // ENUMERATED resultCode = 0 (success)
            0x04, 0x00, // matchedDN = ""
            0x04, 0x00, // diagnosticMessage = ""
        ]
    }

    #[test]
    fn test_parse_success_response() {
        let response = make_success_response();
        let result = parse_starttls_response(&response);
        assert!(
            result.is_ok(),
            "Expected success but got: {:?}",
            result.err()
        );
        assert_eq!(result.unwrap(), 0);
    }

    #[test]
    fn test_parse_failure_response() {
        // resultCode = 52 (unwillingToPerform)
        let response = vec![
            0x30, 0x0c, // SEQUENCE
            0x02, 0x01, 0x01, // messageID = 1
            0x78, 0x07, // APPLICATION 24
            0x0a, 0x01, 0x34, // ENUMERATED resultCode = 52
            0x04, 0x00, // matchedDN
            0x04, 0x00, // diagnosticMessage
        ];
        let result = parse_starttls_response(&response);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), 52);
    }

    #[test]
    fn test_parse_response_with_response_name() {
        let oid = b"1.3.6.1.4.1.1466.20037";
        let oid_len = oid.len() as u8;
        let ext_inner_len = 3 + 2 + 2 + oid_len;
        let msg_inner_len = 3 + 2 + ext_inner_len;

        let mut response = vec![
            0x30,
            msg_inner_len,
            0x02,
            0x01,
            0x01, // messageID = 1
            0x78,
            ext_inner_len,
            0x0a,
            0x01,
            0x00, // resultCode = 0
            0x04,
            0x00, // matchedDN = ""
            0x8a,
            oid_len, // [10] responseName
        ];
        response.extend_from_slice(oid);

        let result = parse_starttls_response(&response);
        assert!(result.is_ok(), "Unexpected error: {:?}", result.err());
        assert_eq!(result.unwrap(), 0);
    }

    #[test]
    fn test_parse_invalid_outer_tag() {
        let response = vec![0x31, 0x05, 0x02, 0x01, 0x01, 0x78, 0x00];
        let result = parse_starttls_response(&response);
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("LDAPMessage SEQUENCE"));
    }

    #[test]
    fn test_parse_truncated_response() {
        let response = vec![0x30, 0x0c, 0x02, 0x01, 0x01];
        let result = parse_starttls_response(&response);
        assert!(result.is_err());
    }

    #[test]
    fn test_parse_wrong_protocol_op() {
        let response = vec![
            0x30, 0x05, // SEQUENCE length 5
            0x02, 0x01, 0x01, // messageID = 1
            0x61, 0x00, // APPLICATION 1 (BindResponse), not ExtendedResponse
        ];
        let result = parse_starttls_response(&response);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("ExtendedResponse"));
    }

    #[test]
    fn test_read_response_exact_limit_accepted() {
        let data = vec![0x42u8; MAX_RESPONSE_SIZE];
        let result = read_response(&mut std::io::Cursor::new(data));
        assert!(
            result.is_ok(),
            "Expected a {MAX_RESPONSE_SIZE}-byte response to be accepted, got: {:?}",
            result.err()
        );
        assert_eq!(result.unwrap().len(), MAX_RESPONSE_SIZE);
    }

    #[test]
    fn test_read_response_over_limit_rejected() {
        let data = vec![0x42u8; MAX_RESPONSE_SIZE + 1];
        let result = read_response(&mut std::io::Cursor::new(data));
        assert!(
            result.is_err(),
            "Expected an over-limit response to be rejected"
        );
        assert!(result.unwrap_err().to_string().contains("too large"));
    }

    #[test]
    fn test_read_response_empty_rejected() {
        let result = read_response(&mut std::io::Cursor::new(vec![]));
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Empty response"));
    }

    #[test]
    fn test_parse_multibyte_result_code_rejected() {
        let response = vec![
            0x30, 0x0d, // SEQUENCE, length 13
            0x02, 0x01, 0x01, // INTEGER messageID = 1
            0x78, 0x08, // APPLICATION 24 (ExtendedResponse), length 8
            0x0a, 0x02, 0x01,
            0x00, // ENUMERATED resultCode = multi-byte (len=2, value 0x01 0x00)
            0x04, 0x00, // matchedDN = ""
            0x04, 0x00, // diagnosticMessage = ""
        ];
        let result = parse_starttls_response(&response);
        assert!(
            result.is_err(),
            "Multi-byte resultCode must be rejected, not silently read as success"
        );
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("Unexpected resultCode ENUMERATED length"),);
    }
}
