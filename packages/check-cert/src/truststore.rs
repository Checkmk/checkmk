// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::prelude::Chain;
use anyhow::{Context, Result};
use openssl::x509::store::X509StoreBuilder;

pub fn system() -> Result<Chain> {
    let mut store = X509StoreBuilder::new().context("Failed to load trust store")?;
    store
        .set_default_paths()
        .context("Failed to load trust store")?;
    Ok(store
        .build()
        .all_certificates()
        .iter()
        .flat_map(|c| c.to_der())
        .collect::<Vec<_>>())
}

#[test]
fn test_system() {
    assert_ne!(system().unwrap().len(), 0);
}
