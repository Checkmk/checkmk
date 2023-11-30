// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{self, SimpleCheckResult, Writer};
use typed_builder::TypedBuilder;
use x509_parser::certificate::X509Certificate;
use x509_parser::prelude::FromDer;

mod details {
    use super::X509Certificate;

    pub enum SelfSigned {
        Yes,
        No,
        Invalid,
    }

    pub fn is_self_signed(cert: &X509Certificate) -> SelfSigned {
        if cert.subject() == cert.issuer() {
            match cert.verify_signature(None) {
                Ok(_) => SelfSigned::Yes,
                Err(_) => SelfSigned::Invalid,
            }
        } else {
            SelfSigned::No
        }
    }
}

use details::SelfSigned;

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    allow_self_signed: bool,
}

pub fn check(der: &[u8], config: Config) -> Writer {
    let cert = match X509Certificate::from_der(der) {
        Ok((_rem, cert)) => cert,
        Err(_) => check::abort("Failed to parse certificate"),
    };

    Writer::from(&mut vec![check_self_signed(
        details::is_self_signed(&cert),
        config.allow_self_signed,
    )
    .into()])
}

fn check_self_signed(self_signed: SelfSigned, allow: bool) -> SimpleCheckResult {
    match self_signed {
        SelfSigned::No => SimpleCheckResult::ok("Certificate is not self signed"),
        SelfSigned::Yes => match allow {
            true => SimpleCheckResult::ok("Certificate is self signed"),
            false => SimpleCheckResult::warn("Certificate is self signed"),
        },
        SelfSigned::Invalid => SimpleCheckResult::warn("Self signed signature is invalid"),
    }
}
