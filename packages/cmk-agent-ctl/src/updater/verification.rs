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

/// The configured signature keys as PEM blocks.
///
/// Separate from [`certificates`] because a parsed certificate borrows the DER
/// of its block: the blocks have to outlive it.
///
/// A key that is no PEM block is dropped with a warning. One unusable entry of
/// the baked configuration must not disable the others.
pub fn pem_blocks(keys: &[String]) -> Vec<x509_parser::pem::Pem> {
    keys.iter()
        .filter_map(|key| match certs::parse_pem(key) {
            Ok(block) => Some(block),
            Err(error) => {
                log::warn!("Ignoring a configured signature key that is no PEM block: {error:#}");
                None
            }
        })
        .collect()
}

/// The certificates of `blocks`, in the form [`verify`] takes them.
///
/// A block that is no certificate is dropped with a warning, for the reason
/// given at [`pem_blocks`].
pub fn certificates(blocks: &[x509_parser::pem::Pem]) -> Vec<X509Certificate<'_>> {
    blocks
        .iter()
        .filter_map(|block| match block.parse_x509() {
            Ok(certificate) => Some(certificate),
            Err(error) => {
                log::warn!("Ignoring a configured signature key that is no certificate: {error}");
                None
            }
        })
        .collect()
}

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
        let Some((public_key_der, subject)) = trusted_certificate_data(entry, local_certificates)
        else {
            return false;
        };

        let Ok(public_key) = rsa::RsaPublicKey::from_public_key_der(&public_key_der) else {
            log::warn!("Certificate {subject} has no RSA key");
            return false;
        };

        let Ok(decoded) = BASE64_STANDARD.decode(entry.signature.as_bytes()) else {
            log::warn!("Signature for certificate {subject} is not base64");
            return false;
        };

        let Ok(signature) = Signature::try_from(decoded.as_slice()) else {
            return false;
        };

        if VerifyingKey::<Sha256>::new(public_key)
            .verify(bytes, &signature)
            .is_err()
        {
            log::warn!("Signature for certificate {subject} does not match the package");
            return false;
        }

        true
    });

    if result.is_none() {
        return Err(Error::msg("Could not verify the signature of this package"));
    }

    Ok(())
}

/// Whether any of `signatures` carries a certificate this host trusts.
///
/// Answers whether [`verify`] could accept a package at all, which is worth
/// knowing before the package is downloaded. The signatures themselves are not
/// checked - a trusted, unexpired certificate is as far as this goes.
///
/// Every certificate it rejects is logged with its reason: when this says no,
/// [`verify`] never runs, so this is the only place that can tell which of the
/// certificates the site sent was unusable and why.
pub fn any_certificate_is_trusted(
    signatures: &[AgentSignature],
    local_certificates: &[X509Certificate],
) -> bool {
    signatures
        .iter()
        .any(|entry| trusted_certificate_data(entry, local_certificates).is_some())
}

/// The public key DER and subject of `entry`'s certificate, if this host trusts
/// it; `None` with the reason logged otherwise. The signature is not checked.
///
/// Both checks use this one, so they cannot disagree about which certificate is
/// acceptable: [`any_certificate_is_trusted`] runs before the download,
/// [`verify`] after it.
///
/// Both values are copies - they borrow the PEM block owned here - trading a
/// few hundred bytes for not parsing that block twice.
fn trusted_certificate_data(
    entry: &AgentSignature,
    local_certificates: &[X509Certificate],
) -> Option<(Vec<u8>, String)> {
    let Ok(pem) = certs::parse_pem(&entry.certificate) else {
        log::warn!("Ignoring a site certificate that is not PEM");
        return None;
    };
    let Ok(certificate) = pem.parse_x509() else {
        log::warn!("Ignoring a site certificate that cannot be parsed");
        return None;
    };

    if certificate.validity().not_after < ASN1Time::now() {
        log::warn!("Certificate {} has expired", certificate.subject());
        return None;
    }

    if !local_certificates.contains(&certificate) {
        log::warn!(
            "Certificate {} is not available locally",
            certificate.subject()
        );
        return None;
    }

    Some((
        certificate.public_key().raw.to_vec(),
        certificate.subject().to_string(),
    ))
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

    #[test]
    fn test_a_trusted_certificate_is_found() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            // No signature of [`RAW_PACKAGE`]: only the certificate counts here.
            signature: String::from("not a signature"),
        };

        assert!(any_certificate_is_trusted(
            &[signature],
            &[x509(&certificate)]
        ));
    }

    #[test]
    fn test_no_certificate_is_trusted_without_signatures() {
        let certificate = certificate("signer", 2000, 4000);

        assert!(!any_certificate_is_trusted(&[], &[x509(&certificate)]));
    }

    #[test]
    fn test_no_certificate_is_trusted_without_local_certificates() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        assert!(!any_certificate_is_trusted(&[signature], &[]));
    }

    #[test]
    fn test_an_expired_certificate_is_not_trusted() {
        let certificate = certificate("signer", 2000, 2001);
        let signature = AgentSignature {
            certificate: pem(&certificate),
            signature: signature(),
        };

        assert!(!any_certificate_is_trusted(
            &[signature],
            &[x509(&certificate)]
        ));
    }

    /// Both certificates are for the same key, as in
    /// [`test_certificate_that_is_not_local_is_rejected`]: only the missing
    /// local certificate makes the difference.
    #[test]
    fn test_a_certificate_that_is_not_local_is_not_trusted() {
        let site_certificate = certificate("site", 2000, 4000);
        let local_certificate = certificate("local", 2000, 4000);
        let signature = AgentSignature {
            certificate: pem(&site_certificate),
            signature: signature(),
        };

        assert!(!any_certificate_is_trusted(
            &[signature],
            &[x509(&local_certificate)]
        ));
    }

    /// One trusted certificate among untrusted ones is enough, the way one
    /// valid signature is enough for [`verify`].
    #[test]
    fn test_one_trusted_certificate_among_others_is_enough() {
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

        assert!(any_certificate_is_trusted(
            &signatures,
            &[x509(&expired), x509(&valid)]
        ));
    }

    #[test]
    fn test_a_corrupt_certificate_is_not_trusted() {
        let certificate = certificate("signer", 2000, 4000);
        let signature = AgentSignature {
            // Valid PEM, but the content is the text "not a certificate".
            certificate: String::from(
                "-----BEGIN CERTIFICATE-----\nbm90IGEgY2VydGlmaWNhdGU=\n-----END CERTIFICATE-----\n",
            ),
            signature: signature(),
        };

        assert!(!any_certificate_is_trusted(
            &[signature],
            &[x509(&certificate)]
        ));
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
