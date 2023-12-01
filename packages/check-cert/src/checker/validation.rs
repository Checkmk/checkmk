// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{self, SimpleCheckResult, Writer};
use typed_builder::TypedBuilder;

mod selfsigned {
    use super::check;
    use x509_parser::certificate::X509Certificate;
    use x509_parser::prelude::FromDer;

    pub enum SelfSigned {
        Yes,
        No,
        Invalid,
    }

    pub fn is_self_signed(der: &[u8]) -> SelfSigned {
        let cert = match X509Certificate::from_der(der) {
            Ok((_rem, cert)) => cert,
            Err(_) => check::abort("Failed to parse certificate"),
        };

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

use selfsigned::SelfSigned;

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config {
    allow_self_signed: bool,
}

pub fn check(chain: &Vec<Vec<u8>>, config: Config) -> Writer {
    assert!(!chain.is_empty());

    Writer::from(&mut vec![
        check_self_signed(
            selfsigned::is_self_signed(&chain[0]),
            config.allow_self_signed,
        )
        .into(),
        // more checks
    ])
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
