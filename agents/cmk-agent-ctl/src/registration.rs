// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#![cfg_attr(test, allow(dead_code))]

use super::{agent_receiver_api, certs, config, constants};
use anyhow::{anyhow, Context, Result as AnyhowResult};

struct InteractiveTrust {}

#[mockall::automock]
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

    pub fn ask_for_trust(server: &str) -> AnyhowResult<()> {
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

#[mockall_double::double]
use super::agent_receiver_api::Api as AgentRecvApi;
#[mockall_double::double]
use InteractiveTrust as IactiveTrust;

fn registration_server_cert(config: &config::RegistrationConfig) -> AnyhowResult<Option<&str>> {
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
                IactiveTrust::ask_for_trust(&config.agent_receiver_address)?;
            }
            Ok(None)
        }
    }
}

pub fn pair(
    config: &config::RegistrationConfig,
) -> AnyhowResult<(String, String, agent_receiver_api::PairingResponse)> {
    let uuid = uuid::Uuid::new_v4().to_string();
    let (csr, private_key) = certs::make_csr(&uuid).context("Error creating CSR.")?;
    Ok((
        uuid,
        private_key,
        AgentRecvApi::pairing(
            &config.agent_receiver_address,
            registration_server_cert(config)?,
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
) -> AnyhowResult<config::ConnectionType> {
    loop {
        let status_resp = AgentRecvApi::status(server, root_cert, uuid, client_cert)?;
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

pub fn register(
    config: config::RegistrationConfig,
    registry: &mut config::Registry,
) -> AnyhowResult<()> {
    // TODO: what if registration_state.contains_key(agent_receiver_address) (already registered)?
    let (uuid, private_key, pairing_response) = pair(&config)?;

    match config.host_reg_data {
        config::HostRegistrationData::Name(hn) => {
            AgentRecvApi::register_with_hostname(
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
            AgentRecvApi::register_with_agent_labels(
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

#[derive(serde::Serialize, serde::Deserialize)]
pub struct SurrogatePullData {
    pub agent_controller_version: String,
    pub connection: config::Connection,
}

pub fn register_surrogate_pull(config: config::RegistrationConfig) -> AnyhowResult<()> {
    let hn = match &config.host_reg_data {
        config::HostRegistrationData::Name(hn) => hn,
        _ => {
            return Err(anyhow!(
                "Surrogate pull registration does not support registration with agent labels"
            ))
        }
    };
    let (uuid, private_key, pairing_response) = pair(&config)?;

    AgentRecvApi::register_with_hostname(
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

#[cfg(test)]
mod tests {
    use super::super::config::JSONLoader;
    use super::*;

    lazy_static::lazy_static! {
        static ref MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());
    }

    fn registry() -> config::Registry {
        config::Registry::new(
            config::RegisteredConnections::new().unwrap(),
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap()
    }

    fn agent_labels() -> config::HostRegistrationData {
        let mut al = std::collections::HashMap::new();
        al.insert(String::from("a"), String::from("b"));
        config::HostRegistrationData::Labels(al)
    }

    fn registration_config(
        root_certificate: Option<String>,
        host_reg_data: config::HostRegistrationData,
        trust_server_cert: bool,
    ) -> config::RegistrationConfig {
        config::RegistrationConfig {
            agent_receiver_address: String::from("server:8000"),
            credentials: config::Credentials {
                username: String::from("user"),
                password: String::from("password"),
            },
            root_certificate,
            host_reg_data,
            trust_server_cert,
        }
    }

    fn pairing_expect_no_root_cert(
        _server_address: &str,
        root_cert: Option<&str>,
        _csr: String,
        _credentials: &config::Credentials,
    ) -> AnyhowResult<agent_receiver_api::PairingResponse> {
        if root_cert.is_none() {
            return Ok(agent_receiver_api::PairingResponse {
                root_cert: String::from("root_cert"),
                client_cert: String::from("client_cert"),
            });
        }
        panic!("No root certificate expected")
    }

    fn pairing_expect_root_cert(
        _server_address: &str,
        root_cert: Option<&str>,
        _csr: String,
        _credentials: &config::Credentials,
    ) -> AnyhowResult<agent_receiver_api::PairingResponse> {
        if root_cert.is_some() {
            return Ok(agent_receiver_api::PairingResponse {
                root_cert: String::from("root_cert"),
                client_cert: String::from("client_cert"),
            });
        }
        panic!("No root certificate expected")
    }

    mod test_pair {
        use super::*;

        #[test]
        fn test_interactive_trust() {
            let _m = MUTEX.lock().unwrap();

            let ask_for_trust_ctx = IactiveTrust::ask_for_trust_context();
            let pairing_ctx = AgentRecvApi::pairing_context();

            ask_for_trust_ctx.expect().times(1).returning(|_| Ok(()));
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_no_root_cert);

            assert!(pair(&registration_config(
                None,
                config::HostRegistrationData::Name(String::from("host")),
                false,
            ))
            .is_ok());
        }

        #[test]
        fn test_blind_trust() {
            let _m = MUTEX.lock().unwrap();

            let pairing_ctx = AgentRecvApi::pairing_context();
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_no_root_cert);

            assert!(pair(&registration_config(
                None,
                config::HostRegistrationData::Name(String::from("host")),
                true,
            ))
            .is_ok());
        }

        #[test]
        fn test_root_cert_from_config() {
            let _m = MUTEX.lock().unwrap();

            let pairing_ctx = AgentRecvApi::pairing_context();
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_root_cert);

            assert!(pair(&registration_config(
                Some(String::from("root_certificate")),
                agent_labels(),
                false,
            ))
            .is_ok());
        }

        #[test]
        fn test_root_cert_from_config_and_blind_trust() {
            let _m = MUTEX.lock().unwrap();

            let pairing_ctx = AgentRecvApi::pairing_context();
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_root_cert);

            assert!(pair(&registration_config(
                Some(String::from("root_certificate")),
                agent_labels(),
                true,
            ))
            .is_ok());
        }
    }

    mod test_register {
        use super::*;

        #[test]
        fn test_host_name() {
            let _m = MUTEX.lock().unwrap();

            let ask_for_trust_ctx = IactiveTrust::ask_for_trust_context();
            let pairing_ctx = AgentRecvApi::pairing_context();
            let register_with_hostname_ctx = AgentRecvApi::register_with_hostname_context();
            let status_ctx = AgentRecvApi::status_context();
            ask_for_trust_ctx.expect().times(1).returning(|_| Ok(()));
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_no_root_cert);
            register_with_hostname_ctx
                .expect()
                .times(1)
                .returning(|_, _, _, _, _| Ok(()));
            status_ctx.expect().times(1).returning(|_, _, _, _| {
                Ok(agent_receiver_api::StatusResponse {
                    hostname: Some(String::from("host")),
                    status: None,
                    connection_type: Some(config::ConnectionType::Pull),
                    message: None,
                })
            });

            let mut registry = registry();
            assert!(!registry.path().exists());
            assert!(register(
                registration_config(
                    None,
                    config::HostRegistrationData::Name(String::from("host")),
                    false,
                ),
                &mut registry,
            )
            .is_ok());
            assert!(!registry.is_empty());
            assert!(registry.path().exists());
        }

        #[test]
        fn test_agent_labels() {
            let _m = MUTEX.lock().unwrap();

            let pairing_ctx = AgentRecvApi::pairing_context();
            let register_with_agent_labels_ctx = AgentRecvApi::register_with_agent_labels_context();
            let status_ctx = AgentRecvApi::status_context();
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_root_cert);
            register_with_agent_labels_ctx
                .expect()
                .times(1)
                .returning(|_, _, _, _, _| Ok(()));
            status_ctx.expect().times(1).returning(|_, _, _, _| {
                Ok(agent_receiver_api::StatusResponse {
                    hostname: Some(String::from("host")),
                    status: Some(agent_receiver_api::HostStatus::New),
                    connection_type: Some(config::ConnectionType::Push),
                    message: None,
                })
            });

            let mut registry = registry();
            assert!(!registry.path().exists());
            assert!(register(
                registration_config(
                    Some(String::from("root_certificate")),
                    agent_labels(),
                    false,
                ),
                &mut registry,
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
            let _m = MUTEX.lock().unwrap();

            let pairing_ctx = AgentRecvApi::pairing_context();
            let register_with_hostname_ctx = AgentRecvApi::register_with_hostname_context();
            pairing_ctx
                .expect()
                .times(1)
                .returning(pairing_expect_no_root_cert);
            register_with_hostname_ctx
                .expect()
                .times(1)
                .returning(|_, _, _, _, _| Ok(()));

            assert!(register_surrogate_pull(registration_config(
                None,
                config::HostRegistrationData::Name(String::from("host")),
                true,
            ))
            .is_ok());
        }

        #[test]
        fn test_agent_labels() {
            assert!(
                register_surrogate_pull(registration_config(None, agent_labels(), true,)).is_err()
            );
        }
    }
}
