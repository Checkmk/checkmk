// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use openssl::error::ErrorStack;
use openssl::x509::store::X509StoreBuilder;

pub fn system() -> Result<Vec<Vec<u8>>, ErrorStack> {
    let mut store = X509StoreBuilder::new()?;
    store.set_default_paths()?;
    let store = store.build();
    Ok(store
        .all_certificates()
        .iter()
        .flat_map(|c| c.to_der())
        .collect::<Vec<_>>())
}

#[test]
fn test_system() {
    let store = system().unwrap();
    assert!(!store.is_empty());
}
