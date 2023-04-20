// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, config, types};
use anyhow::{bail, Context, Result as AnyhowResult};
use http::StatusCode;
use serde::{Deserialize, Serialize};
use serde_with::DisplayFromStr;

#[derive(Serialize)]
struct RenewCertificateBody {
    csr: String,
}

#[derive(Deserialize)]
pub struct RenewCertificateResponse {
    pub agent_cert: String,
}

#[serde_with::serde_as]
#[derive(Serialize)]
struct RegisterExistingBody {
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    csr: String,
    host_name: String,
}

#[derive(Deserialize)]
pub struct RegisterExistingResponse {
    pub root_cert: String,
    pub agent_cert: String,
    pub connection_mode: config::ConnectionMode,
}

#[serde_with::serde_as]
#[derive(Serialize)]
struct RegisterNewBody {
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    csr: String,
    agent_labels: types::AgentLabels,
}

#[derive(Deserialize)]
pub struct RegisterNewResponse {
    pub root_cert: String,
}

#[derive(Deserialize)]
pub struct RegisterNewOngoingResponseDeclined {
    pub reason: String,
}

#[derive(Deserialize)]
pub struct RegisterNewOngoingResponseSuccess {
    pub agent_cert: String,
    pub connection_mode: config::ConnectionMode,
}

#[derive(Deserialize)]
#[serde(tag = "status")]
pub enum RegisterNewOngoingResponse {
    InProgress,
    Declined(RegisterNewOngoingResponseDeclined),
    Success(RegisterNewOngoingResponseSuccess),
}

#[derive(Serialize, Deserialize)]
#[serde(tag = "status")]
pub enum RegistrationStatusV2Response {
    NotRegistered,
    Registered(RegistrationStatusV2ResponseRegistered),
}

#[derive(Serialize, Deserialize)]
pub struct RegistrationStatusV2ResponseRegistered {
    pub hostname: String,
    pub connection_mode: config::ConnectionMode,
}

#[derive(Deserialize)]
struct ErrorResponse {
    pub detail: String,
}

pub trait Registration {
    fn register_existing(
        &self,
        base_url: &reqwest::Url,
        root_cert: &Option<&str>,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        host_name: &str,
    ) -> AnyhowResult<RegisterExistingResponse>;

    fn register_new(
        &self,
        base_url: &reqwest::Url,
        root_cert: &Option<&str>,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        agent_labels: &types::AgentLabels,
    ) -> AnyhowResult<RegisterNewResponse>;

    fn register_new_ongoing(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
    ) -> AnyhowResult<RegisterNewOngoingResponse>;
}

pub trait AgentData {
    fn agent_data(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        compression_algorithm: &str,
        monitoring_data: &[u8],
    ) -> AnyhowResult<()>;
}

pub trait RegistrationStatusV2 {
    fn registration_status_v2(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
    ) -> AnyhowResult<RegistrationStatusV2Response>;
}

pub trait RenewCertificate {
    fn renew_certificate(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        csr: String,
    ) -> AnyhowResult<RenewCertificateResponse>;
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

    fn deserialize_json_response<T>(
        response: reqwest::blocking::Response,
        deserializer: fn(&str) -> serde_json::Result<T>,
    ) -> AnyhowResult<T> {
        let status = response.status();
        if status != StatusCode::OK {
            bail!(Api::error_response_description(
                status,
                response.text().ok()
            ))
        }
        let body = response.text().context("Failed to obtain response body")?;
        deserializer(&body).context(format!("Error parsing this response body: {body}"))
    }

    fn error_response_description(status: StatusCode, body: Option<String>) -> String {
        match body {
            None => format!("Request failed with code {status}, could not obtain response body"),
            Some(body) => format!(
                "Request failed with code {}: {}",
                status,
                if let Ok(error_response) = serde_json::from_str::<ErrorResponse>(&body) {
                    error_response.detail
                } else {
                    body
                }
            ),
        }
    }

    fn check_response_204(response: reqwest::blocking::Response) -> AnyhowResult<()> {
        let status = response.status();
        if status == StatusCode::NO_CONTENT {
            Ok(())
        } else {
            bail!(Api::error_response_description(
                status,
                response.text().ok()
            ))
        }
    }
}

impl RenewCertificate for Api {
    fn renew_certificate(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        csr: String,
    ) -> AnyhowResult<RenewCertificateResponse> {
        Self::deserialize_json_response(
            certs::client(
                Some(connection.tls_handshake_credentials()?),
                self.use_proxy,
            )?
            .post(Self::endpoint_url(
                base_url,
                &["renew_certificate", &connection.uuid.to_string()],
            )?)
            .json(&RenewCertificateBody { csr })
            .send()?,
            |body| serde_json::from_str::<RenewCertificateResponse>(body),
        )
    }
}

impl Registration for Api {
    fn register_existing(
        &self,
        base_url: &reqwest::Url,
        root_cert: &Option<&str>,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        host_name: &str,
    ) -> AnyhowResult<RegisterExistingResponse> {
        self.call_registration_init_endpoint(
            Self::endpoint_url(base_url, &["register_existing"])?,
            root_cert,
            credentials,
            &RegisterExistingBody {
                uuid: uuid.to_owned(),
                csr: csr.to_owned(),
                host_name: String::from(host_name),
            },
            |body| serde_json::from_str::<RegisterExistingResponse>(body),
        )
    }

    fn register_new(
        &self,
        base_url: &reqwest::Url,
        root_cert: &Option<&str>,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        agent_labels: &types::AgentLabels,
    ) -> AnyhowResult<RegisterNewResponse> {
        self.call_registration_init_endpoint(
            Self::endpoint_url(base_url, &["register_new"])?,
            root_cert,
            credentials,
            &RegisterNewBody {
                uuid: uuid.to_owned(),
                csr: csr.to_owned(),
                agent_labels: agent_labels.clone(),
            },
            |body| serde_json::from_str::<RegisterNewResponse>(body),
        )
    }

    fn register_new_ongoing(
        &self,
        base_url: &reqwest::Url,
        root_cert: &str,
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
    ) -> AnyhowResult<RegisterNewOngoingResponse> {
        Self::deserialize_json_response(
            certs::client(
                Some(certs::HandshakeCredentials {
                    server_root_cert: root_cert,
                    client_identity: None,
                }),
                self.use_proxy,
            )?
            .post(Self::endpoint_url(
                base_url,
                &["register_new_ongoing", &uuid.to_string()],
            )?)
            .basic_auth(&credentials.username, Some(&credentials.password))
            .send()
            .context("Calling register_new_ongoing endpoint failed")?,
            |body| serde_json::from_str::<RegisterNewOngoingResponse>(body),
        )
    }
}

impl Api {
    fn call_registration_init_endpoint<'a, T>(
        &self,
        url: reqwest::Url,
        root_cert: &Option<&str>,
        credentials: &types::Credentials,
        body: &impl Serialize,
        deserializer: fn(&str) -> serde_json::Result<T>,
    ) -> AnyhowResult<T>
    where
        T: Deserialize<'a>,
    {
        Self::deserialize_json_response(
            certs::client(
                root_cert.map(|r| certs::HandshakeCredentials {
                    server_root_cert: r,
                    client_identity: None,
                }),
                self.use_proxy,
            )?
            .post(url)
            .basic_auth(&credentials.username, Some(&credentials.password))
            .json(body)
            .send()
            .context("Calling registration endpoint failed")?,
            deserializer,
        )
    }
}

impl AgentData for Api {
    fn agent_data(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
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

impl RegistrationStatusV2 for Api {
    fn registration_status_v2(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
    ) -> AnyhowResult<RegistrationStatusV2Response> {
        Self::deserialize_json_response(
            certs::client(
                Some(connection.tls_handshake_credentials()?),
                self.use_proxy,
            )?
            .get(Self::endpoint_url(
                base_url,
                &["registration_status_v2", &connection.uuid.to_string()],
            )?)
            .send()?,
            |body| serde_json::from_str::<RegistrationStatusV2Response>(body),
        )
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
        let error_value = Api::check_response_204(reqwest::blocking::Response::from(
            http::Response::builder()
                .status(StatusCode::UNAUTHORIZED)
                .body("{\"detail\": \"Insufficient permissions\"}")
                .unwrap(),
        ))
        .unwrap_err();
        assert_eq!(
            format!("{error_value}"),
            "Request failed with code 401 Unauthorized: Insufficient permissions"
        );
    }
}
