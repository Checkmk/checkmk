// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{agent_receiver_api, certs, config, site_spec};
use anyhow::{anyhow, bail, Result as AnyhowResult};
use std::str::FromStr;

pub fn renew_certificate(
    registry: &mut config::Registry,
    renew_certificate_config: config::RenewCertificateConfig,
) -> AnyhowResult<()> {
    let renew_certificate_api = agent_receiver_api::Api {
        use_proxy: renew_certificate_config.use_proxy,
    };
    let (connection, site_id) = find_site_for_ident(registry, &renew_certificate_config.ident)?;

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
