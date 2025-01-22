// copyright (c) 2023 checkmk gmbh - license: gnu general public license v2
// this file is part of checkmk (https://checkmk.com). it is subject to the terms and
// conditions defined in the file copying, which is part of this source code package.

use assertor::*;
use check_cert::truststore;
use tempfile::TempDir;

fn to_pem(der: &[u8]) -> Vec<u8> {
    openssl::x509::X509::from_der(der)
        .unwrap()
        .to_pem()
        .unwrap()
}

#[test]
fn test_load_system_trust_store() {
    // Can the truststore::system() load the system trust store.
    truststore::system().unwrap();
}

#[test]
fn test_load_one_der_certificate() {
    let cert = include_bytes!("../assets/root-ca.der");
    let file_name = "root-ca.der";

    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join(file_name);
    std::fs::write(&file_path, cert).unwrap();

    let store_from_file = truststore::load_store(&file_path).unwrap();
    let store_from_dir = truststore::load_store(&dir.path()).unwrap();

    assert_eq!(store_from_file, store_from_dir);
    assert_that!(store_from_file).has_length(1);
    assert_that!(store_from_dir).has_length(1);
}

#[test]
fn test_load_one_pem_certificate() {
    let cert = to_pem(include_bytes!("../assets/root-ca.der"));
    let file_name = "root-ca.pem";

    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join(file_name);
    std::fs::write(&file_path, cert).unwrap();

    let store_from_file = truststore::load_store(&file_path).unwrap();
    let store_from_dir = truststore::load_store(&dir.path()).unwrap();

    assert_eq!(store_from_file, store_from_dir);
    assert_that!(store_from_file).has_length(1);
    assert_that!(store_from_dir).has_length(1);
}

#[test]
fn test_load_cert_store() {
    let cert = include_bytes!("../assets/root-ca.der");
    let cert = [to_pem(cert), to_pem(cert), to_pem(cert)].concat();
    let file_name = "store.pem";

    let dir = TempDir::new().unwrap();
    let file_path = dir.path().join(file_name);
    std::fs::write(&file_path, cert).unwrap();

    let store_from_file = truststore::load_store(&file_path).unwrap();
    let store_from_dir = truststore::load_store(&dir.path()).unwrap();

    assert_eq!(store_from_file, store_from_dir);
    assert_that!(store_from_file).has_length(3);
    assert_that!(store_from_dir).has_length(3);
}
