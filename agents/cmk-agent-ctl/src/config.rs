// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{certs, cli, constants, setup, site_spec, types};
use anyhow::{anyhow, Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde::Serialize;
use serde_with::DisplayFromStr;
use std::collections::HashMap;
use std::fs;
use std::io;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::time::SystemTime;
use string_enum::StringEnum;

#[derive(StringEnum, PartialEq)]
pub enum ConnectionType {
    /// `push-agent`
    Push,
    /// `pull-agent`
    Pull,
}

pub trait JSONLoader: DeserializeOwned {
    fn new() -> AnyhowResult<Self> {
        Ok(serde_json::from_str("{}")?)
    }

    fn load(path: &Path) -> AnyhowResult<Self> {
        if !path.exists() {
            return Self::new();
        }
        Ok(serde_json::from_str(&fs::read_to_string(path)?)?)
    }
}

pub trait TOMLLoader: DeserializeOwned {
    fn new() -> AnyhowResult<Self> {
        Ok(toml::from_str("")?)
    }

    fn load(path: &Path) -> AnyhowResult<Self> {
        if !path.exists() {
            return Self::new();
        }
        Ok(toml::from_str(&fs::read_to_string(path)?)?)
    }
}

#[derive(Deserialize)]
pub struct RegistrationPreset {
    #[serde(default)]
    site_spec: Option<site_spec::PresetSiteSpec>,

    #[serde(default)]
    credentials: Option<types::OptPwdCredentials>,

    #[serde(default)]
    root_certificate: Option<String>,

    #[serde(default)]
    host_name: Option<String>,

    #[serde(default)]
    agent_labels: Option<types::AgentLabels>,
}

impl JSONLoader for RegistrationPreset {}

#[derive(Debug, PartialEq)]
pub enum HostRegistrationData {
    Name(String),
    Labels(types::AgentLabels),
}

pub struct RegistrationConfig {
    pub coordinates: site_spec::Coordinates,
    pub opt_pwd_credentials: types::OptPwdCredentials,
    pub root_certificate: Option<String>,
    pub host_reg_data: HostRegistrationData,
    pub trust_server_cert: bool,
    pub client_config: ClientConfig,
}

impl RegistrationConfig {
    pub fn new(
        runtime_config: RuntimeConfig,
        preset: RegistrationPreset,
        reg_args: cli::RegistrationArgs,
    ) -> AnyhowResult<RegistrationConfig> {
        let (server_spec, site) = match reg_args.site {
            Some(site) => {
                match reg_args.server {
                    Some(server_spec) => (server_spec, site),
                    None => return Err(anyhow!("Server not specified in the command line arguments, but site was. This should never happen.")),
                }
            }
            None => match preset.site_spec {
                Some(site_spec) => (site_spec.server_spec, site_spec.site),
                None => return Err(anyhow!("Missing server and site specifications"))
            }
        };
        let client_config = ClientConfig::new(runtime_config, reg_args.client_opts);
        let coordinates = site_spec::make_coordinates(
            &server_spec.server,
            server_spec.port,
            &site,
            &client_config,
        )?;
        let opt_pwd_credentials = match reg_args.user {
            Some(username) => types::OptPwdCredentials {
                username,
                password: reg_args.password,
            },
            None => preset.credentials.context("Missing credentials")?,
        };
        let root_certificate = preset.root_certificate;
        let stored_host_name = preset.host_name;
        let stored_agent_labels = preset.agent_labels;
        let host_reg_data = match reg_args
            .host_name
            .map(HostRegistrationData::Name)
            .or_else(|| stored_host_name.map(HostRegistrationData::Name))
        {
            Some(hrd) => hrd,
            None => HostRegistrationData::Labels(Self::enrich_with_automatic_agent_labels(
                stored_agent_labels.unwrap_or_default(),
            )?),
        };
        Ok(RegistrationConfig {
            coordinates,
            opt_pwd_credentials,
            root_certificate,
            host_reg_data,
            trust_server_cert: reg_args.trust_server_cert,
            client_config,
        })
    }

    fn automatic_agent_labels() -> AnyhowResult<types::AgentLabels> {
        Ok(types::AgentLabels::from([
            (
                String::from("cmk/hostname-simple"),
                String::from(
                    gethostname::gethostname()
                        .to_str()
                        .context("Failed to transform host name to str")?,
                ),
            ),
            (
                String::from("cmk/os-family"),
                String::from(std::env::consts::OS),
            ),
        ]))
    }

    fn enrich_with_automatic_agent_labels(
        user_defined_agent_labels: types::AgentLabels,
    ) -> AnyhowResult<types::AgentLabels> {
        let mut agent_labels = Self::automatic_agent_labels()?;
        agent_labels.extend(user_defined_agent_labels);
        Ok(agent_labels)
    }
}

#[derive(Deserialize, Clone)]
pub struct RuntimeConfig {
    #[serde(default)]
    allowed_ip: Option<Vec<String>>,

    #[serde(default)]
    pull_port: Option<u16>,

    #[serde(default)]
    detect_proxy: Option<bool>,

    #[serde(default)]
    validate_api_cert: Option<bool>,
}

impl TOMLLoader for RuntimeConfig {}

#[derive(Debug)]
pub struct LegacyPullMarker(std::path::PathBuf);

impl LegacyPullMarker {
    pub fn new<P>(path: P) -> Self
    where
        P: AsRef<Path>,
    {
        Self(path.as_ref().to_owned())
    }

    pub fn exists(&self) -> bool {
        self.0.exists()
    }

    pub fn remove(&self) -> std::io::Result<()> {
        if !&self.exists() {
            return Ok(());
        }

        fs::remove_file(&self.0)
    }

    pub fn create(&self) -> std::io::Result<()> {
        fs::write(
            &self.0,
            "This file has been placed as a marker for cmk-agent-ctl\n\
            to allow unencrypted legacy agent pull mode.\n\
            It will be removed automatically on first successful agent registration.\n\
            You can remove it manually to disallow legacy mode, but note that\n\
            for regular operation you need to register the agent anyway.\n\
            \n\
            To secure the connection run `cmk-agent-ctl register`.\n",
        )
    }
}

pub struct ClientConfig {
    pub use_proxy: bool,
    pub validate_api_cert: bool,
}

impl ClientConfig {
    pub fn new(runtime_config: RuntimeConfig, client_opts: cli::ClientOpts) -> ClientConfig {
        ClientConfig {
            use_proxy: client_opts.detect_proxy || runtime_config.detect_proxy.unwrap_or(false),
            validate_api_cert: client_opts.validate_api_cert
                || runtime_config.validate_api_cert.unwrap_or(false),
        }
    }
}

pub struct PullConfig {
    pub allowed_ip: Vec<String>,
    pub port: u16,
    pub max_connections: usize,
    pub connection_timeout: u64,
    pub agent_channel: types::AgentChannel,
    pub legacy_pull_marker: LegacyPullMarker,
    pub registry: Registry,
}

impl PullConfig {
    pub fn new(
        runtime_config: RuntimeConfig,
        pull_opts: cli::PullOpts,
        legacy_pull_marker: LegacyPullMarker,
        registry: Registry,
    ) -> AnyhowResult<PullConfig> {
        let allowed_ip = pull_opts
            .allowed_ip
            .or(runtime_config.allowed_ip)
            .unwrap_or_default();
        let port = pull_opts
            .port
            .or(runtime_config.pull_port)
            .unwrap_or(constants::DEFAULT_PULL_PORT);
        #[cfg(unix)]
        let agent_channel = setup::agent_channel();
        #[cfg(windows)]
        let agent_channel = pull_opts.agent_channel.unwrap_or_else(setup::agent_channel);
        Ok(PullConfig {
            allowed_ip,
            port,
            max_connections: setup::max_connections(),
            connection_timeout: setup::connection_timeout(),
            agent_channel,
            legacy_pull_marker,
            registry,
        })
    }

    pub fn refresh(&mut self) -> AnyhowResult<bool> {
        self.registry.refresh()
    }

    pub fn allow_legacy_pull(&self) -> bool {
        self.registry.is_empty() && self.legacy_pull_marker.exists()
    }

    pub fn connections(&self) -> impl Iterator<Item = &Connection> {
        self.registry.pull_connections()
    }

    pub fn has_connections(&self) -> bool {
        !self.registry.pull_is_empty()
    }
}

#[serde_with::serde_as]
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Connection {
    #[serde_as(as = "DisplayFromStr")]
    pub uuid: uuid::Uuid,
    pub private_key: String,
    pub certificate: String,
    pub root_cert: String,
}

impl std::cmp::PartialEq for Connection {
    fn eq(&self, other: &Self) -> bool {
        self.uuid == other.uuid
    }
}

impl std::cmp::Eq for Connection {}

impl std::hash::Hash for Connection {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.uuid.hash(state);
    }
}

impl std::borrow::Borrow<uuid::Uuid> for Connection {
    fn borrow(&self) -> &uuid::Uuid {
        &self.uuid
    }
}

impl Connection {
    pub fn tls_handshake_credentials(&self) -> AnyhowResult<certs::HandshakeCredentials> {
        Ok(certs::HandshakeCredentials {
            server_root_cert: &self.root_cert,
            client_identity: Some(self.identity()?),
        })
    }

    fn identity(&self) -> AnyhowResult<certs::TLSIdentity> {
        Ok(certs::TLSIdentity {
            cert_chain: vec![certs::rustls_certificate(&self.certificate)?],
            key_der: certs::rustls_private_key(&self.private_key)?,
        })
    }
}

#[derive(Serialize, Deserialize, PartialEq, Debug, Clone)]
pub struct RegisteredConnections {
    #[serde(default)]
    pub push: HashMap<site_spec::Coordinates, Connection>,

    #[serde(default)]
    pub pull: HashMap<site_spec::Coordinates, Connection>,

    #[serde(default)]
    pub pull_imported: std::collections::HashSet<Connection>,
}

impl JSONLoader for RegisteredConnections {}

fn mtime(path: &Path) -> AnyhowResult<Option<SystemTime>> {
    Ok(if path.exists() {
        Some(fs::metadata(&path)?.modified()?)
    } else {
        None
    })
}
#[derive(PartialEq, Debug, Clone)]
pub struct Registry {
    connections: RegisteredConnections,
    path: PathBuf,
    last_reload: Option<SystemTime>,
}

impl Registry {
    #[cfg(test)]
    pub fn new<P>(connections: RegisteredConnections, path: P) -> AnyhowResult<Registry>
    where
        P: AsRef<Path>,
    {
        let path = path.as_ref().to_owned();
        let last_reload = mtime(&path)?;
        Ok(Registry {
            connections,
            path,
            last_reload,
        })
    }

    #[cfg(test)]
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn from_file(path: &Path) -> AnyhowResult<Registry> {
        Ok(Registry {
            connections: RegisteredConnections::load(path)?,
            path: PathBuf::from(path),
            last_reload: mtime(path)?,
        })
    }

    pub fn refresh(&mut self) -> AnyhowResult<bool> {
        match (mtime(&self.path)?, self.last_reload) {
            (Some(now), Some(then)) => {
                match now.duration_since(then) {
                    Ok(time) if time.is_zero() => {
                        // No change.
                        Ok(false)
                    }
                    _ => {
                        // This also covers Err(_), which means "negative time".
                        // This may occur due to clock adjustments.
                        // Force reload in this case.
                        // Otherwise, we have a regular posive duration, which means
                        // that our registration was touched.
                        self.reload()?;
                        Ok(true)
                    }
                }
            }

            (None, None) => {
                // Still no file there -> No change.
                Ok(false)
            }

            _ => {
                // File was deleted or is new
                self.reload()?;
                Ok(true)
            }
        }
    }

    pub fn save(&self) -> io::Result<()> {
        let write_op_result = fs::write(
            &self.path,
            &serde_json::to_string_pretty(&self.connections)?,
        );
        #[cfg(windows)]
        return write_op_result;
        #[cfg(unix)]
        {
            write_op_result?;
            fs::set_permissions(&self.path, fs::Permissions::from_mode(0o600))
        }
    }

    pub fn pull_standard_is_empty(&self) -> bool {
        self.connections.pull.is_empty()
    }

    pub fn pull_imported_is_empty(&self) -> bool {
        self.connections.pull_imported.is_empty()
    }

    pub fn pull_is_empty(&self) -> bool {
        self.pull_standard_is_empty() & self.pull_imported_is_empty()
    }

    pub fn push_is_empty(&self) -> bool {
        self.connections.push.is_empty()
    }

    pub fn is_empty(&self) -> bool {
        self.push_is_empty() & self.pull_is_empty()
    }

    pub fn standard_pull_connections(
        &self,
    ) -> impl Iterator<Item = (&site_spec::Coordinates, &Connection)> {
        self.connections.pull.iter()
    }

    pub fn imported_pull_connections(&self) -> impl Iterator<Item = &Connection> {
        self.connections.pull_imported.iter()
    }

    pub fn pull_connections(&self) -> impl Iterator<Item = &Connection> {
        self.connections
            .pull
            .values()
            .chain(self.connections.pull_imported.iter())
    }

    pub fn push_connections(&self) -> impl Iterator<Item = (&site_spec::Coordinates, &Connection)> {
        self.connections.push.iter()
    }

    pub fn register_connection(
        &mut self,
        connection_type: ConnectionType,
        coordinates: &site_spec::Coordinates,
        connection: Connection,
    ) {
        let (insert_connections, remove_connections) = match connection_type {
            ConnectionType::Push => (&mut self.connections.push, &mut self.connections.pull),
            ConnectionType::Pull => (&mut self.connections.pull, &mut self.connections.push),
        };
        remove_connections.remove(coordinates);
        insert_connections.insert(coordinates.clone(), connection);
    }

    pub fn register_imported_connection(&mut self, connection: Connection) {
        self.connections.pull_imported.insert(connection);
    }

    pub fn delete_standard_connection(
        &mut self,
        coordinates: &site_spec::Coordinates,
    ) -> AnyhowResult<()> {
        if self.connections.push.remove(coordinates).is_some() {
            println!("Deleted push connection '{}'", coordinates);
            return Ok(());
        }
        if self.connections.pull.remove(coordinates).is_some() {
            println!("Deleted pull connection '{}'", coordinates);
            return Ok(());
        }
        Err(anyhow!("Connection '{}' not found", coordinates))
    }

    pub fn delete_imported_connection(&mut self, uuid: &uuid::Uuid) -> AnyhowResult<()> {
        if self.connections.pull_imported.remove(uuid) {
            println!("Deleted imported connection '{}'", uuid);
            return Ok(());
        };
        Err(anyhow!(
            "Imported pull connection with UUID {} not found",
            uuid
        ))
    }

    pub fn clear(&mut self) {
        self.connections.push.clear();
        self.connections.pull.clear();
        self.connections.pull_imported.clear();
    }

    fn reload(&mut self) -> AnyhowResult<()> {
        self.connections = RegisteredConnections::load(&self.path)?;
        self.last_reload = mtime(&self.path)?;
        Ok(())
    }
}

#[cfg(test)]
mod test_registration_config {
    use super::*;

    fn registration_args() -> cli::RegistrationArgs {
        cli::RegistrationArgs {
            server: None,
            site: None,
            user: None,
            password: None,
            host_name: None,
            trust_server_cert: false,
            client_opts: cli::ClientOpts {
                detect_proxy: false,
                validate_api_cert: false,
            },
            logging_opts: cli::LoggingOpts { verbose: 0 },
        }
    }

    fn runtime_config() -> RuntimeConfig {
        RuntimeConfig {
            allowed_ip: None,
            pull_port: None,
            detect_proxy: None,
            validate_api_cert: None,
        }
    }

    fn registration_preset() -> RegistrationPreset {
        RegistrationPreset {
            site_spec: None,
            credentials: None,
            root_certificate: None,
            host_name: None,
            agent_labels: None,
        }
    }

    #[test]
    fn test_args_win_over_preset() {
        let mut reg_preset = registration_preset();
        reg_preset.site_spec = Some(site_spec::PresetSiteSpec {
            server_spec: site_spec::ServerSpec {
                server: String::from("unused"),
                port: Some(0),
            },
            site: String::from("unused"),
        });
        reg_preset.credentials = Some(types::OptPwdCredentials {
            username: String::from("unused"),
            password: Some(String::from("unused")),
        });
        reg_preset.host_name = Some(String::from("unused"));

        let mut reg_args = registration_args();
        reg_args.server = Some(site_spec::ServerSpec {
            server: String::from("server"),
            port: Some(123),
        });
        reg_args.site = Some(String::from("site"));
        reg_args.host_name = Some(String::from("hostname"));
        reg_args.user = Some(String::from("user"));

        let reg_config = RegistrationConfig::new(runtime_config(), reg_preset, reg_args).unwrap();

        assert_eq!(reg_config.coordinates.server, "server");
        assert_eq!(reg_config.coordinates.port, 123);
        assert_eq!(reg_config.coordinates.site, "site");
        assert_eq!(reg_config.opt_pwd_credentials.username, "user");
        assert!(reg_config.opt_pwd_credentials.password.is_none());
        assert_eq!(
            reg_config.host_reg_data,
            HostRegistrationData::Name(String::from("hostname"))
        );
    }

    #[test]
    fn test_preset_as_fallback() {
        let mut reg_preset = registration_preset();
        reg_preset.site_spec = Some(site_spec::PresetSiteSpec {
            server_spec: site_spec::ServerSpec {
                server: String::from("server"),
                port: Some(123),
            },
            site: String::from("site"),
        });
        reg_preset.credentials = Some(types::OptPwdCredentials {
            username: String::from("user"),
            password: Some(String::from("secret")),
        });
        reg_preset.host_name = Some(String::from("hostname"));

        let reg_config =
            RegistrationConfig::new(runtime_config(), reg_preset, registration_args()).unwrap();

        assert_eq!(reg_config.coordinates.server, "server");
        assert_eq!(reg_config.coordinates.port, 123);
        assert_eq!(reg_config.coordinates.site, "site");
        assert_eq!(reg_config.opt_pwd_credentials.username, "user");
        assert_eq!(reg_config.opt_pwd_credentials.password.unwrap(), "secret");
        assert_eq!(
            reg_config.host_reg_data,
            HostRegistrationData::Name(String::from("hostname"))
        );
    }

    #[test]
    fn test_hostname_wins_over_labels() {
        let mut reg_preset = registration_preset();
        reg_preset.site_spec = Some(site_spec::PresetSiteSpec {
            server_spec: site_spec::ServerSpec {
                server: String::from("server"),
                port: Some(123),
            },
            site: String::from("site"),
        });
        reg_preset.credentials = Some(types::OptPwdCredentials {
            username: String::from("user"),
            password: None,
        });
        reg_preset.host_name = Some(String::from("hostname"));
        reg_preset.agent_labels = Some(types::AgentLabels::from([(
            String::from("a"),
            String::from("A"),
        )]));

        let reg_config =
            RegistrationConfig::new(runtime_config(), reg_preset, registration_args()).unwrap();

        assert_eq!(
            reg_config.host_reg_data,
            HostRegistrationData::Name(String::from("hostname"))
        );
    }

    #[test]
    fn test_automatic_agent_labels() {
        let mut reg_preset = registration_preset();
        reg_preset.site_spec = Some(site_spec::PresetSiteSpec {
            server_spec: site_spec::ServerSpec {
                server: String::from("server"),
                port: Some(123),
            },
            site: String::from("site"),
        });
        reg_preset.credentials = Some(types::OptPwdCredentials {
            username: String::from("user"),
            password: None,
        });
        reg_preset.agent_labels = Some(types::AgentLabels::new());

        let reg_config =
            RegistrationConfig::new(runtime_config(), reg_preset, registration_args()).unwrap();

        if let HostRegistrationData::Labels(al) = reg_config.host_reg_data {
            let mut keys = al.keys().collect::<Vec<&String>>();
            keys.sort();
            assert_eq!(keys, ["cmk/hostname-simple", "cmk/os-family"]);
        } else {
            panic!("Should have found agent labels")
        }
    }

    #[test]
    fn test_user_defined_agent_label_win_over_automatic_agent_labels() {
        let mut reg_preset = registration_preset();
        reg_preset.site_spec = Some(site_spec::PresetSiteSpec {
            server_spec: site_spec::ServerSpec {
                server: String::from("server"),
                port: Some(123),
            },
            site: String::from("site"),
        });
        reg_preset.credentials = Some(types::OptPwdCredentials {
            username: String::from("user"),
            password: None,
        });
        reg_preset.agent_labels = Some(types::AgentLabels::from([
            (String::from("cmk/os-family"), String::from("funny")),
            (String::from("key2"), String::from("value2")),
        ]));

        let reg_config =
            RegistrationConfig::new(runtime_config(), reg_preset, registration_args()).unwrap();

        if let HostRegistrationData::Labels(al) = reg_config.host_reg_data {
            let mut keys = al.keys().collect::<Vec<&String>>();
            keys.sort();
            assert_eq!(keys, ["cmk/hostname-simple", "cmk/os-family", "key2"]);
            assert_eq!(al["cmk/os-family"], "funny");
        } else {
            panic!("Should have found agent labels")
        }
    }
}

#[cfg(test)]
mod test_legacy_pull_marker {
    use super::*;

    fn legacy_pull_marker() -> LegacyPullMarker {
        LegacyPullMarker::new(tempfile::NamedTempFile::new().unwrap())
    }

    #[test]
    fn test_exists() {
        let lpm = legacy_pull_marker();
        assert!(!lpm.exists());
        lpm.create().unwrap();
        assert!(lpm.exists());
    }

    #[test]
    fn test_remove() {
        let lpm = legacy_pull_marker();
        assert!(lpm.remove().is_ok());
        lpm.create().unwrap();
        assert!(lpm.remove().is_ok());
        assert!(!lpm.exists());
    }

    #[test]
    fn test_create() {
        let lpm = legacy_pull_marker();
        lpm.create().unwrap();
        assert!(lpm.0.is_file());
    }
}

#[cfg(test)]
mod test_registry {
    use super::*;
    use std::str::FromStr;

    fn registry() -> Registry {
        let mut push = std::collections::HashMap::new();
        let mut pull = std::collections::HashMap::new();
        let mut pull_imported = std::collections::HashSet::new();

        push.insert(
            site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            Connection {
                uuid: uuid::Uuid::new_v4(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        pull.insert(
            site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            Connection {
                uuid: uuid::Uuid::new_v4(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );

        pull_imported.insert(Connection {
            uuid: uuid::Uuid::new_v4(),
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });

        Registry::new(
            RegisteredConnections {
                push,
                pull,
                pull_imported,
            },
            tempfile::NamedTempFile::new().unwrap(),
        )
        .unwrap()
    }

    fn connection() -> Connection {
        Connection {
            uuid: uuid::Uuid::new_v4(),
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        }
    }

    #[test]
    fn test_io() {
        let reg = registry();
        assert!(!reg.path.exists());

        reg.save().unwrap();
        assert!(reg.path.exists());
        #[cfg(unix)]
        assert_eq!(
            fs::metadata(&reg.path).unwrap().permissions().mode(),
            0o100600 // mode apparently returns the full file mode, not just the permission bits ...
        );

        let new_reg = Registry::from_file(&reg.path).unwrap();
        assert_eq!(reg.connections, new_reg.connections);
        assert_eq!(reg.path, new_reg.path);
        assert!(new_reg.last_reload.is_some());
    }

    #[test]
    fn test_reload() {
        let reg = registry();
        reg.save().unwrap();
        let mut reg = Registry::from_file(&reg.path).unwrap();
        assert!(!reg.refresh().unwrap());

        let mtime_before_reload = reg.last_reload.unwrap();
        // let a mini-bit of time pass st. we actually get a new mtime
        std::thread::sleep(std::time::Duration::from_millis(10));
        fs::write(&reg.path, "{}").unwrap();
        assert!(reg.refresh().unwrap());
        assert!(!reg
            .last_reload
            .unwrap()
            .duration_since(mtime_before_reload)
            .unwrap()
            .is_zero());
    }

    #[test]
    fn test_register_push_connection_new() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Push,
            &site_spec::Coordinates::from_str("new_server:1234/new-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_push_connection_from_pull() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Push,
            &site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_new() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Pull,
            &site_spec::Coordinates::from_str("new_server:1234/new-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_from_push() {
        let mut reg = registry();
        reg.register_connection(
            ConnectionType::Pull,
            &site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            connection(),
        );
        assert!(reg.connections.push.is_empty());
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_imported_connection() {
        let mut reg = registry();
        let conn = connection();
        let uuid = conn.uuid;
        reg.register_imported_connection(conn);
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 2);
        assert!(reg.connections.pull_imported.contains(&uuid));
    }

    #[test]
    fn test_is_empty() {
        let mut reg = registry();
        assert!(!reg.is_empty());
        reg.connections.push.clear();
        assert!(!reg.is_empty());
        reg.connections.pull.clear();
        assert!(!reg.is_empty());
        reg.connections.pull_imported.clear();
        assert!(reg.is_empty());
    }

    #[test]
    fn test_pull_connections() {
        let reg = registry();
        let pull_conns: Vec<&Connection> = reg.pull_connections().collect();
        assert!(pull_conns.len() == 2);
        assert!(
            pull_conns[0]
                == reg
                    .connections
                    .pull
                    .get(&site_spec::Coordinates::from_str("server:8000/pull-site").unwrap())
                    .unwrap()
        );
        assert!(reg.connections.pull_imported.contains(pull_conns[1]));
    }

    #[test]
    fn test_delete_push() {
        let mut reg = registry();
        assert!(reg
            .delete_standard_connection(
                &site_spec::Coordinates::from_str("server:8000/push-site").unwrap()
            )
            .is_ok());
        assert!(reg.connections.push.is_empty());
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_pull() {
        let mut reg = registry();
        assert!(reg
            .delete_standard_connection(
                &site_spec::Coordinates::from_str("server:8000/pull-site").unwrap()
            )
            .is_ok());
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_missing() {
        let mut reg = registry();
        assert_eq!(
            format!(
                "{}",
                reg.delete_standard_connection(
                    &site_spec::Coordinates::from_str("wiener_schnitzel:8000/pommes").unwrap()
                )
                .unwrap_err()
            ),
            "Connection 'wiener_schnitzel:8000/pommes' not found"
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_imported_connection_ok() {
        let uuid_first_imported = uuid::Uuid::new_v4();
        let uuid_second_imported = uuid::Uuid::new_v4();
        let mut reg = registry();
        reg.connections.pull_imported.clear();
        reg.register_imported_connection(Connection {
            uuid: uuid_first_imported,
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });
        reg.register_imported_connection(Connection {
            uuid: uuid_second_imported,
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });
        assert!(reg.delete_imported_connection(&uuid_first_imported).is_ok());
        assert!(reg.connections.pull_imported.len() == 1);
        assert!(reg
            .connections
            .pull_imported
            .contains(&uuid_second_imported));
    }

    #[test]
    fn test_delete_imported_connection_err() {
        let mut reg = registry();
        let uuid = uuid::Uuid::new_v4();
        assert_eq!(
            format!("{}", reg.delete_imported_connection(&uuid).unwrap_err()),
            format!("Imported pull connection with UUID {} not found", uuid),
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_clear() {
        let mut reg = registry();
        reg.clear();
        assert!(reg.is_empty());
    }
}
