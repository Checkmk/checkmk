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
use x509_parser::traits::FromDer;

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
            .with_client_cert_verifier(CNNoUUIDVerifier::from_roots(root_cert_store(
                connections.iter().map(|it| &it.root_cert),
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
        let client_cert =
            match x509_parser::certificate::X509Certificate::from_der(end_entity.as_ref()) {
                Ok((_rem, cert)) => cert,
                Err(err) => {
                    return Err(RusttlsError::InvalidCertificateData(format!(
                        "Client certificate parsing failed: {}",
                        err
                    )))
                }
            };

        let common_names = match certs::common_names(client_cert.subject()) {
            Ok(cns) => cns,
            Err(err) => {
                return Err(RusttlsError::InvalidCertificateData(format!(
                    "Client certificate parsing failed: {}",
                    err
                )))
            }
        };

        if common_names.len() != 1 {
            return Err(RusttlsError::General(format!(
                "Client certificate contains more than one CN: {}",
                common_names.join(", ")
            )));
        }

        if uuid::Uuid::parse_str(common_names[0]).is_ok() {
            return Err(RusttlsError::General(format!(
                "CN in client certificate is a valid UUID: {}",
                common_names[0]
            )));
        }

        self.verifier
            .verify_client_cert(end_entity, intermediates, now)
    }
}

fn root_cert_store<'a>(
    root_certs: impl Iterator<Item = &'a String>,
) -> AnyhowResult<RootCertStore> {
    let mut cert_store = RootCertStore::empty();

    for root_cert in root_certs {
        cert_store.add(&certs::rustls_certificate(root_cert)?)?;
    }

    Ok(cert_store)
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
    use super::*;

    // CA
    const ROOT_CERT: &str = "-----BEGIN CERTIFICATE-----\nMIIDFTCCAf2gAwIBAgIUaDlr/3eN2SmBMlpmW9cICSVzcEwwDQYJKoZIhvcNAQEL\nBQAwIDEeMBwGA1UEAwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIyMDYxMzEw\nMTQyNVoYDzMwMjAxMDE0MTAxNDI1WjAgMR4wHAYDVQQDDBVTaXRlICdoZXV0ZScg\nbG9jYWwgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDwvHoHuD6E\naQNpEaznTKd/6M/jkiopZ8It+zSEi93zBwu2ZsJlv8Kl1KkWim0s6o/YuQx//USQ\nfVR3lAazRr2k4xxwbThzXh+0S2dp5RWRBZCuJElwQ+u+PVmVsq/Zusj+YVl1Jo3F\nZ5xGUwjS+G9+ZElDnGpDi0NG5GNoozE5L0EEnQArsC+V7MoTUKebN+x9zlcc7bPb\nfphcwLrA/IGuJe7Ab6oLbEm/pA3X1LxyY98/pBoUeVXlEjJMo/8SrW+1Y02GyHCJ\nysVWC2+PwFdm4GXMsZVFMy/FE5lElwjgLHiTUDdytClP3yKHvyeJD3E1pw8Dm7QP\nxb9kCOCslRm3AgMBAAGjRTBDMB0GA1UdDgQWBBSyZwy7Z0SxqhbyXTilbcnJJNGP\nkTASBgNVHRMBAf8ECDAGAQH/AgEAMA4GA1UdDwEB/wQEAwIBBjANBgkqhkiG9w0B\nAQsFAAOCAQEA0zbSOS+9QgB3VcBkiRY5/ZGv+l+MCRoxeBm6rsj76dJyu5KYAEvW\nFg0zzg0xdgFMqcd1WBwVP4w1mqmvLXW0+C899F8GNsP089PfRg1qIzbLKP6P/CNv\nUowHzTqEnI0IDcD1RnuJj+Q4Ao04unFSllTO/OWu+wbfqiNKf/RHdiVs91KWS7XU\nFgG5s3A5p91N1JfDboWk/pQDHQihhjxgaOlfjWp8b0KxShMgnRdxTkqbS/APN/9f\nhcmq7hQrXVq2VUknRzrrlv2wBNn83aqFpw54Gnjor91EUbsB0gXWj6Ki/afvyAwi\ndt+OCdh9sbgEVsdwDYowscUHKcmGI3qoGg==\n-----END CERTIFICATE-----\n";
    // standard site certificate signed by CA
    const CERT_OK: &str = "-----BEGIN CERTIFICATE-----\nMIIC4jCCAcqgAwIBAgIUToJSkbhbRwHjr/9Uu3FEoidwCWMwDQYJKoZIhvcNAQEL\nBQAwIDEeMBwGA1UEAwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIyMDYxMzEw\nMTQyNVoYDzMwMjAxMDE0MTAxNDI1WjAQMQ4wDAYDVQQDDAVoZXV0ZTCCASIwDQYJ\nKoZIhvcNAQEBBQADggEPADCCAQoCggEBAL6Upc1udGIMPymBF8m+Z6PvQA/KPYF/\ne3g9gClSg73376XXdSqO9VkOR80lUM1mW2ZtK+ApF6/gDFaFmUPxThcq5PECgajd\nSug1sdC9GYfd6KQfAxseSR2x59UNYbG3Gt33+lurWHxCy61RL3sGW72CDoqqCGrK\n5hTbkOyNcaVrtXFSFE0N7cFFOK36MLuzopOFHNUeC1S/O0clUwA54kBAA37ARE5B\nfy2myp3A4YAMtD5dbva1WDJ1A9Hg+ivtjBxgrfTOdZF00/AB1vfzOZVktd14eBHZ\nXfmfEwndFmvYe7LsQ4/g9G5P4C1FXEqxcKyJg7EGDAtEZScbwU/6/PcCAwEAAaMi\nMCAwEAYDVR0RBAkwB4IFaGV1dGUwDAYDVR0TAQH/BAIwADANBgkqhkiG9w0BAQsF\nAAOCAQEAjvWil5wjCHz4dYj4Jbwn71/78J/1puX5Uzq2qVp7/UlVGLXeTYYgw9Ax\nH+cbO5Hf7gb7X1pwmjktMru7Utds4RAoQCvHLcJn1rQ0sQAgSN/Piq97ToQfD65+\nfsA5WAQBnlWRgiUhx5YR54La5mRrWbPOUnBddiEt/AOM5emNUEMNLYn0eGG/5cKi\nqC+ygO8KKmhVakFiXOtZjOf2w4DEl+rtEbIXmfGR3MD7oRoEWlfvYkz/mh5TstYr\nLupAH+jnrHlYGSw7tbR2X1LdSykBZgro7SPPSsWyqNxDCIckZbQ0ahYxNO1oCvs0\nPZWBjnJQjlaJVG1iIQBJS8UaZ+hJ5A==\n-----END CERTIFICATE-----\n";
    // certificate signed by CA where CN is a valid UUID
    const CERT_CN_UUID: &str = "-----BEGIN CERTIFICATE-----\nMIIDIDCCAgigAwIBAgIUSXJpdJHE2CUaq0x0zO2EEEngX9cwDQYJKoZIhvcNAQEL\nBQAwIDEeMBwGA1UEAwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIyMDYxMzE3\nMTA0NloYDzMwMjAxMDE0MTcxMDQ2WjAvMS0wKwYDVQQDDCRjZjc3MWVlYi1iNjY2\nLTQ2NzMtOTVjOS02ODM5NjBmYjI5MzkwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw\nggEKAoIBAQCt9G35b5L3/K9AfaFLNGxS46yvbm2rd9FvzbOUospGsvHpN/cHiF8V\nV/fryGhtXWMzns0bB93gxEHd8qs8kvWuBg8FLYkn+H1XEiw7E7Ce80rrq61gaHDt\n3DCi6XID0a3gSQ7LQc2rWQ+Wpg0DjtyNFFXbUI0LV/YKWG6tfWXEFOy4tFUYbCW+\nz/kGshpjzYiK4aVCrYL54U4TAoUp8xvggOo4IXf04QABy7QWpmEDSRajhRtLkmcN\nx4HJ9/fKz7u6mymh4gI62kQWhxXtcVw+54dklp2Xt0ucbALp6T0XdaYFHWUTR1Yq\nSNLIcf79CRzf61vJjHQWVHoulXNpPNZVAgMBAAGjQTA/MC8GA1UdEQQoMCaCJGNm\nNzcxZWViLWI2NjYtNDY3My05NWM5LTY4Mzk2MGZiMjkzOTAMBgNVHRMBAf8EAjAA\nMA0GCSqGSIb3DQEBCwUAA4IBAQDo5JIsjXYAE11w9y1T7d+LzRj6HT7FYt1NLyHm\nMsZJh2y+gExd+k/E6Dlv494PW2/AX/prVG+UsBw+B0aDnrEm32BO3/ottwrdeL9b\nRmX1SQru89UgmfCsbgVpl66P7UGzltI/2vIyWzkcbcwMWP8UA1qAfPoMqnvGAMgu\n+bARCGaTWDT8uO6OCJm4JKMLXLk32kPL54Nd/Pp3lGrwWFOMFnjSbGtiAY2u9UeV\n+3uaganYjbLZkCQ0DP+DKDl6NBz3mrzI5wc+Fcpz8uDNV+UbtrGzreseBulJDLcl\ncr3aR+ZPgQPJDdVD56jXrdlU6hemc58NHJ+cPbw2ISaU9Rop\n-----END CERTIFICATE-----\n";
    // certificate signed by a different CA
    const CERT_INVALID_SIGNATURE: &str = "-----BEGIN CERTIFICATE-----\nMIIC3zCCAcegAwIBAgIUdRy8we2If2wSVioU+nu1420ZD4UwDQYJKoZIhvcNAQEL\nBQAwHzEdMBsGA1UEAwwUU2l0ZSAndGVtcCcgbG9jYWwgQ0EwIBcNMjIwNjEzMTcx\nNzUyWhgPMzAyMDEwMTQxNzE3NTJaMA8xDTALBgNVBAMMBHRlbXAwggEiMA0GCSqG\nSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDZMYl6ZTgmeonGMLizBNtAJNrH8O4rOvV3\nX8EvnWOmM26RCixGwy9MVteOlIptcZUa8QHo1EZ58T+1aS5G01LRtkx9OPK0bvPD\n4nnUGwIeUt12W5tHFH8DKpivl9oql/kJYzPTzGjsjeNXfPHGVUXVvq3pmL3U7d0o\nrC7s30fmRH0M0CArNykuJ9OO6kA52pplQmTbXRCceKTwtN7w0tWh7YYuw2343Rd/\nDQh8XvUduLWiMqkb0PC7otvgkQHFV6GylrE+FAxRvIY+2aqaUBziPHR+JU7Uxkpq\nYblNbOWRT3wjtxjBt0iYRrsMvhD8eD9T4sP51EZNk1S9jo2+PXDvAgMBAAGjITAf\nMA8GA1UdEQQIMAaCBHRlbXAwDAYDVR0TAQH/BAIwADANBgkqhkiG9w0BAQsFAAOC\nAQEASBTxFm2BQGQmmfwdouXT/nf071r5PCbr8Bj9AxKAzCiuJ/G8QBhwtTC01HmR\nL5vA1yi1Iiqm3wZTSetuNYQdi30HHDvJlHE3ADnKa1fo4vJFZTb4v+oKF8DUnaML\npmTkaldJuy3Ksl0tgeJlv6eM9/Rx47/XHMeD+0m72vKte13wBmMac18UNT/FNqM5\nM4H8Qvdxxbjfa/907ZPYnXg1baimqmNHvoELQzJNl8fza7fnDRRBn9XCSJoWiAcx\nu3ebRbIdPL3/BVQYHzBJV11zq4RN1IujYjRRTGWFr+zEVuuKmnbNK6hNAe8zwfLN\nJ7+UOWbsApe3/LIGhGJfGxtD+A==\n-----END CERTIFICATE-----\n";

    fn verifier() -> Arc<dyn ClientCertVerifier> {
        CNNoUUIDVerifier::from_roots(root_cert_store([String::from(ROOT_CERT)].iter()).unwrap())
    }

    #[test]
    fn test_verify_client_cert_ok() {
        assert!(verifier()
            .verify_client_cert(
                &certs::rustls_certificate(CERT_OK).unwrap(),
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
                    &certs::rustls_certificate(CERT_CN_UUID).unwrap(),
                    &[],
                    std::time::SystemTime::now(),
                )
                .unwrap_err()
            {
                RusttlsError::General(s) => s,
                _ => panic!("Wrong error type"),
            },
            "CN in client certificate is a valid UUID: cf771eeb-b666-4673-95c9-683960fb2939"
        )
    }

    #[test]
    fn test_verify_client_cert_invalid_signature() {
        assert!(verifier()
            .verify_client_cert(
                &certs::rustls_certificate(CERT_INVALID_SIGNATURE).unwrap(),
                &[],
                std::time::SystemTime::now(),
            )
            .is_err(),);
    }
}
