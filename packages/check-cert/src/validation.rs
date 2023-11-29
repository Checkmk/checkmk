// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{CheckResult, Real, SimpleCheckResult};
use typed_builder::TypedBuilder;
use x509_parser::certificate::X509Certificate;

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    allow_self_signed: bool,
}

pub fn validate_cert(cert: &X509Certificate, config: Config) -> Vec<CheckResult<Real>> {
    vec![check_self_signed(cert, config.allow_self_signed).into()]
}

fn check_self_signed(cert: &X509Certificate, allow: bool) -> SimpleCheckResult {
    if cert.subject() == cert.issuer() {
        if cert.verify_signature(None).is_ok() {
            match allow {
                true => SimpleCheckResult::ok(String::from("Certificate is self signed")),
                false => SimpleCheckResult::warn(String::from("Certificate is self signed")),
            }
        } else {
            SimpleCheckResult::warn(String::from(
                "Certificate looks self signed but signature verification failed",
            ))
        }
    } else {
        SimpleCheckResult::ok(String::from("Certificate is not self signed"))
    }
}
