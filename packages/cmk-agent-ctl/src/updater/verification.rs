// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Verification of an agent package against its signatures and the local
//! certificates.

use crate::agent_receiver_api::AgentSignature;
use crate::certs;
use anyhow::{Error, Result as AnyhowResult};
use base64::{engine::general_purpose::STANDARD as BASE64_STANDARD, Engine};
use rsa::pkcs1v15::{Signature, VerifyingKey};
use rsa::pkcs8::DecodePublicKey;
use rsa::signature::Verifier;
use sha2::Sha256;
use x509_parser::certificate::X509Certificate;
use x509_parser::prelude::ASN1Time;

/// Check `bytes` against the signatures the site delivered with them.
///
/// # Errors
///
/// If none of `signatures` is a valid signature of `bytes` under one of
/// `local_certificates`.
pub fn verify(
    bytes: &[u8],
    signatures: &[AgentSignature],
    local_certificates: &[X509Certificate],
) -> AnyhowResult<()> {
    let result = signatures.iter().find(|entry| {
        let Ok(pem) = certs::parse_pem(&entry.certificate) else {
            log::warn!("Ignoring a site certificate that is not PEM");
            return false;
        };
        let Ok(certificate) = pem.parse_x509() else {
            log::warn!("Ignoring a site certificate that cannot be parsed");
            return false;
        };

        if certificate.validity().not_after < ASN1Time::now() {
            log::warn!("Certificate {} has expired", certificate.subject());
            return false;
        }

        if !local_certificates.contains(&certificate) {
            log::warn!(
                "Certificate {} is not available locally",
                certificate.subject()
            );
            return false;
        }

        let Ok(public_key) = rsa::RsaPublicKey::from_public_key_der(certificate.public_key().raw)
        else {
            log::warn!("Certificate {} has no RSA key", certificate.subject());
            return false;
        };

        let Ok(decoded) = BASE64_STANDARD.decode(entry.signature.as_bytes()) else {
            log::warn!(
                "Signature for certificate {} is not base64",
                certificate.subject()
            );
            return false;
        };

        let Ok(signature) = Signature::try_from(decoded.as_slice()) else {
            return false;
        };

        if VerifyingKey::<Sha256>::new(public_key)
            .verify(bytes, &signature)
            .is_err()
        {
            log::warn!(
                "Signature for certificate {} does not match the package",
                certificate.subject()
            );
            return false;
        }

        true
    });

    if result.is_none() {
        return Err(Error::msg("Could not verify the signature of this package"));
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const RAW_PACKAGE: &[u8] = b"an agent package";

    #[test]
    fn test_package_signed_with_a_local_certificate_is_accepted() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_ok());
    }

    #[test]
    fn test_one_valid_signature_is_enough() {
        let expired = certificate("expired", 2000, 2001);
        let valid = certificate("valid", 2000, 4000);
        let signatures = [
            AgentSignature {
                certificate: pem(&expired),
                signature: signature(),
            },
            AgentSignature {
                certificate: pem(&valid),
                signature: signature(),
            },
        ];

        let result = verify(RAW_PACKAGE, &signatures, &[x509(&expired), x509(&valid)]);

        assert!(result.is_ok());
    }

    /// Only the end of the validity is checked, as in the Python updater.
    #[test]
    fn test_certificate_that_is_not_valid_yet_is_accepted() {
        let certificate = certificate("signer", 3000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_ok());
    }

    /// The certificates are compared as parsed certificates, so differences in
    /// the PEM text alone do not matter.
    #[test]
    fn test_certificate_with_an_extra_newline_is_accepted() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: format!("{}\n", pem(&certificate)),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_ok());
    }

    #[test]
    fn test_expired_certificate_is_rejected() {
        let certificate = certificate("signer", 2000, 2001);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_err());
    }

    /// Both certificates are for the same key, so the signature itself is
    /// valid: only the missing local certificate rejects it.
    #[test]
    fn test_certificate_that_is_not_local_is_rejected() {
        let site_certificate = certificate("site", 2000, 4000);
        let local_certificate = certificate("local", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&site_certificate),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&local_certificate)]);

        assert!(result.is_err());
    }

    #[test]
    fn test_corrupt_certificate_is_rejected() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            // Valid PEM, but the content is the text "not a certificate".
            certificate: String::from(
                "-----BEGIN CERTIFICATE-----\nbm90IGEgY2VydGlmaWNhdGU=\n-----END CERTIFICATE-----\n",
            ),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_err());
    }

    /// A valid certificate, but for an elliptic curve key.
    #[test]
    fn test_certificate_without_an_rsa_key_is_rejected() {
        use rcgen::{CertificateParams, KeyPair, PKCS_ECDSA_P256_SHA256};
        let key_pair = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256).unwrap();
        let certificate = CertificateParams::default()
            .self_signed(&key_pair)
            .unwrap()
            .der()
            .to_vec();
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_err());
    }

    #[test]
    fn test_tampered_package_is_rejected() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        let result = verify(
            b"a tampered agent package",
            &[signature],
            &[x509(&certificate)],
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_signature_that_is_not_base64_is_rejected() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: String::from("not base64"),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[x509(&certificate)]);

        assert!(result.is_err());
    }

    #[test]
    fn test_package_without_signatures_is_rejected() {
        let certificate = certificate("signer", 2000, 4000);

        let result = verify(RAW_PACKAGE, &[], &[x509(&certificate)]);

        assert!(result.is_err());
    }

    #[test]
    fn test_package_without_local_certificates_is_rejected() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        let result = verify(RAW_PACKAGE, &[signature], &[]);

        assert!(result.is_err());
    }

    /// The key behind every RSA test certificate. Generated once, because RSA
    /// key generation is slow in unoptimized builds.
    static KEY: std::sync::LazyLock<rsa::RsaPrivateKey> = std::sync::LazyLock::new(|| {
        rsa::RsaPrivateKey::new(&mut rand::thread_rng(), 2048).unwrap()
    });

    /// The bytes of a certificate for [`KEY`], valid from the start of
    /// `from_year` to the start of `until_year`. The same arguments give the
    /// same certificate.
    fn certificate(name: &str, from_year: i32, until_year: i32) -> Vec<u8> {
        use rcgen::{date_time_ymd, CertificateParams, DnType, KeyPair, PKCS_RSA_SHA256};
        use rsa::pkcs8::EncodePrivateKey;
        use rustls::pki_types::PrivatePkcs8KeyDer;

        let key_pair = KeyPair::from_pkcs8_der_and_sign_algo(
            &PrivatePkcs8KeyDer::from(KEY.to_pkcs8_der().unwrap().as_bytes()),
            &PKCS_RSA_SHA256,
        )
        .unwrap();
        let mut params = CertificateParams::default();
        params.distinguished_name.push(DnType::CommonName, name);
        params.not_before = date_time_ymd(from_year, 1, 1);
        params.not_after = date_time_ymd(until_year, 1, 1);
        params.self_signed(&key_pair).unwrap().der().to_vec()
    }

    /// The base64 signature of [`RAW_PACKAGE`] with [`KEY`], as the site sends it.
    fn signature() -> String {
        use rsa::pkcs1v15::SigningKey;
        use rsa::signature::{SignatureEncoding, Signer};

        BASE64_STANDARD.encode(
            SigningKey::<Sha256>::new(KEY.clone())
                .sign(RAW_PACKAGE)
                .to_bytes(),
        )
    }

    /// The certificate as PEM text, as the site sends it.
    fn pem(certificate: &[u8]) -> String {
        pem_rfc7468::encode_string("CERTIFICATE", pem_rfc7468::LineEnding::LF, certificate).unwrap()
    }

    /// The certificate parsed, as the host holds its local certificates.
    fn x509(certificate: &[u8]) -> X509Certificate<'_> {
        x509_parser::parse_x509_certificate(certificate).unwrap().1
    }
}
