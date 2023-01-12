// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{
    agent_receiver_api::{self, RenewCertificate},
    certs, config, site_spec,
};
use anyhow::{bail, Result as AnyhowResult};
use std::str::FromStr;

pub fn renew_certificate(
    registry: &mut config::Registry,
    renew_certificate_config: config::RenewCertificateConfig,
) -> AnyhowResult<()> {
    let Ok(site_id) = site_spec::SiteID::from_str(&renew_certificate_config.connection) else {
        bail!("Not a connection id");
    };
    let Some(connection) = registry.get_mutable(&site_id) else {
        bail!("Couldn't find connection with id {}", site_id);
    };
    let uuid = connection.trust.uuid;
    let url = site_spec::make_site_url(&site_id, &connection.receiver_port)?;
    let (csr, private_key) = certs::make_csr(&uuid.to_string())?;
    let receiver_api = agent_receiver_api::Api {
        use_proxy: renew_certificate_config.use_proxy,
    };
    let new_cert = receiver_api.renew_certificate(&url, &connection.trust, csr)?;
    connection.trust.private_key = private_key;
    connection.trust.certificate = new_cert.client_cert;

    registry.save()?;
    Ok(())
}
