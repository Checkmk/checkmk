// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{agent_receiver_api, certs, config, site_spec, version};
use anyhow::{Context, Result as AnyhowResult};
use log::debug;
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
    connection_mode: config::ConnectionMode,
    cert_info: CertParsingResult,
}

enum Remote {
    StatusResponse(AnyhowResult<agent_receiver_api::RegistrationStatusV2Response>),
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
    #[serde(flatten)]
    site_data: Option<SiteData>,
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    local: LocalConnectionStatus,
    remote: Remote,
}

#[derive(serde::Serialize)]
struct SiteData {
    site_id: site_spec::SiteID,
    receiver_port: u16,
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
            from: certs::render_asn1_time(&x509.validity().not_before),
            to: certs::render_asn1_time(&x509.validity().not_after),
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
        site_id: &site_spec::SiteID,
        conn: &config::TrustedConnectionWithRemote,
        agent_rec_api: &impl agent_receiver_api::RegistrationStatusV2,
    ) -> AnyhowResult<agent_receiver_api::RegistrationStatusV2Response> {
        agent_rec_api.registration_status_v2(
            &site_spec::make_site_url(site_id, &conn.receiver_port)?,
            &conn.trust,
        )
    }

    fn from_standard_conn(
        site_id: &site_spec::SiteID,
        conn: &config::TrustedConnectionWithRemote,
        conn_mode: config::ConnectionMode,
        agent_rec_api: &Option<impl agent_receiver_api::RegistrationStatusV2>,
    ) -> ConnectionStatus {
        ConnectionStatus {
            site_data: Some(SiteData {
                site_id: site_id.clone(),
                receiver_port: conn.receiver_port,
            }),
            uuid: conn.trust.uuid,
            local: LocalConnectionStatus {
                connection_mode: conn_mode,
                cert_info: CertParsingResult::from(&conn.trust.certificate),
            },
            remote: match agent_rec_api {
                Some(agent_rec_api) => {
                    Remote::StatusResponse(Self::query_remote(site_id, conn, agent_rec_api))
                }
                None => Remote::QueryDisabled,
            },
        }
    }

    fn from_imported_conn(conn: &config::TrustedConnection) -> ConnectionStatus {
        ConnectionStatus {
            site_data: None,
            uuid: conn.uuid,
            local: LocalConnectionStatus {
                connection_mode: config::ConnectionMode::Pull,
                cert_info: CertParsingResult::from(&conn.certificate),
            },
            remote: Remote::Imported,
        }
    }

    fn local_lines_readable(&self) -> Vec<String> {
        let mut lines = vec![];
        lines.push(format!("Connection mode: {}", self.local.connection_mode));
        lines.push(format!(
            "Connecting to receiver port: {}",
            if let Some(site_data) = &self.site_data {
                site_data.receiver_port.to_string()
            } else {
                String::from("None (imported connection)")
            }
        ));
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

    fn remote_lines_readable(&self) -> Vec<String> {
        match &self.remote {
            Remote::StatusResponse(registration_status_v2_response) => {
                match &registration_status_v2_response {
                    Ok(registration_status_v2_response) => Self::remote_lines_success_readable(
                        registration_status_v2_response,
                        &self.local.connection_mode,
                    ),
                    Err(err) => {
                        vec![mark_problematic(&format!("Error: {err}"))]
                    }
                }
            }
            Remote::Imported => vec![String::from("No remote address (imported connection)")],
            Remote::QueryDisabled => vec![String::from("Remote query disabled")],
        }
    }

    fn remote_lines_success_readable(
        registration_status_v2_response: &agent_receiver_api::RegistrationStatusV2Response,
        local_conn_mode: &config::ConnectionMode,
    ) -> Vec<String> {
        match registration_status_v2_response {
            agent_receiver_api::RegistrationStatusV2Response::NotRegistered => {
                vec![mark_problematic("Not registered")]
            }
            agent_receiver_api::RegistrationStatusV2Response::Registered(
                registration_status_v2_response_registered,
            ) => {
                vec![
                    format!(
                        "Connection mode: {}",
                        if &registration_status_v2_response_registered.connection_mode
                            == local_conn_mode
                        {
                            registration_status_v2_response_registered
                                .connection_mode
                                .to_string()
                        } else {
                            mark_problematic(
                                &registration_status_v2_response_registered.connection_mode,
                            )
                        },
                    ),
                    format!(
                        "Hostname: {}",
                        registration_status_v2_response_registered.hostname
                    ),
                ]
            }
        }
    }

    fn to_human_readable(&self) -> String {
        format!(
            "{}\n\tUUID: {}\n\tLocal:\n\t\t{}\n\tRemote:\n\t\t{}",
            match &self.site_data {
                Some(site_data) => format!("Connection: {}", &site_data.site_id),
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
        agent_rec_api: &Option<impl agent_receiver_api::RegistrationStatusV2>,
    ) -> Status {
        let mut conn_stats = Vec::new();

        for (site_id, push_conn) in registry.get_push_connections() {
            conn_stats.push(ConnectionStatus::from_standard_conn(
                site_id,
                push_conn,
                config::ConnectionMode::Push,
                agent_rec_api,
            ));
        }
        for (site_id, pull_conn) in registry.get_standard_pull_connections() {
            conn_stats.push(ConnectionStatus::from_standard_conn(
                site_id,
                pull_conn,
                config::ConnectionMode::Pull,
                agent_rec_api,
            ));
        }
        for imp_pull_conn in registry.get_imported_pull_connections() {
            conn_stats.push(ConnectionStatus::from_imported_conn(imp_pull_conn));
        }

        Status {
            version: String::from(version::VERSION),
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
            Ok(format!("{self}"))
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
                        .map(|conn_stat| format!("{conn_stat}"))
                        .collect::<Vec<String>>()
                        .join("\n\n\n"),
                )
            }
        )
    }
}

fn mark_problematic(to_mark: &(impl std::fmt::Display + ?Sized)) -> String {
    format!("{to_mark} (!!)")
}

fn _status(
    registry: &config::Registry,
    pull_config: &config::PullConfig,
    json: bool,
    agent_rec_api: &Option<impl agent_receiver_api::RegistrationStatusV2>,
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
    debug!("Mode status started");
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
    debug!("Mode status finished");
    Ok(())
}

#[cfg(test)]
mod test_status {
    use super::*;
    use crate::agent_receiver_api::RegistrationStatusV2ResponseRegistered;
    use crate::cli;
    use anyhow::anyhow;
    use std::str::FromStr;

    fn cert_info() -> CertInfo {
        CertInfo {
            issuer: String::from("Site 'site' local CA"),
            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
        }
    }

    fn local_connection_status() -> LocalConnectionStatus {
        LocalConnectionStatus {
            connection_mode: config::ConnectionMode::Pull,
            cert_info: CertParsingResult::Success(cert_info()),
        }
    }

    #[test]
    fn test_connection_status_remote_disabled() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("localhost/site").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: LocalConnectionStatus {
                        connection_mode: config::ConnectionMode::Pull,
                        cert_info: CertParsingResult::Success(cert_info())
                    },
                    remote: Remote::QueryDisabled
                }
            ),
            String::from(
                "Connection: localhost/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tConnecting to receiver port: 8000\n\
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
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("localhost/site").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: local_connection_status(),
                    remote: Remote::StatusResponse(Ok(
                        agent_receiver_api::RegistrationStatusV2Response::Registered(
                            agent_receiver_api::RegistrationStatusV2ResponseRegistered {
                                connection_mode: config::ConnectionMode::Pull,
                                hostname: String::from("my-host"),
                            }
                        )
                    ))
                }
            ),
            String::from(
                "Connection: localhost/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tConnecting to receiver port: 8000\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tHostname: my-host"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_imported() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    site_data: None,
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: local_connection_status(),
                    remote: Remote::Imported,
                }
            ),
            String::from(
                "Imported connection:\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tConnecting to receiver port: None (imported connection)\n\
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
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("localhost/site").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: local_connection_status(),
                    remote: Remote::StatusResponse(Err(anyhow!("You shall not pass")))
                }
            ),
            String::from(
                "Connection: localhost/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tConnecting to receiver port: 8000\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tError: You shall not pass (!!)"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_mismatch_conn_mode() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("localhost/site").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: local_connection_status(),
                    remote: Remote::StatusResponse(Ok(
                        agent_receiver_api::RegistrationStatusV2Response::Registered(
                            agent_receiver_api::RegistrationStatusV2ResponseRegistered {
                                connection_mode: config::ConnectionMode::Push,
                                hostname: String::from("my-host"),
                            }
                        )
                    ))
                }
            ),
            String::from(
                "Connection: localhost/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tConnecting to receiver port: 8000\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tConnection mode: push-agent (!!)\n\
                 \t\tHostname: my-host"
            )
        );
    }

    #[test]
    fn test_connection_status_fmt_not_registered() {
        assert_eq!(
            format!(
                "{}",
                ConnectionStatus {
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("localhost/site").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("99f56bbc-5965-4b34-bc70-1959ad1d32d6").unwrap(),
                    local: local_connection_status(),
                    remote: Remote::StatusResponse(Ok(
                        agent_receiver_api::RegistrationStatusV2Response::NotRegistered
                    ))
                }
            ),
            String::from(
                "Connection: localhost/site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: pull-agent\n\
                 \t\tConnecting to receiver port: 8000\n\
                 \t\tCertificate issuer: Site 'site' local CA\n\
                 \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
                 \tRemote:\n\
                 \t\tNot registered (!!)"
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
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("localhost/site").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("50611369-7a42-4c0b-927e-9a14330401fe").unwrap(),
                    local: local_connection_status(),
                    remote: Remote::StatusResponse(Ok(
                        agent_receiver_api::RegistrationStatusV2Response::Registered(
                            agent_receiver_api::RegistrationStatusV2ResponseRegistered {
                                connection_mode: config::ConnectionMode::Pull,
                                hostname: String::from("my-host"),
                            },
                        ),
                    )),
                },
                ConnectionStatus {
                    site_data: Some(SiteData {
                        site_id: site_spec::SiteID::from_str("somewhere/site2").unwrap(),
                        receiver_port: 8000,
                    }),
                    uuid: uuid::Uuid::from_str("3c87778b-8bb8-434d-bcc6-6d05f2668c80").unwrap(),
                    local: LocalConnectionStatus {
                        connection_mode: config::ConnectionMode::Push,
                        cert_info: CertParsingResult::Success(CertInfo {
                            issuer: String::from("Site 'site2' local CA"),
                            from: String::from("Thu, 16 Dec 2021 08:18:41 +0000"),
                            to: String::from("Tue, 18 Apr 3020 08:18:41 +0000"),
                        }),
                    },
                    remote: Remote::StatusResponse(Ok(
                        agent_receiver_api::RegistrationStatusV2Response::Registered(
                            agent_receiver_api::RegistrationStatusV2ResponseRegistered {
                                connection_mode: config::ConnectionMode::Push,
                                hostname: String::from("my-host2"),
                            },
                        ),
                    )),
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
             Connection: localhost/site\n\
             \tUUID: 50611369-7a42-4c0b-927e-9a14330401fe\n\
             \tLocal:\n\
             \t\tConnection mode: pull-agent\n\
             \t\tConnecting to receiver port: 8000\n\
             \t\tCertificate issuer: Site 'site' local CA\n\
             \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
             \tRemote:\n\
             \t\tConnection mode: pull-agent\n\
             \t\tHostname: my-host\n\n\n\
             Connection: somewhere/site2\n\
             \tUUID: 3c87778b-8bb8-434d-bcc6-6d05f2668c80\n\
             \tLocal:\n\
             \t\tConnection mode: push-agent\n\
             \t\tConnecting to receiver port: 8000\n\
             \t\tCertificate issuer: Site 'site2' local CA\n\
             \t\tCertificate validity: Thu, 16 Dec 2021 08:18:41 +0000 - Tue, 18 Apr 3020 08:18:41 +0000\n\
             \tRemote:\n\
             \t\tConnection mode: push-agent\n\
             \t\tHostname: my-host2"
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

    impl agent_receiver_api::RegistrationStatusV2 for MockApi {
        fn registration_status_v2(
            &self,
            _base_url: &reqwest::Url,
            _connection: &config::TrustedConnection,
        ) -> AnyhowResult<agent_receiver_api::RegistrationStatusV2Response> {
            Ok(
                agent_receiver_api::RegistrationStatusV2Response::Registered(
                    agent_receiver_api::RegistrationStatusV2ResponseRegistered {
                        hostname: String::from("host"),
                        connection_mode: config::ConnectionMode::Pull,
                    },
                ),
            )
        }
    }

    #[test]
    fn test_status_end_to_end() {
        let r = config::test_helpers::TestRegistry::new().add_connection(
            &config::ConnectionMode::Push,
            "server/push-site",
            "99f56bbc-5965-4b34-bc70-1959ad1d32d6",
        );

        assert_eq!(
            _status(
                &r.registry,
                &config::PullConfig::new(
                    config::RuntimeConfig::default(),
                    cli::PullOpts {
                        port: None,
                        #[cfg(windows)]
                        agent_channel: None,
                    },
                    r.registry.clone()
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
                 Connection: server/push-site\n\
                 \tUUID: 99f56bbc-5965-4b34-bc70-1959ad1d32d6\n\
                 \tLocal:\n\
                 \t\tConnection mode: push-agent\n\
                 \t\tConnecting to receiver port: 8000\n\
                 \t\tCertificate parsing failed (!!)\n\
                 \tRemote:\n\
                 \t\tConnection mode: pull-agent (!!)\n\
                 \t\tHostname: host",
                version::VERSION,
                if cfg!(unix) {
                    "inoperational (!!)"
                } else {
                    "operational"
                }
            )
        );
    }

    #[test]
    fn test_remote_lines_success_readable_not_registered() {
        assert_eq!(
            "Not registered (!!)",
            ConnectionStatus::remote_lines_success_readable(
                &agent_receiver_api::RegistrationStatusV2Response::NotRegistered,
                &config::ConnectionMode::Push
            )
            .join("\n")
        );
        assert_eq!(
            "Not registered (!!)",
            ConnectionStatus::remote_lines_success_readable(
                &agent_receiver_api::RegistrationStatusV2Response::NotRegistered,
                &config::ConnectionMode::Pull
            )
            .join("\n")
        );
    }

    // macro to allow testing combinations of input for ConnectionStatus::remote_lines_success_readable.
    macro_rules! remote_lines_success_readable_tests {
        ($($name:ident: $value:expr,)*) => {
        $(
            #[test]
            fn $name() {
                let (hostname, connection_mode_registered, connection_mode_local, expected) = $value;
                let registered = RegistrationStatusV2ResponseRegistered {
                    hostname: hostname.to_string(),
                    connection_mode: connection_mode_registered,
                };
                let registration_status_v2_response = agent_receiver_api::RegistrationStatusV2Response::Registered(registered);
                assert_eq!(expected, ConnectionStatus::remote_lines_success_readable(&registration_status_v2_response, &connection_mode_local).join("\n"));
                }
        )*
        }
    }

    remote_lines_success_readable_tests! {
        test_remote_lines_success_readable_push_push: ("host_01",config::ConnectionMode::Push, config::ConnectionMode::Push, "Connection mode: push-agent\nHostname: host_01"),
        test_remote_lines_success_readable_pull_pull: ("host_02",config::ConnectionMode::Pull, config::ConnectionMode::Pull, "Connection mode: pull-agent\nHostname: host_02"),
        test_remote_lines_success_readable_pull_push: ("host_03",config::ConnectionMode::Pull, config::ConnectionMode::Push, "Connection mode: pull-agent (!!)\nHostname: host_03"),
        test_remote_lines_success_readable_push_pull: ("host_04",config::ConnectionMode::Push, config::ConnectionMode::Pull, "Connection mode: push-agent (!!)\nHostname: host_04"),

    }
}
