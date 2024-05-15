// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use check_cert::checker::verification::{self, Config};

#[test]
fn test_verification_with_canned_certs() {
    // Taken from `rust-openssl`
    let ca = include_bytes!("../assets/root-ca.der");
    let cert = include_bytes!("../assets/cert.der");

    let trust_store = vec![ca.to_vec()];
    let config = Config::builder().trust_store(&trust_store).build();

    let res = verification::check(&[cert.to_vec()], config);
    assert_eq!(
        res.to_string(),
        "OK - Verification: OK\nCertificate chain verification OK"
    );
}
