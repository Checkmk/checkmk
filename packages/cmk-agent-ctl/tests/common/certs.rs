// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use rcgen::{
    BasicConstraints, Certificate, CertificateParams, DistinguishedName, DnType, Ia5String, IsCa,
    KeyPair, KeyUsagePurpose, SanType, PKCS_ECDSA_P256_SHA256,
};

#[derive(Clone)]
pub struct X509Certs {
    pub ca_cert: Vec<u8>,
    pub controller_private_key: Vec<u8>,
    pub controller_cert: Vec<u8>,
    pub receiver_private_key: Vec<u8>,
    pub receiver_cert: Vec<u8>,
}

impl X509Certs {
    pub fn new(ca_name: &str, receiver_name: &str, controller_uuid: &str) -> X509Certs {
        let (ca_cert, ca_key_pair) = mk_ca_cert(ca_name).unwrap();
        let (controller_cert, controller_key_pair) =
            mk_ca_signed_cert(&ca_cert, &ca_key_pair, controller_uuid).unwrap();
        let (receiver_cert, receiver_key_pair) =
            mk_ca_signed_cert(&ca_cert, &ca_key_pair, receiver_name).unwrap();

        X509Certs {
            ca_cert: cert_pem(&ca_cert),
            controller_private_key: key_pem(&controller_key_pair),
            controller_cert: cert_pem(&controller_cert),
            receiver_private_key: key_pem(&receiver_key_pair),
            receiver_cert: cert_pem(&receiver_cert),
        }
    }
}

fn cert_pem(cert: &Certificate) -> Vec<u8> {
    pem_rfc7468::encode_string(
        "CERTIFICATE",
        pem_rfc7468::LineEnding::LF,
        cert.der().as_ref(),
    )
    .expect("failed to PEM-encode test certificate")
    .into_bytes()
}

fn key_pem(key_pair: &KeyPair) -> Vec<u8> {
    pem_rfc7468::encode_string(
        "PRIVATE KEY",
        pem_rfc7468::LineEnding::LF,
        &key_pair.serialize_der(),
    )
    .expect("failed to PEM-encode test private key")
    .into_bytes()
}

fn base_params(cn: &str) -> CertificateParams {
    let mut params = CertificateParams::default();
    params.distinguished_name = DistinguishedName::new();
    params.distinguished_name.push(DnType::CommonName, cn);
    params.not_before = time::OffsetDateTime::now_utc();
    params.not_after = params.not_before + time::Duration::days(365);
    params
}

// Make a CA certificate and private key
fn mk_ca_cert(cn: &str) -> Result<(Certificate, KeyPair), rcgen::Error> {
    let key_pair = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256)?;
    let mut params = base_params(cn);
    params.is_ca = IsCa::Ca(BasicConstraints::Unconstrained);
    params.key_usages = vec![KeyUsagePurpose::KeyCertSign, KeyUsagePurpose::CrlSign];
    let cert = params.self_signed(&key_pair)?;
    Ok((cert, key_pair))
}

// Make a certificate and private key signed by the given CA cert and private key
fn mk_ca_signed_cert(
    ca_cert: &Certificate,
    ca_key_pair: &KeyPair,
    cn: &str,
) -> Result<(Certificate, KeyPair), rcgen::Error> {
    let key_pair = KeyPair::generate_for(&PKCS_ECDSA_P256_SHA256)?;
    let mut params = base_params(cn);
    params.key_usages = vec![
        KeyUsagePurpose::ContentCommitment,
        KeyUsagePurpose::DigitalSignature,
        KeyUsagePurpose::KeyEncipherment,
    ];
    params.subject_alt_names = vec![SanType::DnsName(Ia5String::try_from(cn.to_string())?)];
    let cert = params.signed_by(&key_pair, ca_cert, ca_key_pair)?;
    Ok((cert, key_pair))
}
