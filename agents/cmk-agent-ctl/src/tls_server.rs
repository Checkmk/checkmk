use crate::config::Connection;

use super::config;
use anyhow::{anyhow, Context, Result as AnyhowResult};
use rustls::RootCertStore;
use rustls::{
    server::AllowAnyAuthenticatedClient, server::ResolvesServerCertUsingSni, sign::CertifiedKey,
    sign::RsaSigningKey, Certificate, PrivateKey, ServerConfig, ServerConnection,
    Stream as RustlsStream,
};
use rustls_pemfile::Item;
use std::fs::File;
use std::io::Result as IoResult;
use std::io::{Read, Write};
use std::os::unix::prelude::FromRawFd;
use std::sync::Arc;

pub fn tls_connection<'a>(
    connections: impl Iterator<Item = &'a config::Connection>,
) -> AnyhowResult<ServerConnection> {
    Ok(ServerConnection::new(tls_config(connections)?)?)
}

pub fn tls_stream<'a>(
    server_connection: &'a mut ServerConnection,
    stream: &'a mut IoStream,
) -> RustlsStream<'a, ServerConnection, IoStream> {
    RustlsStream::new(server_connection, stream)
}

fn tls_config<'a>(
    connections: impl Iterator<Item = &'a config::Connection>,
) -> AnyhowResult<Arc<ServerConfig>> {
    let connections: Vec<&Connection> = connections.collect();
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
    connections: impl Iterator<Item = &'a Connection>,
) -> AnyhowResult<Arc<ResolvesServerCertUsingSni>> {
    let mut resolver = rustls::server::ResolvesServerCertUsingSni::new();

    for conn in connections {
        let key = private_key(&conn.private_key)?;
        let cert = certificate(&conn.certificate)?;

        let certified_key = CertifiedKey::new(vec![cert], Arc::new(RsaSigningKey::new(&key)?));

        resolver.add(&conn.uuid, certified_key)?;
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

pub struct IoStream {
    reader: File,
    writer: File,
}

impl IoStream {
    pub fn new() -> Self {
        IoStream {
            // Using File type from raw FDs here instead of
            // io::StdIn/StdOut because the latter are buffered,
            // and this is at some point incompatible to the TLS handshake
            // (freezes in the middle)
            reader: unsafe { File::from_raw_fd(0) },
            writer: unsafe { File::from_raw_fd(1) },
        }
    }
}

impl Read for IoStream {
    fn read(&mut self, buf: &mut [u8]) -> IoResult<usize> {
        self.reader.read(buf)
    }
}

impl Write for IoStream {
    fn write(&mut self, buf: &[u8]) -> IoResult<usize> {
        self.writer.write(buf)
    }
    fn flush(&mut self) -> IoResult<()> {
        self.writer.flush()
    }
}
