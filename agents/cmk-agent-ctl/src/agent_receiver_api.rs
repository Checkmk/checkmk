// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config;
use crate::certs;
use anyhow::{anyhow, Context, Error as AnyhowError, Result as AnyhowResult};
use http::StatusCode;
use serde::{Deserialize, Serialize};
use string_enum::StringEnum;

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

#[derive(Serialize)]
struct RegistrationWithALBody {
    uuid: String,
    agent_labels: config::AgentLabels,
}

pub fn pairing(
    server_address: &str,
    root_cert: Option<&str>,
    csr: String,
    credentials: &config::Credentials,
) -> AnyhowResult<PairingResponse> {
    let response = certs::client(root_cert)?
        .post(format!("https://{}/pairing", server_address))
        .basic_auth(&credentials.username, Some(&credentials.password))
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
    credentials: &config::Credentials,
    uuid: &str,
    host_name: &str,
) -> AnyhowResult<()> {
    check_response_204(
        certs::client(Some(root_cert))?
            .post(format!("https://{}/register_with_hostname", server_address))
            .basic_auth(&credentials.username, Some(&credentials.password))
            .json(&RegistrationWithHNBody {
                uuid: String::from(uuid),
                host_name: String::from(host_name),
            })
            .send()?,
    )
}

pub fn register_with_agent_labels(
    server_address: &str,
    root_cert: &str,
    credentials: &config::Credentials,
    uuid: &str,
    agent_labels: &config::AgentLabels,
) -> AnyhowResult<()> {
    check_response_204(
        certs::client(Some(root_cert))?
            .post(format!("https://{}/register_with_labels", server_address))
            .basic_auth(&credentials.username, Some(&credentials.password))
            .json(&RegistrationWithALBody {
                uuid: String::from(uuid),
                agent_labels: agent_labels.clone(),
            })
            .send()?,
    )
}

fn encode_pem_cert_base64(cert: &str) -> AnyhowResult<String> {
    Ok(base64::encode_config(
        certs::parse_pem(cert)?.contents,
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
        certs::client(Some(root_cert))?
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

#[derive(StringEnum)]
pub enum HostStatus {
    /// `new`
    New,
    /// `pending`
    Pending,
    /// `declined`
    Declined,
    /// `ready`
    Ready,
    /// `discoverable`
    Discoverable,
}

#[derive(Deserialize)]
pub struct StatusResponse {
    pub hostname: Option<String>,
    pub status: Option<HostStatus>,
    #[serde(rename = "type")]
    pub connection_type: Option<config::ConnectionType>,
    pub message: Option<String>,
}

#[derive(thiserror::Error, Debug)]
pub enum StatusError {
    #[error(transparent)]
    // Note: we deliberately do not use '#[from] reqwest::Error' here because we do not want to
    // create this variant from any reqwest::Error (otherwise, we could for example write
    // 'response.text()?', which would then result in this variant)
    ConnectionRefused(reqwest::Error),

    #[error("Client certificate invalid")]
    CertificateInvalid,

    #[error(transparent)]
    UnspecifiedError(#[from] AnyhowError),
}

pub fn status(
    server_address: &str,
    root_cert: &str,
    uuid: &str,
    certificate: &str,
) -> Result<StatusResponse, StatusError> {
    let response = certs::client(Some(root_cert))?
        .get(format!(
            "https://{}/registration_status/{}",
            server_address, uuid
        ))
        .header("certificate", encode_pem_cert_base64(certificate)?)
        .send()
        .map_err(StatusError::ConnectionRefused)?;

    match response.status() {
        StatusCode::OK => Ok(serde_json::from_str::<StatusResponse>(
            &response.text().context("Failed to obtain response body")?,
        )
        .context("Failed to deserialize response body")?),
        StatusCode::UNAUTHORIZED => Err(StatusError::CertificateInvalid),
        _ => Err(StatusError::UnspecifiedError(anyhow!(format!(
            "{}",
            response
                .json::<serde_json::Value>()
                .context("Failed to deserialize response body to JSON")?
                .get("detail")
                .context("Unknown failure")?
        )))),
    }
}
