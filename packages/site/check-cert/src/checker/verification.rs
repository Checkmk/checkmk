// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::check::{Check, SimpleCheckResult};
use typed_builder::TypedBuilder;

mod verify {
    use openssl::stack::Stack;
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

    fn make_stack(chain: &[Vec<u8>]) -> (X509, Stack<X509>) {
        let mut iter = chain.iter();
        let cert = from_der(iter.next().unwrap());
        let mut stack = Stack::<X509>::new().unwrap();
        for der in iter {
            stack.push(from_der(der)).unwrap();
        }
        (cert, stack)
    }

    pub fn verify(chain: &[Vec<u8>], cacerts: &[Vec<u8>]) -> (bool, X509VerifyResult) {
        let store = make_store(cacerts);
        let (cert, chain) = make_stack(chain);

        let mut verify_ctx = X509StoreContext::new().unwrap();
        let result = verify_ctx.init(&store, &cert, &chain, X509StoreContextRef::verify_cert);

        (result.unwrap(), verify_ctx.error())
    }
}

#[derive(Debug, TypedBuilder)]
#[builder(field_defaults(default))]
pub struct Config<'a> {
    #[builder(!default)]
    trust_store: &'a [Vec<u8>],
    allow_self_signed: bool,
}

pub fn check(chain: &[Vec<u8>], config: Config) -> Check {
    assert!(!chain.is_empty());

    Check::from(check_verify_chain(
        chain,
        config.trust_store,
        config.allow_self_signed,
    ))
}

fn check_verify_chain(
    chain: &[Vec<u8>],
    cacerts: &[Vec<u8>],
    allow_self_signed: bool,
) -> SimpleCheckResult {
    let (ok, reason) = verify::verify(chain, cacerts);
    if ok {
        SimpleCheckResult::ok_with_details("Verification: OK", "Verification: OK")
    } else if reason.as_raw() == 18 && allow_self_signed {
        SimpleCheckResult::ok_with_details(
            format!("Verification: {reason} (allowed)"),
            format!("Verification: {reason} (allowed)"),
        )
    } else {
        SimpleCheckResult::warn_with_details(
            format!("Verification: {reason}"),
            format!("Verification: {reason}"),
        )
    }
}
