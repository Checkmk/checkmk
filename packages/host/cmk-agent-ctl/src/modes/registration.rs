// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{
    agent_receiver_api::{self, RegistrationStatusV2},
    certs, config, constants, misc, site_spec, types,
};
use anyhow::{bail, Context, Result as AnyhowResult};
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

        eprintln!("PEM-encoded certificate:\n{pem_str}");
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
            certs::render_asn1_time(&validity.not_before),
            certs::render_asn1_time(&validity.not_after),
        );
        Ok(())
    }
}

impl TrustEstablishing for InteractiveTrust {
    fn prompt_server_certificate(&self, server: &str, port: &u16) -> AnyhowResult<()> {
        eprintln!("Attempting to register at {server}, port {port}. Server certificate details:\n",);
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
                    bail!(format!(
                        "Cannot continue without trusting {server}, port {port}"
                    ))
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
        eprint!("Please enter password for '{user}'\n> ");
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
            Ok(Some(cert))
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

struct RegistrationInput<'a> {
    root_cert: Option<&'a str>,
    credentials: types::Credentials,
    uuid: uuid::Uuid,
    private_key: String,
    csr: String,
}

fn prepare_registration<'a>(
    config: &'a config::RegistrationConnectionConfig,
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<RegistrationInput<'a>> {
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
    Ok(RegistrationInput {
        root_cert,
        credentials,
        uuid,
        private_key,
        csr,
    })
}

struct RegistrationResult {
    root_cert: String,
    agent_cert: String,
    connection_mode: config::ConnectionMode,
}

impl std::convert::From<agent_receiver_api::RegisterExistingResponse> for RegistrationResult {
    fn from(register_existing_response: agent_receiver_api::RegisterExistingResponse) -> Self {
        Self {
            root_cert: register_existing_response.root_cert,
            agent_cert: register_existing_response.agent_cert,
            connection_mode: register_existing_response.connection_mode,
        }
    }
}

trait RegistrationEndpointCall {
    fn call(
        &self,
        site_url: &reqwest::Url,
        registration_input: &RegistrationInput,
        agent_rec_api: &impl agent_receiver_api::Registration,
    ) -> AnyhowResult<RegistrationResult>;
}

struct RegistrationCallExisting<'a> {
    host_name: &'a str,
}

impl RegistrationEndpointCall for RegistrationCallExisting<'_> {
    fn call(
        &self,
        site_url: &reqwest::Url,
        registration_input: &RegistrationInput,
        agent_rec_api: &impl agent_receiver_api::Registration,
    ) -> AnyhowResult<RegistrationResult> {
        Ok(RegistrationResult::from(
            agent_rec_api
                .register_existing(
                    site_url,
                    &registration_input.root_cert,
                    &registration_input.credentials,
                    &registration_input.uuid,
                    &registration_input.csr,
                    self.host_name,
                )
                .context(format!("Error registering existing host at {}", site_url))?,
        ))
    }
}

struct RegistrationCallNew<'a> {
    agent_labels: &'a types::AgentLabels,
}

impl RegistrationEndpointCall for RegistrationCallNew<'_> {
    fn call(
        &self,
        site_url: &reqwest::Url,
        registration_input: &RegistrationInput,
        agent_rec_api: &impl agent_receiver_api::Registration,
    ) -> AnyhowResult<RegistrationResult> {
        let reg_new_response = agent_rec_api
            .register_new(
                site_url,
                &registration_input.root_cert,
                &registration_input.credentials,
                &registration_input.uuid,
                &registration_input.csr,
                self.agent_labels,
            )
            .context(format!("Error registering new host at {}", site_url))?;

        loop {
            match agent_rec_api
                .register_new_ongoing(
                    site_url,
                    &reg_new_response.root_cert,
                    &registration_input.credentials,
                    &registration_input.uuid,
                )
                .context(format!(
                    "Error querying registration progress at {}",
                    site_url
                ))? {
                agent_receiver_api::RegisterNewOngoingResponse::InProgress => {
                    println!(
                        "Waiting for registration to complete on Checkmk instance, sleeping 20 s"
                    );
                    std::thread::sleep(std::time::Duration::from_secs(20));
                }
                agent_receiver_api::RegisterNewOngoingResponse::Declined(declined_resp) => bail!(
                    "Registration declined by Checkmk instance: {}",
                    declined_resp.reason
                ),
                agent_receiver_api::RegisterNewOngoingResponse::Success(success_resp) => {
                    return Ok(RegistrationResult {
                        root_cert: reg_new_response.root_cert,
                        agent_cert: success_resp.agent_cert,
                        connection_mode: success_resp.connection_mode,
                    })
                }
            }
        }
    }
}

fn direct_registration(
    config: &config::RegistrationConnectionConfig,
    registry: &mut config::Registry,
    agent_rec_api: &impl agent_receiver_api::Registration,
    trust_establisher: &impl TrustEstablishing,
    endpoint_call: &impl RegistrationEndpointCall,
) -> AnyhowResult<()> {
    let registration_input = prepare_registration(config, trust_establisher)?;

    let registration_result = endpoint_call.call(
        &site_spec::make_site_url(&config.site_id, &config.receiver_port)?,
        &registration_input,
        agent_rec_api,
    )?;

    registry.register_connection(
        &registration_result.connection_mode,
        &config.site_id,
        config::TrustedConnectionWithRemote {
            trust: config::TrustedConnection {
                uuid: registration_input.uuid,
                private_key: registration_input.private_key,
                certificate: registration_result.agent_cert,
                root_cert: registration_result.root_cert,
            },
            receiver_port: config.receiver_port,
        },
    );

    registry.save()?;

    Ok(())
}

fn proxy_registration(
    config: &config::RegisterExistingConfig,
    agent_rec_api: &impl agent_receiver_api::Registration,
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<()> {
    let registration_input = prepare_registration(&config.connection_config, trust_establisher)?;

    let registration_result = RegistrationCallExisting {
        host_name: &config.host_name,
    }
    .call(
        &site_spec::make_site_url(
            &config.connection_config.site_id,
            &config.connection_config.receiver_port,
        )?,
        &registration_input,
        agent_rec_api,
    )?;

    if registration_result.connection_mode == config::ConnectionMode::Push {
        eprintln!(
            "WARNING: The host you just registered is configured to be a push host. The imported \
             connection will only work if the monitored host can connect to the monitoring server."
        )
    }

    println!(
        "{}",
        serde_json::to_string(&ProxyPullData {
            agent_controller_version: String::from(constants::VERSION),
            connection: config::TrustedConnection {
                uuid: registration_input.uuid,
                private_key: registration_input.private_key,
                certificate: registration_result.agent_cert,
                root_cert: registration_result.root_cert,
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

pub fn register_existing(
    config: &config::RegisterExistingConfig,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    direct_registration(
        &config.connection_config,
        registry,
        &agent_receiver_api::Api {
            use_proxy: config.connection_config.client_config.use_proxy,
        },
        &InteractiveTrust {},
        &RegistrationCallExisting {
            host_name: &config.host_name,
        },
    )?;
    println!("Registration complete.");
    Ok(())
}

pub fn register_new(
    config: &config::RegisterNewConfig,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    direct_registration(
        &config.connection_config,
        registry,
        &agent_receiver_api::Api {
            use_proxy: config.connection_config.client_config.use_proxy,
        },
        &InteractiveTrust {},
        &RegistrationCallNew {
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
        &RegistrationPreConfiguredImpl {},
    )
}

fn _register_pre_configured(
    pre_configured_connections: &config::PreConfiguredConnections,
    client_config: &config::ClientConfig,
    registry: &mut config::Registry,
    registration_pre_configured: &impl RegistrationPreConfigured,
) -> AnyhowResult<()> {
    for (site_id, pre_configured_connection) in pre_configured_connections.connections.iter() {
        if let Err(error) = process_pre_configured_connection(
            site_id,
            pre_configured_connection,
            &pre_configured_connections.agent_labels,
            client_config,
            registry,
            registration_pre_configured,
        ) {
            error!(
                "Error while processing connection {}: {}",
                site_id,
                misc::anyhow_error_to_human_readable(&error)
            )
        }
    }

    if !pre_configured_connections.keep_existing_connections {
        delete_vanished_connections(
            registry,
            registry
                .get_registered_site_ids()
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

trait RegistrationPreConfigured {
    fn register(
        &self,
        config: &config::RegisterNewConfig,
        registry: &mut config::Registry,
    ) -> AnyhowResult<()>;

    fn registration_status_v2(
        &self,
        site_id: &site_spec::SiteID,
        connection: &config::TrustedConnectionWithRemote,
        client_config: &config::ClientConfig,
    ) -> AnyhowResult<agent_receiver_api::RegistrationStatusV2Response>;
}

struct RegistrationPreConfiguredImpl;

impl RegistrationPreConfigured for RegistrationPreConfiguredImpl {
    fn register(
        &self,
        config: &config::RegisterNewConfig,
        registry: &mut config::Registry,
    ) -> AnyhowResult<()> {
        register_new(config, registry)
    }

    fn registration_status_v2(
        &self,
        site_id: &site_spec::SiteID,
        connection: &config::TrustedConnectionWithRemote,
        client_config: &config::ClientConfig,
    ) -> AnyhowResult<agent_receiver_api::RegistrationStatusV2Response> {
        agent_receiver_api::Api {
            use_proxy: client_config.use_proxy,
        }
        .registration_status_v2(
            &site_spec::make_site_url(site_id, &connection.receiver_port)?,
            &connection.trust,
        )
    }
}

fn process_pre_configured_connection(
    site_id: &site_spec::SiteID,
    pre_configured: &config::PreConfiguredConnection,
    agent_labels: &types::AgentLabels,
    client_config: &config::ClientConfig,
    registry: &mut config::Registry,
    registration_pre_configured: &impl RegistrationPreConfigured,
) -> AnyhowResult<()> {
    let receiver_port = match pre_configured.port {
        Some(receiver_port) => receiver_port,
        None => site_spec::discover_receiver_port(site_id, client_config)?,
    };

    if let Some(registered_connection) = registry.get_connection_as_mut(site_id) {
        registered_connection.receiver_port = receiver_port;
        info!(
            "Updated agent receiver port for existing connection {}",
            site_id
        );
        if matches!(
            registration_pre_configured.registration_status_v2(
                site_id,
                registered_connection,
                client_config
            )?,
            agent_receiver_api::RegistrationStatusV2Response::Registered(..)
        ) {
            return Ok(());
        }
    }

    let registration_config = config::RegisterNewConfig::new(
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

    registration_pre_configured.register(&registration_config, registry)?;
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

pub fn proxy_register(config: &config::RegisterExistingConfig) -> AnyhowResult<()> {
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
    use config::test_helpers::TestRegistry;
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
        Existing,
        New,
    }

    struct MockApi {
        expect_root_cert: bool,
        expected_registration_method: Option<RegistrationMethod>,
    }

    impl agent_receiver_api::Registration for MockApi {
        fn register_existing(
            &self,
            base_url: &reqwest::Url,
            root_cert: &Option<&str>,
            _credentials: &types::Credentials,
            _uuid: &uuid::Uuid,
            _csr: &str,
            host_name: &str,
        ) -> AnyhowResult<agent_receiver_api::RegisterExistingResponse> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::Existing
            ));
            assert!(base_url == &expected_url());
            assert!(root_cert.is_some() == self.expect_root_cert);
            assert!(host_name == HOST_NAME);
            Ok(agent_receiver_api::RegisterExistingResponse {
                root_cert: String::from("root_cert"),
                agent_cert: String::from("agent_cert"),
                connection_mode: config::ConnectionMode::Pull,
            })
        }

        fn register_new(
            &self,
            base_url: &reqwest::Url,
            root_cert: &Option<&str>,
            _credentials: &types::Credentials,
            _uuid: &uuid::Uuid,
            _csr: &str,
            ag_labels: &types::AgentLabels,
        ) -> AnyhowResult<agent_receiver_api::RegisterNewResponse> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::New
            ));
            assert!(base_url == &expected_url());
            assert!(root_cert.is_some() == self.expect_root_cert);
            assert!(ag_labels == &agent_labels());
            Ok(agent_receiver_api::RegisterNewResponse {
                root_cert: String::from("root_cert"),
            })
        }

        fn register_new_ongoing(
            &self,
            base_url: &reqwest::Url,
            _root_cert: &str,
            _credentials: &types::Credentials,
            _uuid: &uuid::Uuid,
        ) -> AnyhowResult<agent_receiver_api::RegisterNewOngoingResponse> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::New
            ));
            assert!(base_url == &expected_url());
            Ok(agent_receiver_api::RegisterNewOngoingResponse::Success(
                agent_receiver_api::RegisterNewOngoingResponseSuccess {
                    agent_cert: String::from("agent_cert"),
                    connection_mode: config::ConnectionMode::Push,
                },
            ))
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

    mod test_prepare_registration {
        use super::*;

        #[test]
        fn test_interactive_trust() {
            assert!(prepare_registration(
                &registration_connection_config(None, None, false),
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
        fn test_existing() {
            let mut r = TestRegistry::new();
            let registry = &mut r.registry;
            assert!(!registry.path().exists());
            assert!(direct_registration(
                &registration_connection_config(None, None, false),
                registry,
                &MockApi {
                    expect_root_cert: false,
                    expected_registration_method: Some(RegistrationMethod::Existing),
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: true,
                    expect_password_prompt: true,
                },
                &RegistrationCallExisting {
                    host_name: HOST_NAME
                },
            )
            .is_ok());
            assert!(!registry.is_empty());
            assert!(registry.path().exists());
        }

        #[test]
        fn test_new() {
            let mut r = TestRegistry::new();
            let registry = &mut r.registry;
            assert!(!registry.path().exists());
            assert!(direct_registration(
                &registration_connection_config(
                    Some(String::from("root_certificate")),
                    Some(String::from("password")),
                    false
                ),
                registry,
                &MockApi {
                    expect_root_cert: true,
                    expected_registration_method: Some(RegistrationMethod::New),
                },
                &MockInteractiveTrust {
                    expect_server_cert_prompt: false,
                    expect_password_prompt: false,
                },
                &RegistrationCallNew {
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
                &config::RegisterExistingConfig {
                    connection_config: registration_connection_config(None, None, true),
                    host_name: String::from(HOST_NAME),
                },
                &MockApi {
                    expect_root_cert: false,
                    expected_registration_method: Some(RegistrationMethod::Existing),
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

        fn registry() -> TestRegistry {
            TestRegistry::new()
                .add_connection(
                    &config::ConnectionMode::Pull,
                    "server/pre-baked-pull-site",
                    uuid::Uuid::new_v4(),
                )
                .add_connection(
                    &config::ConnectionMode::Pull,
                    "server/other-pull-site",
                    uuid::Uuid::new_v4(),
                )
                .add_connection(
                    &config::ConnectionMode::Push,
                    "server/pre-baked-push-site",
                    uuid::Uuid::new_v4(),
                )
                .add_connection(
                    &config::ConnectionMode::Push,
                    "server/other-push-site",
                    uuid::Uuid::new_v4(),
                )
                .add_imported_connection(uuid::Uuid::new_v4())
        }

        fn pre_configured_connections(
            keep_existing_connections: bool,
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
                keep_existing_connections,
            }
        }

        struct MockRegistrationPreConfiguredImpl {
            is_registered_at_remote: bool,
        }

        impl RegistrationPreConfigured for MockRegistrationPreConfiguredImpl {
            fn register(
                &self,
                config: &config::RegisterNewConfig,
                registry: &mut config::Registry,
            ) -> AnyhowResult<()> {
                assert!(config.connection_config.password.is_some());
                assert!(config.connection_config.root_certificate.is_some());
                assert!(!config.connection_config.trust_server_cert);
                assert_eq!(config.agent_labels.get("key").unwrap(), "value");
                registry.register_connection(
                    std::collections::HashMap::from([
                        ("server/pre-baked-pull-site", config::ConnectionMode::Pull),
                        ("server/pre-baked-pull-site-2", config::ConnectionMode::Pull),
                        ("server/pre-baked-push-site", config::ConnectionMode::Push),
                        ("server/pre-baked-push-site-2", config::ConnectionMode::Push),
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

            fn registration_status_v2(
                &self,
                _site_id: &site_spec::SiteID,
                _connection: &config::TrustedConnectionWithRemote,
                _client_config: &config::ClientConfig,
            ) -> AnyhowResult<agent_receiver_api::RegistrationStatusV2Response> {
                Ok(if self.is_registered_at_remote {
                    agent_receiver_api::RegistrationStatusV2Response::Registered(
                        agent_receiver_api::RegistrationStatusV2ResponseRegistered {
                            hostname: String::from("my-host"),
                            connection_mode: config::ConnectionMode::Pull,
                        },
                    )
                } else {
                    agent_receiver_api::RegistrationStatusV2Response::NotRegistered
                })
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
            keep_existing_connections: bool,
            registry: &mut config::Registry,
        ) {
            // We reload to ensure that the changes were written to disk
            let mut registry = config::Registry::from_file(registry.path()).unwrap();

            let mut expected_pull_site_ids =
                vec!["server/pre-baked-pull-site", "server/pre-baked-pull-site-2"];
            let mut expected_push_site_ids =
                vec!["server/pre-baked-push-site", "server/pre-baked-push-site-2"];
            if keep_existing_connections {
                expected_pull_site_ids.push("server/other-pull-site");
                expected_push_site_ids.push("server/other-push-site");
            }
            test_registered_standard_connections(
                expected_pull_site_ids.into_iter(),
                registry.get_standard_pull_connections(),
            );
            test_registered_standard_connections(
                expected_push_site_ids.into_iter(),
                registry.get_push_connections(),
            );

            assert_eq!(
                registry
                    .get_connection_as_mut(
                        &site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap()
                    )
                    .unwrap()
                    .receiver_port,
                1001
            );
            assert_eq!(
                registry
                    .get_connection_as_mut(
                        &site_spec::SiteID::from_str("server/pre-baked-push-site").unwrap()
                    )
                    .unwrap()
                    .receiver_port,
                1003
            );

            assert_eq!(
                registry.get_imported_pull_connections().count(),
                match keep_existing_connections {
                    true => 1,
                    false => 0,
                },
            );
        }

        #[test]
        fn test_keep_existing_connections() {
            let mut r = registry();
            assert!(_register_pre_configured(
                &pre_configured_connections(true),
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                &mut r.registry,
                &MockRegistrationPreConfiguredImpl {
                    is_registered_at_remote: true
                },
            )
            .is_ok());
            test_registry_after_registration(true, &mut r.registry)
        }

        #[test]
        fn test_remove_vanished_connections() {
            let mut r = registry();
            assert!(_register_pre_configured(
                &pre_configured_connections(false),
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                &mut r.registry,
                &MockRegistrationPreConfiguredImpl {
                    is_registered_at_remote: true
                },
            )
            .is_ok());
            test_registry_after_registration(false, &mut r.registry)
        }

        #[test]
        fn test_port_update_only() {
            let mut r = TestRegistry::new();
            let registry = &mut r.registry;
            registry.register_connection(
                &config::ConnectionMode::Pull,
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
                keep_existing_connections: true,
            };
            assert!(_register_pre_configured(
                &pre_configured_connections,
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                registry,
                &MockRegistrationPreConfiguredImpl {
                    is_registered_at_remote: true
                },
            )
            .is_ok());

            // We reload to ensure that the changes were written to disk
            let mut registry = config::Registry::from_file(registry.path()).unwrap();
            assert_eq!(
                registry
                    .get_connection_as_mut(
                        &site_spec::SiteID::from_str("server/pre-baked-pull-site").unwrap()
                    )
                    .unwrap()
                    .receiver_port,
                1001
            );
        }

        #[test]
        fn test_registered_locally_but_not_at_remote() -> AnyhowResult<()> {
            let mut r = registry();
            let registry_before_registration = r.registry.clone();
            let pre_configured_connections = pre_configured_connections(true);
            assert!(_register_pre_configured(
                &pre_configured_connections,
                &config::ClientConfig {
                    use_proxy: false,
                    validate_api_cert: false,
                },
                &mut r.registry,
                &MockRegistrationPreConfiguredImpl {
                    is_registered_at_remote: false
                },
            )
            .is_ok());

            // for any connection which was already present before registering the pre-configured
            // connections, we expect the uuid to change, because the remote says that we are not
            // registered --> re-registration
            for site_id in pre_configured_connections.connections.keys() {
                if let Some(connection_before_registration) =
                    registry_before_registration.get(site_id)
                {
                    assert_ne!(
                        connection_before_registration.trust.uuid,
                        r.registry.get(site_id).unwrap().trust.uuid
                    );
                }
            }
            Ok(())
        }
    }
}
