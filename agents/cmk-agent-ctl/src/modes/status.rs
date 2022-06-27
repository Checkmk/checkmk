// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{agent_receiver_api, certs, config, constants, site_spec};
use anyhow::{Context, Result as AnyhowResult};
use serde::ser::SerializeStruct;
use serde_with::DisplayFromStr;

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

enum Remote {
    StatusResponse(AnyhowResult<RemoteConnectionStatus>),
    Imported,
    QueryDisabled,
}

impl serde::ser::Serialize for Remote {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::ser::Serializer,
    {
        match self {
            Self::StatusResponse(remote_conn_stat) => match remote_conn_stat {
                Ok(remote_conn_stat) => remote_conn_stat.serialize(serializer),
                Err(err) => {
                    let mut s = serializer.serialize_struct("Error", 1)?;
                    s.serialize_field("error", &err.to_string())?;
                    s.end()
                }
            },
            Self::Imported => serializer.serialize_str("imported_connection"),
            Self::QueryDisabled => serializer.serialize_str("remote_query_disabled"),
        }
    }
}

#[serde_with::serde_as]
#[derive(serde::Serialize)]
struct ConnectionStatus {
    coordinates: Option<site_spec::Coordinates>,
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    local: LocalConnectionStatus,
    remote: Remote,
}

#[derive(serde::Serialize)]
struct Status {
    version: String,
    agent_socket_operational: bool,
    ip_allowlist: Vec<String>,
    allow_legacy_pull: bool,
    connections: Vec<ConnectionStatus>,
}

impl CertInfo {
    fn from(certificate: &str) -> AnyhowResult<CertInfo> {
        let pem = certs::parse_pem(certificate)?;
        let x509 = pem.parse_x509()?;
        Ok(CertInfo {
            issuer: certs::common_names(x509.issuer())?.join(", "),
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

impl ConnectionStatus {
    fn query_remote(
        coordinates: &site_spec::Coordinates,
        conn: &config::Connection,
        agent_rec_api: &impl agent_receiver_api::Status,
    ) -> AnyhowResult<RemoteConnectionStatus> {
        let status_response = agent_rec_api.status(&coordinates.to_url()?, conn)?;
        Ok(RemoteConnectionStatus {
            connection_type: status_response.connection_type,
            registration_state: status_response.status,
            host_name: status_response.hostname,
        })
    }

    fn from_standard_conn(
        coordinates: &site_spec::Coordinates,
        conn: &config::Connection,
        conn_type: config::ConnectionType,
        agent_rec_api: &Option<impl agent_receiver_api::Status>,
    ) -> ConnectionStatus {
        ConnectionStatus {
            coordinates: Some(coordinates.clone()),
            uuid: conn.uuid,
            local: LocalConnectionStatus {
                connection_type: conn_type,
                cert_info: CertParsingResult::from(&conn.certificate),
            },
            remote: match agent_rec_api {
                Some(agent_rec_api) => {
                    Remote::StatusResponse(Self::query_remote(coordinates, conn, agent_rec_api))
                }
                None => Remote::QueryDisabled,
            },
        }
    }

    fn from_imported_conn(conn: &config::Connection) -> ConnectionStatus {
        ConnectionStatus {
            coordinates: None,
            uuid: conn.uuid,
            local: LocalConnectionStatus {
                connection_type: config::ConnectionType::Pull,
                cert_info: CertParsingResult::from(&conn.certificate),
            },
            remote: Remote::Imported,
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
                lines.push(mark_problematic("Certificate parsing failed"))
            }
        }
        lines
    }

    fn remote_conn_type_str(
        local_conn_type: &config::ConnectionType,
        remote_conn_type: &Option<config::ConnectionType>,
    ) -> String {
        match remote_conn_type {
            Some(ct) => {
                if ct == local_conn_type {
                    format!("{}", ct)
                } else {
                    mark_problematic(&format!("{}", ct))
                }
            }
            None => mark_problematic("unknown"),
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
                    mark_problematic("unknown")
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
                "Connection type: {}",
                ConnectionStatus::remote_conn_type_str(
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
                match &remote_conn_stat.host_name {
                    Some(hn) => hn,
                    None => "unknown",
                }
            ),
        ]
    }

    fn remote_lines_readable(&self) -> Vec<String> {
        match &self.remote {
            Remote::StatusResponse(remote_conn_stat) => match &remote_conn_stat {
                Ok(remote_conn_stat) => Self::remote_lines_success_readable(
                    remote_conn_stat,
                    &self.local.connection_type,
                ),
                Err(err) => {
                    vec![mark_problematic(&format!("Error: {}", err))]
                }
            },
            Remote::Imported => vec![String::from("No remote address (imported connection)")],
            Remote::QueryDisabled => vec![String::from("Remote query disabled")],
        }
    }

    fn to_human_readable(&self) -> String {
        format!(
            "{}\n\tUUID: {}\n\tLocal:\n\t\t{}\n\tRemote:\n\t\t{}",
            match &self.coordinates {
                Some(coord) => format!("Connection: {}", coord),
                None => "Imported connection:".to_string(),
            },
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
        pull_config: &config::PullConfig,
        agent_rec_api: &Option<impl agent_receiver_api::Status>,
    ) -> Status {
        let mut conn_stats = Vec::new();

        for (coordinates, push_conn) in registry.push_connections() {
            conn_stats.push(ConnectionStatus::from_standard_conn(
                coordinates,
                push_conn,
                config::ConnectionType::Push,
                agent_rec_api,
            ));
        }
        for (coordinates, pull_conn) in registry.standard_pull_connections() {
            conn_stats.push(ConnectionStatus::from_standard_conn(
                coordinates,
                pull_conn,
                config::ConnectionType::Pull,
                agent_rec_api,
            ));
        }
        for imp_pull_conn in registry.imported_pull_connections() {
            conn_stats.push(ConnectionStatus::from_imported_conn(imp_pull_conn));
        }

        Status {
            version: String::from(constants::VERSION),
            agent_socket_operational: pull_config.agent_channel.operational(),
            ip_allowlist: pull_config.allowed_ip.to_vec(),
            allow_legacy_pull: pull_config.allow_legacy_pull(),
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
            "Version: {}\nAgent socket: {}\nIP allowlist: {}{}{}",
            self.version,
            match self.agent_socket_operational {
                true => String::from("operational"),
                false => mark_problematic("inoperational"),
            },
            match self.ip_allowlist.is_empty() {
                true => String::from("any"),
                false => self.ip_allowlist.join(" "),
            },
            match self.allow_legacy_pull {
                true => "\nLegacy mode: enabled",
                false => "",
            },
            if self.connections.is_empty() {
                String::from("\nNo connections")
            } else {
                format!(
                    "\n\n\n{}",
                    self.connections
                        .iter()
                        .map(|conn_stat| format!("{}", conn_stat))
                        .collect::<Vec<String>>()
                        .join("\n\n\n"),
                )
            }
        )
    }
}

fn mark_problematic(to_mark: &str) -> String {
    format!("{} (!!)", to_mark)
}

fn _status(
    registry: &config::Registry,
    pull_config: &config::PullConfig,
    json: bool,
    agent_rec_api: &Option<impl agent_receiver_api::Status>,
) -> AnyhowResult<String> {
    Status::from(registry, pull_config, agent_rec_api).to_string(json)
}

pub fn status(
    registry: &config::Registry,
    pull_config: &config::PullConfig,
    client_config: config::ClientConfig,
    json: bool,
    query_remote: bool,
) -> AnyhowResult<()> {
    println!(
        "{}",
        _status(
            registry,
            pull_config,
            json,
            &match query_remote {
                true => Some(agent_receiver_api::Api {
                    use_proxy: client_config.use_proxy
                }),
                false => None,
            }
        )?
    );
    Ok(())
}

#[cfg(test)]
mod test_status {
    use super::*;
    use crate::cli;
    use crate::config::TOMLLoader;
    use anyhow::anyhow;
    use std::str::FromStr;

    #[test]
    fn test_connection_status_remote_disabled() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    coordinates: Some(site_spec::Coordinates::from_str("localhost:8000/site").unwrap()),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::QueryDisabled
                }
            ),
            String::from(
                "Connection: localhost:8000/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tRemote query disabled"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_normal() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    coordinates: Some(site_spec::Coordinates::from_str("localhost:8000/site").unwrap()),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::StatusResponse(Ok(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: None,
                            host_name: Some(String::from("my-host")),
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
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
                    coordinates: Some(site_spec::Coordinates::from_str("localhost:8000/site").unwrap()),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::StatusResponse(Ok(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: Some(agent_receiver_api::HostStatus::Discoverable),
                            host_name: Some(String::from("my-host")),
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
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
                    coordinates: None,
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::Imported,
                }
            ),
            String::from(
                "Imported connection:\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
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
    fn test_connection_status_fmt_error() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    coordinates: Some(site_spec::Coordinates::from_str("localhost:8000/site").unwrap()),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::StatusResponse(Err(anyhow!("You shall not pass")))
                }
            ),
            String::from(
                "Connection: localhost:8000/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection type: pull-agent\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tError: You shall not pass (!!)"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_mismatch_conn_type() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    coordinates: Some(site_spec::Coordinates::from_str("localhost:8000/site").unwrap()),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::StatusResponse(Ok(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Push),
                            registration_state: None,
                            host_name: Some(String::from("my-host")),
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
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
                    coordinates: Some(site_spec::Coordinates::from_str("localhost:8000/site").unwrap()),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        })
                    },
                    remote: Remote::StatusResponse(Ok(
                        RemoteConnectionStatus {
                            connection_type: Some(config::ConnectionType::Pull),
                            registration_state: None,
                            host_name: None,
                        }
                    ))
                }
            ),
            String::from(
                "Connection: localhost:8000/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
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
            version: String::from("1.0.0"),
            agent_socket_operational: true,
            ip_allowlist: vec![String::from("192.168.1.13"), String::from("[::1]")],
            allow_legacy_pull: false,
            connections: vec![
                ConnectionStatus {
                    coordinates: Some(
                        site_spec::Coordinates::from_str("localhost:8000/site").unwrap(),
                    ),
                    uuid: uuid::Uuid::from_str("50611369-7a42-4c0b-927e-9a14330401fe").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Pull,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        }),
                    },
                    remote: Remote::StatusResponse(Ok(RemoteConnectionStatus {
                        connection_type: Some(config::ConnectionType::Pull),
                        registration_state: None,
                        host_name: Some(String::from("my-host")),
                    })),
                },
                ConnectionStatus {
                    coordinates: Some(
                        site_spec::Coordinates::from_str("somewhere:8000/site2").unwrap(),
                    ),
                    uuid: uuid::Uuid::from_str("3c87778b-8bb8-434d-bcc6-6d05f2668c80").unwrap(),
                    local: LocalConnectionStatus {
                        connection_type: config::ConnectionType::Push,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site2' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        }),
                    },
                    remote: Remote::StatusResponse(Ok(RemoteConnectionStatus {
                        connection_type: Some(config::ConnectionType::Push),
                        registration_state: None,
                        host_name: Some(String::from("my-host2")),
                    })),
                },
            ],
        }
    }

    #[test]
    fn test_status_str_human_readable() {
        assert_eq!(
            build_status().to_string(false).unwrap(),
            "Version: 1.0.0\n\
             Agent socket: operational\n\
             IP allowlist: 192.168.1.13 [::1]\n\n\n\
             Connection: localhost:8000/site\n\
             \tUUID: 50611369-7a42-4c0b-927e-9a14330401fe\n\
             \tLocal:\n\
             \t\tConnection type: pull-agent\n\
             \t\tCertificate issuer: Site 'site' local CA\n\
             \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
             \tRemote:\n\
             \t\tConnection type: pull-agent\n\
             \t\tRegistration state: operational\n\
             \t\tHost name: my-host\n\n\n\
             Connection: somewhere:8000/site2\n\
             \tUUID: 3c87778b-8bb8-434d-bcc6-6d05f2668c80\n\
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
                version: String::from("2.3r18"),
                agent_socket_operational: false,
                ip_allowlist: vec![],
                allow_legacy_pull: true,
                connections: vec![],
            }
            .to_string(false)
            .unwrap(),
            "Version: 2.3r18\n\
             Agent socket: inoperational (!!)\n\
             IP allowlist: any\n\
             Legacy mode: enabled\n\
             No connections"
        );
    }

    struct MockApi {}

    impl agent_receiver_api::Status for MockApi {
        fn status(
            &self,
            _base_url: &reqwest::Url,
            _connection: &config::Connection,
        ) -> AnyhowResult<agent_receiver_api::StatusResponse> {
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
            site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            config::Connection {
                uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );
        let registry = config::Registry::new(
            config::RegisteredConnections {
                push,
                pull: std::collections::HashMap::new(),
                pull_imported: std::collections::HashSet::new(),
            },
            tempfile::NamedTempFile::new().unwrap(),
        )
        .unwrap();

        assert_eq!(
            _status(
                &registry,
                &config::PullConfig::new(
                    config::RuntimeConfig::new().unwrap(),
                    cli::PullOpts {
                        port: None,
                        #[cfg(windows)]
                        agent_channel: None,
                        allowed_ip: None,
                    },
                    config::LegacyPullMarker::new(tempfile::NamedTempFile::new().unwrap()),
                    registry.clone()
                )
                .unwrap(),
                false,
                &Some(MockApi {}),
            )
            .unwrap(),
            format!(
                "Version: {}\n\
                 Agent socket: {}\n\
                 IP allowlist: any\n\n\n\
                 Connection: server:8000/push-site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection type: push-agent\n\
                 \t\tCertificate parsing failed (!!)\n\
                 \tRemote:\n\
                 \t\tConnection type: pull-agent (!!)\n\
                 \t\tRegistration state: operational\n\
                 \t\tHost name: host",
                constants::VERSION,
                if cfg!(unix) {
                    "inoperational (!!)"
                } else {
                    "operational"
                }
            )
        );
    }
}
