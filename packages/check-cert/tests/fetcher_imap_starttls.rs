// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

// End-to-end tests for fetching a server certificate via IMAP STARTTLS
// (CMK-32025). An in-process IMAP server performs the plaintext STARTTLS
// exchange on a real TCP socket and then upgrades the connection to TLS,
// serving a self-signed certificate via the shared tls_server helper.

use check_cert::fetcher::{fetch_server_cert, ConnectionType};
use openssl::pkey::{PKey, Private};
use openssl::x509::X509;
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread::{self, JoinHandle};
use std::time::Duration;

// Allow duplicate mod for cross-tooling compatibility (Cargo + Bazel)
#[allow(clippy::duplicate_mod)]
#[path = "starttls/common/tls_server.rs"]
mod tls_server;
use tls_server::{accept_tls, config, make_self_signed_cert};

const GREETING: &[u8] = b"* OK Dovecot ready.\r\n";
const STARTTLS_OK: &[u8] = b"A001 OK Begin TLS negotiation now.\r\n";
const STARTTLS_NO: &[u8] = b"A001 NO STARTTLS not available\r\n";
const TIMEOUT: Duration = Duration::from_secs(10);

fn read_starttls_command(stream: &TcpStream) -> String {
    // The client sends nothing but the STARTTLS command before it waits for
    // our reply, so reading a single buffered line cannot swallow TLS bytes.
    let mut line = String::new();
    BufReader::new(stream.try_clone().unwrap())
        .read_line(&mut line)
        .unwrap();
    line
}

/// Spawn an IMAP server that offers STARTTLS and upgrades to TLS using `cert`.
fn spawn_imap_starttls_server(cert: X509, key: PKey<Private>) -> (u16, JoinHandle<()>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        stream.write_all(GREETING).unwrap();
        assert_eq!(read_starttls_command(&stream).trim_end(), "A001 STARTTLS");
        stream.write_all(STARTTLS_OK).unwrap();

        let mut tls_stream = accept_tls(stream, &cert, &key);
        // Block until the client has fetched the certificate and shut the
        // connection down; closing early would race the client's close_notify.
        let _ = tls_stream.read(&mut [0u8; 64]);
    });
    (port, handle)
}

#[test]
fn test_fetch_server_cert_via_imap_starttls() {
    let (cert, key) = make_self_signed_cert("localhost");
    let (port, server) = spawn_imap_starttls_server(cert.clone(), key);

    let chain = fetch_server_cert(
        "127.0.0.1",
        port,
        config(ConnectionType::ImapStarttls, TIMEOUT),
    )
    .unwrap();

    assert_eq!(chain.len(), 1, "Expected exactly the self-signed cert");
    assert_eq!(chain[0], cert.to_der().unwrap());
    server.join().unwrap();
}

#[test]
fn test_fetch_server_cert_imap_starttls_declined() {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let server = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        stream.write_all(GREETING).unwrap();
        assert_eq!(read_starttls_command(&stream).trim_end(), "A001 STARTTLS");
        stream.write_all(STARTTLS_NO).unwrap();
    });

    let result = fetch_server_cert(
        "127.0.0.1",
        port,
        config(ConnectionType::ImapStarttls, TIMEOUT),
    );

    let err = result.expect_err("Expected error when server declines STARTTLS");
    assert!(
        err.to_string().contains("declined STARTTLS"),
        "Error message was: {}",
        err
    );
    server.join().unwrap();
}
