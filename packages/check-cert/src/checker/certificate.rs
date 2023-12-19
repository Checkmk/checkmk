// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{
    self, CheckResult, Collection, LevelsChecker, LevelsCheckerArgs, Real, SimpleCheckResult,
};
use time::Duration;
use typed_builder::TypedBuilder;
use x509_parser::certificate::X509Certificate;
use x509_parser::prelude::AlgorithmIdentifier;
use x509_parser::prelude::FromDer;
use x509_parser::public_key::PublicKey;
use x509_parser::signature_algorithm::SignatureAlgorithm;
use x509_parser::time::ASN1Time;
use x509_parser::x509::{AttributeTypeAndValue, SubjectPublicKeyInfo, X509Name};

macro_rules! unwrap_into {
    ($($e:expr),* $(,)?) => {
        {
            vec![
            $( $e.unwrap_or_default().into(), )*
            ]
        }
    };
}

macro_rules! check_eq {
    ($name:tt, $left:expr, $right:expr $(,)?) => {
        if &$left == &$right {
            SimpleCheckResult::ok(format!("{}: {}", $name, $left))
        } else {
            SimpleCheckResult::warn(format!("{} is {} but expected {}", $name, $left, $right))
        }
    };
}

fn first_of<'a>(iter: &mut impl Iterator<Item = &'a AttributeTypeAndValue<'a>>) -> &'a str {
    iter.next()
        .and_then(|a| a.as_str().ok())
        .unwrap_or_default()
}

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    pubkey_algorithm: Option<String>,
    pubkey_size: Option<usize>,
    serial: Option<String>,
    signature_algorithm: Option<String>,
    subject_cn: Option<String>,
    subject_o: Option<String>,
    subject_ou: Option<String>,
    issuer: Option<String>,
    not_after: Option<LevelsChecker<Duration>>,
}

pub fn check(der: &[u8], config: Config) -> Collection {
    let cert = match X509Certificate::from_der(der) {
        Ok((_rem, cert)) => cert,
        Err(_) => check::abort("Failed to parse certificate"),
    };

    Collection::from(&mut unwrap_into!(
        check_serial(cert.tbs_certificate.raw_serial_as_string(), config.serial),
        config.subject_cn.map(|expected| {
            check_eq!(
                "Subject CN",
                first_of(&mut cert.tbs_certificate.subject().iter_common_name()),
                expected
            )
        }),
        config.subject_o.map(|expected| {
            check_eq!(
                "Subject O",
                first_of(&mut cert.tbs_certificate.subject().iter_organization()),
                expected
            )
        }),
        config.subject_ou.map(|expected| {
            check_eq!(
                "Subject OU",
                first_of(&mut cert.tbs_certificate.subject().iter_organizational_unit()),
                expected
            )
        }),
        check_issuer(cert.tbs_certificate.issuer(), config.issuer),
        check_signature_algorithm(&cert.signature_algorithm, config.signature_algorithm),
        check_pubkey_algorithm(cert.public_key(), config.pubkey_algorithm),
        check_pubkey_size(cert.public_key(), config.pubkey_size),
        check_validity_not_after(
            cert.tbs_certificate.validity().time_to_expiration(),
            config.not_after,
            cert.tbs_certificate.validity().not_after,
        )
        .map(|cr: CheckResult<Duration>| cr.map(|x| Real::from(x.whole_days() as isize))),
    ))
}

fn check_serial(serial: String, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| check_eq!("Serial", serial.to_lowercase(), expected.to_lowercase()))
}

fn check_signature_algorithm(
    signature_algorithm: &AlgorithmIdentifier,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        check_eq!(
            "Signature algorithm",
            match SignatureAlgorithm::try_from(signature_algorithm) {
                Ok(SignatureAlgorithm::RSA) => "RSA",
                Ok(SignatureAlgorithm::RSASSA_PSS(_)) => "RSASSA_PSS",
                Ok(SignatureAlgorithm::RSAAES_OAEP(_)) => "RSAAES_OAEP",
                Ok(SignatureAlgorithm::DSA) => "DSA",
                Ok(SignatureAlgorithm::ECDSA) => "ECDSA",
                Ok(SignatureAlgorithm::ED25519) => "ED25519",
                Err(_) => return SimpleCheckResult::warn("Signature algorithm: Parser failed"),
            },
            expected
        )
    })
}

fn check_pubkey_algorithm(
    pubkey: &SubjectPublicKeyInfo,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        check_eq!(
            "Public key algorithm",
            match pubkey.parsed() {
                Ok(PublicKey::RSA(_)) => "RSA",
                Ok(PublicKey::EC(_)) => "EC",
                Ok(PublicKey::DSA(_)) => "DSA",
                Ok(PublicKey::GostR3410(_)) => "GostR3410",
                Ok(PublicKey::GostR3410_2012(_)) => "GostR3410_2012",
                Ok(PublicKey::Unknown(_)) => "Unknown",
                Err(_) => return SimpleCheckResult::warn("Invalid public key"),
            },
            expected
        )
    })
}

fn check_pubkey_size(
    pubkey: &SubjectPublicKeyInfo,
    expected: Option<usize>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        check_eq!(
            "Public key size",
            match pubkey.parsed() {
                // more or less stolen from upstream `examples/print-cert.rs`.
                Ok(PublicKey::RSA(rsa)) => rsa.key_size(),
                Ok(PublicKey::EC(ec)) => ec.key_size(),
                Ok(PublicKey::DSA(k))
                | Ok(PublicKey::GostR3410(k))
                | Ok(PublicKey::GostR3410_2012(k))
                | Ok(PublicKey::Unknown(k)) => 8 * k.len(),
                Err(_) => return SimpleCheckResult::warn("Invalid public key"),
            },
            expected
        )
    })
}

fn check_issuer(issuer: &X509Name, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| check_eq!("Issuer", issuer.to_string(), expected))
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

#[cfg(test)]
mod test_check_serial {
    use super::{check_serial, SimpleCheckResult};

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_case_insensitive() {
        let result = Some(SimpleCheckResult::ok("Serial: aa:11:bb:22:cc"));

        assert_eq!(
            check_serial(s("aa:11:bb:22:cc"), Some(s("aa:11:bb:22:cc"))),
            result
        );
        assert_eq!(
            check_serial(s("AA:11:BB:22:CC"), Some(s("aa:11:bb:22:cc"))),
            result
        );
        assert_eq!(
            check_serial(s("aa:11:bb:22:cc"), Some(s("AA:11:BB:22:CC"))),
            result
        );
        assert_eq!(
            check_serial(s("AA:11:bb:22:CC"), Some(s("aa:11:BB:22:cc"))),
            result
        );
    }
}
