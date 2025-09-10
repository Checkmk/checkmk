// copyright (c) 2025 checkmk gmbh - license: gnu general public license v2
// this file is part of checkmk (https://checkmk.com). it is subject to the terms and
// conditions defined in the file copying, which is part of this source code package.

use check_cert::starttls::smtp::perform as perform_starttls;
use std::io::{Read, Write};

/// A mock stream that returns responses in sequence for each read.
#[derive(Debug)]
struct MockStream {
    responses: Vec<Vec<u8>>,
    write_log: Vec<u8>,
}

impl MockStream {
    fn new(responses: Vec<Vec<u8>>) -> Self {
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
    let result = perform_starttls(&mut MockStream::new(responses), domain);
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
    let result = perform_starttls(&mut MockStream::new(responses), domain);
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
    let result = perform_starttls(&mut MockStream::new(responses), domain);
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
    let result = perform_starttls(&mut MockStream::new(responses), domain);
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
    let result = perform_starttls(&mut MockStream::new(responses), domain);
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
