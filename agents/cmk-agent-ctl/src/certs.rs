extern crate openssl;

use openssl::error::ErrorStack;
use openssl::hash::MessageDigest;
use openssl::nid::Nid;
use openssl::pkey::PKey;
use openssl::rsa::Rsa;
use openssl::x509::{X509Name, X509Req};

pub fn make_csr(cn: &str) -> Result<(Vec<u8>, Vec<u8>), ErrorStack> {
    // https://github.com/sfackler/rust-openssl/blob/master/openssl/examples/mk_certs.rs
    let rsa = Rsa::generate(2048)?;
    let key_pair = PKey::from_rsa(rsa)?;

    let mut name = X509Name::builder()?;
    name.append_entry_by_nid(Nid::COMMONNAME, cn)?;
    let name = name.build();

    let mut builder = X509Req::builder()?;
    builder.set_version(2).unwrap();
    builder.set_subject_name(&name).unwrap();
    builder.set_pubkey(&key_pair).unwrap();
    builder.sign(&key_pair, MessageDigest::sha256())?;

    Ok((
        builder.build().to_pem()?,
        key_pair.private_key_to_pem_pkcs8()?,
    ))
}
