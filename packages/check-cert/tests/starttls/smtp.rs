// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::starttls::smtp::perform;

// Allow duplicate mod for cross-tooling compatibility (Cargo + Bazel)
#[allow(clippy::duplicate_mod)]
#[path = "common/mock_stream.rs"]
mod mock_stream;
use mock_stream::MockStream;

#[test]
fn test_perform_starttls_success() {
    let responses = vec![
        b"220 sample.server.com\r\n".to_vec(),
        b"250-sample.server.com at your service, [2001:a61:118e:9b01:fa56:153f:7bdd:5f2a]\
        \r\n250-SIZE 35882577\r\n250-8BITMIME\r\n250-STARTTLS\r\n250 SMTPUTF8\r\n"
            .to_vec(),
        b"220 2.0.0 Ready to start TLS\r\n".to_vec(),
    ];
    let domain = "example.com";
    let result = perform(&mut MockStream::new(responses), domain);
    assert!(
        result.is_ok(),
        "STARTTLS handshake failed: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_starttls_success_with_response_split_in_two_reads() {
    let responses = vec![
        b"220 sample.server.com\r\n".to_vec(),
        // EHLO response split into two reads:
        b"250-sample.server.com at your service, [2001:a61:118e:9b01:fa56:153f:7bdd:5f2a]\r\n"
            .to_vec(),
        b"250-SIZE 35882577\r\n250-8BITMIME\r\n250-STARTTLS\r\n250 SMTPUTF8\r\n".to_vec(),
        b"220 2.0.0 Ready to start TLS\r\n".to_vec(),
    ];
    let domain = "example.com";
    let result = perform(&mut MockStream::new(responses), domain);
    assert!(
        result.is_ok(),
        "STARTTLS handshake failed: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_starttls_invalid_greeting() {
    let responses = vec![b"500 Invalid greeting\r\n".to_vec()];
    let domain = "example.com";
    let result = perform(&mut MockStream::new(responses), domain);
    assert!(
        result.is_err(),
        "Expected error on invalid server greeting but got success"
    );
    let err = result.unwrap_err();
    let expected_msg = "Unsupported SMTP reply code. Got: '500'";
    assert!(
        err.to_string().contains(expected_msg),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_unexpected_response_after_ehlo() {
    let responses = vec![
        b"220 sample.server.com\r\n".to_vec(),
        b"500 Unexpected error\r\n".to_vec(),
    ];
    let domain = "example.com";
    let result = perform(&mut MockStream::new(responses), domain);
    assert!(
        result.is_err(),
        "Expected error on unexpected response after EHLO but got success"
    );
    let err = result.unwrap_err();
    let expected_msg = "Unsupported SMTP reply code. Got: '500'";
    assert!(
        err.to_string().contains(expected_msg),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_missing_starttls() {
    let responses = vec![
        b"220 sample.server.com\r\n".to_vec(),
        b"250-sample.server.com at your service\r\n250-SIZE 35882577\r\n250-8BITMIME\r\n250 SMTPUTF8\r\n".to_vec(),
    ];
    let domain = "example.com";
    let result = perform(&mut MockStream::new(responses), domain);
    assert!(
        result.is_err(),
        "Expected error when STARTTLS is missing but got success"
    );
    let err = result.unwrap_err();
    let expected_msg = "Server does not support STARTTLS";
    assert!(
        err.to_string().contains(expected_msg),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_starttls_not_available_temporary() {
    let responses = vec![
        b"220 sample.server.com\r\n".to_vec(),
        b"250-sample.server.com at your service, [2001:a61:118e:9b01:fa56:153f:7bdd:5f2a]\
        \r\n250-SIZE 35882577\r\n250-8BITMIME\r\n250-STARTTLS\r\n250 SMTPUTF8\r\n"
            .to_vec(),
        b"454 TLS not available due to temporary reason\r\n".to_vec(),
    ];
    let domain = "example.com";
    let result = perform(&mut MockStream::new(responses), domain);
    assert!(
        result.is_err(),
        "Expected error when TLS is temporarily unavailable but got success"
    );
    let err = result.unwrap_err();
    let expected_msg = "Unexpected STARTTLS response code: 454";
    assert!(
        err.to_string().contains(expected_msg),
        "Error message was: {}",
        err
    );
}
