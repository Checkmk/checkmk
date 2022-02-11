// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{agent_receiver_api, certs, config};
use anyhow::{Context, Result as AnyhowResult};

#[derive(serde::Serialize)]
struct CertInfo {
    issuer: String,
    from: String,
    to: String,
}

#[derive(serde::Serialize)]
#[serde(untagged)]
enum CertParsingResult {
    Success(CertInfo),
    Error(String),
}

#[derive(serde::Serialize)]
struct LocalConnectionStatus {
    connection_type: config::ConnectionType,
    cert_info: CertParsingResult,
}

#[derive(serde::Serialize)]
struct RemoteConnectionStatus {
    connection_type: Option<config::ConnectionType>,
    registration_state: Option<agent_receiver_api::HostStatus>,
    host_name: Option<String>,
}

#[derive(serde::Serialize)]
enum RemoteConnectionError {
    #[serde(rename = "connection_refused")]
    ConnRefused,
    #[serde(rename = "certificate_invalid")]
    CertInvalid,
    #[serde(rename = "unspeficied_error")]
    Unspecified,
}

#[derive(serde::Serialize)]
#[serde(untagged)]
enum RemoteConnectionStatusResponse {
    Success(RemoteConnectionStatus),
    Error(RemoteConnectionError),
}

#[derive(serde::Serialize)]
struct ConnectionStatus {
    connection: String,
    uuid: String,
    local: LocalConnectionStatus,
    remote: Option<RemoteConnectionStatusResponse>,
}

#[derive(serde::Serialize)]
struct Status {
    connections: Vec<ConnectionStatus>,
}

impl CertInfo {
    fn from(certificate: &str) -> AnyhowResult<CertInfo> {
        let pem = certs::parse_pem(certificate)?;
        let x509 = pem.parse_x509()?;
        Ok(CertInfo {
            issuer: certs::join_common_names(x509.issuer()),
            from: x509.validity().not_before.to_rfc2822(),
            to: x509.validity().not_after.to_rfc2822(),
        })
    }
}

impl CertParsingResult {
    fn from(certificate: &str) -> CertParsingResult {
        match CertInfo::from(certificate) {
            Ok(cert_info) => CertParsingResult::Success(cert_info),
            _ => CertParsingResult::Error(String::from("parsing_error")),
        }
    }
}

impl RemoteConnectionError {
    fn from(status_err: agent_receiver_api::StatusError) -> RemoteConnectionError {
        match status_err {
            agent_receiver_api::StatusError::ConnectionRefused(..) => {
                RemoteConnectionError::ConnRefused
            }
            agent_receiver_api::StatusError::CertificateInvalid => {
                RemoteConnectionError::CertInvalid
            }
            agent_receiver_api::StatusError::UnspecifiedError(..) => {
                RemoteConnectionError::Unspecified
            }
        }
    }
}

impl std::fmt::Display for RemoteConnectionError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "{}",
            match self {
                RemoteConnectionError::ConnRefused => "refused",
                RemoteConnectionError::CertInvalid => "certificate invalid",
                RemoteConnectionError::Unspecified => "unspecified error",
            }
        )
    }
}

impl RemoteConnectionStatusResponse {
    fn from(
        server_address: &str,
        connection: &config::Connection,
        agent_rec_api: &impl agent_receiver_api::Status,
    ) -> RemoteConnectionStatusResponse {
        match agent_rec_api.status(
            server_address,
            &connection.root_cert,
            &connection.uuid,
            &connection.certificate,
        ) {
            Ok(status_response) => {
                RemoteConnectionStatusResponse::Success(RemoteConnectionStatus {
                    connection_type: status_response.connection_type,
                    registration_state: status_response.status,
                    host_name: status_response.hostname,
                })
            }
            Err(err) => RemoteConnectionStatusResponse::Error(RemoteConnectionError::from(err)),
        }
    }
}

impl ConnectionStatus {
    fn from_standard_conn(
        server: &str,
        conn: &config::Connection,
        conn_type: config::ConnectionType,
        agent_rec_api: &impl agent_receiver_api::Status,
    ) -> ConnectionStatus {
        ConnectionStatus {
            connection: String::from(server),
            uuid: String::from(&conn.uuid),
            local: LocalConnectionStatus {
                connection_type: conn_type,
                cert_info: CertParsingResult::from(&conn.certificate),
            },
            remote: Some(RemoteConnectionStatusResponse::from(
                server,
                conn,
                agent_rec_api,
            )),
        }
    }

    fn from_imported_conn(conn: &config::Connection, idx: usize) -> ConnectionStatus {
        ConnectionStatus {
            connection: format!("imported-{}", idx),
            uuid: String::from(&conn.uuid),
            local: LocalConnectionStatus {
                connection_type: config::ConnectionType::Pull,
                cert_info: CertParsingResult::from(&conn.certificate),
            },
            remote: None,
        }
    }

    fn local_lines_readable(&self) -> Vec<String> {
        let mut lines = vec![];
        lines.push(format!("Connection type: {}", self.local.connection_type));
        match &self.local.cert_info {
            CertParsingResult::Success(cert_info) => {
                lines.push(format!("Certificate issuer: {}", cert_info.issuer));
                lines.push(format!(
                    "Certificate validity: {} - {}",
                    cert_info.from, cert_info.to
                ));
            }
            CertParsingResult::Error(..) => {
                lines.push(String::from("Certificate parsing failed (!!)"))
            }
        }
        lines
    }

    fn remote_conn_type_marker(
        local_conn_type: &config::ConnectionType,
        remote_conn_type: &Option<config::ConnectionType>,
    ) -> String {
        match remote_conn_type {
            Some(ct) => {
                if ct == local_conn_type {
                    String::from("")
                } else {
                    String::from(" (!!)")
                }
            }
            None => String::from(" (!!)"),
        }
    }

    fn registration_state_str(remote_conn_stat: &RemoteConnectionStatus) -> String {
        match &remote_conn_stat.registration_state {
            Some(st) => format!("{}", st),
            None => {
                if remote_conn_stat.connection_type.is_some() & remote_conn_stat.host_name.is_some()
                {
                    String::from("operational")
                } else {
                    String::from("unknown (!!)")
                }
            }
        }
    }

    fn remote_lines_success_readable(
        remote_conn_stat: &RemoteConnectionStatus,
        local_conn_type: &config::ConnectionType,
    ) -> Vec<String> {
        vec![
            format!(
                "Connection type: {}{}",
                fmt_option_to_str(&remote_conn_stat.connection_type, "unknown"),
                ConnectionStatus::remote_conn_type_marker(
                    local_conn_type,
                    &remote_conn_stat.connection_type
                ),
            ),
            format!(
                "Registration state: {}",
                ConnectionStatus::registration_state_str(remote_conn_stat),
            ),
            format!(
                "Host name: {}",
                fmt_option_to_str(&remote_conn_stat.host_name, "unknown"),
            ),
        ]
    }

    fn remote_lines_readable(&self) -> Vec<String> {
        match &self.remote {
            Some(remote_stat_resp) => match &remote_stat_resp {
                RemoteConnectionStatusResponse::Success(remote_conn_stat) => {
                    ConnectionStatus::remote_lines_success_readable(
                        remote_conn_stat,
                        &self.local.connection_type,
                    )
                }
                RemoteConnectionStatusResponse::Error(err) => {
                    vec![format!("Connection error: {} (!!)", err)]
                }
            },
            None => vec![String::from("No remote address (imported connection)")],
        }
    }

    fn to_human_readable(&self) -> String {
        format!(
            "Connection: {}\n\tUUID: {}\n\tLocal:\n\t\t{}\n\tRemote:\n\t\t{}",
            self.connection,
            self.uuid,
            self.local_lines_readable().join("\n\t\t"),
            self.remote_lines_readable().join("\n\t\t")
        )
    }
}

impl std::fmt::Display for ConnectionStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(f, "{}", self.to_human_readable())
    }
}

impl Status {
    fn from(
        registry: &config::Registry,
        agent_rec_api: &impl agent_receiver_api::Status,
    ) -> Status {
        let mut conn_stats = Vec::new();

        for (server, push_conn) in registry.push_connections() {
            conn_stats.push(ConnectionStatus::from_standard_conn(
                server,
                push_conn,
                config::ConnectionType::Push,
                agent_rec_api,
            ));
        }
        for (server, pull_conn) in registry.standard_pull_connections() {
            conn_stats.push(ConnectionStatus::from_standard_conn(
                server,
                pull_conn,
                config::ConnectionType::Pull,
                agent_rec_api,
            ));
        }
        for (idx, imp_pull_conn) in registry.imported_pull_connections().enumerate() {
            conn_stats.push(ConnectionStatus::from_imported_conn(imp_pull_conn, idx + 1));
        }

        Status {
            connections: conn_stats,
        }
    }

    fn to_json(&self) -> AnyhowResult<String> {
        serde_json::to_string(&self).context("Failed to serialize status to JSON")
    }

    fn to_string(&self, json: bool) -> AnyhowResult<String> {
        if json {
            self.to_json()
        } else {
            Ok(format!("{}", self))
        }
    }
}

impl std::fmt::Display for Status {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        write!(
            f,
            "{}",
            if self.connections.is_empty() {
                String::from("No connections")
            } else {
                self.connections
                    .iter()
                    .map(|conn_stat| format!("{}", conn_stat))
                    .collect::<Vec<String>>()
                    .join("\n\n\n")
            }
        )
    }
}

fn fmt_option_to_str(op: &Option<impl std::fmt::Display>, none_str: &str) -> String {
    match op {
        Some(formattable) => format!("{}", formattable),
        None => String::from(none_str),
    }
}

fn _status(
    registry: &config::Registry,
    json: bool,
    agent_rec_api: &impl agent_receiver_api::Status,
) -> AnyhowResult<String> {
    Status::from(registry, agent_rec_api).to_string(json)
}

pub fn status(registry: &config::Registry, json: bool) -> AnyhowResult<()> {
    println!("{}", _status(registry, json, &agent_receiver_api::Api {})?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_connection_status_fmt_normal() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Some(RemoteConnectionStatusResponse::Success(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: None,
                            host_name: Some(String::from("my-host")),
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tRegistration state: operational\n\
                 \t\tHost name: my-host"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_discoverable() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Some(RemoteConnectionStatusResponse::Success(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: Some(agent_receiver_api::HostStatus::Discoverable),
                            host_name: Some(String::from("my-host")),
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tRegistration state: discoverable\n\
                 \t\tHost name: my-host"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_imported() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("imported-1"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: None
                }
            ),
            String::from(
                "Connection: imported-1\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tNo remote address (imported connection)"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_cert_malformed() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Error(String::from("parsing_error"))
                    },
                    remote: Some(RemoteConnectionStatusResponse::Error(
                        RemoteConnectionError::Unspecified
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate parsing failed (!!)\n\
                 \tRemote:\n\
                 \t\tConnection error: unspecified error (!!)"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_refused() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Some(RemoteConnectionStatusResponse::Error(
                        RemoteConnectionError::ConnRefused
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection error: refused (!!)"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_mismatch_conn_type() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Some(RemoteConnectionStatusResponse::Success(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Push),
                            registration_state: None,
                            host_name: Some(String::from("my-host")),
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection type: push-agent (!!)\n\
                 \t\tRegistration state: operational\n\
                 \t\tHost name: my-host"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_unkn_reg_state() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Some(RemoteConnectionStatusResponse::Success(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: None,
                            host_name: None,
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000\n\
                 \tUUID: abc-123\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tRegistration state: unknown (!!)\n\
                 \t\tHost name: unknown"
            )
        );
    }

    fn build_status() -> Status {
        Status {
            connections: vec![
                ConnectionStatus {
                    connection: String::from("localhost:8000"),
                    uuid: String::from("abc-123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        }),
                    },
                    remote: Some(RemoteConnectionStatusResponse::Success(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: None,
                            host_name: Some(String::from("my-host")),
                        },
                    )),
                },
                ConnectionStatus {
                    connection: String::from("somehwere:8000"),
                    uuid: String::from("ghghhfjdkgf123"),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Push,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site2' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        }),
                    },
                    remote: Some(RemoteConnectionStatusResponse::Success(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Push),
                            registration_state: None,
                            host_name: Some(String::from("my-host2")),
                        },
                    )),
                },
            ],
        }
    }

    #[test]
    fn test_status_str_human_readable() {
        assert_eq!(
            build_status().to_string(false).unwrap(),
            "Connection: localhost:8000\n\
             \tUUID: abc-123\n\
             \tLocal:\n\
             \t\tConnection type: pull-agent\n\
             \t\tCertificate issuer: Site 'site' local CA\n\
             \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
             \tRemote:\n\
             \t\tConnection type: pull-agent\n\
             \t\tRegistration state: operational\n\
             \t\tHost name: my-host\n\n\n\
             Connection: somehwere:8000\n\
             \tUUID: ghghhfjdkgf123\n\
             \tLocal:\n\
             \t\tConnection type: push-agent\n\
             \t\tCertificate issuer: Site 'site2' local CA\n\
             \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
             \tRemote:\n\
             \t\tConnection type: push-agent\n\
             \t\tRegistration state: operational\n\
             \t\tHost name: my-host2"
        );
    }

    #[test]
    fn test_status_str_json() {
        assert_eq!(
            build_status().to_string(true).unwrap(),
            serde_json::to_string(&build_status()).unwrap(),
        );
    }

    #[test]
    fn test_status_str_empty() {
        assert_eq!(
            Status {
                connections: vec![],
            }
            .to_string(false)
            .unwrap(),
            "No connections"
        );
    }

    struct MockApi {}

    impl agent_receiver_api::Status for MockApi {
        fn status(
            &self,
            _server_address: &str,
            _root_cert: &str,
            _uuid: &str,
            _certificate: &str,
        ) -> Result<agent_receiver_api::StatusResponse, agent_receiver_api::StatusError> {
            Ok(agent_receiver_api::StatusResponse {
                hostname: Some(String::from("host")),
                status: None,
                connection_type: Some(config::ConnectionType::Pull),
                message: None,
            })
        }
    }

    #[test]
    fn test_status_end_to_end() {
        let mut push = std::collections::HashMap::new();
        push.insert(
            String::from("push_server:8000"),
            config::Connection {
                uuid: String::from("uuid-push"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );
        let registry = config::Registry::new(
            config::RegisteredConnections {
                push,
                pull: std::collections::HashMap::new(),
                pull_imported: vec![],
            },
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap();

        assert_eq!(
            _status(&registry, false, &MockApi {},).unwrap(),
            "Connection: push_server:8000\n\tUUID: uuid-push\n\
             \tLocal:\n\
             \t\tConnection type: push-agent\n\
             \t\tCertificate parsing failed (!!)\n\
             \tRemote:\n\
             \t\tConnection type: pull-agent (!!)\n\
             \t\tRegistration state: operational\n\
             \t\tHost name: host"
        );
    }
}
