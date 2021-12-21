// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{agent_receiver_api, certs, config};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use uuid::Uuid;

fn display_agent_receiver_cert(server: &str) -> AnyhowResult<()> {
    let pem_str = certs::fetch_server_cert_pem(server)?;
    let pem = certs::parse_pem(&pem_str)?;
    let x509 = pem.parse_x509()?;
    let validity = x509.validity();

    println!(
        "Attempting to register at {}. Server certificate details:\n",
        server
    );
    println!("PEM-encoded certificate:\n{}", pem_str);
    println!("Issued by:\n\t{}", certs::join_common_names(x509.issuer()));
    println!("Issued to:\n\t{}", certs::join_common_names(x509.subject()));
    println!(
        "Validity:\n\tFrom {}\n\tTo   {}",
        validity.not_before.to_rfc2822(),
        validity.not_after.to_rfc2822(),
    );
    Ok(())
}

fn interactive_trust_agent_receiver(server: &str) -> AnyhowResult<()> {
    display_agent_receiver_cert(server)?;
    println!();
    match requestty::prompt_one(
        requestty::Question::confirm("trust_server")
            .message("Do you want to establish this connection?")
            .build(),
    ) {
        Ok(requestty::Answer::Bool(yes_or_no)) => match yes_or_no {
            true => Ok(()),
            false => Err(anyhow!(format!(
                "Cannot continue without trusting {}",
                server
            ))),
        },
        Ok(answer) => Err(anyhow!(format!(
            "Asking if {} should be trusted failed, got answer: {:#?}",
            server, answer,
        ))),
        Err(err) => Err(anyhow!(
            "Asking if {} should be trusted failed: {:#?}",
            server,
            err,
        )),
    }
}

fn registration_server_cert(config: &config::RegistrationConfig) -> AnyhowResult<Option<&str>> {
    match &config.root_certificate {
        Some(cert) => {
            if config.trust_server_cert {
                eprintln!(
                    "Blind trust of server certificate enabled but a root certificate was \
                     given in the configuration and will be used to verify the server certificate."
                );
            }
            Ok(Some(cert.as_str()))
        }
        None => {
            if !config.trust_server_cert {
                interactive_trust_agent_receiver(&config.agent_receiver_address)?;
            }
            Ok(None)
        }
    }
}

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
    mut registry: config::Registry,
) -> AnyhowResult<()> {
    // TODO: what if registration_state.contains_key(agent_receiver_address) (already registered)?
    let uuid = Uuid::new_v4().to_string();
    let (csr, private_key) = certs::make_csr(&uuid).context("Error creating CSR.")?;
    let pairing_response = agent_receiver_api::pairing(
        &config.agent_receiver_address,
        registration_server_cert(&config)?,
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

    registry.register_connection(
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

    registry.save()?;

    Ok(())
}
