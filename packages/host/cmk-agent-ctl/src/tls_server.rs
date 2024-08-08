// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, config};
use anyhow::{anyhow, Result as AnyhowResult};
use rustls::crypto::{verify_tls12_signature, verify_tls13_signature, CryptoProvider, KeyProvider};
use std::sync::Arc;
use tokio_rustls::rustls::client::danger::HandshakeSignatureValid;
use tokio_rustls::rustls::pki_types::{CertificateDer, UnixTime};
use tokio_rustls::rustls::server::danger::{ClientCertVerified, ClientCertVerifier};
use tokio_rustls::rustls::server::{ResolvesServerCertUsingSni, WebPkiClientVerifier};
use tokio_rustls::rustls::sign::CertifiedKey;
use tokio_rustls::rustls::{
    DigitallySignedStruct, Error as RusttlsError, RootCertStore, ServerConfig,
};
use tokio_rustls::TlsAcceptor;

pub fn tls_acceptor<'a>(
    connections: impl Iterator<Item = &'a config::TrustedConnection>,
) -> AnyhowResult<TlsAcceptor> {
    Ok(TlsAcceptor::from(tls_config(
        connections,
        CryptoProvider::get_default().ok_or(anyhow!("No default crypto provider set"))?,
    )?))
}

fn tls_config<'a>(
    connections: impl Iterator<Item = &'a config::TrustedConnection>,
    crypto_provider: &Arc<CryptoProvider>,
) -> AnyhowResult<Arc<ServerConfig>> {
    let connections: Vec<&config::TrustedConnection> = connections.collect();
    Ok(Arc::new(
        ServerConfig::builder()
            .with_client_cert_verifier(Arc::new(CNNoUUIDVerifier::from_roots_and_crypto_provider(
                certs::root_cert_store(connections.iter().map(|it| it.root_cert.as_str()))?,
                crypto_provider,
            )?))
            .with_cert_resolver(sni_resolver(
                connections.into_iter(),
                crypto_provider.key_provider,
            )?),
    ))
}

#[derive(Debug)]
struct CNNoUUIDVerifier {
    crypto_provider: Arc<CryptoProvider>,
    verifier: Arc<dyn ClientCertVerifier>,
}

impl CNNoUUIDVerifier {
    pub fn from_roots_and_crypto_provider(
        roots: RootCertStore,
        crypto_provider: &Arc<CryptoProvider>,
    ) -> AnyhowResult<Self> {
        Ok(Self {
            crypto_provider: crypto_provider.clone(),
            verifier: WebPkiClientVerifier::builder_with_provider(
                Arc::new(roots),
                crypto_provider.clone(),
            )
            .build()?,
        })
    }
}

impl ClientCertVerifier for CNNoUUIDVerifier {
    fn root_hint_subjects(&self) -> &[rustls::DistinguishedName] {
        self.verifier.root_hint_subjects()
    }

    fn verify_client_cert(
        &self,
        end_entity: &CertificateDer,
        intermediates: &[CertificateDer],
        now: UnixTime,
    ) -> Result<ClientCertVerified, RusttlsError> {
        let cn_checker = certs::CNCheckerUUID::try_from(end_entity)?;
        if cn_checker.cn_is_uuid() {
            return Err(RusttlsError::General(format!(
                "CN in client certificate is a valid UUID: {}",
                cn_checker.cn()
            )));
        }
        self.verifier
            .verify_client_cert(end_entity, intermediates, now)
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
    ) -> Result<HandshakeSignatureValid, rustls::Error> {
        verify_tls13_signature(
            message,
            cert,
            dss,
            &self.crypto_provider.signature_verification_algorithms,
        )
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        self.crypto_provider
            .signature_verification_algorithms
            .supported_schemes()
    }
}

fn sni_resolver<'a>(
    connections: impl Iterator<Item = &'a config::TrustedConnection>,
    key_provider: &dyn KeyProvider,
) -> AnyhowResult<Arc<ResolvesServerCertUsingSni>> {
    let mut resolver = rustls::server::ResolvesServerCertUsingSni::new();

    for conn in connections {
        let key = certs::rustls_private_key(&conn.private_key)?;
        let cert = certs::rustls_certificate(&conn.certificate)?;

        let certified_key = CertifiedKey::new(vec![cert], key_provider.load_private_key(key)?);

        resolver.add(&conn.uuid.to_string(), certified_key)?;
    }

    Ok(Arc::new(resolver))
}

#[cfg(test)]
mod test_cn_no_uuid_verifier {
    use super::super::constants;
    use super::*;
    use rustls::crypto::ring::default_provider;

    fn verifier() -> AnyhowResult<CNNoUUIDVerifier> {
        CNNoUUIDVerifier::from_roots_and_crypto_provider(
            certs::root_cert_store([constants::TEST_ROOT_CERT].into_iter())?,
            &Arc::new(default_provider()),
        )
    }

    #[test]
    fn test_verify_client_cert_ok() {
        assert!(verifier()
            .unwrap()
            .verify_client_cert(
                &certs::rustls_certificate(constants::TEST_CERT_OK).unwrap(),
                &[],
                UnixTime::now(),
            )
            .is_ok());
    }

    #[test]
    fn test_verify_client_cert_cn_is_uuid() {
        assert_eq!(
            match verifier()
                .unwrap()
                .verify_client_cert(
                    &certs::rustls_certificate(constants::TEST_CERT_CN_UUID).unwrap(),
                    &[],
                    UnixTime::now(),
                )
                .unwrap_err()
            {
                rustls::Error::General(s) => s,
                _ => panic!("Wrong error type"),
            },
            "CN in client certificate is a valid UUID: cf771eeb-b666-4673-95c9-683960fb2939"
        )
    }

    #[test]
    fn test_verify_client_cert_invalid_signature() {
        assert!(verifier()
            .unwrap()
            .verify_client_cert(
                &certs::rustls_certificate(constants::TEST_CERT_INVALID_SIGNATURE).unwrap(),
                &[],
                UnixTime::now(),
            )
            .is_err(),);
    }
}
