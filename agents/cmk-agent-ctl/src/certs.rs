// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{anyhow, Context, Result as AnyhowResult};
use openssl::hash::MessageDigest;
use openssl::nid::Nid;
use openssl::pkey::PKey;
use openssl::rsa::Rsa;
use openssl::ssl::{SslConnector, SslMethod, SslVerifyMode};
use openssl::x509::{X509Name, X509Req};
use reqwest::blocking::{Client, ClientBuilder};
use rustls::{
    client::ServerCertVerified, client::ServerCertVerifier, client::ServerName,
    client::WebPkiVerifier, Certificate, Certificate as RustlsCertificate, Error as RusttlsError,
    PrivateKey as RustlsPrivateKey, RootCertStore,
};
use rustls_pemfile::Item;
use std::net::TcpStream;
use std::sync::Arc;
use x509_parser::traits::FromDer;

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

pub fn root_cert_store<'a>(
    root_certs: impl Iterator<Item = &'a str>,
) -> AnyhowResult<RootCertStore> {
    let mut cert_store = RootCertStore::empty();

    for root_cert in root_certs {
        cert_store.add(&rustls_certificate(root_cert)?)?;
    }

    Ok(cert_store)
}

pub struct CNCheckerUUID {
    cn: String,
}

impl CNCheckerUUID {
    pub fn cn(&self) -> &str {
        &self.cn
    }

    pub fn cn_is_uuid(&self) -> bool {
        uuid::Uuid::parse_str(&self.cn).is_ok()
    }
}

impl std::convert::TryFrom<&Certificate> for CNCheckerUUID {
    type Error = RusttlsError;

    fn try_from(certificate: &Certificate) -> Result<Self, RusttlsError> {
        let (_rem, cert) = x509_parser::certificate::X509Certificate::from_der(
            certificate.as_ref(),
        )
        .map_err(|e| {
            RusttlsError::InvalidCertificateData(format!("Certificate parsing failed: {}", e))
        })?;

        let common_names = common_names(cert.subject()).map_err(|e| {
            RusttlsError::InvalidCertificateData(format!("Certificate parsing failed: {}", e))
        })?;

        if common_names.len() != 1 {
            return Err(RusttlsError::General(format!(
                "Expected exactly one CN in certificate, found: {}",
                common_names.join(", ")
            )));
        }

        Ok(Self {
            cn: String::from(common_names[0]),
        })
    }
}

struct CnIsNoUuidAcceptAnyHostname {
    verifier: Box<dyn ServerCertVerifier>,
}

impl CnIsNoUuidAcceptAnyHostname {
    pub fn from_roots(roots: RootCertStore) -> Arc<dyn ServerCertVerifier> {
        Arc::new(Self {
            verifier: Box::new(WebPkiVerifier::new(roots, None)),
        })
    }
}

impl ServerCertVerifier for CnIsNoUuidAcceptAnyHostname {
    fn verify_server_cert(
        &self,
        end_entity: &Certificate,
        intermediates: &[Certificate],
        _server_name: &ServerName,
        scts: &mut dyn Iterator<Item = &[u8]>,
        ocsp_response: &[u8],
        now: std::time::SystemTime,
    ) -> Result<ServerCertVerified, RusttlsError> {
        let cn_checker = CNCheckerUUID::try_from(end_entity)?;
        if cn_checker.cn_is_uuid() {
            return Err(RusttlsError::General(format!(
                "CN in server certificate is a valid UUID: {}",
                cn_checker.cn()
            )));
        }
        self.verifier.verify_server_cert(
            end_entity,
            intermediates,
            // emulate reqwest::ClientBuilder::danger_accept_invalid_hostnames
            &ServerName::try_from(cn_checker.cn()).map_err(|e| {
                RusttlsError::General(format!(
                    "CN in server certificate cannot be used as server name: {}",
                    e
                ))
            })?,
            scts,
            ocsp_response,
            now,
        )
    }
}

pub struct TLSIdentity {
    pub cert_chain: Vec<rustls::Certificate>,
    pub key_der: rustls::PrivateKey,
}

pub struct HandshakeCredentials<'a> {
    pub server_root_cert: &'a str,
    pub client_identity: Option<TLSIdentity>,
}

fn tls_config(handshake_credentials: HandshakeCredentials) -> AnyhowResult<rustls::ClientConfig> {
    let builder = rustls::ClientConfig::builder()
        .with_safe_defaults()
        .with_custom_certificate_verifier(CnIsNoUuidAcceptAnyHostname::from_roots(
            root_cert_store([handshake_credentials.server_root_cert].into_iter())?,
        ));
    Ok(match handshake_credentials.client_identity {
        Some(identity) => builder.with_single_cert(identity.cert_chain, identity.key_der)?,
        None => builder.with_no_client_auth(),
    })
}

pub fn client(
    handshake_credentials: Option<HandshakeCredentials>,
    use_proxy: bool,
) -> AnyhowResult<Client> {
    let mut client_builder = ClientBuilder::new();

    client_builder = if let Some(handshake_credentials) = handshake_credentials {
        client_builder.use_preconfigured_tls(tls_config(handshake_credentials)?)
    } else {
        client_builder.danger_accept_invalid_certs(true)
    };

    if !use_proxy {
        client_builder = client_builder.no_proxy()
    };

    Ok(client_builder.build()?)
}

pub fn fetch_server_cert_pem(server: &str, port: &u16) -> AnyhowResult<String> {
    let tcp_stream = TcpStream::connect(format!("{}:{}", server, port))?;
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

pub fn common_names<'a>(x509_name: &'a x509_parser::x509::X509Name) -> AnyhowResult<Vec<&'a str>> {
    x509_name
        .iter_common_name()
        .map(|n| {
            n.as_str()
                .map_err(|e| anyhow!(format!("Failed to parse CN to string: {}", e)))
        })
        .collect::<AnyhowResult<Vec<_>>>()
}

pub fn rustls_private_key(key_pem: &str) -> AnyhowResult<RustlsPrivateKey> {
    if let Item::PKCS8Key(it) = rustls_pemfile::read_one(&mut key_pem.to_owned().as_bytes())?
        .context("Could not load private key")?
    {
        Ok(RustlsPrivateKey(it))
    } else {
        Err(anyhow!("Could not process private key"))
    }
}

pub fn rustls_certificate(cert_pem: &str) -> AnyhowResult<RustlsCertificate> {
    if let Item::X509Certificate(it) =
        rustls_pemfile::read_one(&mut cert_pem.to_owned().as_bytes())?
            .context("Could not load certificate")?
    {
        Ok(RustlsCertificate(it))
    } else {
        Err(anyhow!("Could not process certificate"))
    }
}

#[cfg(test)]
mod test_cn_no_uuid {
    use super::super::constants;
    use super::*;

    #[test]
    fn test_cn_extraction() {
        let cn_checker =
            CNCheckerUUID::try_from(&rustls_certificate(constants::TEST_CERT_OK).unwrap()).unwrap();
        assert_eq!(cn_checker.cn(), "heute");
    }

    #[test]
    fn test_verify_no_uuid() {
        let cn_checker =
            CNCheckerUUID::try_from(&rustls_certificate(constants::TEST_CERT_OK).unwrap()).unwrap();
        assert!(!cn_checker.cn_is_uuid());
    }

    #[test]
    fn test_verify_uiid() {
        let cn_checker =
            CNCheckerUUID::try_from(&rustls_certificate(constants::TEST_CERT_CN_UUID).unwrap())
                .unwrap();
        assert!(cn_checker.cn_is_uuid());
    }

    fn verifier() -> Arc<dyn ServerCertVerifier> {
        CnIsNoUuidAcceptAnyHostname::from_roots(
            root_cert_store([constants::TEST_ROOT_CERT].into_iter()).unwrap(),
        )
    }

    #[test]
    fn test_verify_server_cert_ok() {
        assert!(verifier()
            .verify_server_cert(
                &rustls_certificate(constants::TEST_CERT_OK).unwrap(),
                &[],
                &ServerName::try_from("lsdafhgldfhg").unwrap(),
                &mut [].into_iter(),
                &[],
                std::time::SystemTime::now(),
            )
            .is_ok());
    }

    #[test]
    fn test_verify_server_cert_cn_is_uuid() {
        assert_eq!(
            match verifier()
                .verify_server_cert(
                    &rustls_certificate(constants::TEST_CERT_CN_UUID).unwrap(),
                    &[],
                    &ServerName::try_from("lsdafhgldfhg").unwrap(),
                    &mut [].into_iter(),
                    &[],
                    std::time::SystemTime::now(),
                )
                .unwrap_err()
            {
                rustls::Error::General(s) => s,
                _ => panic!("Wrong error type"),
            },
            "CN in server certificate is a valid UUID: cf771eeb-b666-4673-95c9-683960fb2939"
        )
    }

    #[test]
    fn test_verify_server_cert_invalid_signature() {
        assert!(verifier()
            .verify_server_cert(
                &rustls_certificate(constants::TEST_CERT_INVALID_SIGNATURE).unwrap(),
                &[],
                &ServerName::try_from("lsdafhgldfhg").unwrap(),
                &mut [].into_iter(),
                &[],
                std::time::SystemTime::now(),
            )
            .is_err());
    }
}
