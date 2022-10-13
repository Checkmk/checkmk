// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{agent_receiver_api, certs, config, constants, misc, site_spec, types};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use log::{error, info};

trait TrustEstablishing {
    fn prompt_server_certificate(&self, server: &str, port: &u16) -> AnyhowResult<()>;
    fn prompt_password(&self, user: &str) -> AnyhowResult<String>;
}

struct InteractiveTrust {}

impl InteractiveTrust {
    fn display_cert(server: &str, port: &u16) -> AnyhowResult<()> {
        let pem_str = certs::fetch_server_cert_pem(server, port)?;
        let pem = certs::parse_pem(&pem_str)?;
        let x509 = pem.parse_x509()?;
        let validity = x509.validity();

        eprintln!("PEM-encoded certificate:\n{}", pem_str);
        eprintln!(
            "Issued by:\n\t{}",
            certs::common_names(x509.issuer())?.join(", ")
        );
        eprintln!(
            "Issued to:\n\t{}",
            certs::common_names(x509.subject())?.join(", ")
        );
        eprintln!(
            "Validity:\n\tFrom {}\n\tTo   {}",
            validity.not_before.to_rfc2822(),
            validity.not_after.to_rfc2822(),
        );
        Ok(())
    }
}

impl TrustEstablishing for InteractiveTrust {
    fn prompt_server_certificate(&self, server: &str, port: &u16) -> AnyhowResult<()> {
        eprintln!(
            "Attempting to register at {}, port {}. Server certificate details:\n",
            server, port,
        );
        InteractiveTrust::display_cert(server, port)?;
        eprintln!();
        eprintln!("Do you want to establish this connection? [Y/n]");
        eprint!("> ");
        loop {
            let mut answer = String::new();
            std::io::stdin()
                .read_line(&mut answer)
                .context("Failed to read answer from standard input")?;
            match answer.to_lowercase().trim() {
                "y" | "" => return Ok(()),
                "n" => {
                    return Err(anyhow!(format!(
                        "Cannot continue without trusting {}, port {}",
                        server, port
                    )))
                }
                _ => {
                    eprintln!("Please answer 'y' or 'n'");
                    eprint!("> ");
                }
            }
        }
    }

    fn prompt_password(&self, user: &str) -> AnyhowResult<String> {
        eprintln!();
        eprint!("Please enter password for '{}'\n> ", user);
        rpassword::read_password().context("Failed to obtain API password")
    }
}

fn registration_server_cert<'a>(
    config: &'a config::RegistrationConnectionConfig,
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<Option<&'a str>> {
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
                trust_establisher
                    .prompt_server_certificate(&config.site_id.server, &config.receiver_port)?;
            }
            Ok(None)
        }
    }
}

fn prepare_registration(
    config: &config::RegistrationConnectionConfig,
    agent_rec_api: &impl agent_receiver_api::Pairing,
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<(types::Credentials, PairingResult)> {
    let uuid = uuid::Uuid::new_v4();
    let (csr, private_key) = certs::make_csr(&uuid.to_string()).context("Error creating CSR.")?;
    let root_cert = registration_server_cert(config, trust_establisher)?;
    let credentials = types::Credentials {
        username: config.username.clone(),
        password: if let Some(password) = &config.password {
            String::from(password)
        } else {
            trust_establisher.prompt_password(&config.username)?
        },
    };
    let pairing_response = agent_rec_api
        .pair(
            &site_spec::make_site_url(&config.site_id, &config.receiver_port)?,
            root_cert,
            csr,
            &credentials,
        )
        .context(format!(
            "Error pairing with {}, port {}",
            &config.site_id, &config.receiver_port
        ))?;
    Ok((
        credentials,
        PairingResult {
            uuid,
            private_key,
            pairing_response,
        },
    ))
}

struct PairingResult {
    uuid: uuid::Uuid,
    private_key: String,
    pairing_response: agent_receiver_api::PairingResponse,
}

trait RegistrationEndpointCall {
    fn call(
        &self,
        config: &config::RegistrationConnectionConfig,
        credentials: &types::Credentials,
        pairing_result: &PairingResult,
        agent_rec_api: &impl agent_receiver_api::Registration,
    ) -> AnyhowResult<()>;
}

struct HostNameRegistration<'a> {
    host_name: &'a str,
}

impl RegistrationEndpointCall for HostNameRegistration<'_> {
    fn call(
        &self,
        config: &config::RegistrationConnectionConfig,
        credentials: &types::Credentials,
        pairing_result: &PairingResult,
        agent_rec_api: &impl agent_receiver_api::Registration,
    ) -> AnyhowResult<()> {
        agent_rec_api
            .register_with_hostname(
                &site_spec::make_site_url(&config.site_id, &config.receiver_port)?,
                &pairing_result.pairing_response.root_cert,
                credentials,
                &pairing_result.uuid,
                self.host_name,
            )
            .context(format!(
                "Error registering with host name at {}, port {}",
                &config.site_id, &config.receiver_port
            ))
    }
}

struct AgentLabelsRegistration<'a> {
    agent_labels: &'a types::AgentLabels,
}

impl RegistrationEndpointCall for AgentLabelsRegistration<'_> {
    fn call(
        &self,
        config: &config::RegistrationConnectionConfig,
        credentials: &types::Credentials,
        pairing_result: &PairingResult,
        agent_rec_api: &impl agent_receiver_api::Registration,
    ) -> AnyhowResult<()> {
        agent_rec_api
            .register_with_agent_labels(
                &site_spec::make_site_url(&config.site_id, &config.receiver_port)?,
                &pairing_result.pairing_response.root_cert,
                credentials,
                &pairing_result.uuid,
                self.agent_labels,
            )
            .context(format!(
                "Error registering with host name at {}, port {}",
                &config.site_id, &config.receiver_port
            ))
    }
}

fn post_registration_conn_type(
    site_id: &site_spec::SiteID,
    connection: &config::TrustedConnectionWithRemote,
    agent_rec_api: &impl agent_receiver_api::Status,
) -> AnyhowResult<config::ConnectionType> {
    loop {
        let status_resp = agent_rec_api.status(
            &site_spec::make_site_url(site_id, &connection.receiver_port)?,
            &connection.trust,
        )?;
        if let Some(agent_receiver_api::HostStatus::Declined) = status_resp.status {
            return Err(anyhow!(
                "Registration declined by Checkmk instance{}",
                if let Some(msg) = status_resp.message {
                    format!(": {}", msg)
                } else {
                    String::from("")
                }
            ));
        }
        if let Some(ct) = status_resp.connection_type {
            return Ok(ct);
        }
        println!("Waiting for registration to complete on Checkmk instance, sleeping 20 s");
        std::thread::sleep(std::time::Duration::from_secs(20));
    }
}

fn direct_registration(
    config: &config::RegistrationConnectionConfig,
    registry: &mut config::Registry,
    agent_rec_api: &(impl agent_receiver_api::Pairing
          + agent_receiver_api::Registration
          + agent_receiver_api::Status),
    trust_establisher: &impl TrustEstablishing,
    endpoint_call: &impl RegistrationEndpointCall,
) -> AnyhowResult<()> {
    let (credentials, pairing_result) =
        prepare_registration(config, agent_rec_api, trust_establisher)?;

    endpoint_call.call(config, &credentials, &pairing_result, agent_rec_api)?;

    let connection = config::TrustedConnectionWithRemote {
        trust: config::TrustedConnection {
            uuid: pairing_result.uuid,
            private_key: pairing_result.private_key,
            certificate: pairing_result.pairing_response.client_cert,
            root_cert: pairing_result.pairing_response.root_cert,
        },
        receiver_port: config.receiver_port,
    };

    registry.register_connection(
        &post_registration_conn_type(&config.site_id, &connection, agent_rec_api)?,
        &config.site_id,
        connection,
    );

    registry.save()?;

    Ok(())
}

fn proxy_registration(
    config: &config::RegistrationConfigHostName,
    agent_rec_api: &(impl agent_receiver_api::Pairing + agent_receiver_api::Registration),
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<()> {
    let (credentials, pairing_result) =
        prepare_registration(&config.connection_config, agent_rec_api, trust_establisher)?;

    HostNameRegistration {
        host_name: &config.host_name,
    }
    .call(
        &config.connection_config,
        &credentials,
        &pairing_result,
        agent_rec_api,
    )?;

    println!(
        "{}",
        serde_json::to_string(&ProxyPullData {
            agent_controller_version: String::from(constants::VERSION),
            connection: config::TrustedConnection {
                uuid: pairing_result.uuid,
                private_key: pairing_result.private_key,
                certificate: pairing_result.pairing_response.client_cert,
                root_cert: pairing_result.pairing_response.root_cert,
            }
        })?
    );
    Ok(())
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct ProxyPullData {
    pub agent_controller_version: String,
    pub connection: config::TrustedConnection,
}

impl config::JSONLoader for ProxyPullData {}

pub fn register_host_name(
    config: &config::RegistrationConfigHostName,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    direct_registration(
        &config.connection_config,
        registry,
        &agent_receiver_api::Api {
            use_proxy: config.connection_config.client_config.use_proxy,
        },
        &InteractiveTrust {},
        &HostNameRegistration {
            host_name: &config.host_name,
        },
    )?;
    println!("Registration complete.");
    Ok(())
}

pub fn register_agent_labels(
    config: &config::RegistrationConfigAgentLabels,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    direct_registration(
        &config.connection_config,
        registry,
        &agent_receiver_api::Api {
            use_proxy: config.connection_config.client_config.use_proxy,
        },
        &InteractiveTrust {},
        &AgentLabelsRegistration {
            agent_labels: &config.agent_labels,
        },
    )?;
    println!("Registration complete. It may take few minutes until the newly created host and its services are visible in the site.");
    Ok(())
}

pub fn register_pre_configured(
    pre_configured_connections: &config::PreConfiguredConnections,
    client_config: &config::ClientConfig,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    _register_pre_configured(
        pre_configured_connections,
        client_config,
        registry,
        &RegistrationWithAgentLabelsImpl {},
    )
}

fn _register_pre_configured(
    pre_configured_connections: &config::PreConfiguredConnections,
    client_config: &config::ClientConfig,
    registry: &mut config::Registry,
    registration_with_labels: &impl RegistrationWithAgentLabels,
) -> AnyhowResult<()> {
    for (site_id, pre_configured_connection) in pre_configured_connections.connections.iter() {
        if let Err(error) = process_pre_configured_connection(
            site_id,
            pre_configured_connection,
            &pre_configured_connections.agent_labels,
            client_config,
            registry,
            registration_with_labels,
        ) {
            error!(
                "Error while processing connection {}: {}",
                site_id,
                misc::anyhow_error_to_human_readable(&error)
            )
        }
    }

    if !pre_configured_connections.keep_vanished_connections {
        delete_vanished_connections(
            registry,
            registry
                .registered_site_ids()
                .filter(|site_id| !pre_configured_connections.connections.contains_key(site_id))
                .cloned()
                .collect::<Vec<site_spec::SiteID>>()
                .iter(),
        )
    }

    registry
        .save()
        .context("Failed to save registered connections")
}

trait RegistrationWithAgentLabels {
    fn register(
        &self,
        config: &config::RegistrationConfigAgentLabels,
        registry: &mut config::Registry,
    ) -> AnyhowResult<()>;
}

struct RegistrationWithAgentLabelsImpl;

impl RegistrationWithAgentLabels for RegistrationWithAgentLabelsImpl {
    fn register(
        &self,
        config: &config::RegistrationConfigAgentLabels,
        registry: &mut config::Registry,
    ) -> AnyhowResult<()> {
        register_agent_labels(config, registry)
    }
}

fn process_pre_configured_connection(
    site_id: &site_spec::SiteID,
    pre_configured: &config::PreConfiguredConnection,
    agent_labels: &types::AgentLabels,
    client_config: &config::ClientConfig,
    registry: &mut config::Registry,
    registration_with_labels: &impl RegistrationWithAgentLabels,
) -> AnyhowResult<()> {
    let receiver_port = match pre_configured.port {
        Some(receiver_port) => receiver_port,
        None => site_spec::discover_receiver_port(site_id, client_config)?,
    };

    if let Some(registered_connection) = registry.get_mutable(site_id) {
        registered_connection.receiver_port = receiver_port;
        info!(
            "Updated agent receiver port for existing connection {}",
            site_id
        );
        return Ok(());
    }

    let registration_config = config::RegistrationConfigAgentLabels::new(
        config::RegistrationConnectionConfig {
            site_id: site_id.clone(),
            receiver_port,
            username: pre_configured.credentials.username.clone(),
            password: Some(pre_configured.credentials.password.clone()),
            root_certificate: Some(pre_configured.root_cert.clone()),
            trust_server_cert: false,
            client_config: client_config.clone(),
        },
        agent_labels.clone(),
    )?;

    registration_with_labels.register(&registration_config, registry)?;
    info!("Registered new connection {}", site_id);

    Ok(())
}

fn delete_vanished_connections<'a>(
    registry: &mut config::Registry,
    site_ids_to_delete: impl Iterator<Item = &'a site_spec::SiteID>,
) {
    for site_id in site_ids_to_delete {
        if let Err(error) = registry.delete_standard_connection(site_id) {
            error!(
                "Error deleting vanished connection {}: {}",
                site_id,
                misc::anyhow_error_to_human_readable(&error)
            )
        }
    }

    registry.clear_imported();
}

pub fn proxy_register(config: &config::RegistrationConfigHostName) -> AnyhowResult<()> {
    proxy_registration(
        config,
        &agent_receiver_api::Api {
            use_proxy: config.connection_config.client_config.use_proxy,
        },
        &InteractiveTrust {},
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    const SERVER: &str = "server";
    const PORT: u16 = 8000;
    const SITE: &str = "site";
    const HOST_NAME: &str = "host";
    const USERNAME: &str = "user";

    fn site_id() -> site_spec::SiteID {
        site_spec::SiteID {
            server: String::from(SERVER),
            site: String::from(SITE),
        }
    }

    fn expected_url() -> reqwest::Url {
        site_spec::make_site_url(&site_id(), &PORT).unwrap()
    }

    enum RegistrationMethod {
        HostName,
        AgentLabels,
    }

    struct MockApi {
        expect_root_cert_for_pairing: bool,
        expected_registration_method: Option<RegistrationMethod>,
    }

    impl agent_receiver_api::Pairing for MockApi {
        fn pair(
            &self,
            base_url: &reqwest::Url,
            root_cert: Option<&str>,
            _csr: String,
            _credentials: &types::Credentials,
        ) -> AnyhowResult<agent_receiver_api::PairingResponse> {
            assert!(base_url == &expected_url());
            assert!(root_cert.is_some() == self.expect_root_cert_for_pairing);
            Ok(agent_receiver_api::PairingResponse {
                root_cert: String::from("root_cert"),
                client_cert: String::from("client_cert"),
            })
        }
    }

    impl agent_receiver_api::Registration for MockApi {
        fn register_with_hostname(
            &self,
            base_url: &reqwest::Url,
            _root_cert: &str,
            _credentials: &types::Credentials,
            _uuid: &uuid::Uuid,
            host_name: &str,
        ) -> AnyhowResult<()> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::HostName
            ));
            assert!(base_url == &expected_url());
            assert!(host_name == HOST_NAME);
            Ok(())
        }

        fn register_with_agent_labels(
            &self,
            base_url: &reqwest::Url,
            _root_cert: &str,
            _credentials: &types::Credentials,
            _uuid: &uuid::Uuid,
            ag_labels: &types::AgentLabels,
        ) -> AnyhowResult<()> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::AgentLabels
            ));
            assert!(base_url == &expected_url());
            assert!(ag_labels == &agent_labels());
            Ok(())
        }
    }

    impl agent_receiver_api::Status for MockApi {
        fn status(
            &self,
            base_url: &reqwest::Url,
            _connection: &config::TrustedConnection,
        ) -> AnyhowResult<agent_receiver_api::StatusResponse> {
            assert!(base_url == &expected_url());
            Ok(agent_receiver_api::StatusResponse {
                hostname: Some(String::from(HOST_NAME)),
                status: None,
                connection_type: Some(config::ConnectionType::Pull),
                message: None,
            })
        }
    }

    struct MockInteractiveTrust {
        expect_server_cert_prompt: bool,
        expect_password_prompt: bool,
    }

    impl TrustEstablishing for MockInteractiveTrust {
        fn prompt_server_certificate(&self, server: &str, port: &u16) -> AnyhowResult<()> {
            assert!(self.expect_server_cert_prompt);
            assert!(server == SERVER);
            assert!(port == &PORT);
            Ok(())
        }

        fn prompt_password(&self, user: &str) -> AnyhowResult<String> {
            assert!(self.expect_password_prompt);
            assert_eq!(user, USERNAME);
            Ok(String::from("password"))
        }
    }

    fn registry() -> config::Registry {
        config::Registry::new(tempfile::NamedTempFile::new().unwrap().as_ref()).unwrap()
    }

    fn agent_labels() -> types::AgentLabels {
        let mut al = std::collections::HashMap::new();
        al.insert(String::from("a"), String::from("b"));
        al
    }

    fn registration_connection_config(
        root_certificate: Option<String>,
        password: Option<String>,
        trust_server_cert: bool,
    ) -> config::RegistrationConnectionConfig {
        config::RegistrationConnectionConfig {
            site_id: site_id(),
            receiver_port: PORT,
            username: String::from(USERNAME),
            password,
            root_certificate,
            trust_server_cert,
            client_config: config::ClientConfig {
                use_proxy: false,
                validate_api_cert: false,
            },
        }
    }

    mod test_pair {
        use super::*;

        #[test]
        fn test_interactive_trust() {
            assert!(prepare_registration(
                &registration_connection_config(None, None, false),
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: true,
                    expect_password_prompt: true,
                },
            )
            .is_ok());
        }

        #[test]
        fn test_blind_trust() {
            assert!(prepare_registration(
                &registration_connection_config(None, Some(String::from("password")), true),
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: false,
                    expect_password_prompt: false,
                },
            )
            .is_ok());
        }

        #[test]
        fn test_root_cert_from_config() {
            assert!(prepare_registration(
                &registration_connection_config(
                    Some(String::from("root_certificate")),
                    Some(String::from("password")),
                    false
                ),
                &MockApi {
                    expect_root_cert_for_pairing: true,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: false,
                    expect_password_prompt: false,
                },
            )
            .is_ok());
        }

        #[test]
        fn test_root_cert_from_config_and_blind_trust() {
            assert!(prepare_registration(
                &registration_connection_config(Some(String::from("root_certificate")), None, true),
                &MockApi {
                    expect_root_cert_for_pairing: true,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: false,
                    expect_password_prompt: true,
                },
            )
            .is_ok());
        }
    }

    mod test_register_manual {
        use super::*;

        #[test]
        fn test_host_name() {
            let mut registry = registry();
            assert!(!registry.path().exists());
            assert!(direct_registration(
                &registration_connection_config(None, None, false),
                &mut registry,
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: Some(RegistrationMethod::HostName),
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: true,
                    expect_password_prompt: true,
                },
                &HostNameRegistration {
                    host_name: HOST_NAME
                },
            )
            .is_ok());
            assert!(!registry.is_empty());
            assert!(registry.path().exists());
        }

        #[test]
        fn test_agent_labels() {
            let mut registry = registry();
            assert!(!registry.path().exists());
            assert!(direct_registration(
                &registration_connection_config(
                    Some(String::from("root_certificate")),
                    Some(String::from("password")),
                    false
                ),
                &mut registry,
                &MockApi {
                    expect_root_cert_for_pairing: true,
                    expected_registration_method: Some(RegistrationMethod::AgentLabels),
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: false,
                    expect_password_prompt: false,
                },
                &AgentLabelsRegistration {
                    agent_labels: &agent_labels()
                },
            )
            .is_ok());
            assert!(!registry.is_empty());
            assert!(registry.path().exists());
        }

        #[test]
        fn test_proxy() {
            assert!(proxy_registration(
                &config::RegistrationConfigHostName {
                    connection_config: registration_connection_config(None, None, true),
                    host_name: String::from(HOST_NAME),
                },
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: Some(RegistrationMethod::HostName),
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: false,
                    expect_password_prompt: true,
                },
            )
            .is_ok());
        }
    }

    mod test_register_pre_configured {
        use super::*;

        fn registry() -> config::Registry {
            let mut registry = super::registry();
            registry.register_connection(
                &config::ConnectionType::Pull,
                &site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap(),
                config::TrustedConnectionWithRemote::from(uuid::Uuid::new_v4()),
            );
            registry.register_connection(
                &config::ConnectionType::Pull,
                &site_spec::SiteID::from_str("server/other-pull-site").unwrap(),
                config::TrustedConnectionWithRemote::from(uuid::Uuid::new_v4()),
            );
            registry.register_connection(
                &config::ConnectionType::Push,
                &site_spec::SiteID::from_str("server/pre-baked-push-site").unwrap(),
                config::TrustedConnectionWithRemote::from(uuid::Uuid::new_v4()),
            );
            registry.register_connection(
                &config::ConnectionType::Push,
                &site_spec::SiteID::from_str("server/other-push-site").unwrap(),
                config::TrustedConnectionWithRemote::from(uuid::Uuid::new_v4()),
            );
            registry.register_imported_connection(config::TrustedConnection::from(
                uuid::Uuid::new_v4(),
            ));
            registry
        }

        fn pre_configured_connections(
            keep_vanished_connections: bool,
        ) -> config::PreConfiguredConnections {
            config::PreConfiguredConnections {
                connections: std::collections::HashMap::from([
                    (
                        site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap(),
                        config::PreConfiguredConnection {
                            port: Some(1001),
                            credentials: types::Credentials {
                                username: String::from("user"),
                                password: String::from("password"),
                            },
                            root_cert: String::from("root_cert"),
                        },
                    ),
                    (
                        site_spec::SiteID::from_str("server/pre-baked-pull-site-2").unwrap(),
                        config::PreConfiguredConnection {
                            port: Some(1002),
                            credentials: types::Credentials {
                                username: String::from("user"),
                                password: String::from("password"),
                            },
                            root_cert: String::from("root_cert"),
                        },
                    ),
                    (
                        site_spec::SiteID::from_str("server/pre-baked-push-site").unwrap(),
                        config::PreConfiguredConnection {
                            port: Some(1003),
                            credentials: types::Credentials {
                                username: String::from("user"),
                                password: String::from("password"),
                            },
                            root_cert: String::from("root_cert"),
                        },
                    ),
                    (
                        site_spec::SiteID::from_str("server/pre-baked-push-site-2").unwrap(),
                        config::PreConfiguredConnection {
                            port: Some(1004),
                            credentials: types::Credentials {
                                username: String::from("user"),
                                password: String::from("password"),
                            },
                            root_cert: String::from("root_cert"),
                        },
                    ),
                ]),
                agent_labels: types::AgentLabels::from([(
                    String::from("key"),
                    String::from("value"),
                )]),
                keep_vanished_connections,
            }
        }

        struct MockRegistrationWithAgentLabelsImpl;

        impl RegistrationWithAgentLabels for MockRegistrationWithAgentLabelsImpl {
            fn register(
                &self,
                config: &config::RegistrationConfigAgentLabels,
                registry: &mut config::Registry,
            ) -> AnyhowResult<()> {
                assert!(config.connection_config.password.is_some());
                assert!(config.connection_config.root_certificate.is_some());
                assert!(!config.connection_config.trust_server_cert);
                assert_eq!(config.agent_labels.get("key").unwrap(), "value");
                registry.register_connection(
                    std::collections::HashMap::from([
                        ("server/pre-baked-pull-site", config::ConnectionType::Pull),
                        ("server/pre-baked-pull-site-2", config::ConnectionType::Pull),
                        ("server/pre-baked-push-site", config::ConnectionType::Push),
                        ("server/pre-baked-push-site-2", config::ConnectionType::Push),
                    ])
                    .get(config.connection_config.site_id.to_string().as_str())
                    .unwrap(),
                    &config.connection_config.site_id,
                    config::TrustedConnectionWithRemote {
                        trust: config::TrustedConnection {
                            uuid: uuid::Uuid::new_v4(),
                            private_key: String::from("private_key"),
                            certificate: String::from("certificate"),
                            root_cert: String::from("root_cert"),
                        },
                        receiver_port: config.connection_config.receiver_port,
                    },
                );
                Ok(())
            }
        }

        fn test_registered_standard_connections<'a>(
            expected_site_ids: impl Iterator<Item = &'a str>,
            registered_connections: impl Iterator<
                Item = (
                    &'a site_spec::SiteID,
                    &'a config::TrustedConnectionWithRemote,
                ),
            >,
        ) {
            let mut exp_site_ids: Vec<&str> = expected_site_ids.collect();
            exp_site_ids.sort_unstable();
            let mut reg_site_ids: Vec<String> = registered_connections
                .map(|site_id_and_conn| site_id_and_conn.0.to_string())
                .collect();
            reg_site_ids.sort_unstable();
            assert_eq!(exp_site_ids, reg_site_ids);
        }

        fn test_registry_after_registration(
            keep_vanished_connections: bool,
            registry: &mut config::Registry,
        ) {
            // We reload to ensure that the changes were written to disk
            let mut registry = config::Registry::from_file(registry.path()).unwrap();

            let mut expected_pull_site_ids =
                vec!["server/pre-baked-pull-site", "server/pre-baked-pull-site-2"];
            let mut expected_push_site_ids =
                vec!["server/pre-baked-push-site", "server/pre-baked-push-site-2"];
            if keep_vanished_connections {
                expected_pull_site_ids.push("server/other-pull-site");
                expected_push_site_ids.push("server/other-push-site");
            }
            test_registered_standard_connections(
                expected_pull_site_ids.into_iter(),
                registry.standard_pull_connections(),
            );
            test_registered_standard_connections(
                expected_push_site_ids.into_iter(),
                registry.push_connections(),
            );

            assert_eq!(
                registry
                    .get_mutable(
                        &site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap()
                    )
                    .unwrap()
                    .receiver_port,
                1001
            );
            assert_eq!(
                registry
                    .get_mutable(
                        &site_spec::SiteID::from_str("server/pre-baked-push-site").unwrap()
                    )
                    .unwrap()
                    .receiver_port,
                1003
            );

            assert_eq!(
                registry.imported_pull_connections().count(),
                if keep_vanished_connections { 1 } else { 0 }
            );
        }

        #[test]
        fn test_keep_vanished_connections() {
            let mut registry = registry();
            assert!(_register_pre_configured(
                &pre_configured_connections(true),
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                &mut registry,
                &MockRegistrationWithAgentLabelsImpl {},
            )
            .is_ok());
            test_registry_after_registration(true, &mut registry)
        }

        #[test]
        fn test_remove_vanished_connections() {
            let mut registry = registry();
            assert!(_register_pre_configured(
                &pre_configured_connections(false),
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                &mut registry,
                &MockRegistrationWithAgentLabelsImpl {},
            )
            .is_ok());
            test_registry_after_registration(false, &mut registry)
        }

        #[test]
        fn test_port_update_only() {
            let mut registry = super::registry();
            registry.register_connection(
                &config::ConnectionType::Pull,
                &site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap(),
                config::TrustedConnectionWithRemote::from(uuid::Uuid::new_v4()),
            );
            let pre_configured_connections = config::PreConfiguredConnections {
                connections: std::collections::HashMap::from([(
                    site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap(),
                    config::PreConfiguredConnection {
                        port: Some(1001),
                        credentials: types::Credentials {
                            username: String::from("user"),
                            password: String::from("password"),
                        },
                        root_cert: String::from("root_cert"),
                    },
                )]),
                agent_labels: types::AgentLabels::from([(
                    String::from("key"),
                    String::from("value"),
                )]),
                keep_vanished_connections: true,
            };
            assert!(_register_pre_configured(
                &pre_configured_connections,
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                &mut registry,
                &MockRegistrationWithAgentLabelsImpl {},
            )
            .is_ok());

            // We reload to ensure that the changes were written to disk
            let mut registry = config::Registry::from_file(registry.path()).unwrap();
            assert_eq!(
                registry
                    .get_mutable(
                        &site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap()
                    )
                    .unwrap()
                    .receiver_port,
                1001
            );
        }
    }
}
