// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::agent_receiver_api;
use super::certs;
use super::config;
use anyhow::{anyhow, Context, Result as AnyhowResult};
use uuid::Uuid;

fn post_registration_conn_type(
    server: &str,
    root_cert: &str,
    uuid: &str,
    client_cert: &str,
) -> AnyhowResult<config::ConnectionType> {
    loop {
        let status_resp = agent_receiver_api::status(server, root_cert, uuid, client_cert)?;
        if let Some(agent_receiver_api::HostStatus::Declined) = status_resp.status {
            return Err(anyhow!(
                "Registration declined by Checkmk instance, please check credentials"
            ));
        }
        if let Some(ct) = status_resp.connection_type {
            return Ok(ct);
        }
        println!("Waiting for registration to complete on Checkmk instance, sleeping 20 s");
        std::thread::sleep(std::time::Duration::from_secs(20));
    }
}

pub fn register(
    config: config::RegistrationConfig,
    mut registration: config::Registration,
) -> AnyhowResult<()> {
    // TODO: what if registration_state.contains_key(agent_receiver_address) (already registered)?
    let uuid = Uuid::new_v4().to_string();
    let server_cert = match &config.root_certificate {
        Some(cert) => Some(cert.as_str()),
        None => {
            let fetched_server_cert = certs::fetch_server_cert(&config.agent_receiver_address)
                .context("Error establishing trust with agent_receiver.")?;
            println!("Trusting \n\n{}\nfor pairing", &fetched_server_cert);
            None
        }
    };

    let (csr, private_key) = certs::make_csr(&uuid).context("Error creating CSR.")?;
    let pairing_response = agent_receiver_api::pairing(
        &config.agent_receiver_address,
        server_cert,
        csr,
        &config.credentials,
    )
    .context(format!(
        "Error pairing with {}",
        &config.agent_receiver_address
    ))?;

    match config.host_reg_data {
        config::HostRegistrationData::Name(hn) => {
            agent_receiver_api::register_with_hostname(
                &config.agent_receiver_address,
                &pairing_response.root_cert,
                &config.credentials,
                &uuid,
                &hn,
            )
            .context(format!(
                "Error registering with hostname at {}",
                &config.agent_receiver_address
            ))?;
        }
        config::HostRegistrationData::Labels(al) => {
            agent_receiver_api::register_with_agent_labels(
                &config.agent_receiver_address,
                &pairing_response.root_cert,
                &config.credentials,
                &uuid,
                &al,
            )
            .context(format!(
                "Error registering with agent labels at {}",
                &config.agent_receiver_address
            ))?;
        }
    }

    registration.register_connection(
        post_registration_conn_type(
            &config.agent_receiver_address,
            &pairing_response.root_cert,
            &uuid,
            &pairing_response.client_cert,
        )?,
        config.agent_receiver_address,
        config::Connection {
            uuid,
            private_key,
            certificate: pairing_response.client_cert,
            root_cert: pairing_response.root_cert,
        },
    )?;

    registration.save()?;

    Ok(())
}
