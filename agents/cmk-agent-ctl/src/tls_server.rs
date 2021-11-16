use super::config;
use rustls::{
    server::ResolvesServerCertUsingSni, sign::CertifiedKey, sign::RsaSigningKey, Certificate,
    PrivateKey, ServerConfig, ServerConnection, Stream as RustlsStream,
};
use rustls_pemfile::Item;
use std::error::Error;
use std::fs::File;
use std::io::Result as IoResult;
use std::io::{Read, Write};
use std::os::unix::prelude::FromRawFd;
use std::sync::Arc;

pub fn tls_connection(
    reg_state: config::RegistrationState,
) -> Result<ServerConnection, Box<dyn Error>> {
    let server_specs = reg_state.server_specs.into_values().collect();
    Ok(ServerConnection::new(tls_config(server_specs)?).unwrap())
}

pub fn tls_stream<'a>(
    server_connection: &'a mut ServerConnection,
    stream: &'a mut IoStream,
) -> RustlsStream<'a, ServerConnection, IoStream> {
    RustlsStream::new(server_connection, stream)
}

fn tls_config(server_specs: Vec<config::ServerSpec>) -> Result<Arc<ServerConfig>, Box<dyn Error>> {
    Ok(Arc::new(
        ServerConfig::builder()
            .with_safe_defaults()
            .with_no_client_auth()
            .with_cert_resolver(sni_resolver(server_specs)?),
    ))
}

fn sni_resolver(
    server_specs: Vec<config::ServerSpec>,
) -> Result<Arc<ResolvesServerCertUsingSni>, Box<dyn Error>> {
    let mut resolver = rustls::server::ResolvesServerCertUsingSni::new();

    for spec in server_specs {
        let key = if let Item::PKCS8Key(it) =
            rustls_pemfile::read_one(&mut spec.private_key.as_bytes())
                .unwrap()
                .unwrap()
        {
            Ok(PrivateKey(it))
        } else {
            Err("Could not load private key")
        }?;

        let cert = if let Item::X509Certificate(it) =
            rustls_pemfile::read_one(&mut spec.certificate.as_bytes())
                .unwrap()
                .unwrap()
        {
            Ok(Certificate(it))
        } else {
            Err("Could not load certificate")
        }?;

        let certified_key =
            CertifiedKey::new(vec![cert], Arc::new(RsaSigningKey::new(&key).unwrap()));

        resolver.add(&spec.uuid, certified_key).unwrap();
    }

    Ok(Arc::new(resolver))
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
