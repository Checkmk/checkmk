// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, config, types};
use anyhow::{Context, Result as AnyhowResult};
use http::StatusCode;
use reqwest::header::AUTHORIZATION;
use serde::{Deserialize, Serialize};
use serde_with::DisplayFromStr;
use std::time::Duration;

// Timeouts of the agent update calls. Set explicitly because the default of the
// blocking reqwest client is 30 seconds and the code says so nowhere.
//
// The values differ from the legacy updater's because the 120 seconds of
// `cmk_update_agent` are an inactivity timeout: 120 seconds without a single
// byte. That never bounds a transfer as a whole, so a slow download simply takes
// as long as it takes. The blocking reqwest client offers no inactivity timeout,
// only a cap on total wall-clock time, so each value here has to be a budget for
// the whole call.

/// Cap for the agent update status request.
///
/// Very small JSON objects to send/recv: time to outlast a TLS handshake and a bit busy site.
const UPDATE_STATUS_TIMEOUT: Duration = Duration::from_secs(30);

/// Cap for the agent package download.
///
/// 300 is approximately 30 MB at 100 kB/s.
const AGENT_DOWNLOAD_TIMEOUT: Duration = Duration::from_secs(300);

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

/// Whether the registration file of a UUID permits agent updates through its
/// connection, as the site of the registration reports it.
#[derive(Deserialize, Clone, Copy, Debug, Default, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AgentUpdateAuthorization {
    Authorized,
    NotPermitted,
    /// Also stands for a site that predates the field, and for a value that
    /// this controller doesn't know.
    #[default]
    #[serde(other)]
    Unavailable,
}

#[derive(Deserialize)]
pub struct RegisterExistingResponse {
    pub root_cert: String,
    pub agent_cert: String,
    pub connection_mode: config::ConnectionMode,
    #[serde(default)]
    pub agent_update_authorization: AgentUpdateAuthorization,
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
    #[serde(default)]
    pub agent_update_authorization: AgentUpdateAuthorization,
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

/// An error of a request to the agent receiver, keeping the status code of
/// an answer the caller has to tell apart.
#[derive(Debug)]
pub enum ApiError {
    /// The site answered, but not with the expected status.
    Status {
        status: StatusCode,
        body: Option<String>,
    },
    Other(anyhow::Error),
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ApiError::Status { status, body } => {
                f.write_str(&Api::error_response_description(*status, body.clone()))
            }
            ApiError::Other(error) => write!(f, "{error}"),
        }
    }
}

impl std::error::Error for ApiError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            ApiError::Status { .. } => None,
            ApiError::Other(error) => error.source(),
        }
    }
}

impl From<anyhow::Error> for ApiError {
    fn from(error: anyhow::Error) -> Self {
        ApiError::Other(error)
    }
}

impl From<reqwest::Error> for ApiError {
    fn from(error: reqwest::Error) -> Self {
        ApiError::Other(error.into())
    }
}

/// What the host tells the site about its agent. The site keeps no state about
/// the host beyond this, so every field is reported on every check.
///
/// Borrows its fields: the body is a view of the updater's artifacts, assembled
/// for one request.
#[derive(Serialize)]
pub struct UpdateStatusBody<'a> {
    /// Target platform of the installed package, for example "linux_deb".
    pub platform: &'a str,

    /// Hash of the installed agent package.
    pub installed_aghash: &'a types::AgentHash,

    /// Error of the last update attempt, which the site quotes back in its
    /// deployment views.
    pub last_error: Option<&'a str>,
}

/// One signature of the offered agent package.
///
/// Serialized as well as read: the install request carries the signatures on
/// to the privileged install step, in the shape the site sent them.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct AgentSignature {
    /// PEM-encoded certificate of the signing key.
    pub certificate: String,

    /// Base64-encoded signature of the package.
    pub signature: String,
}

/// The agent package the site has for this host.
#[derive(Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct TargetAgent {
    /// Hash of the package the site would deliver.
    pub aghash: types::AgentHash,

    /// Signatures to verify a downloaded package against. A site that signs
    /// nothing may leave the field out altogether.
    #[serde(default)]
    pub signatures: Vec<AgentSignature>,
}

/// What the site answers a status request with.
#[derive(Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct UpdateStatusResponse {
    /// The package offered to this host, absent if the site has none. Carrying
    /// the hash and its signatures together keeps a package without a hash,
    /// or a hash without the signatures that belong to it, unrepresentable.
    pub target_agent: Option<TargetAgent>,
}

/// Which package to fetch. The site serves the one it named in the status.
#[derive(Serialize)]
pub struct AgentDownloadBody<'a> {
    /// Target platform of the installed package, for example "linux_deb".
    pub platform: &'a str,

    /// Hash of the package to fetch.
    pub aghash: &'a types::AgentHash,
}

pub trait AgentUpdate {
    /// Report what is installed and learn which package the site would deliver.
    ///
    /// The client certificate of `connection` authenticates the host; the site
    /// resolves its UUID to a host name. There is no further credential.
    fn update_status(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        body: &UpdateStatusBody<'_>,
    ) -> AnyhowResult<UpdateStatusResponse, ApiError>;

    /// Fetch the agent package itself, unverified.
    fn download_agent(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        body: &AgentDownloadBody<'_>,
    ) -> AnyhowResult<Vec<u8>, ApiError>;
}

pub trait Registration {
    fn register_existing(
        &self,
        base_url: &reqwest::Url,
        root_certs: &[&str],
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        host_name: &str,
    ) -> AnyhowResult<RegisterExistingResponse>;

    fn register_new(
        &self,
        base_url: &reqwest::Url,
        root_certs: &[&str],
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
    ) -> Result<T, ApiError> {
        let status = response.status();
        if status != StatusCode::OK {
            return Err(ApiError::Status {
                status,
                body: response.text().ok(),
            });
        }
        let body = response.text().context("Failed to obtain response body")?;
        Ok(deserializer(&body).context(format!("Error parsing this response body: {body}"))?)
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

    /// The body of a response that is not JSON, for example an agent package.
    fn response_bytes(response: reqwest::blocking::Response) -> Result<Vec<u8>, ApiError> {
        let status = response.status();
        if status != StatusCode::OK {
            return Err(ApiError::Status {
                status,
                body: response.text().ok(),
            });
        }
        Ok(response
            .bytes()
            .context("Failed to obtain response body")?
            .to_vec())
    }

    fn check_response_204(response: reqwest::blocking::Response) -> Result<(), ApiError> {
        let status = response.status();
        if status == StatusCode::NO_CONTENT {
            Ok(())
        } else {
            Err(ApiError::Status {
                status,
                body: response.text().ok(),
            })
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
        Ok(Self::deserialize_json_response(
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
        )?)
    }
}

impl Registration for Api {
    fn register_existing(
        &self,
        base_url: &reqwest::Url,
        root_certs: &[&str],
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        host_name: &str,
    ) -> AnyhowResult<RegisterExistingResponse> {
        let endpoint = match credentials {
            types::Credentials::OneTimeToken { .. } => "register_existing_token",
            _ => "register_existing",
        };
        self.call_registration_init_endpoint(
            Self::endpoint_url(base_url, &[endpoint])?,
            root_certs,
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
        root_certs: &[&str],
        credentials: &types::Credentials,
        uuid: &uuid::Uuid,
        csr: &str,
        agent_labels: &types::AgentLabels,
    ) -> AnyhowResult<RegisterNewResponse> {
        self.call_registration_init_endpoint(
            Self::endpoint_url(base_url, &["register_new"])?,
            root_certs,
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
        Ok(Self::deserialize_json_response(
            Self::apply_registration_auth(
                certs::client(
                    Some(certs::HandshakeCredentials {
                        server_root_certs: vec![root_cert],
                        client_identity: None,
                    }),
                    self.use_proxy,
                )?
                .post(Self::endpoint_url(
                    base_url,
                    &["register_new_ongoing", &uuid.to_string()],
                )?),
                credentials,
            )
            .send()
            .context("Calling register_new_ongoing endpoint failed")?,
            |body| serde_json::from_str::<RegisterNewOngoingResponse>(body),
        )?)
    }
}

impl Api {
    fn call_registration_init_endpoint<'a, T>(
        &self,
        url: reqwest::Url,
        root_certs: &[&str],
        credentials: &types::Credentials,
        body: &impl Serialize,
        deserializer: fn(&str) -> serde_json::Result<T>,
    ) -> AnyhowResult<T>
    where
        T: Deserialize<'a>,
    {
        Ok(Self::deserialize_json_response(
            Self::apply_registration_auth(
                certs::client(
                    (!root_certs.is_empty()).then(|| certs::HandshakeCredentials {
                        server_root_certs: root_certs.to_vec(),
                        client_identity: None,
                    }),
                    self.use_proxy,
                )?
                .post(url),
                credentials,
            )
            .json(body)
            .send()
            .context("Calling registration endpoint failed")?,
            deserializer,
        )?)
    }

    fn apply_registration_auth(
        builder: reqwest::blocking::RequestBuilder,
        credentials: &types::Credentials,
    ) -> reqwest::blocking::RequestBuilder {
        match credentials {
            types::Credentials::UsernamePassword { username, password } => {
                builder.basic_auth(username, Some(password))
            }
            types::Credentials::OneTimeToken { ott } => {
                builder.header(AUTHORIZATION, format!("CMK-TOKEN {ott}"))
            }
        }
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
        Ok(Api::check_response_204(
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
        )?)
    }
}

impl RegistrationStatusV2 for Api {
    fn registration_status_v2(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
    ) -> AnyhowResult<RegistrationStatusV2Response> {
        Ok(Self::deserialize_json_response(
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
        )?)
    }
}

impl AgentUpdate for Api {
    fn update_status(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        body: &UpdateStatusBody<'_>,
    ) -> AnyhowResult<UpdateStatusResponse, ApiError> {
        Self::deserialize_json_response(
            certs::client(
                Some(connection.tls_handshake_credentials()?),
                self.use_proxy,
            )?
            .post(Self::endpoint_url(
                base_url,
                &["agent_update", "status", &connection.uuid.to_string()],
            )?)
            .timeout(UPDATE_STATUS_TIMEOUT)
            .json(body)
            .send()?,
            |body| serde_json::from_str::<UpdateStatusResponse>(body),
        )
    }

    fn download_agent(
        &self,
        base_url: &reqwest::Url,
        connection: &config::TrustedConnection,
        body: &AgentDownloadBody<'_>,
    ) -> AnyhowResult<Vec<u8>, ApiError> {
        Self::response_bytes(
            certs::client(
                Some(connection.tls_handshake_credentials()?),
                self.use_proxy,
            )?
            .post(Self::endpoint_url(
                base_url,
                &["agent_update", "agent", &connection.uuid.to_string()],
            )?)
            .timeout(AGENT_DOWNLOAD_TIMEOUT)
            .json(body)
            .send()?,
        )
    }
}

#[cfg(test)]
mod test_api {
    use super::*;

    fn authorization_of_register_existing(field: &str) -> AgentUpdateAuthorization {
        serde_json::from_str::<RegisterExistingResponse>(&format!(
            r#"{{"root_cert": "root", "agent_cert": "cert", "connection_mode": "pull-agent"{field}}}"#
        ))
        .unwrap()
        .agent_update_authorization
    }

    /// CMK-39588 AC1
    #[test]
    fn test_register_existing_response_reports_authorized() {
        assert_eq!(
            authorization_of_register_existing(r#", "agent_update_authorization": "authorized""#),
            AgentUpdateAuthorization::Authorized
        );
    }

    /// CMK-39588 AC1
    #[test]
    fn test_register_existing_response_reports_not_permitted() {
        assert_eq!(
            authorization_of_register_existing(
                r#", "agent_update_authorization": "not_permitted""#
            ),
            AgentUpdateAuthorization::NotPermitted
        );
    }

    /// CMK-39588 AC1: a site that predates the field.
    #[test]
    fn test_register_existing_response_without_authorization_is_unavailable() {
        assert_eq!(
            authorization_of_register_existing(""),
            AgentUpdateAuthorization::Unavailable
        );
    }

    /// CMK-39588 AC1
    #[test]
    fn test_register_existing_response_with_an_unknown_authorization_is_unavailable() {
        assert_eq!(
            authorization_of_register_existing(r#", "agent_update_authorization": "pending""#),
            AgentUpdateAuthorization::Unavailable
        );
    }

    /// CMK-39588 AC1, AC6
    #[test]
    fn test_register_new_ongoing_success_reports_the_authorization() {
        let response = serde_json::from_str::<RegisterNewOngoingResponse>(
            r#"{"status": "Success", "agent_cert": "cert", "connection_mode": "push-agent",
                "agent_update_authorization": "authorized"}"#,
        )
        .unwrap();

        let RegisterNewOngoingResponse::Success(success) = response else {
            panic!("not a success");
        };
        assert_eq!(
            success.agent_update_authorization,
            AgentUpdateAuthorization::Authorized
        );
    }

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

    const AGENT_HASH: &str = "0123456789abcdef";

    #[test]
    fn test_update_status_body_serialization() {
        assert_eq!(
            serde_json::to_string(&UpdateStatusBody {
                platform: "linux_deb",
                installed_aghash: &AGENT_HASH.parse().unwrap(),
                last_error: Some("boom"),
            })
            .unwrap(),
            r#"{"platform":"linux_deb","installed_aghash":"0123456789abcdef","last_error":"boom"}"#
        );
    }

    #[test]
    fn test_agent_download_body_serialization() {
        assert_eq!(
            serde_json::to_string(&AgentDownloadBody {
                platform: "linux_deb",
                aghash: &AGENT_HASH.parse().unwrap(),
            })
            .unwrap(),
            r#"{"platform":"linux_deb","aghash":"0123456789abcdef"}"#
        );
    }

    #[test]
    fn test_response_bytes_ok() {
        assert_eq!(
            Api::response_bytes(reqwest::blocking::Response::from(
                http::Response::builder()
                    .status(StatusCode::OK)
                    .body("a package")
                    .unwrap(),
            ))
            .unwrap(),
            b"a package"
        );
    }

    #[test]
    fn test_response_bytes_error() {
        assert_eq!(
            Api::response_bytes(reqwest::blocking::Response::from(
                http::Response::builder()
                    .status(StatusCode::NOT_FOUND)
                    .body("{\"detail\": \"No such agent\"}")
                    .unwrap(),
            ))
            .unwrap_err()
            .to_string(),
            "Request failed with code 404 Not Found: No such agent"
        );
    }

    #[test]
    fn test_update_status_response_deserialization() {
        let response = serde_json::from_str::<UpdateStatusResponse>(
            r#"{"target_agent": {"aghash": "0123456789abcdef",
                "signatures": [{"certificate": "CERT", "signature": "c2ln"}]}}"#,
        )
        .unwrap();

        let target_agent = response.target_agent.unwrap();
        assert_eq!(target_agent.aghash.as_str(), AGENT_HASH);
        assert_eq!(
            target_agent.signatures,
            [AgentSignature {
                certificate: String::from("CERT"),
                signature: String::from("c2ln"),
            }]
        );
    }

    /// A site that signs nothing may leave the signatures out entirely.
    #[test]
    fn test_update_status_response_of_an_unsigned_package() {
        let response = serde_json::from_str::<UpdateStatusResponse>(
            r#"{"target_agent": {"aghash": "0123456789abcdef"}}"#,
        )
        .unwrap();

        assert!(response.target_agent.unwrap().signatures.is_empty());
    }

    /// A site with nothing to offer leaves the target agent out entirely.
    #[test]
    fn test_update_status_response_without_a_package() {
        let response = serde_json::from_str::<UpdateStatusResponse>(r#"{}"#).unwrap();

        assert!(response.target_agent.is_none());
    }

    /// The target hash becomes the name of a file handed to a privileged
    /// process, so a response carrying something else is not a status at all.
    #[test]
    fn test_update_status_response_rejects_a_target_hash_that_is_not_one() {
        assert!(serde_json::from_str::<UpdateStatusResponse>(
            r#"{"target_agent": {"aghash": "../../etc/passwd"}}"#,
        )
        .is_err());
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
