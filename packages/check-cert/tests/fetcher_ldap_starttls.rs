// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! End-to-end tests for LDAP STARTTLS certificate fetching (CMK-32024).
//!
//! An in-process server speaks the plaintext LDAP STARTTLS exchange and
//! then upgrades the very same TCP connection to TLS. This
//! exercises the full `fetch_server_cert` pipeline (TCP connect -> STARTTLS
//! handshake -> TLS handshake -> certificate retrieval) against a real socket
//! and a real TLS stack, which the mock-stream unit tests cannot cover.
//!
//! Certificate generation, the Config builder and the TLS upgrade come from
//! the shared tls_server test helper.

use check_cert::fetcher::{fetch_server_cert, ConnectionType};
use openssl::pkey::{PKey, Private};
use openssl::x509::X509;
use std::io::Read;
use std::io::Write;
use std::net::TcpListener;
use std::thread::{self, JoinHandle};
use std::time::Duration;

// Allow duplicate mod for cross-tooling compatibility (Cargo + Bazel)
#[allow(clippy::duplicate_mod)]
#[path = "starttls/common/tls_server.rs"]
mod tls_server;
use tls_server::{accept_tls, config, make_self_signed_cert};

const STARTTLS_OID: &[u8] = b"1.3.6.1.4.1.1466.20037";
const RESULT_SUCCESS: u8 = 0;
const RESULT_UNWILLING_TO_PERFORM: u8 = 52;
const TIMEOUT: Duration = Duration::from_secs(5);

fn ldap_extended_response(result_code: u8) -> Vec<u8> {
    let mut response = vec![
        0x30, 0x0c, // SEQUENCE, length 12
        0x02, 0x01, 0x01, // INTEGER messageID = 1
        0x78, 0x07, // APPLICATION 24 (ExtendedResponse), length 7
        0x0a, 0x01, 0x00, // ENUMERATED resultCode (placeholder, set below)
        0x04, 0x00, // matchedDN = ""
        0x04, 0x00, // diagnosticMessage = ""
    ];
    response[9] = result_code;
    response
}

/// Spawn an in-process LDAP server on an ephemeral loopback port.
///
/// Like a real LDAP server it stays silent after accepting the connection,
/// answers the client's STARTTLS ExtendedRequest with `result_code` and, on
/// success, upgrades the connection to TLS serving `cert`. Returns the port
/// and a handle yielding the raw STARTTLS request received from the client.
fn spawn_ldap_starttls_server(
    cert: X509,
    key: PKey<Private>,
    result_code: u8,
) -> (u16, JoinHandle<Vec<u8>>) {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    let port = listener.local_addr().unwrap().port();
    let handle = thread::spawn(move || {
        let (mut stream, _) = listener.accept().unwrap();
        stream.set_read_timeout(Some(TIMEOUT)).unwrap();

        // RFC 4511: the client speaks first with an ExtendedRequest.
        let mut request = vec![0u8; 256];
        let n = stream.read(&mut request).unwrap();
        request.truncate(n);
        stream
            .write_all(&ldap_extended_response(result_code))
            .unwrap();

        if result_code == RESULT_SUCCESS {
            // Wait for the client's close_notify before tearing down.
            let mut tls = accept_tls(stream, &cert, &key);
            let _ = tls.read(&mut [0u8; 32]);
        }
        request
    });
    (port, handle)
}

#[test]
fn test_fetch_server_cert_via_ldap_starttls() {
    let (cert, key) = make_self_signed_cert("localhost");
    let (port, server) = spawn_ldap_starttls_server(cert.clone(), key, RESULT_SUCCESS);

    let chain = fetch_server_cert(
        "127.0.0.1",
        port,
        config(ConnectionType::LdapStarttls, TIMEOUT),
    )
    .expect("fetching the certificate via LDAP STARTTLS failed");

    assert_eq!(chain.len(), 1);
    assert_eq!(chain[0], cert.to_der().unwrap());

    // The client must have sent the STARTTLS extended operation (RFC 2830).
    let request = server.join().unwrap();
    assert!(
        request
            .windows(STARTTLS_OID.len())
            .any(|window| window == STARTTLS_OID),
        "STARTTLS request did not contain OID 1.3.6.1.4.1.1466.20037: {request:02x?}"
    );
}

#[test]
fn test_fetch_server_cert_ldap_starttls_refused() {
    let (cert, key) = make_self_signed_cert("localhost");
    let (port, server) = spawn_ldap_starttls_server(cert, key, RESULT_UNWILLING_TO_PERFORM);

    let err = fetch_server_cert(
        "127.0.0.1",
        port,
        config(ConnectionType::LdapStarttls, TIMEOUT),
    )
    .expect_err("a refused STARTTLS request must not yield a certificate");

    assert!(
        err.to_string().contains("result code 52"),
        "Error message was: {err}"
    );
    server.join().unwrap();
}
