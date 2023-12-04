// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{self, Collection, SimpleCheckResult};
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
    use openssl::stack::Stack;
    use openssl::x509::store::{X509Store, X509StoreBuilder};
    use openssl::x509::{X509StoreContext, X509StoreContextRef, X509};

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

    fn make_stack(chain: &[Vec<u8>]) -> (X509, Stack<X509>) {
        let mut iter = chain.iter();
        let cert = from_der(iter.next().unwrap());
        let mut stack = Stack::<X509>::new().unwrap();
        for der in iter {
            stack.push(from_der(der)).unwrap();
        }
        (cert, stack)
    }

    pub fn verify(chain: &[Vec<u8>], cacerts: &[Vec<u8>]) -> (bool, String) {
        let store = make_store(cacerts);
        let (cert, chain) = make_stack(chain);

        let mut verify_ctx = X509StoreContext::new().unwrap();
        let result = verify_ctx.init(&store, &cert, &chain, X509StoreContextRef::verify_cert);

        (result.unwrap(), verify_ctx.error().to_string())
    }
}

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config<'a> {
    #[builder(!default)]
    trust_store: &'a [Vec<u8>],
    allow_self_signed: bool,
}

pub fn check(chain: &[Vec<u8>], config: Config) -> Collection {
    assert!(!chain.is_empty());

    Collection::from(&mut vec![
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
