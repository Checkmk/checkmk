// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, config, types};
use anyhow::{anyhow, bail, Context, Result as AnyhowResult};
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

#[derive(Deserialize)]
struct ErrorResponse {
    pub detail: String,
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
        connection: &config::Connection,
        compression_algorithm: &str,
        monitoring_data: &[u8],
    ) -> AnyhowResult<()>;
}

pub trait Status {
    fn status(
        &self,
        base_url: &reqwest::Url,
        connection: &config::Connection,
    ) -> AnyhowResult<StatusResponse>;
}

pub struct Api {
    pub use_proxy: bool,
}

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

    fn error_response_description(status: StatusCode, body: Option<String>) -> String {
        match body {
            None => format!(
                "Request failed with code {}, could not obtain response body",
                status
            ),
            Some(body) => format!(
                "Request failed with code {}: {}",
                status,
                match serde_json::from_str::<ErrorResponse>(&body) {
                    Ok(error_response) => error_response.detail,
                    _ => body,
                }
            ),
        }
    }

    fn check_response_204(response: reqwest::blocking::Response) -> AnyhowResult<()> {
        let status = response.status();
        if status == StatusCode::NO_CONTENT {
            Ok(())
        } else {
            Err(anyhow!(Api::error_response_description(
                status,
                response.text().ok()
            )))
        }
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
        let response = certs::client(
            root_cert.map(|r| certs::HandshakeCredentials {
                server_root_cert: r,
                client_identity: None,
            }),
            self.use_proxy,
        )?
        .post(Self::endpoint_url(base_url, &["pairing"])?)
        .basic_auth(&credentials.username, Some(&credentials.password))
        .json(&PairingBody { csr })
        .send()?;
        let status = response.status();

        if status == StatusCode::OK {
            let body = response.text().context("Failed to obtain response body")?;
            serde_json::from_str::<PairingResponse>(&body)
                .context(format!("Error parsing this response body: {}", body))
        } else {
            Err(anyhow!(Api::error_response_description(
                status,
                response.text().ok()
            )))
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
        Api::check_response_204(
            certs::client(
                Some(certs::HandshakeCredentials {
                    server_root_cert: root_cert,
                    client_identity: None,
                }),
                self.use_proxy,
            )?
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
        Api::check_response_204(
            certs::client(
                Some(certs::HandshakeCredentials {
                    server_root_cert: root_cert,
                    client_identity: None,
                }),
                self.use_proxy,
            )?
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
        connection: &config::Connection,
        compression_algorithm: &str,
        monitoring_data: &[u8],
    ) -> AnyhowResult<()> {
        Api::check_response_204(
            certs::client(
                Some(connection.tls_handshake_credentials()?),
                self.use_proxy,
            )?
            .post(Self::endpoint_url(
                base_url,
                &["agent_data", &connection.uuid.to_string()],
            )?)
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
        connection: &config::Connection,
    ) -> AnyhowResult<StatusResponse> {
        let response = certs::client(
            Some(connection.tls_handshake_credentials()?),
            self.use_proxy,
        )?
        .get(Self::endpoint_url(
            base_url,
            &["registration_status", &connection.uuid.to_string()],
        )?)
        .send()?;

        match response.status() {
            StatusCode::OK => {
                let body = response.text()?;
                Ok(serde_json::from_str::<StatusResponse>(&body)
                    .context(format!("Failed to deserialize response body: {}", body))?)
            }
            _ => bail!(Api::error_response_description(
                response.status(),
                response.text().ok()
            )),
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

    #[test]
    fn test_error_response_description_body_missing() {
        assert_eq!(
            Api::error_response_description(StatusCode::INTERNAL_SERVER_ERROR, None,),
            "Request failed with code 500 Internal Server Error, could not obtain response body"
        )
    }

    #[test]
    fn test_error_response_description_body_parsable() {
        assert_eq!(
            Api::error_response_description(
                StatusCode::BAD_REQUEST,
                Some(String::from("{\"detail\": \"Something went wrong\"}")),
            ),
            "Request failed with code 400 Bad Request: Something went wrong"
        )
    }

    #[test]
    fn test_error_response_description_body_not_parsable() {
        assert_eq!(
            Api::error_response_description(
                StatusCode::NOT_FOUND,
                Some(String::from("{\"detail\": {\"title\": \"whatever\"}}")),
            ),
            "Request failed with code 404 Not Found: {\"detail\": {\"title\": \"whatever\"}}"
        )
    }

    #[test]
    fn test_check_response_204_ok() {
        assert!(Api::check_response_204(reqwest::blocking::Response::from(
            http::Response::builder()
                .status(StatusCode::NO_CONTENT)
                .body("")
                .unwrap(),
        ))
        .is_ok());
    }

    #[test]
    fn test_check_response_204_error() {
        match Api::check_response_204(reqwest::blocking::Response::from(
            http::Response::builder()
                .status(StatusCode::UNAUTHORIZED)
                .body("{\"detail\": \"Insufficient permissions\"}")
                .unwrap(),
        )) {
            Err(err) => {
                assert_eq!(
                    format!("{}", err),
                    "Request failed with code 401 Unauthorized: Insufficient permissions"
                )
            }
            _ => panic!("Expected an error"),
        }
    }
}
