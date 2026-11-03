// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Shared helpers for the STARTTLS end-to-end tests.
//!
//! These back the in-process servers used by `fetcher_*_starttls.rs`: they
//! generate a self-signed certificate, build a fetcher `Config` and upgrade an
//! accepted plaintext socket to TLS. The protocol-specific plaintext exchange
//! (LDAP, IMAP, ...) stays in the individual test files.

use check_cert::fetcher::{Config, ConnectionType};
use openssl::asn1::{Asn1Integer, Asn1Time};
use openssl::bn::BigNum;
use openssl::hash::MessageDigest;
use openssl::pkey::{PKey, Private};
use openssl::rsa::Rsa;
use openssl::ssl::{SslAcceptor, SslMethod, SslStream};
use openssl::x509::{X509NameBuilder, X509};
use std::net::TcpStream;
use std::time::Duration;

/// Generate a self-signed certificate (and its private key) for `common_name`.
pub fn make_self_signed_cert(common_name: &str) -> (X509, PKey<Private>) {
    let key = PKey::from_rsa(Rsa::generate(2048).unwrap()).unwrap();

    let mut name = X509NameBuilder::new().unwrap();
    name.append_entry_by_text("CN", common_name).unwrap();
    let name = name.build();

    let mut builder = X509::builder().unwrap();
    builder.set_version(2).unwrap();
    builder
        .set_serial_number(&Asn1Integer::from_bn(&BigNum::from_u32(1).unwrap()).unwrap())
        .unwrap();
    builder.set_subject_name(&name).unwrap();
    builder.set_issuer_name(&name).unwrap();
    builder.set_pubkey(&key).unwrap();
    builder
        .set_not_before(&Asn1Time::days_from_now(0).unwrap())
        .unwrap();
    builder
        .set_not_after(&Asn1Time::days_from_now(365).unwrap())
        .unwrap();
    builder.sign(&key, MessageDigest::sha256()).unwrap();
    (builder.build(), key)
}

/// Build a fetcher `Config` for `connection_type` with the given `timeout`.
pub fn config(connection_type: ConnectionType, timeout: Duration) -> Config {
    Config::builder()
        .timeout(Some(timeout))
        .connection_type(connection_type)
        .proxy(None)
        .build()
}

/// Upgrade an accepted plaintext socket to TLS, serving `cert` and `key`.
pub fn accept_tls(stream: TcpStream, cert: &X509, key: &PKey<Private>) -> SslStream<TcpStream> {
    let mut builder = SslAcceptor::mozilla_intermediate(SslMethod::tls()).unwrap();
    builder.set_private_key(key).unwrap();
    builder.set_certificate(cert).unwrap();
    builder.check_private_key().unwrap();
    builder.build().accept(stream).unwrap()
}
