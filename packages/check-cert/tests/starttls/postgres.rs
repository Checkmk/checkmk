// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::starttls::postgres::perform;

// Allow duplicate mod for cross-tooling compatibility (Cargo + Bazel)
#[allow(clippy::duplicate_mod)]
#[path = "common/mock_stream.rs"]
mod mock_stream;
use mock_stream::MockStream;

#[test]
fn test_perform_postgres_ssl_supported() {
    let responses = vec![vec![b'S']];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_ok(),
        "Expected SSL support but got error: {:?}",
        result.err()
    );
}

#[test]
fn test_perform_postgres_ssl_not_supported() {
    let responses = vec![vec![b'N']];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_err(),
        "Expected error for SSL not supported but got success"
    );
    let err = result.unwrap_err();
    let expected_msg = "PostgreSQL server does not support SSL (STARTTLS)";
    assert!(
        err.to_string().contains(expected_msg),
        "Error message was: {}",
        err
    );
}

#[test]
fn test_perform_postgres_invalid_response() {
    let responses = vec![vec![0x00]];
    let result = perform(&mut MockStream::new(responses));
    assert!(
        result.is_err(),
        "Expected error for invalid response but got success"
    );
    let err = result.unwrap_err();
    let expected_msg = "Invalid response byte";
    assert!(
        err.to_string().contains(expected_msg),
        "Error message was: {}",
        err
    );
}
