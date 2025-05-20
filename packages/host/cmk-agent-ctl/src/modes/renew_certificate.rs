// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{agent_receiver_api, certs, config, constants, misc, site_spec};
use anyhow::{anyhow, bail, Result as AnyhowResult};
use log::{debug, info, warn};
use std::str::FromStr;
use std::thread;
use std::time::{Duration, Instant};
use x509_parser;

pub fn renew_certificate(
    mut registry: config::Registry,
    ident: &str,
    client_config: config::ClientConfig,
) -> AnyhowResult<()> {
    let renew_certificate_api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    _renew_certificate(&mut registry, ident, &renew_certificate_api)
}

fn _renew_certificate(
    registry: &mut config::Registry,
    ident: &str,
    renew_certificate_api: &impl agent_receiver_api::RenewCertificate,
) -> AnyhowResult<()> {
    let (connection, site_id) = find_site_for_ident(registry, ident)?;

    renew_connection_cert(&site_id, connection, renew_certificate_api)?;

    registry.save()?;
    Ok(())
}

fn find_site_for_ident<'reg>(
    registry: &'reg mut config::Registry,
    ident: &str,
) -> AnyhowResult<(
    &'reg mut config::TrustedConnectionWithRemote,
    site_spec::SiteID,
)> {
    let site_id = site_id_from_ident(registry, ident)?;
    Ok((
        registry
            .get_connection_as_mut(&site_id)
            .ok_or_else(|| anyhow!("Couldn't find connection with site ID {}", site_id))?,
        site_id,
    ))
}

fn site_id_from_ident(registry: &config::Registry, ident: &str) -> AnyhowResult<site_spec::SiteID> {
    if let Ok(site_id) = site_spec::SiteID::from_str(ident) {
        return Ok(site_id);
    };

    let Ok(uuid) = uuid::Uuid::from_str(ident) else {
        bail!(
            "Provided connection identifier '{}' is neither valid as site ID nor as UUID",
            ident
        );
    };
    registry
        .retrieve_standard_connection_by_uuid(&uuid)
        .ok_or_else(|| anyhow!("Couldn't find connection with UUID '{}'", ident))
}

fn renew_connection_cert(
    site_id: &site_spec::SiteID,
    connection: &mut config::TrustedConnectionWithRemote,
    renew_certificate_api: &impl agent_receiver_api::RenewCertificate,
) -> AnyhowResult<()> {
    let url = site_spec::make_site_url(site_id, &connection.receiver_port)?;
    let (csr, private_key) = certs::make_csr(&connection.trust.uuid.to_string())?;
    let new_cert = renew_certificate_api.renew_certificate(&url, &connection.trust, csr)?;
    connection.trust.private_key = private_key;
    connection.trust.certificate = new_cert.agent_cert;

    Ok(())
}

pub fn fn_thread(
    mut registry: config::Registry,
    client_config: config::ClientConfig,
) -> AnyhowResult<()> {
    misc::sleep_randomly();
    let renew_certificate_api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    loop {
        debug!("Checking registered connections for certificate expiry.");
        registry.refresh()?;
        let begin = Instant::now();
        if let Err(error) = renew_all_certificates(&mut registry, &renew_certificate_api) {
            warn!("Error running renew-certificate cycle. ({})", error);
        };
        thread::sleep(Duration::from_secs(60 * 60 * 24).saturating_sub(begin.elapsed()));
    }
}

fn renew_all_certificates(
    registry: &mut config::Registry,
    renew_certificate_api: &impl agent_receiver_api::RenewCertificate,
) -> AnyhowResult<()> {
    if registry.is_empty() {
        // if the registry is empty, we mustn't save, otherwise we might remove the legacy pull marker
        return Ok(());
    }
    for (site_id, connection) in registry.get_standard_connections_as_mut() {
        conditionally_renew_connection_cert(site_id, connection, renew_certificate_api)?;
    }
    registry.save()?;
    Ok(())
}

fn conditionally_renew_connection_cert(
    site_id: &site_spec::SiteID,
    connection: &mut config::TrustedConnectionWithRemote,
    renew_certificate_api: &impl agent_receiver_api::RenewCertificate,
) -> AnyhowResult<()> {
    let cert = certs::rustls_certificate(&connection.trust.certificate)?;
    let (_rem, cert) = x509_parser::parse_x509_certificate(cert.as_ref())?;
    let Some(validity) = cert.validity().time_to_expiration() else {
        warn!("Certificate for {} expired, can't renew", site_id);
        return Ok(());
    };

    if validity < Duration::from_secs(constants::CERT_VALIDITY_LOWER_LIMIT) {
        info!(
            "Certificate for {} is about to expire (validity < 45 days), renewing...",
            site_id
        );
    } else if validity > Duration::from_secs(constants::CERT_VALIDITY_UPPER_LIMIT) {
        info!(
            "Certificate for {} has too long validity (> 500 years), renewing...",
            site_id
        );
    } else {
        return Ok(());
    }

    renew_connection_cert(site_id, connection, renew_certificate_api)
}
#[cfg(test)]
mod test_renew_certificate {

    use crate::config::Registry;
    use crate::configuration::config::test_helpers::TestRegistry;
    use crate::modes::renew_certificate::*;
    use openssl;
    use openssl::asn1::Asn1Time;
    use openssl::bn::{BigNum, MsbOption};
    use openssl::hash::MessageDigest;
    use openssl::pkey::PKey;
    use openssl::rsa::Rsa;
    use openssl::x509::extension::{BasicConstraints, KeyUsage, SubjectKeyIdentifier};
    use openssl::x509::{X509NameBuilder, X509};
    use std::convert::From;
    use std::time::{SystemTime, UNIX_EPOCH};

    // Taken from openssl::examples with minor adaptions
    fn mk_ca_cert(days_valid: u32) -> AnyhowResult<String> {
        let rsa = Rsa::generate(2048)?;
        let key_pair = PKey::from_rsa(rsa)?;

        let mut x509_name = X509NameBuilder::new()?;
        x509_name.append_entry_by_text("CN", "test")?;
        let x509_name = x509_name.build();

        let mut cert_builder = X509::builder()?;
        cert_builder.set_version(2)?;
        let serial_number = {
            let mut serial = BigNum::new()?;
            serial.rand(159, MsbOption::MAYBE_ZERO, false)?;
            serial.to_asn1_integer()?
        };
        cert_builder.set_serial_number(&serial_number)?;
        cert_builder.set_subject_name(&x509_name)?;
        cert_builder.set_issuer_name(&x509_name)?;
        cert_builder.set_pubkey(&key_pair)?;
        let not_before = Asn1Time::days_from_now(0)?;
        cert_builder.set_not_before(&not_before)?;

        // We have to calculate the not_after time like this, because Asn1Time::days_from_now()
        // wants to calculate the resulting seconds (at least on Windows) as u32, which is not
        // enough for our 600 years.
        let not_after = {
            let na = SystemTime::now() + Duration::from_secs((days_valid as u64) * 24 * 60 * 60);
            Asn1Time::from_unix(na.duration_since(UNIX_EPOCH)?.as_secs().try_into()?)?
        };
        cert_builder.set_not_after(&not_after)?;

        cert_builder.append_extension(BasicConstraints::new().critical().ca().build()?)?;
        cert_builder.append_extension(
            KeyUsage::new()
                .critical()
                .key_cert_sign()
                .crl_sign()
                .build()?,
        )?;

        let subject_key_identifier =
            SubjectKeyIdentifier::new().build(&cert_builder.x509v3_context(None, None))?;
        cert_builder.append_extension(subject_key_identifier)?;

        cert_builder.sign(&key_pair, MessageDigest::sha256())?;
        let cert = cert_builder.build();

        Ok(String::from_utf8(cert.to_pem().unwrap())?)
    }

    struct TestApi {}

    impl agent_receiver_api::RenewCertificate for TestApi {
        fn renew_certificate(
            &self,
            _base_url: &reqwest::Url,
            connection: &config::TrustedConnection,
            _csr: String,
        ) -> AnyhowResult<agent_receiver_api::RenewCertificateResponse> {
            Ok(agent_receiver_api::RenewCertificateResponse {
                agent_cert: format!("new_cert_for_{}", connection.uuid),
            })
        }
    }

    struct RegistryFixture {
        test_registry: TestRegistry,
        push_uuid: uuid::Uuid,
        pull_uuid: uuid::Uuid,
        imported_uuid: uuid::Uuid,
    }

    impl RegistryFixture {
        fn new() -> Self {
            let test_registry = TestRegistry::new().fill_registry();
            let reg = &test_registry.registry;
            let push_uuid = reg.get_push_connections().next().unwrap().1.trust.uuid;
            let pull_uuid = reg
                .get_standard_pull_connections()
                .next()
                .unwrap()
                .1
                .trust
                .uuid;
            let imported_uuid = reg.get_imported_pull_connections().next().unwrap().uuid;
            Self {
                test_registry,
                push_uuid,
                pull_uuid,
                imported_uuid,
            }
        }
    }

    #[test]
    fn test_renew_certificate_push() {
        let mut r = RegistryFixture::new();
        let registry = &mut r.test_registry.registry;
        _renew_certificate(registry, &r.push_uuid.to_string(), &TestApi {}).unwrap();
        assert!(
            registry
                .get_push_connections()
                .next()
                .unwrap()
                .1
                .trust
                .certificate
                == format!("new_cert_for_{}", r.push_uuid)
        );
    }

    #[test]
    fn test_renew_certificate_pull() {
        let mut r = RegistryFixture::new();
        let registry = &mut r.test_registry.registry;
        _renew_certificate(registry, "server/pull-site", &TestApi {}).unwrap();
        assert!(
            registry
                .get_standard_pull_connections()
                .next()
                .unwrap()
                .1
                .trust
                .certificate
                == format!("new_cert_for_{}", r.pull_uuid)
        );
    }

    #[test]
    fn test_renew_certificate_errors() {
        let mut r = RegistryFixture::new();
        let registry = &mut r.test_registry.registry;
        let test_api = TestApi {};
        assert!(_renew_certificate(registry, &r.imported_uuid.to_string(), &test_api).is_err());
        assert!(_renew_certificate(registry, "not_a_uuid", &test_api).is_err());
        assert!(_renew_certificate(registry, "unknown/site_id", &test_api).is_err());
    }

    fn new_trusted_connection_with_remote(cert: String) -> config::TrustedConnectionWithRemote {
        config::TrustedConnectionWithRemote {
            trust: new_trusted_connection(cert),
            receiver_port: 8000,
        }
    }

    fn new_trusted_connection(cert: String) -> config::TrustedConnection {
        config::TrustedConnection {
            uuid: uuid::Uuid::new_v4(),
            private_key: String::from("private_key"),
            certificate: cert,
            root_cert: String::from("root_cert"),
        }
    }

    struct AllFixture {
        test_registry: TestRegistry,
        cert_too_short: String,
        cert_ok: String,
    }

    impl AllFixture {
        fn new() -> Self {
            let cert_too_short = mk_ca_cert(10).unwrap();
            let cert_too_long = mk_ca_cert(365 * 600).unwrap();
            let cert_ok = mk_ca_cert(100).unwrap();

            let test_registry = TestRegistry::new()
                .add_connection(
                    &config::ConnectionMode::Push,
                    "server/push-site_1",
                    new_trusted_connection_with_remote(cert_too_short.clone()),
                )
                .add_connection(
                    &config::ConnectionMode::Push,
                    "server/push-site_2",
                    new_trusted_connection_with_remote(cert_too_long.clone()),
                )
                .add_connection(
                    &config::ConnectionMode::Pull,
                    "server/pull-site_1",
                    new_trusted_connection_with_remote(cert_too_long),
                )
                .add_connection(
                    &config::ConnectionMode::Pull,
                    "server/pull-site_2",
                    new_trusted_connection_with_remote(cert_ok.clone()),
                )
                .add_imported_connection(new_trusted_connection(cert_too_short.clone()));
            Self {
                test_registry,
                cert_too_short,
                cert_ok,
            }
        }
    }

    fn get_connection(registry: &Registry, site_name: &str) -> config::TrustedConnection {
        registry
            .get(&site_spec::SiteID::from_str(site_name).unwrap())
            .unwrap()
            .trust
            .clone()
    }

    #[test]
    fn test_renew_all_certificates() -> AnyhowResult<()> {
        let mut a = AllFixture::new();
        let registry = &mut a.test_registry.registry;
        renew_all_certificates(registry, &TestApi {})?;

        let conn = get_connection(registry, "server/push-site_1");
        assert!(conn.certificate == format!("new_cert_for_{}", conn.uuid));

        let conn = get_connection(registry, "server/push-site_2");
        assert!(conn.certificate == format!("new_cert_for_{}", conn.uuid));

        let conn = get_connection(registry, "server/pull-site_1");
        assert!(conn.certificate == format!("new_cert_for_{}", conn.uuid));

        let conn = get_connection(registry, "server/pull-site_2");
        assert!(conn.certificate == a.cert_ok);

        let conn = &registry.get_imported_pull_connections().next().unwrap();
        assert!(conn.certificate == a.cert_too_short);
        Ok(())
    }

    #[test]
    fn test_renew_all_certificates_legacy_pull_mode() -> AnyhowResult<()> {
        let mut r = TestRegistry::new();
        let reg = &mut r.registry;
        reg.activate_legacy_pull()?;
        renew_all_certificates(reg, &TestApi {})?;
        assert!(reg.is_legacy_pull_active());
        Ok(())
    }
}
