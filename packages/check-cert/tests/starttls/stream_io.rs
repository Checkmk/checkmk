// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::starttls::stream_io::{read_line, MAX_LINE_SIZE};
use std::io::{BufReader, Cursor};

#[test]
fn test_read_line_success() {
    let data = b"Hello, world!\n";
    let cursor = Cursor::new(data);
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "Hello, world!\n");
}

#[test]
fn test_read_line_with_carriage_return() {
    let data = b"SMTP response\r\n";
    let cursor = Cursor::new(data);
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_ok());
    assert_eq!(result.unwrap(), "SMTP response\r\n");
}

#[test]
fn test_read_line_empty_stream() {
    let data = b"";
    let cursor = Cursor::new(data);
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_err());
    assert!(result
        .unwrap_err()
        .to_string()
        .contains("Unexpected end of stream"));
}

#[test]
fn test_read_line_exceeds_max_size() {
    // Create a line that's longer than MAX_LINE_SIZE bytes without a newline
    // This simulates a DoS attack where an attacker sends data without newlines
    let data = vec![b'A'; MAX_LINE_SIZE + 1000];
    let cursor = Cursor::new(data);
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains(&format!(
            "Maximum line size of {} bytes reached when reading",
            MAX_LINE_SIZE
        )),
        "Expected 'Maximum line size of {} bytes reached when reading' error but got: {}",
        MAX_LINE_SIZE,
        err
    );
}

#[test]
fn test_read_line_max_size_without_newline() {
    // Create exactly MAX_LINE_SIZE bytes without a newline - should hit the limit
    let data = vec![b'B'; MAX_LINE_SIZE];
    let cursor = Cursor::new(data);
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains(&format!(
            "Maximum line size of {} bytes reached when reading",
            MAX_LINE_SIZE
        )),
        "Expected 'Maximum line size of {} bytes reached when reading' error but got: {}",
        MAX_LINE_SIZE,
        err
    );
}
#[test]
fn test_read_line_max_size_with_newline() {
    // Create a line that's exactly MAX_LINE_SIZE bytes including the newline
    // This should fail because we can't distinguish between a legitimate MAX_LINE_SIZE-byte line
    // and a longer line that was truncated at the limit
    let mut data = vec![b'A'; MAX_LINE_SIZE - 1];
    data.push(b'\n');
    assert_eq!(data.len(), MAX_LINE_SIZE);

    let cursor = Cursor::new(data.clone());
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_err());
    let err = result.unwrap_err();
    assert!(
        err.to_string().contains(&format!(
            "Maximum line size of {} bytes reached when reading",
            MAX_LINE_SIZE
        )),
        "Expected 'Maximum line size of {} bytes reached when reading' error but got: {}",
        MAX_LINE_SIZE,
        err
    );
}

#[test]
fn test_read_line_just_under_max_size() {
    // Create a line that's MAX_LINE_SIZE - 1 bytes including the newline (just under the limit)
    let mut data = vec![b'C'; MAX_LINE_SIZE - 2];
    data.push(b'\n');
    assert_eq!(data.len(), MAX_LINE_SIZE - 1);

    let cursor = Cursor::new(data.clone());
    let mut reader = BufReader::new(cursor);

    let result = read_line(&mut reader);
    assert!(result.is_ok());
    let line = result.unwrap();
    assert_eq!(line.len(), MAX_LINE_SIZE - 1);
}

#[test]
fn test_read_line_multiple_lines() {
    let data = b"First line\nSecond line\nThird line\n";
    let cursor = Cursor::new(data);
    let mut reader = BufReader::new(cursor);

    let result1 = read_line(&mut reader);
    assert!(result1.is_ok());
    assert_eq!(result1.unwrap(), "First line\n");

    let result2 = read_line(&mut reader);
    assert!(result2.is_ok());
    assert_eq!(result2.unwrap(), "Second line\n");

    let result3 = read_line(&mut reader);
    assert!(result3.is_ok());
    assert_eq!(result3.unwrap(), "Third line\n");
}
