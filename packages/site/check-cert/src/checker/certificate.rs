// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{
    self, pretty_levels, Check, CheckResult, CheckResultLevelsText, Levels, Metric, Real,
    SimpleCheckResult,
};
use std::collections::HashSet;
use std::convert::AsRef;
use time::Duration;
use typed_builder::TypedBuilder;
use x509_parser::certificate::{BasicExtension, Validity, X509Certificate};
use x509_parser::error::X509Error;
use x509_parser::extensions::{GeneralName, SubjectAlternativeName};
use x509_parser::prelude::FromDer;
use x509_parser::prelude::{oid2sn, oid_registry};
use x509_parser::public_key::PublicKey;
use x509_parser::time::ASN1Time;
use x509_parser::x509::{AttributeTypeAndValue, SubjectPublicKeyInfo};

macro_rules! unwrap_into {
    ($($e:expr),* $(,)?) => {
        {
            vec![
            $( $e.unwrap_or_default().into(), )*
            ]
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
    subject_alt_names: Option<Vec<String>>,
    subject_o: Option<String>,
    subject_ou: Option<String>,
    issuer_cn: Option<String>,
    issuer_o: Option<String>,
    issuer_ou: Option<String>,
    issuer_st: Option<String>,
    issuer_c: Option<String>,
    not_after: Option<Levels<Duration>>,
    max_validity: Option<Duration>,
}

fn handle_empty(s: &str) -> &str {
    if s.trim().is_empty() {
        "empty"
    } else {
        s
    }
}

fn format_oid(oid: &oid_registry::Oid) -> String {
    match oid2sn(oid, oid_registry()) {
        Ok(s) => s.to_owned(),
        _ => format!("{oid}"),
    }
}

pub fn check(der: &[u8], config: Config) -> Check {
    let cert = match X509Certificate::from_der(der) {
        Ok((_rem, cert)) => cert,
        Err(_) => check::abort("Failed to parse certificate"),
    };

    let subject_cn = first_of(&mut cert.subject().iter_common_name());
    let issuer_cn = first_of(&mut cert.issuer().iter_common_name());

    Check::from(&mut unwrap_into!(
        Some(check_subject_cn(subject_cn, config.subject_cn)),
        check_subject_alt_names(cert.subject_alternative_name(), config.subject_alt_names),
        config.subject_o.map(|expected| {
            let name = "Subject O";
            let value = first_of(&mut cert.subject().iter_organization());
            if expected == value {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(value)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(value),
                ))
            }
        }),
        config.subject_ou.map(|expected| {
            let name = "Subject OU";
            let value = first_of(&mut cert.subject().iter_organizational_unit());
            if expected == value {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(value)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(value),
                ))
            }
        }),
        check_serial(cert.raw_serial_as_string(), config.serial),
        Some(check_issuer_cn(issuer_cn, config.issuer_cn)),
        config.issuer_o.map(|expected| {
            let name = "Issuer O";
            let value = first_of(&mut cert.issuer().iter_organization());
            if expected == value {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(value)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(value),
                ))
            }
        }),
        config.issuer_ou.map(|expected| {
            let name = "Issuer OU";
            let value = first_of(&mut cert.issuer().iter_organizational_unit());
            if expected == value {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(value)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(value),
                ))
            }
        }),
        config.issuer_st.map(|expected| {
            let name = "Issuer ST";
            let value = first_of(&mut cert.issuer().iter_state_or_province());
            if expected == value {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(value)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(value),
                ))
            }
        }),
        config.issuer_c.map(|expected| {
            let name = "Issuer C";
            let value = first_of(&mut cert.issuer().iter_country());
            if expected == value {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(value)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(value),
                ))
            }
        }),
        config.signature_algorithm.map(|expected| {
            let name = "Certificate signature algorithm";
            let value = &cert.signature_algorithm.algorithm;
            if expected == value.to_string() {
                SimpleCheckResult::notice(format!("{name}: {}", handle_empty(&format_oid(value))))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} ({value}) but expected {expected}",
                    handle_empty(&format_oid(value)),
                ))
            }
        }),
        check_pubkey_algorithm(cert.public_key(), config.pubkey_algorithm),
        check_pubkey_size(cert.public_key(), config.pubkey_size),
        check_validity(
            ASN1Time::now(),
            cert.validity().not_before,
            cert.validity().not_after
        ),
        check_validity_duration(cert.validity().time_to_expiration(), config.not_after,),
        check_max_validity(cert.validity(), config.max_validity),
    ))
}

fn check_serial(serial: String, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let name = "Serial number";
        if serial.to_lowercase() == expected.to_lowercase() {
            SimpleCheckResult::notice(format!("{name}: {serial}"))
        } else {
            SimpleCheckResult::warn(format!("{name}: {serial} but expected {expected}"))
        }
    })
}

fn check_subject_cn(subject_cn: &str, expected: Option<String>) -> SimpleCheckResult {
    let name = "Subject CN";
    expected.map_or(
        SimpleCheckResult::ok(format!("{name}: {}", handle_empty(subject_cn))),
        |expected| {
            if expected == subject_cn {
                SimpleCheckResult::ok(format!("{name}: {}", handle_empty(subject_cn)))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: {} but expected {expected}",
                    handle_empty(subject_cn),
                ))
            }
        },
    )
}

fn check_issuer_cn(issuer_cn: &str, expected: Option<String>) -> SimpleCheckResult {
    let name = "Issuer CN";
    let details = format!("{name}: {}", handle_empty(issuer_cn));
    expected.map_or(SimpleCheckResult::notice(&details), |expected| {
        if expected == issuer_cn {
            SimpleCheckResult::notice(&details)
        } else {
            SimpleCheckResult::warn(format!(
                "{name}: {} but expected {expected}",
                handle_empty(issuer_cn),
            ))
        }
    })
}

fn check_subject_alt_names(
    alt_names: Result<Option<BasicExtension<&SubjectAlternativeName<'_>>>, X509Error>,
    expected: Option<Vec<String>>,
) -> Option<SimpleCheckResult> {
    let name = "Certificate subject alternative names";
    expected.map(|expected| match alt_names {
        Err(err) => SimpleCheckResult::crit(format!("{name}: {err}")),
        Ok(None) => {
            if expected.is_empty() {
                SimpleCheckResult::notice(format!("No {}", name.to_lowercase()))
            } else {
                SimpleCheckResult::warn(format!("No {}", name.to_lowercase()))
            }
        }
        Ok(Some(ext)) => {
            let found = HashSet::<&str>::from_iter(ext.value.general_names.iter().flat_map(
                |name| match name {
                    GeneralName::DNSName(v) => Some(*v),
                    _ => None,
                },
            ));
            let expected_set = HashSet::from_iter(expected.iter().map(AsRef::as_ref));
            if found.is_superset(&expected_set) {
                SimpleCheckResult::notice(format!("{name}: {}", expected.join(", ")))
            } else {
                SimpleCheckResult::warn(format!(
                    "{name}: missing {}",
                    expected_set
                        .difference(&found)
                        .map(|s| format!(r#""{s}""#))
                        .collect::<Vec<_>>()
                        .join(", ")
                ))
            }
        }
    })
}

fn check_pubkey_algorithm(
    pubkey: &SubjectPublicKeyInfo,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let name = "Public key algorithm";
        let value = match pubkey.parsed() {
            Ok(PublicKey::RSA(_)) => "RSA",
            Ok(PublicKey::EC(_)) => "EC",
            Ok(PublicKey::DSA(_)) => "DSA",
            Ok(PublicKey::GostR3410(_)) => "GostR3410",
            Ok(PublicKey::GostR3410_2012(_)) => "GostR3410_2012",
            Ok(PublicKey::Unknown(_)) => "Unknown",
            Err(_) => return SimpleCheckResult::warn("Invalid public key"),
        };
        if expected == value {
            SimpleCheckResult::notice(format!("{name}: {value}"))
        } else {
            SimpleCheckResult::warn(format!("{name}: {value} but expected {expected}"))
        }
    })
}

fn check_pubkey_size(
    pubkey: &SubjectPublicKeyInfo,
    expected: Option<usize>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let name = "Public key size";
        let value = match pubkey.parsed() {
            // more or less stolen from upstream `examples/print-cert.rs`.
            Ok(PublicKey::RSA(rsa)) => rsa.key_size(),
            Ok(PublicKey::EC(ec)) => ec.key_size(),
            Ok(PublicKey::DSA(k))
            | Ok(PublicKey::GostR3410(k))
            | Ok(PublicKey::GostR3410_2012(k))
            | Ok(PublicKey::Unknown(k)) => 8 * k.len(),
            Err(_) => return SimpleCheckResult::warn("Invalid public key"),
        };
        if expected == value {
            SimpleCheckResult::notice(format!("{name}: {value}"))
        } else {
            SimpleCheckResult::warn(format!("{name}: {value} but expected {expected}"))
        }
    })
}

fn check_validity(
    now: ASN1Time,
    not_before: ASN1Time,
    not_after: ASN1Time,
) -> Option<SimpleCheckResult> {
    // The validity period for a certificate is the period of time from
    // notBefore through notAfter, inclusive.
    // RFC 5280, Section 4.1.2.5. Validity
    if not_before > now {
        return Some(SimpleCheckResult::crit(format!(
            "Certificate not yet valid until {0}",
            not_before
        )));
    }
    if now > not_after {
        return Some(SimpleCheckResult::crit(format!(
            "Certificate expired ({0})",
            not_after
        )));
    }
    None
}

fn check_validity_duration(
    time_to_expiration: Option<Duration>,
    levels: Option<Levels<Duration>>,
) -> Option<CheckResult<Real>> {
    time_to_expiration.map(|time_to_expiration| {
        let metric = Metric::builder()
            .label("certificate_remaining_validity")
            .value(time_to_expiration)
            .uom("s".parse().unwrap())
            .levels(levels.clone())
            .build()
            .map(|x| Real::from(x.whole_seconds() as isize));
        let message = format!(
            "Server certificate validity: {} day(s)",
            time_to_expiration.whole_days()
        );
        match levels {
            None => CheckResult::ok(message, metric.clone()),
            Some(levels) => CheckResult::from_levels(
                CheckResultLevelsText::new(
                    message.clone(),
                    pretty_levels(
                        &message,
                        levels.clone().map(|x| Real::from(x.whole_days() as isize)),
                        "day(s)",
                    ),
                ),
                metric.clone(),
            ),
        }
    })
}

fn check_max_validity(
    validity: &Validity,
    max_validity: Option<Duration>,
) -> Option<SimpleCheckResult> {
    max_validity.map(|max_validity| {
        if let Some(total_validity) = validity.not_after - validity.not_before {
            match total_validity <= max_validity {
                true => SimpleCheckResult::notice(format!(
                    "Allowed validity: {} day(s)",
                    total_validity.whole_days()
                )),
                false => SimpleCheckResult::warn(format!(
                    "Allowed validity: {} day(s) but expected at most {}",
                    total_validity.whole_days(),
                    max_validity.whole_days(),
                )),
            }
        } else {
            SimpleCheckResult::crit("Invalid certificate validity")
        }
    })
}

#[cfg(test)]
mod test_check_validity {
    use super::{check_validity, SimpleCheckResult};
    use x509_parser::time::ASN1Time;

    #[test]
    fn test_now_less_than_not_before() {
        assert_eq!(
            check_validity(
                ASN1Time::from_timestamp(0).unwrap(),
                ASN1Time::from_timestamp(100).unwrap(),
                ASN1Time::from_timestamp(200).unwrap()
            ),
            Some(SimpleCheckResult::crit(
                "Certificate not yet valid until Jan  1 00:01:40 1970 +00:00"
            ))
        );
    }

    #[test]
    fn test_now_bigger_than_not_after() {
        assert_eq!(
            check_validity(
                ASN1Time::from_timestamp(200).unwrap(),
                ASN1Time::from_timestamp(0).unwrap(),
                ASN1Time::from_timestamp(100).unwrap()
            ),
            Some(SimpleCheckResult::crit(
                "Certificate expired (Jan  1 00:01:40 1970 +00:00)"
            ))
        );
    }

    #[test]
    fn test_valid() {
        assert_eq!(
            check_validity(
                ASN1Time::from_timestamp(100).unwrap(),
                ASN1Time::from_timestamp(0).unwrap(),
                ASN1Time::from_timestamp(200).unwrap()
            ),
            None
        );
    }
}

#[cfg(test)]
mod test_check_serial {
    use super::{check_serial, SimpleCheckResult};

    fn s(s: &str) -> String {
        String::from(s)
    }

    #[test]
    fn test_case_insensitive() {
        assert_eq!(
            check_serial(s("aa:11:bb:22:cc"), Some(s("aa:11:bb:22:cc"))),
            Some(SimpleCheckResult::notice("Serial number: aa:11:bb:22:cc"))
        );
        assert_eq!(
            check_serial(s("AA:11:BB:22:CC"), Some(s("aa:11:bb:22:cc"))),
            Some(SimpleCheckResult::notice("Serial number: AA:11:BB:22:CC"))
        );
        assert_eq!(
            check_serial(s("aa:11:bb:22:cc"), Some(s("AA:11:BB:22:CC"))),
            Some(SimpleCheckResult::notice("Serial number: aa:11:bb:22:cc"))
        );
        assert_eq!(
            check_serial(s("AA:11:bb:22:CC"), Some(s("aa:11:BB:22:cc"))),
            Some(SimpleCheckResult::notice("Serial number: AA:11:bb:22:CC"))
        );
    }
}
