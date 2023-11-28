// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{CheckResult, LevelsChecker, LevelsCheckerArgs, Real, SimpleCheckResult};
use time::Duration;
use typed_builder::TypedBuilder;
use x509_parser::certificate::X509Certificate;
use x509_parser::prelude::AlgorithmIdentifier;
use x509_parser::prelude::FromDer;
use x509_parser::public_key::PublicKey;
use x509_parser::signature_algorithm::SignatureAlgorithm;
use x509_parser::time::ASN1Time;
use x509_parser::x509::{SubjectPublicKeyInfo, X509Name};

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    pubkey_algorithm: Option<String>,
    serial: Option<String>,
    signature_algorithm: Option<String>,
    subject: Option<String>,
    issuer: Option<String>,
    not_after_levels_checker: Option<LevelsChecker<Duration>>,
}

pub fn check_cert(der: &[u8], config: Config) -> Vec<CheckResult<Real>> {
    let cert = match X509Certificate::from_der(der) {
        Ok((_rem, cert)) => cert,
        Err(_) => {
            return vec![
                SimpleCheckResult::crit(String::from("Failed to parse certificate")).into(),
            ]
        }
    };
    vec![
        check_serial(cert.tbs_certificate.raw_serial_as_string(), config.serial)
            .unwrap_or_default()
            .into(),
        check_subject(cert.tbs_certificate.subject(), config.subject)
            .unwrap_or_default()
            .into(),
        check_issuer(cert.tbs_certificate.issuer(), config.issuer)
            .unwrap_or_default()
            .into(),
        check_signature_algorithm(&cert.signature_algorithm, config.signature_algorithm)
            .unwrap_or_default()
            .into(),
        check_pubkey_algorithm(cert.public_key(), config.pubkey_algorithm)
            .unwrap_or_default()
            .into(),
        check_validity_not_after(
            cert.tbs_certificate.validity().time_to_expiration(),
            config.not_after_levels_checker,
            cert.tbs_certificate.validity().not_after,
        )
        .map(|cr: CheckResult<Duration>| cr.map(|x| Real::from(x.whole_days() as isize)))
        .unwrap_or_default(),
    ]
}

fn check_serial(serial: String, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        if serial == expected {
            SimpleCheckResult::ok(format!("Serial {}", serial))
        } else {
            SimpleCheckResult::warn(format!("Serial is {} but expected {}", serial, expected))
        }
    })
}

fn check_subject(subject: &X509Name, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let subject = subject.to_string();
        // subject string has the form: `CN=domain`
        if subject == expected {
            SimpleCheckResult::ok(subject.to_string())
        } else {
            SimpleCheckResult::warn(format!("Subject is {} but expected {}", subject, expected))
        }
    })
}

fn check_signature_algorithm(
    signature_algorithm: &AlgorithmIdentifier,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let signature_algorithm = match SignatureAlgorithm::try_from(signature_algorithm) {
            Ok(SignatureAlgorithm::RSA) => "RSA",
            Ok(SignatureAlgorithm::RSASSA_PSS(_)) => "RSASSA_PSS",
            Ok(SignatureAlgorithm::RSAAES_OAEP(_)) => "RSAAES_OAEP",
            Ok(SignatureAlgorithm::DSA) => "DSA",
            Ok(SignatureAlgorithm::ECDSA) => "ECDSA",
            Ok(SignatureAlgorithm::ED25519) => "ED25519",
            Err(_) => {
                return SimpleCheckResult::warn(String::from("Signature algorithm: Parser failed"))
            }
        };

        if signature_algorithm == expected {
            SimpleCheckResult::ok(format!("Signature algorithm: {}", signature_algorithm))
        } else {
            SimpleCheckResult::warn(format!(
                "Signature algorithm is {} but expected {}",
                signature_algorithm, expected
            ))
        }
    })
}

fn check_pubkey_algorithm(
    pubkey: &SubjectPublicKeyInfo,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let pubkey_alg = match pubkey.parsed() {
            // We could also check for the size but I'm not sure we can put
            // everything into an enum then.
            Ok(PublicKey::RSA(_)) => "RSA",
            Ok(PublicKey::EC(_)) => "EC",
            Ok(PublicKey::DSA(_)) => "DSA",
            Ok(PublicKey::GostR3410(_)) => "GostR3410",
            Ok(PublicKey::GostR3410_2012(_)) => "GostR3410_2012",
            Ok(PublicKey::Unknown(_)) => "Unknown",
            Err(_) => return SimpleCheckResult::warn(String::from("Invalid public key")),
        };

        if pubkey_alg == expected {
            SimpleCheckResult::ok(format!("Public key algorithm: {}", pubkey_alg))
        } else {
            SimpleCheckResult::warn(format!(
                "Public key algorithm is {} but expected {}",
                pubkey_alg, expected
            ))
        }
    })
}

fn check_issuer(issuer: &X509Name, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let issuer = issuer.to_string();

        if issuer == expected {
            SimpleCheckResult::ok(format!("Issuer {}", issuer))
        } else {
            SimpleCheckResult::warn(format!("Issuer is {} but expected {}", issuer, expected))
        }
    })
}

fn check_validity_not_after(
    time_to_expiration: Option<Duration>,
    levels: Option<LevelsChecker<Duration>>,
    not_after: ASN1Time,
) -> Option<CheckResult<Duration>> {
    levels.map(|levels| match time_to_expiration {
        None => SimpleCheckResult::crit(format!("Certificate expired ({})", not_after)).into(),
        Some(time_to_expiration) => levels.check(
            time_to_expiration,
            format!(
                "Certificate expires in {} day(s) ({})",
                time_to_expiration.whole_days(),
                not_after
            ),
            LevelsCheckerArgs::builder().label("validity").build(),
        ),
    })
}
