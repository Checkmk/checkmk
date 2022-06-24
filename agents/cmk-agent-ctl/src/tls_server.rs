// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, config};
use anyhow::Result as AnyhowResult;
use std::sync::Arc;
use tokio_rustls::rustls::{
    server::AllowAnyAuthenticatedClient, server::ClientCertVerified, server::ClientCertVerifier,
    server::ResolvesServerCertUsingSni, sign::CertifiedKey, sign::RsaSigningKey, Certificate,
    Error as RusttlsError, RootCertStore, ServerConfig,
};
use tokio_rustls::TlsAcceptor;

#[cfg(windows)]
use std::io::{Read, Result as IoResult, Write};

pub fn tls_acceptor<'a>(
    connections: impl Iterator<Item = &'a config::Connection>,
) -> AnyhowResult<TlsAcceptor> {
    Ok(TlsAcceptor::from(tls_config(connections)?))
}

fn tls_config<'a>(
    connections: impl Iterator<Item = &'a config::Connection>,
) -> AnyhowResult<Arc<ServerConfig>> {
    let connections: Vec<&config::Connection> = connections.collect();
    Ok(Arc::new(
        ServerConfig::builder()
            .with_safe_defaults()
            .with_client_cert_verifier(CNNoUUIDVerifier::from_roots(certs::root_cert_store(
                connections.iter().map(|it| it.root_cert.as_str()),
            )?))
            .with_cert_resolver(sni_resolver(connections.into_iter())?),
    ))
}
struct CNNoUUIDVerifier {
    verifier: Arc<dyn ClientCertVerifier>,
}

impl CNNoUUIDVerifier {
    pub fn from_roots(roots: RootCertStore) -> Arc<dyn ClientCertVerifier> {
        Arc::new(Self {
            verifier: AllowAnyAuthenticatedClient::new(roots),
        })
    }
}

impl ClientCertVerifier for CNNoUUIDVerifier {
    fn client_auth_root_subjects(
        &self,
    ) -> Option<tokio_rustls::rustls::internal::msgs::handshake::DistinguishedNames> {
        self.verifier.client_auth_root_subjects()
    }

    fn verify_client_cert(
        &self,
        end_entity: &Certificate,
        intermediates: &[Certificate],
        now: std::time::SystemTime,
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
}

fn sni_resolver<'a>(
    connections: impl Iterator<Item = &'a config::Connection>,
) -> AnyhowResult<Arc<ResolvesServerCertUsingSni>> {
    let mut resolver = rustls::server::ResolvesServerCertUsingSni::new();

    for conn in connections {
        let key = certs::rustls_private_key(&conn.private_key)?;
        let cert = certs::rustls_certificate(&conn.certificate)?;

        let certified_key = CertifiedKey::new(vec![cert], Arc::new(RsaSigningKey::new(&key)?));

        resolver.add(&conn.uuid.to_string(), certified_key)?;
    }

    Ok(Arc::new(resolver))
}

#[cfg(windows)]
pub struct IoStream {
    // Windows Agent will not use stdio/stdin as a communication channel
    // This is just temporary stub to keep API more or less in sync.
    reader: std::io::Stdin,
    writer: std::io::Stdout,
}

#[cfg(windows)]
impl Read for IoStream {
    fn read(&mut self, buf: &mut [u8]) -> IoResult<usize> {
        let mut handle = self.reader.lock();
        handle.read(buf)
    }
}

#[cfg(windows)]
impl Write for IoStream {
    fn write(&mut self, buf: &[u8]) -> IoResult<usize> {
        let mut handle = self.writer.lock();
        handle.write(buf)
    }
    fn flush(&mut self) -> IoResult<()> {
        let mut handle = self.writer.lock();
        handle.flush()
    }
}

#[cfg(test)]
mod test_cn_no_uuid_verifier {
    use super::super::constants;
    use super::*;

    fn verifier() -> Arc<dyn ClientCertVerifier> {
        CNNoUUIDVerifier::from_roots(
            certs::root_cert_store([constants::TEST_ROOT_CERT].into_iter()).unwrap(),
        )
    }

    #[test]
    fn test_verify_client_cert_ok() {
        assert!(verifier()
            .verify_client_cert(
                &certs::rustls_certificate(constants::TEST_CERT_OK).unwrap(),
                &[],
                std::time::SystemTime::now(),
            )
            .is_ok());
    }

    #[test]
    fn test_verify_client_cert_cn_is_uuid() {
        assert_eq!(
            match verifier()
                .verify_client_cert(
                    &certs::rustls_certificate(constants::TEST_CERT_CN_UUID).unwrap(),
                    &[],
                    std::time::SystemTime::now(),
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
            .verify_client_cert(
                &certs::rustls_certificate(constants::TEST_CERT_INVALID_SIGNATURE).unwrap(),
                &[],
                std::time::SystemTime::now(),
            )
            .is_err(),);
    }
}
