// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use openssl::x509::store::X509StoreBuilder;
use openssl::x509::X509Ref;

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
