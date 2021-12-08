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
use std::io::{self, Result as IoResult};
use std::io::{Read, Write};
use std::os::unix::prelude::FromRawFd;
use std::slice::Iter;
use std::sync::Arc;

pub fn tls_connection(
    reg_conns: Vec<config::RegisteredConnection>,
) -> AnyhowResult<ServerConnection> {
    Ok(ServerConnection::new(tls_config(reg_conns)?)?)
}

pub fn tls_stream<'a>(
    server_connection: &'a mut ServerConnection,
    stream: &'a mut IoStream,
) -> RustlsStream<'a, ServerConnection, IoStream> {
    RustlsStream::new(server_connection, stream)
}

fn tls_config(reg_conns: Vec<config::RegisteredConnection>) -> AnyhowResult<Arc<ServerConfig>> {
    Ok(Arc::new(
        ServerConfig::builder()
            .with_safe_defaults()
            .with_client_cert_verifier(AllowAnyAuthenticatedClient::new(root_cert_store(
                reg_conns.iter(),
            )?))
            .with_cert_resolver(sni_resolver(reg_conns.iter())?),
    ))
}

fn root_cert_store(reg_conns: Iter<config::RegisteredConnection>) -> AnyhowResult<RootCertStore> {
    let mut cert_store = RootCertStore::empty();

    for conn in reg_conns {
        cert_store.add(&certificate(&mut conn.root_cert.as_bytes())?)?;
    }

    Ok(cert_store)
}

fn sni_resolver(
    reg_conns: Iter<config::RegisteredConnection>,
) -> AnyhowResult<Arc<ResolvesServerCertUsingSni>> {
    let mut resolver = rustls::server::ResolvesServerCertUsingSni::new();

    for spec in reg_conns {
        let key = private_key(&mut spec.private_key.as_bytes())?;
        let cert = certificate(&mut spec.certificate.as_bytes())?;

        let certified_key = CertifiedKey::new(vec![cert], Arc::new(RsaSigningKey::new(&key)?));

        resolver.add(&spec.uuid, certified_key)?;
    }

    Ok(Arc::new(resolver))
}

fn private_key(bytes: &mut dyn io::BufRead) -> AnyhowResult<PrivateKey> {
    if let Item::PKCS8Key(it) =
        rustls_pemfile::read_one(bytes)?.context("Could not load private key")?
    {
        Ok(PrivateKey(it))
    } else {
        Err(anyhow!("Could not process private key"))
    }
}

pub fn certificate(bytes: &mut dyn io::BufRead) -> AnyhowResult<Certificate> {
    if let Item::X509Certificate(it) =
        rustls_pemfile::read_one(bytes)?.context("Could not load certificate")?
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
