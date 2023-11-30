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

mod verify {
    use openssl::ssl::{SslContext, SslMethod};
    use openssl::x509::store::{X509Store, X509StoreBuilder};
    use openssl::x509::{X509StoreContext, X509StoreContextRef, X509VerifyResult, X509};

    fn from_der(der: &[u8]) -> X509 {
        X509::from_der(der).unwrap()
    }

    fn make_store(cacerts: &[Vec<u8>]) -> X509Store {
        let mut store = X509StoreBuilder::new().unwrap();
        for der in cacerts {
            let _ = store.add_cert(from_der(der));
        }
        store.build()
    }

    fn make_ssl_ctx(chain: &[Vec<u8>], store: X509Store) -> SslContext {
        let mut ctx = SslContext::builder(SslMethod::tls()).unwrap();
        ctx.set_cert_store(store);

        let mut iter = chain.iter();
        let _ = ctx.set_certificate(&from_der(iter.next().unwrap()));
        for der in iter {
            let _ = ctx.add_extra_chain_cert(from_der(der));
        }
        ctx.build()
    }

    fn verify_with_ssl_ctx(ssl_ctx: &SslContext) -> (bool, X509VerifyResult) {
        let mut verify_ctx = X509StoreContext::new().unwrap();
        let result = verify_ctx.init(
            ssl_ctx.cert_store(),
            ssl_ctx.certificate().unwrap(),
            ssl_ctx.extra_chain_certs(),
            X509StoreContextRef::verify_cert,
        );
        (result.unwrap(), verify_ctx.error())
    }

    pub fn verify(chain: &[Vec<u8>], cacerts: &[Vec<u8>]) -> (bool, String) {
        let store = make_store(cacerts);
        let ssl_ctx = make_ssl_ctx(chain, store);
        let (res, reason) = verify_with_ssl_ctx(&ssl_ctx);
        (res, reason.to_string())
    }
}

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config<'a> {
    #[builder(!default)]
    trust_store: &'a [Vec<u8>],
    allow_self_signed: bool,
}

pub fn check(chain: &[Vec<u8>], config: Config) -> Writer {
    assert!(!chain.is_empty());

    Writer::from(&mut vec![
        check_self_signed(
            selfsigned::is_self_signed(&chain[0]),
            config.allow_self_signed,
        )
        .into(),
        check_verify_chain(chain, config.trust_store).into(),
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

fn check_verify_chain(chain: &[Vec<u8>], cacerts: &[Vec<u8>]) -> SimpleCheckResult {
    let (ok, reason) = verify::verify(chain, cacerts);
    if ok {
        SimpleCheckResult::ok("Certificate chain verification OK")
    } else {
        SimpleCheckResult::warn(&format!(
            "Certificate chain verification failed: {}",
            reason
        ))
    }
}
