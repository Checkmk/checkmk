// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{agent_receiver_api, certs, config, constants};
use anyhow::{anyhow, Context, Result as AnyhowResult};

trait TrustEstablishing {
    fn ask_for_trust(&self, server: &str) -> AnyhowResult<()>;
}

struct InteractiveTrust {}

impl InteractiveTrust {
    fn display_cert(server: &str) -> AnyhowResult<()> {
        let pem_str = certs::fetch_server_cert_pem(server)?;
        let pem = certs::parse_pem(&pem_str)?;
        let x509 = pem.parse_x509()?;
        let validity = x509.validity();

        eprintln!(
            "Attempting to register at {}. Server certificate details:\n",
            server
        );
        eprintln!("PEM-encoded certificate:\n{}", pem_str);
        eprintln!("Issued by:\n\t{}", certs::join_common_names(x509.issuer()));
        eprintln!("Issued to:\n\t{}", certs::join_common_names(x509.subject()));
        eprintln!(
            "Validity:\n\tFrom {}\n\tTo   {}",
            validity.not_before.to_rfc2822(),
            validity.not_after.to_rfc2822(),
        );
        Ok(())
    }
}

impl TrustEstablishing for InteractiveTrust {
    fn ask_for_trust(&self, server: &str) -> AnyhowResult<()> {
        InteractiveTrust::display_cert(server)?;
        eprintln!();
        eprintln!("\x1b[1mDo you want to establish this connection?\x1b[0m \x1b[90m(\x1b[0my\x1b[90mes/\x1b[0mn\x1b[90mo)\x1b[0m");
        eprint!("> ");
        loop {
            let mut answer = String::new();
            std::io::stdin()
                .read_line(&mut answer)
                .context("Failed to read answer from standard input")?;
            match answer.to_lowercase().trim() {
                "y" | "yes" => return Ok(()),
                "n" | "no" => {
                    return Err(anyhow!(format!(
                        "Cannot continue without trusting {}",
                        server
                    )))
                }
                _ => {
                    eprintln!("Please answer 'y' or 'n'");
                    eprint!("> ");
                }
            }
        }
    }
}

fn registration_server_cert<'a>(
    config: &'a config::RegistrationConfig,
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
                trust_establisher.ask_for_trust(&config.agent_receiver_address)?;
            }
            Ok(None)
        }
    }
}

fn pair(
    config: &config::RegistrationConfig,
    agent_rec_api: &impl agent_receiver_api::Pairing,
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<(String, String, agent_receiver_api::PairingResponse)> {
    let uuid = uuid::Uuid::new_v4().to_string();
    let (csr, private_key) = certs::make_csr(&uuid).context("Error creating CSR.")?;
    Ok((
        uuid,
        private_key,
        agent_rec_api
            .pair(
                &config.agent_receiver_address,
                registration_server_cert(config, trust_establisher)?,
                csr,
                &config.credentials,
            )
            .context(format!(
                "Error pairing with {}",
                &config.agent_receiver_address
            ))?,
    ))
}

fn post_registration_conn_type(
    server: &str,
    root_cert: &str,
    uuid: &str,
    client_cert: &str,
    agent_rec_api: &impl agent_receiver_api::Status,
) -> AnyhowResult<config::ConnectionType> {
    loop {
        let status_resp = agent_rec_api.status(server, root_cert, uuid, client_cert)?;
        if let Some(agent_receiver_api::HostStatus::Declined) = status_resp.status {
            return Err(anyhow!(
                "Registration declined by Checkmk instance, please check credentials"
            ));
        }
        if let Some(ct) = status_resp.connection_type {
            return Ok(ct);
        }
        println!("Waiting for registration to complete on Checkmk instance, sleeping 20 s");
        std::thread::sleep(std::time::Duration::from_secs(20));
    }
}

fn _register(
    config: config::RegistrationConfig,
    registry: &mut config::Registry,
    agent_rec_api: &(impl agent_receiver_api::Pairing
          + agent_receiver_api::Registration
          + agent_receiver_api::Status),
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<()> {
    // TODO: what if registration_state.contains_key(agent_receiver_address) (already registered)?
    let (uuid, private_key, pairing_response) = pair(&config, agent_rec_api, trust_establisher)?;

    match config.host_reg_data {
        config::HostRegistrationData::Name(hn) => {
            agent_rec_api
                .register_with_hostname(
                    &config.agent_receiver_address,
                    &pairing_response.root_cert,
                    &config.credentials,
                    &uuid,
                    &hn,
                )
                .context(format!(
                    "Error registering with hostname at {}",
                    &config.agent_receiver_address,
                ))?;
        }
        config::HostRegistrationData::Labels(al) => {
            agent_rec_api
                .register_with_agent_labels(
                    &config.agent_receiver_address,
                    &pairing_response.root_cert,
                    &config.credentials,
                    &uuid,
                    &al,
                )
                .context(format!(
                    "Error registering with agent labels at {}",
                    &config.agent_receiver_address,
                ))?;
        }
    }

    registry.register_connection(
        post_registration_conn_type(
            &config.agent_receiver_address,
            &pairing_response.root_cert,
            &uuid,
            &pairing_response.client_cert,
            agent_rec_api,
        )?,
        &config.agent_receiver_address,
        config::Connection {
            uuid,
            private_key,
            certificate: pairing_response.client_cert,
            root_cert: pairing_response.root_cert,
        },
    );

    registry.save()?;

    Ok(())
}

pub fn register(
    config: config::RegistrationConfig,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    _register(
        config,
        registry,
        &agent_receiver_api::Api {},
        &InteractiveTrust {},
    )
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct SurrogatePullData {
    pub agent_controller_version: String,
    pub connection: config::Connection,
}

fn _register_surrogate_pull(
    config: config::RegistrationConfig,
    agent_rec_api: &(impl agent_receiver_api::Pairing + agent_receiver_api::Registration),
    trust_establisher: &impl TrustEstablishing,
) -> AnyhowResult<()> {
    let hn = match &config.host_reg_data {
        config::HostRegistrationData::Name(hn) => hn,
        _ => {
            return Err(anyhow!(
                "Surrogate pull registration does not support registration with agent labels"
            ))
        }
    };
    let (uuid, private_key, pairing_response) = pair(&config, agent_rec_api, trust_establisher)?;

    agent_rec_api
        .register_with_hostname(
            &config.agent_receiver_address,
            &pairing_response.root_cert,
            &config.credentials,
            &uuid,
            hn,
        )
        .context(format!(
            "Error registering with hostname at {}",
            &config.agent_receiver_address
        ))?;

    println!(
        "{}",
        serde_json::to_string(&SurrogatePullData {
            agent_controller_version: String::from(constants::VERSION),
            connection: config::Connection {
                uuid,
                private_key,
                certificate: pairing_response.client_cert,
                root_cert: pairing_response.root_cert,
            }
        })?
    );
    Ok(())
}

pub fn register_surrogate_pull(config: config::RegistrationConfig) -> AnyhowResult<()> {
    _register_surrogate_pull(config, &agent_receiver_api::Api {}, &InteractiveTrust {})
}

#[cfg(test)]
mod tests {
    use super::super::config::JSONLoader;
    use super::*;

    const SERVER_ADDRESS: &str = "server:8000";
    const HOST_NAME: &str = "host";

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
            server_address: &str,
            root_cert: Option<&str>,
            _csr: String,
            _credentials: &config::Credentials,
        ) -> AnyhowResult<agent_receiver_api::PairingResponse> {
            assert!(server_address == SERVER_ADDRESS);
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
            server_address: &str,
            _root_cert: &str,
            _credentials: &config::Credentials,
            _uuid: &str,
            host_name: &str,
        ) -> AnyhowResult<()> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::HostName
            ));
            assert!(server_address == SERVER_ADDRESS);
            assert!(host_name == HOST_NAME);
            Ok(())
        }

        fn register_with_agent_labels(
            &self,
            server_address: &str,
            _root_cert: &str,
            _credentials: &config::Credentials,
            _uuid: &str,
            ag_labels: &config::AgentLabels,
        ) -> AnyhowResult<()> {
            assert!(matches!(
                self.expected_registration_method.as_ref().unwrap(),
                RegistrationMethod::AgentLabels
            ));
            assert!(server_address == SERVER_ADDRESS);
            assert!(ag_labels == &agent_labels());
            Ok(())
        }
    }

    impl agent_receiver_api::Status for MockApi {
        fn status(
            &self,
            server_address: &str,
            _root_cert: &str,
            _uuid: &str,
            _certificate: &str,
        ) -> Result<agent_receiver_api::StatusResponse, agent_receiver_api::StatusError> {
            assert!(server_address == SERVER_ADDRESS);
            Ok(agent_receiver_api::StatusResponse {
                hostname: Some(String::from(HOST_NAME)),
                status: None,
                connection_type: Some(config::ConnectionType::Pull),
                message: None,
            })
        }
    }

    struct MockInteractiveTrust {}

    impl TrustEstablishing for MockInteractiveTrust {
        fn ask_for_trust(&self, server: &str) -> AnyhowResult<()> {
            assert!(server == SERVER_ADDRESS);
            Ok(())
        }
    }

    fn registry() -> config::Registry {
        config::Registry::new(
            config::RegisteredConnections::new().unwrap(),
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap()
    }

    fn agent_labels() -> config::AgentLabels {
        let mut al = std::collections::HashMap::new();
        al.insert(String::from("a"), String::from("b"));
        al
    }

    fn registration_config(
        root_certificate: Option<String>,
        host_reg_data: config::HostRegistrationData,
        trust_server_cert: bool,
    ) -> config::RegistrationConfig {
        config::RegistrationConfig {
            agent_receiver_address: String::from(SERVER_ADDRESS),
            credentials: config::Credentials {
                username: String::from("user"),
                password: String::from("password"),
            },
            root_certificate,
            host_reg_data,
            trust_server_cert,
        }
    }

    mod test_pair {
        use super::*;

        #[test]
        fn test_interactive_trust() {
            assert!(pair(
                &registration_config(
                    None,
                    config::HostRegistrationData::Name(String::from(HOST_NAME)),
                    false,
                ),
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
        }

        #[test]
        fn test_blind_trust() {
            assert!(pair(
                &registration_config(
                    None,
                    config::HostRegistrationData::Name(String::from(HOST_NAME)),
                    true,
                ),
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
        }

        #[test]
        fn test_root_cert_from_config() {
            assert!(pair(
                &registration_config(
                    Some(String::from("root_certificate")),
                    config::HostRegistrationData::Labels(agent_labels()),
                    false,
                ),
                &MockApi {
                    expect_root_cert_for_pairing: true,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
        }

        #[test]
        fn test_root_cert_from_config_and_blind_trust() {
            assert!(pair(
                &registration_config(
                    Some(String::from("root_certificate")),
                    config::HostRegistrationData::Labels(agent_labels()),
                    true
                ),
                &MockApi {
                    expect_root_cert_for_pairing: true,
                    expected_registration_method: None,
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
        }
    }

    mod test_register {
        use super::*;

        #[test]
        fn test_host_name() {
            let mut registry = registry();
            assert!(!registry.path().exists());
            assert!(_register(
                registration_config(
                    None,
                    config::HostRegistrationData::Name(String::from(HOST_NAME)),
                    false,
                ),
                &mut registry,
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: Some(RegistrationMethod::HostName),
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
            assert!(!registry.is_empty());
            assert!(registry.path().exists());
        }

        #[test]
        fn test_agent_labels() {
            let mut registry = registry();
            assert!(!registry.path().exists());
            assert!(_register(
                registration_config(
                    Some(String::from("root_certificate")),
                    config::HostRegistrationData::Labels(agent_labels()),
                    false,
                ),
                &mut registry,
                &MockApi {
                    expect_root_cert_for_pairing: true,
                    expected_registration_method: Some(RegistrationMethod::AgentLabels),
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
            assert!(!registry.is_empty());
            assert!(registry.path().exists());
        }
    }

    mod test_register_surrogate_pull {
        use super::*;

        #[test]
        fn test_host_name() {
            assert!(_register_surrogate_pull(
                registration_config(
                    None,
                    config::HostRegistrationData::Name(String::from(HOST_NAME)),
                    true,
                ),
                &MockApi {
                    expect_root_cert_for_pairing: false,
                    expected_registration_method: Some(RegistrationMethod::HostName),
                },
                &MockInteractiveTrust {},
            )
            .is_ok());
        }

        #[test]
        fn test_agent_labels() {
            assert!(register_surrogate_pull(registration_config(
                None,
                config::HostRegistrationData::Labels(agent_labels()),
                true,
            ))
            .is_err());
        }
    }
}
