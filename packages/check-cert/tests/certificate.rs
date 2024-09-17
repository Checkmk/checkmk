// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::check;
use check_cert::checker::certificate::{self, Config as CertConfig};

fn as_der(crt: &[u8]) -> Vec<u8> {
    openssl::x509::X509::from_pem(crt)
        .expect("Cannot fail")
        .to_der()
        .unwrap()
}

#[test]
fn test_signature_algorithm_sha256_with_rsa_encryption() {
    static DER: &[u8] = include_bytes!("../assets/cert.der");

    let coll = certificate::check(
        DER,
        CertConfig::builder()
            .signature_algorithm(Some(String::from("1.2.840.113549.1.1.11")))
            .build(),
    );
    assert_eq!(check::exit_code(&coll), 0);
    assert_eq!(
        coll.to_string(),
        format!("OK\nSignature algorithm: sha256WithRSAEncryption")
    );
}

#[test]
fn test_signature_algorithm_ee_pss_sha256() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha256-cert.pem");

    let coll = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(String::from("1.2.840.113549.1.1.10")))
            .build(),
    );
    assert_eq!(check::exit_code(&coll), 0);
    assert_eq!(
        coll.to_string(),
        format!("OK\nSignature algorithm: rsassa-pss")
    );
}

#[test]
fn test_signature_algorithm_ee_pss_sha256_wrong_alg() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha256-cert.pem");

    let coll = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(String::from("1.2.3.4.5.6")))
            .build(),
    );

    assert_eq!(check::exit_code(&coll), 1);
    assert_eq!(
        coll.to_string(),
        format!(
            "Signature algorithm is rsassa-pss (1.2.840.113549.1.1.10) but expected 1.2.3.4.5.6 (!)"
        )
    );
}

#[test]
fn test_signature_algorithm_ee_pss_sha1() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha1-cert.pem");

    let coll = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(String::from("1.2.840.113549.1.1.10")))
            .build(),
    );
    assert_eq!(check::exit_code(&coll), 0);
    assert_eq!(
        coll.to_string(),
        format!("OK\nSignature algorithm: rsassa-pss")
    );
}

#[test]
fn test_signature_algorithm_ee_pss_sha1_wrong_alg() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha1-cert.pem");

    let coll = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(String::from("1.2.840.113549.1.1.11")))
            .build(),
    );

    assert_eq!(check::exit_code(&coll), 1);
    assert_eq!(
        coll.to_string(),
        format!(
            "Signature algorithm is rsassa-pss (1.2.840.113549.1.1.10) but expected 1.2.840.113549.1.1.11 (!)"
        )
    );
}
