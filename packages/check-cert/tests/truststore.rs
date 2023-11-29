// copyright (c) 2023 checkmk gmbh - license: gnu general public license v2
// this file is part of checkmk (https://checkmk.com). it is subject to the terms and
// conditions defined in the file copying, which is part of this source code package.

use check_cert::truststore;

#[test]
fn test_load_system_trust_store() {
    assert_ne!(
        truststore::system()
            .expect("Failed to load trust store")
            .len(),
        0
    );
}
