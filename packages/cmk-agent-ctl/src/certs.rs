// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::constants;
use anyhow::{anyhow, bail, Context, Result as AnyhowResult};
use reqwest::blocking::{Client, ClientBuilder};
use rsa::pkcs8::{EncodePrivateKey, LineEnding};
use rustls::client::danger::{
    DangerousClientConfigBuilder, HandshakeSignatureValid, ServerCertVerified, ServerCertVerifier,
};
use rustls::client::WebPkiServerVerifier;
use rustls::crypto::{verify_tls12_signature, verify_tls13_signature, CryptoProvider};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer, ServerName, UnixTime};
use rustls::{
    CertificateError, ClientConfig, DigitallySignedStruct, Error as RusttlsError, RootCertStore,
    SignatureScheme,
};
use rustls_pemfile::Item;
use std::net::TcpStream;
use std::sync::Arc;
use x509_parser::oid_registry::OID_X509_EXT_AUTHORITY_KEY_IDENTIFIER;
use x509_parser::prelude::FromDer;

pub fn make_csr(cn: &str) -> AnyhowResult<(String, String)> {
    let private_key = rsa::RsaPrivateKey::new(
        &mut rand::thread_rng(),
        constants::CERT_RSA_KEY_SIZE as usize,
    )?;
    let private_key_der = private_key.to_pkcs8_der()?;
    let private_key_pem = private_key.to_pkcs8_pem(LineEnding::LF)?;

    let key_pair = rcgen::KeyPair::from_pkcs8_der_and_sign_algo(
        &PrivatePkcs8KeyDer::from(private_key_der.as_bytes()),
        &rcgen::PKCS_RSA_SHA256,
    )?;
    let mut params = rcgen::CertificateParams::default();
    params.distinguished_name = rcgen::DistinguishedName::new();
    params
        .distinguished_name
        .push(rcgen::DnType::CommonName, cn);

    Ok((
        pem_rfc7468::encode_string(
            "CERTIFICATE REQUEST",
            LineEnding::LF,
            params.serialize_request(&key_pair)?.der().as_ref(),
        )
        .map_err(|e| anyhow!("Failed to PEM-encode certificate request: {e}"))?,
        private_key_pem.to_string(),
    ))
}

pub fn root_cert_store<'a>(
    root_certs: impl Iterator<Item = &'a str>,
) -> AnyhowResult<RootCertStore> {
    let mut cert_store = RootCertStore::empty();

    for root_cert in root_certs {
        cert_store.add(rustls_certificate(root_cert)?)?;
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

impl std::convert::TryFrom<&CertificateDer<'_>> for CNCheckerUUID {
    type Error = RusttlsError;

    fn try_from(certificate: &CertificateDer) -> Result<Self, RusttlsError> {
        let (_rem, cert) =
            x509_parser::certificate::X509Certificate::from_der(certificate.as_ref())
                .map_err(|_e| RusttlsError::InvalidCertificate(CertificateError::BadEncoding))?;

        let common_names =
            common_names(cert.subject()).map_err(|e| RusttlsError::General(e.to_string()))?;

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

/// How [`ServerCertChecker`] validates the peer certificate chain. The
/// handshake-signature checks (proving the peer holds the key) are identical
/// for every policy — only the chain validation differs.
#[derive(Debug)]
enum ServerCertPolicy {
    /// Accept any certificate, emulating openssl's `SslVerifyMode::NONE`: the
    /// chain is not validated at all (the handshake signatures still are). Used
    /// for the trust-on-first-use certificate fetch.
    AcceptAny,
    /// Full WebPKI verification against the configured roots, with hostname
    /// checking bypassed, plus rejection of certificates whose CN is a UUID.
    CnIsNoUuidAcceptAnyHostname(Arc<dyn ServerCertVerifier>),
}

#[derive(Debug)]
struct ServerCertChecker {
    crypto_provider: Arc<CryptoProvider>,
    policy: ServerCertPolicy,
}

impl ServerCertChecker {
    fn accept_any(crypto_provider: &Arc<CryptoProvider>) -> Self {
        Self {
            crypto_provider: crypto_provider.clone(),
            policy: ServerCertPolicy::AcceptAny,
        }
    }

    fn cn_is_no_uuid_accept_any_hostname(
        roots: RootCertStore,
        crypto_provider: &Arc<CryptoProvider>,
    ) -> AnyhowResult<Self> {
        Ok(Self {
            crypto_provider: crypto_provider.clone(),
            policy: ServerCertPolicy::CnIsNoUuidAcceptAnyHostname(
                WebPkiServerVerifier::builder_with_provider(
                    Arc::new(roots),
                    crypto_provider.clone(),
                )
                .build()?,
            ),
        })
    }
}

impl ServerCertVerifier for ServerCertChecker {
    fn verify_server_cert(
        &self,
        end_entity: &CertificateDer,
        intermediates: &[CertificateDer],
        _server_name: &ServerName,
        ocsp_response: &[u8],
        now: UnixTime,
    ) -> Result<ServerCertVerified, RusttlsError> {
        let verifier = match &self.policy {
            ServerCertPolicy::AcceptAny => return Ok(ServerCertVerified::assertion()),
            ServerCertPolicy::CnIsNoUuidAcceptAnyHostname(verifier) => verifier,
        };

        let cn_checker = CNCheckerUUID::try_from(end_entity)?;
        if cn_checker.cn_is_uuid() {
            return Err(RusttlsError::General(format!(
                "CN in server certificate is a valid UUID: {}",
                cn_checker.cn()
            )));
        }
        verifier.verify_server_cert(
            end_entity,
            intermediates,
            // emulate reqwest::ClientBuilder::danger_accept_invalid_hostnames
            &ServerName::try_from(cn_checker.cn()).map_err(|e| {
                RusttlsError::General(format!(
                    "CN in server certificate cannot be used as server name: {e}"
                ))
            })?,
            ocsp_response,
            now,
        )
    }

    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, RusttlsError> {
        verify_tls12_signature(
            message,
            cert,
            dss,
            &self.crypto_provider.signature_verification_algorithms,
        )
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, RusttlsError> {
        verify_tls13_signature(
            message,
            cert,
            dss,
            &self.crypto_provider.signature_verification_algorithms,
        )
    }

    fn supported_verify_schemes(&self) -> Vec<SignatureScheme> {
        self.crypto_provider
            .signature_verification_algorithms
            .supported_schemes()
    }
}

pub struct TLSIdentity {
    pub cert_chain: Vec<CertificateDer<'static>>,
    pub key_der: PrivateKeyDer<'static>,
}

pub struct HandshakeCredentials<'a> {
    pub server_root_cert: &'a str,
    pub client_identity: Option<TLSIdentity>,
}

fn tls_config(
    handshake_credentials: HandshakeCredentials,
    crypto_provider: &Arc<CryptoProvider>,
) -> AnyhowResult<ClientConfig> {
    let builder = DangerousClientConfigBuilder {
        cfg: ClientConfig::builder(),
    }
    .with_custom_certificate_verifier(Arc::new(
        ServerCertChecker::cn_is_no_uuid_accept_any_hostname(
            root_cert_store([handshake_credentials.server_root_cert].into_iter())?,
            crypto_provider,
        )?,
    ));
    Ok(match handshake_credentials.client_identity {
        Some(identity) => builder.with_client_auth_cert(identity.cert_chain, identity.key_der)?,
        None => builder.with_no_client_auth(),
    })
}

pub fn client(
    handshake_credentials: Option<HandshakeCredentials>,
    use_proxy: bool,
) -> AnyhowResult<Client> {
    let mut client_builder = ClientBuilder::new();

    client_builder = if let Some(handshake_credentials) = handshake_credentials {
        client_builder.use_preconfigured_tls(tls_config(
            handshake_credentials,
            CryptoProvider::get_default().ok_or(anyhow!("No default crypto provider set"))?,
        )?)
    } else {
        client_builder.danger_accept_invalid_certs(true)
    };

    if !use_proxy {
        client_builder = client_builder.no_proxy()
    };

    Ok(client_builder.build()?)
}

pub fn fetch_server_cert_pem(server: &str, port: &u16) -> AnyhowResult<String> {
    let crypto_provider =
        CryptoProvider::get_default().ok_or(anyhow!("No default crypto provider set"))?;
    let config = DangerousClientConfigBuilder {
        cfg: ClientConfig::builder(),
    }
    .with_custom_certificate_verifier(Arc::new(ServerCertChecker::accept_any(crypto_provider)))
    .with_no_client_auth();

    let mut connection = rustls::ClientConnection::new(
        Arc::new(config),
        ServerName::try_from(server.to_owned())
            .context("Server name cannot be used for a TLS connection")?,
    )?;
    let mut tcp_stream = TcpStream::connect(format!("{server}:{port}"))?;
    while connection.is_handshaking() {
        connection.complete_io(&mut tcp_stream)?;
    }

    let server_cert = pem_rfc7468::encode_string(
        "CERTIFICATE",
        LineEnding::LF,
        connection
            .peer_certificates()
            .context("Failed fetching peer cert chain")?
            .first()
            .context("Failed unpacking peer cert chain")?
            .as_ref(),
    )
    .map_err(|e| anyhow!("Failed to PEM-encode server certificate: {e}"))?;

    connection.send_close_notify();
    let _ = connection.complete_io(&mut tcp_stream);

    Ok(server_cert)
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
                .map_err(|e| anyhow!(format!("Failed to parse CN to string: {e}")))
        })
        .collect::<AnyhowResult<Vec<_>>>()
}

pub fn has_authority_key_identifier(
    certificate: &x509_parser::certificate::X509Certificate,
) -> bool {
    matches!(
        certificate.get_extension_unique(&OID_X509_EXT_AUTHORITY_KEY_IDENTIFIER),
        Ok(Some(_))
    )
}

pub fn render_asn1_time(asn1_tine: &x509_parser::time::ASN1Time) -> String {
    match asn1_tine.to_rfc2822() {
        Ok(s) => s,
        Err(s) => s,
    }
}

pub fn rustls_private_key(key_pem: &str) -> AnyhowResult<PrivateKeyDer<'static>> {
    if let Item::Pkcs8Key(it) = rustls_pemfile::read_one(&mut key_pem.to_owned().as_bytes())?
        .context("Could not load private key")?
    {
        Ok(PrivateKeyDer::Pkcs8(it))
    } else {
        bail!("Could not process private key")
    }
}

pub fn rustls_certificate(cert_pem: &str) -> AnyhowResult<CertificateDer<'static>> {
    if let Item::X509Certificate(it) =
        rustls_pemfile::read_one(&mut cert_pem.to_owned().as_bytes())?
            .context("Could not load certificate")?
    {
        Ok(it)
    } else {
        bail!("Could not process certificate")
    }
}

#[cfg(test)]
mod test_cn_no_uuid {
    use super::super::constants;
    use super::*;
    use rustls::crypto::ring::default_provider;

    #[test]
    fn test_csr_version() {
        let (csr, key) = make_csr("stuff").unwrap();
        let csr_pem = parse_pem(&csr).unwrap();
        let (_rem, csr_obj) =
            x509_parser::certification_request::X509CertificationRequest::from_der(
                &csr_pem.contents,
            )
            .unwrap();
        // A CSR is a simple x509 structure without any extensions, and must be of version 1,
        // which equals to a raw version value of 0.
        // See also https://www.rfc-editor.org/rfc/rfc2986 .
        // This is actually tested in recent versions of python-cryptography and a registration call
        // with a non-compliant CSR would fail.
        assert!(csr_obj.certification_request_info.version.0 == 0);
        assert_eq!(
            common_names(&csr_obj.certification_request_info.subject).unwrap(),
            ["stuff"]
        );
        // The private key must remain consumable by our TLS stack.
        assert!(rustls_private_key(&key).is_ok());
    }

    #[test]
    fn test_cn_extraction() {
        let cn_checker =
            CNCheckerUUID::try_from(&rustls_certificate(constants::TEST_CERT_OK).unwrap()).unwrap();
        assert_eq!(cn_checker.cn(), "heute");
    }

    #[test]
    fn test_missing_authority_key_identifier() {
        // TEST_CERT_CN_UUID has the shape of an agent certificate from an older Checkmk
        // version: subject alternative name and basic constraints, but no authority key
        // identifier.
        let cert = rustls_certificate(constants::TEST_CERT_CN_UUID).unwrap();
        let (_rem, cert) =
            x509_parser::certificate::X509Certificate::from_der(cert.as_ref()).unwrap();
        assert!(!has_authority_key_identifier(&cert));
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

    fn verifier() -> AnyhowResult<ServerCertChecker> {
        ServerCertChecker::cn_is_no_uuid_accept_any_hostname(
            root_cert_store([constants::TEST_ROOT_CERT].into_iter())?,
            &Arc::new(default_provider()),
        )
    }

    #[test]
    fn test_verify_server_cert_ok() {
        assert!(verifier()
            .unwrap()
            .verify_server_cert(
                &rustls_certificate(constants::TEST_CERT_OK).unwrap(),
                &[],
                &ServerName::try_from("lsdafhgldfhg").unwrap(),
                &[],
                UnixTime::now(),
            )
            .is_ok());
    }

    #[test]
    fn test_verify_server_cert_cn_is_uuid() {
        assert_eq!(
            match verifier()
                .unwrap()
                .verify_server_cert(
                    &rustls_certificate(constants::TEST_CERT_CN_UUID).unwrap(),
                    &[],
                    &ServerName::try_from("lsdafhgldfhg").unwrap(),
                    &[],
                    UnixTime::now(),
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
            .unwrap()
            .verify_server_cert(
                &rustls_certificate(constants::TEST_CERT_INVALID_SIGNATURE).unwrap(),
                &[],
                &ServerName::try_from("lsdafhgldfhg").unwrap(),
                &[],
                UnixTime::now(),
            )
            .is_err());
    }

    #[test]
    fn test_accept_any_accepts_untrusted_cert() {
        // The accept-any policy must accept a certificate the verifying policy
        // rejects (untrusted / invalid signature); only the handshake-signature
        // check remains, which this static certificate does not exercise.
        let checker = ServerCertChecker::accept_any(&Arc::new(default_provider()));
        assert!(checker
            .verify_server_cert(
                &rustls_certificate(constants::TEST_CERT_INVALID_SIGNATURE).unwrap(),
                &[],
                &ServerName::try_from("whatever").unwrap(),
                &[],
                UnixTime::now(),
            )
            .is_ok());
    }
}
