// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{CheckResult, LevelsChecker, LevelsCheckerArgs, Real, SimpleCheckResult};
use time::Duration;
use typed_builder::TypedBuilder;
use x509_parser::certificate::X509Certificate;
use x509_parser::prelude::FromDer;
use x509_parser::time::ASN1Time;
use x509_parser::x509::X509Name;

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    serial: Option<String>,
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
        check_details_serial(cert.tbs_certificate.raw_serial_as_string(), config.serial)
            .unwrap_or_default()
            .into(),
        check_details_subject(cert.tbs_certificate.subject(), config.subject)
            .unwrap_or_default()
            .into(),
        check_details_issuer(cert.tbs_certificate.issuer(), config.issuer)
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

fn check_details_serial(serial: String, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        if serial == expected {
            SimpleCheckResult::ok(format!("Serial {}", serial))
        } else {
            SimpleCheckResult::warn(format!("Serial is {} but expected {}", serial, expected))
        }
    })
}

fn check_details_subject(
    subject: &X509Name,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
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

fn check_details_issuer(issuer: &X509Name, expected: Option<String>) -> Option<SimpleCheckResult> {
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
