// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{certs, tls_server};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use http::StatusCode;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
struct PairingBody {
    csr: String,
}

#[derive(Deserialize)]
pub struct PairingResponse {
    pub root_cert: String,
    pub client_cert: String,
}

#[derive(Serialize)]
struct RegistrationWithHNBody {
    uuid: String,
    host_name: String,
}

pub fn pairing(
    server_address: &str,
    root_cert: Option<String>,
    csr: String,
    credentials: &str,
) -> AnyhowResult<PairingResponse> {
    let response = certs::client(root_cert.map(|cert_str| cert_str.into_bytes()))?
        .post(format!("https://{}/pairing", server_address))
        .header("authentication", format!("Bearer {}", credentials))
        .json(&PairingBody { csr })
        .send()?;
    let status = response.status();
    // Get the text() instead of directly calling json(), because both methods would consume the response.
    // Otherwise, in case of a json parsing error, we would have no information about the body.
    let body = response.text()?;

    if let StatusCode::OK = status {
        Ok(serde_json::from_str::<PairingResponse>(&body)
            .context(format!("Error parsing this response body: {}", body))?)
    } else {
        Err(anyhow!("Request failed with code {}: {}", status, body))
    }
}

fn check_response_204(response: reqwest::blocking::Response) -> AnyhowResult<()> {
    if let StatusCode::NO_CONTENT = response.status() {
        Ok(())
    } else {
        Err(anyhow!(
            "Request failed with code {}: {}",
            response.status(),
            response.text().unwrap_or_else(|_| String::from(""))
        ))
    }
}

pub fn register_with_hostname(
    server_address: &str,
    root_cert: &str,
    credentials: &str,
    uuid: &str,
    host_name: &str,
) -> AnyhowResult<()> {
    check_response_204(
        certs::client(Some(String::from(root_cert).into_bytes()))?
            .post(format!("https://{}/register_with_hostname", server_address))
            .header("authentication", format!("Bearer {}", credentials))
            .json(&RegistrationWithHNBody {
                uuid: String::from(uuid),
                host_name: String::from(host_name),
            })
            .send()?,
    )
}

fn encode_pem_cert_base64(cert: &str) -> AnyhowResult<String> {
    Ok(base64::encode_config(
        tls_server::certificate(&mut String::from(cert).as_bytes())?.0,
        base64::URL_SAFE,
    ))
}

pub fn agent_data(
    agent_receiver_address: &str,
    root_cert: &str,
    uuid: &str,
    certificate: &str,
    monitoring_data: &[u8],
) -> AnyhowResult<()> {
    check_response_204(
        certs::client(Some(String::from(root_cert).into_bytes()))?
            .post(format!(
                "https://{}/agent_data/{}",
                agent_receiver_address, uuid,
            ))
            .header("certificate", encode_pem_cert_base64(certificate)?)
            .multipart(
                reqwest::blocking::multipart::Form::new().part(
                    "monitoring_data",
                    reqwest::blocking::multipart::Part::bytes(monitoring_data.to_owned())
                        // Note: We need to set the file name, otherwise the request won't have the
                        // right format. However, the value itself does not matter.
                        .file_name("agent_data"),
                ),
            )
            .send()?,
    )
}
