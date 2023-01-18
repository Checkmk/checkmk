// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
    let (connection, site_id) = find_site_for_ident(&mut registry, ident)?;

    renew_connection_cert(&site_id, connection, &renew_certificate_api)?;

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
            .get_mutable(&site_id)
            .ok_or_else(|| anyhow!("Couldn't find connection with site ID {}", site_id))?,
        site_id,
    ))
}

fn site_id_from_ident(registry: &config::Registry, ident: &str) -> AnyhowResult<site_spec::SiteID> {
    if let Ok(site_id) = site_spec::SiteID::from_str(ident) {
        return Ok(site_id);
    };

    let Ok(uuid) = uuid::Uuid::from_str(ident) else {
        bail!("Provided connection identifier '{}' is neither valid as site ID nor as UUID", ident);
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
    connection.trust.certificate = new_cert.client_cert;

    Ok(())
}

pub fn daemon(
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
        registry.save()?;
        thread::sleep(Duration::from_secs(60 * 60 * 24).saturating_sub(begin.elapsed()));
    }
}

fn renew_all_certificates(
    registry: &mut config::Registry,
    renew_certificate_api: &impl agent_receiver_api::RenewCertificate,
) -> AnyhowResult<()> {
    for (site_id, connection) in registry.standard_connections_mut() {
        conditionally_renew_connection_cert(site_id, connection, renew_certificate_api)?;
    }
    Ok(())
}

fn conditionally_renew_connection_cert(
    site_id: &site_spec::SiteID,
    connection: &mut config::TrustedConnectionWithRemote,
    renew_certificate_api: &impl agent_receiver_api::RenewCertificate,
) -> AnyhowResult<()> {
    let raw_cert = certs::rustls_certificate(&connection.trust.certificate)
        .unwrap()
        .0;
    let (_rem, cert) = x509_parser::parse_x509_certificate(&raw_cert)?;
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
