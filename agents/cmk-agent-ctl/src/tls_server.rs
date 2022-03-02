// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config;
use anyhow::{anyhow, Context, Result as AnyhowResult};
use rustls_pemfile::Item;
use std::sync::Arc;
use tokio_rustls::rustls::{
    server::AllowAnyAuthenticatedClient, server::ResolvesServerCertUsingSni, sign::CertifiedKey,
    sign::RsaSigningKey, Certificate, PrivateKey, RootCertStore, ServerConfig,
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
            .with_client_cert_verifier(AllowAnyAuthenticatedClient::new(root_cert_store(
                connections.iter().map(|it| &it.root_cert),
            )?))
            .with_cert_resolver(sni_resolver(connections.into_iter())?),
    ))
}

fn root_cert_store<'a>(
    root_certs: impl Iterator<Item = &'a String>,
) -> AnyhowResult<RootCertStore> {
    let mut cert_store = RootCertStore::empty();

    for root_cert in root_certs {
        cert_store.add(&certificate(root_cert)?)?;
    }

    Ok(cert_store)
}

fn sni_resolver<'a>(
    connections: impl Iterator<Item = &'a config::Connection>,
) -> AnyhowResult<Arc<ResolvesServerCertUsingSni>> {
    let mut resolver = rustls::server::ResolvesServerCertUsingSni::new();

    for conn in connections {
        let key = private_key(&conn.private_key)?;
        let cert = certificate(&conn.certificate)?;

        let certified_key = CertifiedKey::new(vec![cert], Arc::new(RsaSigningKey::new(&key)?));

        resolver.add(&conn.uuid.to_string(), certified_key)?;
    }

    Ok(Arc::new(resolver))
}

fn private_key(key_pem: &str) -> AnyhowResult<PrivateKey> {
    if let Item::PKCS8Key(it) = rustls_pemfile::read_one(&mut key_pem.to_owned().as_bytes())?
        .context("Could not load private key")?
    {
        Ok(PrivateKey(it))
    } else {
        Err(anyhow!("Could not process private key"))
    }
}

fn certificate(cert_pem: &str) -> AnyhowResult<Certificate> {
    if let Item::X509Certificate(it) =
        rustls_pemfile::read_one(&mut cert_pem.to_owned().as_bytes())?
            .context("Could not load certificate")?
    {
        Ok(Certificate(it))
    } else {
        Err(anyhow!("Could not process certificate"))
    }
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
