// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::starttls::imap::perform;

// Allow duplicate mod for cross-tooling compatibility (Cargo + Bazel)
#[allow(clippy::duplicate_mod)]
#[path = "common/mock_stream.rs"]
mod mock_stream;
use mock_stream::MockStream;

#[test]
fn test_perform_starttls_success() {
    let responses = vec![
        b"* OK Dovecot ready.\r\n".to_vec(),
        b"A001 OK Begin TLS negotiation now.\r\n".to_vec(),
    ];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_ok(),
        "IMAP STARTTLS handshake failed: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_starttls_success_with_untagged_before_ok() {
    let responses = vec![
        b"* OK Cyrus IMAP ready.\r\n".to_vec(),
        b"* CAPABILITY IMAP4rev1 STARTTLS\r\nA001 OK Begin TLS negotiation.\r\n".to_vec(),
    ];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_ok(),
        "IMAP STARTTLS handshake failed: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_starttls_preauth_greeting() {
    // PREAUTH greeting is valid — server considers us already authenticated
    let responses = vec![
        b"* PREAUTH Already authenticated as user\r\n".to_vec(),
        b"A001 OK Begin TLS negotiation.\r\n".to_vec(),
    ];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_ok(),
        "IMAP STARTTLS with PREAUTH greeting failed: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_starttls_bye_greeting() {
    let responses = vec![b"* BYE Too many connections.\r\n".to_vec()];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on BYE greeting");
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains("rejected connection"),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_no_response() {
    let responses = vec![
        b"* OK Server ready.\r\n".to_vec(),
        b"A001 NO STARTTLS not available\r\n".to_vec(),
    ];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on NO response");
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains("declined STARTTLS"),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_bad_response() {
    let responses = vec![
        b"* OK Server ready.\r\n".to_vec(),
        b"A001 BAD Unknown command\r\n".to_vec(),
    ];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on BAD response");
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains("rejected STARTTLS command"),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_invalid_greeting() {
    let responses = vec![b"INVALID not an imap response\r\n".to_vec()];
    let result = perform(&mut MockStream::new(responses));
    assert!(result.is_err(), "Expected error on invalid greeting");
}
