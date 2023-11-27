// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{CheckResult, LevelsChecker, SimpleCheckResult};
use time::Duration;
use x509_parser::time::ASN1Time;
use x509_parser::x509::X509Name;

pub fn check_details_serial(serial: String, expected: Option<String>) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        if serial == expected {
            SimpleCheckResult::ok(format!("Serial {}", serial))
        } else {
            SimpleCheckResult::warn(format!("Serial is {} but expected {}", serial, expected))
        }
    })
}

pub fn check_details_subject(
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

pub fn check_details_issuer(
    issuer: &X509Name,
    expected: Option<String>,
) -> Option<SimpleCheckResult> {
    expected.map(|expected| {
        let issuer = issuer.to_string();

        if issuer == expected {
            SimpleCheckResult::ok(format!("Issuer {}", issuer))
        } else {
            SimpleCheckResult::warn(format!("Issuer is {} but expected {}", issuer, expected))
        }
    })
}

pub fn check_validity_not_after(
    time_to_expiration: Option<Duration>,
    levels: LevelsChecker<Duration>,
    not_after: ASN1Time,
) -> CheckResult<Duration> {
    match time_to_expiration {
        None => SimpleCheckResult::crit(format!("Certificate expired ({})", not_after)).into(),
        Some(time_to_expiration) => levels.check(
            "validity",
            time_to_expiration,
            format!(
                "Certificate expires in {} day(s) ({})",
                time_to_expiration.whole_days(),
                not_after
            ),
        ),
    }
}
