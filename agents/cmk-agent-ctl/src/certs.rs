use openssl::error::ErrorStack;
use openssl::hash::MessageDigest;
use openssl::nid::Nid;
use openssl::pkey::PKey;
use openssl::rsa::Rsa;
use openssl::x509::{X509Name, X509Req};
use reqwest;
use reqwest::blocking::{Client, ClientBuilder};
use reqwest::{Certificate, Identity};
use std::error::Error;

pub fn make_csr(cn: &str) -> Result<(Vec<u8>, Vec<u8>), ErrorStack> {
    // https://github.com/sfackler/rust-openssl/blob/master/openssl/examples/mk_certs.rs
    let rsa = Rsa::generate(2048)?;
    let key_pair = PKey::from_rsa(rsa)?;

    let mut name = X509Name::builder()?;
    name.append_entry_by_nid(Nid::COMMONNAME, cn)?;
    let name = name.build();

    let mut crt_builder = X509Req::builder()?;
    crt_builder.set_version(2).unwrap();
    crt_builder.set_subject_name(&name).unwrap();
    crt_builder.set_pubkey(&key_pair).unwrap();
    crt_builder.sign(&key_pair, MessageDigest::sha256())?;

    Ok((
        crt_builder.build().to_pem()?,
        key_pair.private_key_to_pem_pkcs8()?,
    ))
}

pub fn client(
    client_chain: Option<Vec<u8>>,
    root_cert: Option<Vec<u8>>,
) -> Result<Client, Box<dyn Error>> {
    let client_builder = ClientBuilder::new();

    let client_builder = if let Some(chain) = client_chain {
        client_builder.identity(Identity::from_pem(&chain)?)
    } else {
        client_builder
    };

    let client_builder = if let Some(cert) = root_cert {
        client_builder.add_root_certificate(Certificate::from_pem(&cert)?)
    } else {
        client_builder
    };

    Ok(client_builder
        .danger_accept_invalid_hostnames(true)
        .build()?)
}
