use anyhow::{Context, Result as AnyhowResult};
use openssl::hash::MessageDigest;
use openssl::nid::Nid;
use openssl::pkey::PKey;
use openssl::rsa::Rsa;
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
use openssl::x509::{X509Name, X509Req};
use reqwest::blocking::{Client, ClientBuilder};
use reqwest::Certificate;
use std::net::TcpStream;

pub fn make_csr(cn: &str) -> AnyhowResult<(String, String)> {
    // https://github.com/sfackler/rust-openssl/blob/master/openssl/examples/mk_certs.rs
    let rsa = Rsa::generate(2048)?;
    let key_pair = PKey::from_rsa(rsa)?;

    let mut name = X509Name::builder()?;
    name.append_entry_by_nid(Nid::COMMONNAME, cn)?;
    let name = name.build();

    let mut crt_builder = X509Req::builder()?;
    crt_builder.set_version(2)?;
    crt_builder.set_subject_name(&name)?;
    crt_builder.set_pubkey(&key_pair)?;
    crt_builder.sign(&key_pair, MessageDigest::sha256())?;

    Ok((
        String::from_utf8(crt_builder.build().to_pem()?)?,
        String::from_utf8(key_pair.private_key_to_pem_pkcs8()?)?,
    ))
}

pub fn client(root_cert: Option<&str>) -> AnyhowResult<Client> {
    let client_builder = ClientBuilder::new();

    let client_builder = if let Some(cert) = root_cert {
        client_builder.add_root_certificate(Certificate::from_pem(cert.as_bytes())?)
    } else {
        client_builder.danger_accept_invalid_certs(true)
    };

    Ok(client_builder
        .danger_accept_invalid_hostnames(true)
        .build()?)
}

pub fn fetch_server_cert_pem(address: &str) -> AnyhowResult<String> {
    let tcp_stream = TcpStream::connect(address)?;
    let mut ssl_connector_builder = SslConnector::builder(SslMethod::tls())?;
    ssl_connector_builder.set_verify(SslVerifyMode::NONE);
    let mut ssl_stream = ssl_connector_builder.build().connect("dummy", tcp_stream)?;

    let server_cert = ssl_stream
        .ssl()
        .peer_cert_chain()
        .context("Failed fetching peer cert chain")?
        .iter()
        .next()
        .context("Failed unpacking peer cert chain")?
        .to_pem()?;

    ssl_stream.shutdown()?;

    Ok(String::from_utf8(server_cert)?)
}

pub fn parse_pem(cert: &str) -> AnyhowResult<x509_parser::pem::Pem> {
    x509_parser::pem::Pem::iter_from_buffer(cert.as_bytes())
        .next()
        .context("Input data does not contain a PEM block")?
        .context("PEM data invalid")
}
