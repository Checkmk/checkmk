// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, config, types};
use anyhow::{anyhow, Context, Error as AnyhowError, Result as AnyhowResult};
use http::StatusCode;
use serde::{Deserialize, Serialize};
use serde_with::DisplayFromStr;
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

#[serde_with::serde_as]
#[derive(Serialize)]
struct RegistrationWithHNBody {
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    host_name: String,
}

#[serde_with::serde_as]
#[derive(Serialize)]
struct RegistrationWithALBody {
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    agent_labels: types::AgentLabels,
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

fn encode_pem_cert_base64(cert: &str) -> AnyhowResult<String> {
    Ok(base64::encode_config(
        certs::parse_pem(cert)?.contents,
        base64::URL_SAFE,
    ))
}

pub trait Pairing {
    fn pair(
        &self,
        base_url: &reqwest::Url,
        root_cert: Option<&str>,
        csr: String,
        credentials: &types::Credentials,
    ) -> AnyhowResult<PairingResponse>;
}

pub trait Registration {
    fn register_with_hostname(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        host_name: &str,
    ) -> AnyhowResult<()>;

    fn register_with_agent_labels(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        agent_labels: &types::AgentLabels,
    ) -> AnyhowResult<()>;
}

pub trait AgentData {
    fn agent_data(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        uuid: &uuid::Uuid,
        certificate: &str,
        compression_algorithm: &str,
        monitoring_data: &[u8],
    ) -> AnyhowResult<()>;
}

pub trait Status {
    fn status(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        uuid: &uuid::Uuid,
        certificate: &str,
    ) -> Result<StatusResponse, StatusError>;
}

pub struct Api {}

impl Api {
    fn endpoint_url(
        base_url: &reqwest::Url,
        endpoint_segments: &[&str],
    ) -> AnyhowResult<reqwest::Url> {
        // The API of reqwest::Url for extending existing urls is strange (reqwest::Url::join), see
        // also https://github.com/servo/rust-url/issues/333
        reqwest::Url::parse(
            &(base_url.to_string() + "/agent-receiver/" + &endpoint_segments.join("/")),
        )
        .context(format!(
            "Failed to construct agent receiver API endpoint URL from base URL {} and segments {}",
            base_url,
            endpoint_segments.join(", ")
        ))
    }
}

impl Pairing for Api {
    fn pair(
        &self,
        base_url: &reqwest::Url,
        root_cert: Option<&str>,
        csr: String,
        credentials: &types::Credentials,
    ) -> AnyhowResult<PairingResponse> {
        let response = certs::client(root_cert)?
            .post(Self::endpoint_url(base_url, &["pairing"])?)
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
}

impl Registration for Api {
    fn register_with_hostname(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        host_name: &str,
    ) -> AnyhowResult<()> {
        check_response_204(
            certs::client(Some(root_cert))?
                .post(Self::endpoint_url(base_url, &["register_with_hostname"])?)
                .basic_auth(&credentials.username, Some(&credentials.password))
                .json(&RegistrationWithHNBody {
                    uuid: uuid.to_owned(),
                    host_name: String::from(host_name),
                })
                .send()?,
        )
    }

    fn register_with_agent_labels(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        agent_labels: &types::AgentLabels,
    ) -> AnyhowResult<()> {
        check_response_204(
            certs::client(Some(root_cert))?
                .post(Self::endpoint_url(base_url, &["register_with_labels"])?)
                .basic_auth(&credentials.username, Some(&credentials.password))
                .json(&RegistrationWithALBody {
                    uuid: uuid.to_owned(),
                    agent_labels: agent_labels.clone(),
                })
                .send()?,
        )
    }
}

impl AgentData for Api {
    fn agent_data(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        uuid: &uuid::Uuid,
        certificate: &str,
        compression_algorithm: &str,
        monitoring_data: &[u8],
    ) -> AnyhowResult<()> {
        check_response_204(
            certs::client(Some(root_cert))?
                .post(Self::endpoint_url(
                    base_url,
                    &["agent_data", &uuid.to_string()],
                )?)
                .header("certificate", encode_pem_cert_base64(certificate)?)
                .header("compression", compression_algorithm)
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
}

impl Status for Api {
    fn status(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        uuid: &uuid::Uuid,
        certificate: &str,
    ) -> Result<StatusResponse, StatusError> {
        let response = certs::client(Some(root_cert))?
            .get(Self::endpoint_url(
                base_url,
                &["registration_status", &uuid.to_string()],
            )?)
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
}

#[cfg(test)]
mod test_api {
    use super::*;

    #[test]
    fn test_endpoint_url() {
        assert_eq!(
            Api::endpoint_url(
                &reqwest::Url::parse("https://my_server:7766/site2").unwrap(),
                &["some", "endpoint"]
            )
            .unwrap()
            .to_string(),
            "https://my_server:7766/site2/agent-receiver/some/endpoint"
        );
    }
}
