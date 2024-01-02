// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::checker::certificate::{self, Config as CertConfig, SignatureAlgorithm};

fn as_der(crt: &[u8]) -> Vec<u8> {
    openssl::x509::X509::from_pem(crt)
        .expect("Cannot fail")
        .to_der()
        .unwrap()
}

#[test]
fn test_signature_algorithm_rsa() {
    static DER: &[u8] = include_bytes!("../assets/cert.der");

    let out = certificate::check(
        DER,
        CertConfig::builder()
            .signature_algorithm(Some(SignatureAlgorithm::RSA))
            .build(),
    );
    assert_eq!(out.to_string(), format!("OK\nSignature algorithm: RSA"));
}

#[test]
fn test_signature_algorithm_rsassa_pss_sha256() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha256-cert.pem");

    let out = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(SignatureAlgorithm::RSASSA_PSS(String::from("sha256"))))
            .build(),
    );
    assert_eq!(
        out.to_string(),
        format!("OK\nSignature algorithm: RSASSA_PSS-SHA256")
    );
}

#[test]
fn test_signature_algorithm_rsassa_pss_sha256_wrong_alg() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha256-cert.pem");

    let out = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(SignatureAlgorithm::RSAAES_OAEP(String::from(
                "sha256",
            ))))
            .build(),
    );

    assert_eq!(
        out.to_string(),
        format!("WARNING - Signature algorithm is RSASSA_PSS-SHA256 but expected RSAAES_OAEP-SHA256 (!)")
    );
}

#[test]
fn test_signature_algorithm_rsassa_pss_sha256_wrong_hash() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha256-cert.pem");

    let out = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(SignatureAlgorithm::RSASSA_PSS(String::from("sha128"))))
            .build(),
    );
    assert_eq!(
        out.to_string(),
        format!(
            "WARNING - Signature algorithm is RSASSA_PSS-SHA256 but expected RSASSA_PSS-SHA128 (!)"
        )
    );
}

#[test]
fn test_signature_algorithm_rsassa_pss_sha1() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha1-cert.pem");

    let out = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(SignatureAlgorithm::RSASSA_PSS(String::from(
                "id-sha1",
            ))))
            .build(),
    );
    assert_eq!(
        out.to_string(),
        format!("OK\nSignature algorithm: RSASSA_PSS-ID-SHA1")
    );
}

#[test]
fn test_signature_algorithm_rsassa_pss_sha1_wrong_alg() {
    // from openssl repo
    static PEM: &[u8] = include_bytes!("../assets/ee-pss-sha1-cert.pem");

    let out = certificate::check(
        &as_der(PEM),
        CertConfig::builder()
            .signature_algorithm(Some(SignatureAlgorithm::RSA))
            .build(),
    );

    assert_eq!(
        out.to_string(),
        format!("WARNING - Signature algorithm is RSASSA_PSS-ID-SHA1 but expected RSA (!)")
    );
}
