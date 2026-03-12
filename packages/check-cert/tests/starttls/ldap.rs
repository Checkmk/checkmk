// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::starttls::ldap::perform;

// Allow duplicate mod for cross-tooling compatibility (Cargo + Bazel)
#[allow(clippy::duplicate_mod)]
#[path = "common/mock_stream.rs"]
mod mock_stream;
use mock_stream::MockStream;

fn success_response() -> Vec<u8> {
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
fn test_perform_starttls_success() {
    let responses = vec![success_response()];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_ok(),
        "LDAP STARTTLS handshake failed: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_starttls_unwilling_to_perform() {
    // resultCode = 52 (unwillingToPerform)
    let responses = vec![vec![
        0x30, 0x0c, // SEQUENCE
        0x02, 0x01, 0x01, // messageID = 1
        0x78, 0x07, // APPLICATION 24
        0x0a, 0x01, 0x34, // ENUMERATED resultCode = 52
        0x04, 0x00, // matchedDN
        0x04, 0x00, // diagnosticMessage
    ]];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on non-success result code");
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains("result code 52"),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_confidentiality_required() {
    // resultCode = 13 (confidentialityRequired)
    let responses = vec![vec![
        0x30, 0x0c, // SEQUENCE
        0x02, 0x01, 0x01, // messageID = 1
        0x78, 0x07, // APPLICATION 24
        0x0a, 0x01, 0x0d, // ENUMERATED resultCode = 13
        0x04, 0x00, // matchedDN
        0x04, 0x00, // diagnosticMessage
    ]];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on non-success result code");
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains("result code 13"),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_empty_response() {
    let responses = vec![vec![]];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on empty response");
}

#[test]
fn test_perform_starttls_invalid_response() {
    // Not an LDAP message at all
    let responses = vec![b"HTTP/1.1 400 Bad Request\r\n".to_vec()];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on invalid response");
}
