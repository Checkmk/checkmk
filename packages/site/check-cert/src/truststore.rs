// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Result};
use openssl::x509::store::X509StoreBuilder;
use openssl::x509::{X509Ref, X509};
use std::path::Path;

pub fn system() -> Result<Vec<Vec<u8>>> {
    let mut store = X509StoreBuilder::new()?;
    store.set_default_paths()?;
    let store = store.build();
    Ok(store
        .all_certificates()
        .iter()
        .flat_map(X509Ref::to_der)
        .collect::<Vec<_>>())
}

fn try_to_parse(content: &[u8]) -> Vec<Vec<u8>> {
    if X509::from_der(content).is_ok() {
        return vec![content.to_vec()];
    };
    if let Ok(certs) = X509::stack_from_pem(content) {
        return certs.iter().flat_map(|c| c.to_der()).collect::<Vec<_>>();
    }
    if let Ok(cert) = X509::from_pem(content).and_then(|c| c.to_der()) {
        return vec![cert];
    }
    Vec::new()
}

pub fn load_store(path: &impl AsRef<Path>) -> Result<Vec<Vec<u8>>> {
    let path = path.as_ref();

    let mut store: Vec<Vec<u8>> = Vec::new();

    if let Ok(path) = std::fs::read(path) {
        store.append(&mut try_to_parse(&path));
    } else if let Ok(dir) = path.read_dir() {
        for entry in dir.flatten() {
            if let Ok(path) = std::fs::read(entry.path()) {
                store.append(&mut try_to_parse(&path));
            }
        }
    }

    (!store.is_empty())
        .then_some(store)
        .ok_or(anyhow!("CA store not found"))
}

#[cfg(test)]
mod test {
    use super::try_to_parse;

    static DER: &[u8] = include_bytes!("../assets/certificate.der");

    fn to_pem(der: &[u8]) -> Vec<u8> {
        openssl::x509::X509::from_der(der)
            .unwrap()
            .to_pem()
            .unwrap()
    }

    #[test]
    fn test_try_to_parse_der() {
        assert_eq!(try_to_parse(DER).len(), 1);
    }

    #[test]
    fn test_try_to_parse_pem() {
        let pem = to_pem(DER);
        assert_eq!(try_to_parse(&pem).len(), 1);
    }

    #[test]
    fn test_try_to_parse_store() {
        let mut store = to_pem(DER);
        store.append(&mut to_pem(DER));
        store.append(&mut to_pem(DER));
        let store = store;

        assert_eq!(try_to_parse(&store).len(), 3);
    }

    #[test]
    fn test_try_to_parse_invalid() {
        assert_eq!(try_to_parse(&[]).len(), 0);
        assert_eq!(try_to_parse(&DER[1..]).len(), 0);
        assert_eq!(try_to_parse(&to_pem(DER)[1..]).len(), 0);
    }
}
