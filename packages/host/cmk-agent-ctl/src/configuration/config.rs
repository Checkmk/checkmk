// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::{certs, cli, constants, setup, site_spec, types};
use anyhow::{bail, Context, Result as AnyhowResult};
use serde::de::DeserializeOwned;
use serde::Deserialize;
use serde::Serialize;
use serde_with::DisplayFromStr;
use std::collections::HashMap;
use std::ffi;
use std::fmt;
use std::fs;
use std::io;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

pub trait JSONLoader: DeserializeOwned {
    fn load(path: &Path) -> AnyhowResult<Self> {
        Ok(serde_json::from_str(&fs::read_to_string(path)?)?)
    }
}

pub trait JSONLoaderMissingSafe: JSONLoader + Default {
    fn load_missing_safe(path: &Path) -> AnyhowResult<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        Self::load(path)
    }
}

pub trait TOMLLoader: DeserializeOwned {
    fn load(path: &Path) -> AnyhowResult<Self> {
        Ok(toml::from_str(&fs::read_to_string(path)?)?)
    }
}

pub trait TOMLLoaderMissingSafe: TOMLLoader + Default {
    fn load_missing_safe(path: &Path) -> AnyhowResult<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        Self::load(path)
    }
}

pub struct RegisterExistingConfig {
    pub connection_config: RegistrationConnectionConfig,
    pub host_name: String,
}

impl RegisterExistingConfig {
    pub fn new(
        runtime_config: RuntimeConfig,
        register_opts: cli::RegisterOpts,
    ) -> AnyhowResult<Self> {
        Ok(Self {
            connection_config: RegistrationConnectionConfig::new(
                runtime_config,
                register_opts.connection_opts,
            )?,
            host_name: register_opts.hostname,
        })
    }
}

pub struct RegisterNewConfig {
    pub connection_config: RegistrationConnectionConfig,
    pub agent_labels: types::AgentLabels,
}

impl RegisterNewConfig {
    pub fn new(
        connection_config: RegistrationConnectionConfig,
        agent_labels: types::AgentLabels,
    ) -> AnyhowResult<Self> {
        Ok(Self {
            connection_config,
            agent_labels: Self::enrich_with_automatic_agent_labels(agent_labels)?,
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

pub struct RegistrationConnectionConfig {
    pub site_id: site_spec::SiteID,
    pub receiver_port: u16,
    pub username: String,
    pub password: Option<String>,
    pub root_certificate: Option<String>,
    pub trust_server_cert: bool,
    pub client_config: ClientConfig,
}

impl RegistrationConnectionConfig {
    pub fn new(
        runtime_config: RuntimeConfig,
        registration_connection_opts: cli::RegistrationConnectionOpts,
    ) -> AnyhowResult<Self> {
        let site_id = site_spec::SiteID {
            server: registration_connection_opts.server_spec.server,
            site: registration_connection_opts.site,
        };
        let client_config = ClientConfig::new(
            runtime_config,
            registration_connection_opts.client_opts,
            Some(registration_connection_opts.reg_client_opts),
        );
        let receiver_port = (if let Some(p) = registration_connection_opts.server_spec.port {
            Ok(p)
        } else {
            site_spec::discover_receiver_port(&site_id, &client_config)
        })?;
        Ok(Self {
            site_id,
            receiver_port,
            username: registration_connection_opts.user,
            password: registration_connection_opts.password,
            root_certificate: None,
            trust_server_cert: registration_connection_opts.trust_server_cert,
            client_config,
        })
    }
}

#[derive(Deserialize)]
pub struct PreConfiguredConnections {
    pub connections: HashMap<site_spec::SiteID, PreConfiguredConnection>,
    pub agent_labels: types::AgentLabels,
    pub keep_existing_connections: bool,
}

impl JSONLoader for PreConfiguredConnections {}

#[derive(Deserialize, Clone)]
pub struct PreConfiguredConnection {
    pub port: Option<u16>,
    pub credentials: types::Credentials,
    pub root_cert: String,
}

#[derive(Deserialize, Clone, Default)]
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
impl TOMLLoaderMissingSafe for RuntimeConfig {}

#[derive(Clone)]
pub struct ClientConfig {
    pub use_proxy: bool,
    pub validate_api_cert: bool,
}

impl ClientConfig {
    pub fn new(
        runtime_config: RuntimeConfig,
        client_opts: cli::ClientOpts,
        reg_client_opts: Option<cli::RegistrationClientOpts>,
    ) -> ClientConfig {
        ClientConfig {
            use_proxy: client_opts.detect_proxy || runtime_config.detect_proxy.unwrap_or(false),
            validate_api_cert: (if let Some(reg_client_opts) = reg_client_opts {
                reg_client_opts.validate_api_cert
            } else {
                false
            }) || runtime_config.validate_api_cert.unwrap_or(false),
        }
    }
}

pub struct PullConfig {
    pub allowed_ip: Vec<String>,
    pub port: u16,
    pub max_connections: usize,
    pub connection_timeout: u64,
    pub agent_channel: types::AgentChannel,
    registry: Registry,
}

impl PullConfig {
    pub fn new(
        runtime_config: RuntimeConfig,
        pull_opts: cli::PullOpts,
        registry: Registry,
    ) -> AnyhowResult<PullConfig> {
        let allowed_ip = runtime_config.allowed_ip.unwrap_or_default();
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
            registry,
        })
    }

    pub fn refresh(&mut self) -> AnyhowResult<bool> {
        self.registry.refresh()
    }

    pub fn allow_legacy_pull(&self) -> bool {
        self.registry.is_legacy_pull_active()
    }

    pub fn get_pull_connections(&self) -> impl Iterator<Item = &TrustedConnection> {
        self.registry.get_pull_connections()
    }

    pub fn has_connections(&self) -> bool {
        !self.registry.is_pull_empty()
    }
}

#[derive(Clone)]
pub struct Registry {
    connections: RegisteredConnections,
    path: PathBuf,
    last_reload: Option<SystemTime>,
    legacy_pull_marker: LegacyPullMarker,
}

impl Registry {
    #[cfg(test)]
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn new(path: impl AsRef<Path>) -> AnyhowResult<Self> {
        Ok(Self {
            connections: RegisteredConnections::default(),
            path: PathBuf::from(path.as_ref()),
            last_reload: None,
            legacy_pull_marker: LegacyPullMarker::new(Self::make_path_legacy_pull_marker(path)?),
        })
    }

    pub fn from_file(path: impl AsRef<Path>) -> AnyhowResult<Self> {
        Ok(Self {
            connections: RegisteredConnections::load_missing_safe(path.as_ref())?,
            path: PathBuf::from(path.as_ref()),
            last_reload: mtime(path.as_ref())?,
            legacy_pull_marker: LegacyPullMarker::new(Self::make_path_legacy_pull_marker(path)?),
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
        let tmp_path = self.make_tmp_path_for_save();
        fs::write(&tmp_path, serde_json::to_string_pretty(&self.connections)?)?;
        fs::rename(&tmp_path, &self.path)?;
        #[cfg(unix)]
        fs::set_permissions(&self.path, fs::Permissions::from_mode(0o600))?;
        self.legacy_pull_marker.remove()
    }

    pub fn is_standard_pull_empty(&self) -> bool {
        self.connections.pull.is_empty()
    }

    pub fn is_imported_pull_empty(&self) -> bool {
        self.connections.pull_imported.is_empty()
    }

    pub fn is_pull_empty(&self) -> bool {
        self.is_standard_pull_empty() & self.is_imported_pull_empty()
    }

    pub fn is_push_empty(&self) -> bool {
        self.connections.push.is_empty()
    }

    pub fn is_empty(&self) -> bool {
        self.is_push_empty() & self.is_pull_empty()
    }

    pub fn get_standard_pull_connections(
        &self,
    ) -> impl Iterator<Item = (&site_spec::SiteID, &TrustedConnectionWithRemote)> {
        self.connections.pull.iter()
    }

    pub fn get_imported_pull_connections(&self) -> impl Iterator<Item = &TrustedConnection> {
        self.connections.pull_imported.iter()
    }

    pub fn get_pull_connections(&self) -> impl Iterator<Item = &TrustedConnection> {
        self.connections
            .pull
            .values()
            .map(|c| &c.trust)
            .chain(self.connections.pull_imported.iter())
    }

    pub fn get_push_connections(
        &self,
    ) -> impl Iterator<Item = (&site_spec::SiteID, &TrustedConnectionWithRemote)> {
        self.connections.push.iter()
    }

    pub fn get_standard_connections_as_mut(
        &mut self,
    ) -> impl Iterator<Item = (&site_spec::SiteID, &mut TrustedConnectionWithRemote)> {
        self.connections
            .push
            .iter_mut()
            .chain(self.connections.pull.iter_mut())
    }

    pub fn get_registered_site_ids(&self) -> impl Iterator<Item = &site_spec::SiteID> {
        self.connections
            .pull
            .keys()
            .chain(self.connections.push.keys())
    }

    pub fn get_connection_as_mut(
        &mut self,
        site_id: &site_spec::SiteID,
    ) -> Option<&mut TrustedConnectionWithRemote> {
        self.connections
            .pull
            .get_mut(site_id)
            .or_else(|| self.connections.push.get_mut(site_id))
    }

    pub fn register_connection(
        &mut self,
        connection_mode: &ConnectionMode,
        site_id: &site_spec::SiteID,
        connection: TrustedConnectionWithRemote,
    ) {
        let (insert_connections, remove_connections) = match connection_mode {
            ConnectionMode::Push => (&mut self.connections.push, &mut self.connections.pull),
            ConnectionMode::Pull => (&mut self.connections.pull, &mut self.connections.push),
        };
        remove_connections.remove(site_id);
        insert_connections.insert(site_id.clone(), connection);
    }

    pub fn register_imported_connection(&mut self, connection: TrustedConnection) {
        self.connections.pull_imported.insert(connection);
    }

    pub fn delete_standard_connection(&mut self, site_id: &site_spec::SiteID) -> AnyhowResult<()> {
        if self.connections.push.remove(site_id).is_some() {
            println!("Deleted push connection '{site_id}'");
            return Ok(());
        }
        if self.connections.pull.remove(site_id).is_some() {
            println!("Deleted pull connection '{site_id}'");
            return Ok(());
        }
        bail!("Connection '{}' not found", site_id)
    }

    pub fn delete_imported_connection(&mut self, uuid: &uuid::Uuid) -> AnyhowResult<()> {
        if self.connections.pull_imported.remove(uuid) {
            println!("Deleted imported connection '{uuid}'");
            return Ok(());
        };
        bail!("Imported pull connection with UUID {} not found", uuid)
    }

    pub fn clear(&mut self) {
        self.connections.push.clear();
        self.connections.pull.clear();
        self.clear_imported();
    }

    pub fn clear_imported(&mut self) {
        self.connections.pull_imported.clear();
    }

    pub fn is_legacy_pull_active(&self) -> bool {
        self.is_empty() && self.legacy_pull_marker.exists()
    }

    pub fn activate_legacy_pull(&self) -> AnyhowResult<()> {
        if !self.is_empty() {
            bail!("Cannot enable legacy pull mode since there are registered connections")
        }
        self.legacy_pull_marker
            .create()
            .context("Failed to activate legacy pull mode")
    }

    pub fn retrieve_standard_connection_by_uuid(
        &self,
        uuid: &uuid::Uuid,
    ) -> Option<site_spec::SiteID> {
        for (site_id, connection) in self
            .get_push_connections()
            .chain(self.get_standard_pull_connections())
        {
            if &connection.trust.uuid == uuid {
                return Some(site_id.clone());
            }
        }
        None
    }

    fn make_tmp_path_for_save(&self) -> PathBuf {
        let mut tmp_path = PathBuf::from(&self.path);
        let mut ext = tmp_path
            .extension()
            .map(|ext| ext.to_owned())
            .unwrap_or_else(|| ffi::OsString::from(""));
        ext.push(".tmp");
        tmp_path.set_extension(ext);
        tmp_path
    }

    fn make_path_legacy_pull_marker(registry_path: impl AsRef<Path>) -> AnyhowResult<PathBuf> {
        Ok(registry_path
            .as_ref()
            .parent()
            .context("Failed to determine parent path of connection registry")?
            .join("allow-legacy-pull"))
    }

    fn reload(&mut self) -> AnyhowResult<()> {
        self.connections = RegisteredConnections::load_missing_safe(&self.path)?;
        self.last_reload = mtime(&self.path)?;
        Ok(())
    }
}

#[derive(Serialize, Deserialize, PartialEq, Eq, Debug, Clone, Default)]
struct RegisteredConnections {
    #[serde(default)]
    push: HashMap<site_spec::SiteID, TrustedConnectionWithRemote>,

    #[serde(default)]
    pull: HashMap<site_spec::SiteID, TrustedConnectionWithRemote>,

    #[serde(default)]
    pull_imported: std::collections::HashSet<TrustedConnection>,
}

impl JSONLoader for RegisteredConnections {}
impl JSONLoaderMissingSafe for RegisteredConnections {}

#[derive(Serialize, Deserialize, Eq, Debug, Clone)]
pub struct TrustedConnectionWithRemote {
    #[serde(flatten)]
    pub trust: TrustedConnection,
    pub receiver_port: u16,
}

impl PartialEq for TrustedConnectionWithRemote {
    fn eq(&self, other: &Self) -> bool {
        self.trust == other.trust
    }
}

#[serde_with::serde_as]
#[derive(Serialize, Deserialize, Eq, Debug, Clone)]
pub struct TrustedConnection {
    #[serde_as(as = "DisplayFromStr")]
    pub uuid: uuid::Uuid,
    pub private_key: String,
    pub certificate: String,
    pub root_cert: String,
}

impl PartialEq for TrustedConnection {
    fn eq(&self, other: &Self) -> bool {
        self.uuid == other.uuid
    }
}

impl std::hash::Hash for TrustedConnection {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.uuid.hash(state);
    }
}

impl std::borrow::Borrow<uuid::Uuid> for TrustedConnection {
    fn borrow(&self) -> &uuid::Uuid {
        &self.uuid
    }
}

impl TrustedConnection {
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

#[derive(Debug, Clone)]
struct LegacyPullMarker(std::path::PathBuf);

impl LegacyPullMarker {
    fn new(path: impl AsRef<Path>) -> Self {
        Self(PathBuf::from(path.as_ref()))
    }

    fn exists(&self) -> bool {
        self.0.exists()
    }

    fn remove(&self) -> std::io::Result<()> {
        if !&self.exists() {
            return Ok(());
        }

        fs::remove_file(&self.0)
    }

    fn create(&self) -> std::io::Result<()> {
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

#[derive(Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConnectionMode {
    /// `push-agent`
    #[serde(rename = "push-agent")]
    Push,
    /// `pull-agent`
    #[serde(rename = "pull-agent")]
    Pull,
}

impl fmt::Display for ConnectionMode {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match &self {
            Self::Push => write!(f, "push-agent"),
            Self::Pull => write!(f, "pull-agent"),
        }
    }
}

fn mtime(path: &Path) -> AnyhowResult<Option<SystemTime>> {
    Ok(if path.exists() {
        Some(fs::metadata(path)?.modified()?)
    } else {
        None
    })
}

#[cfg(test)]
pub mod test_helpers {
    use crate::config::{ConnectionMode, Registry, TrustedConnection, TrustedConnectionWithRemote};
    use crate::site_spec;
    use std::convert::From;
    use std::str::FromStr;

    pub struct TestRegistry {
        pub registry: Registry,
        _dir: Option<tempfile::TempDir>,
    }

    impl Drop for TestRegistry {
        fn drop(&mut self) {
            // We can manage to move the TempDir out (close() needs to) by replacing it with None.
            // drop(self._dir);
            self._dir.take().unwrap().close().unwrap();
        }
    }

    impl Default for TestRegistry {
        fn default() -> Self {
            Self::new()
        }
    }

    impl TestRegistry {
        pub fn new() -> Self {
            let test_dir = Some(tempfile::tempdir().unwrap());
            let registry = TestRegistry::create_registry(&test_dir);
            Self {
                registry,
                _dir: test_dir,
            }
        }

        pub fn create_registry(dir: &Option<tempfile::TempDir>) -> Registry {
            Registry::new(
                dir.as_ref()
                    .unwrap()
                    .path()
                    .join("registered_connections.json"),
            )
            .unwrap()
        }

        pub fn add_connection<T>(
            mut self,
            mode: &ConnectionMode,
            site_name: &str,
            uuid: T, //uuid::Uuid,
        ) -> Self
        where
            TrustedConnectionWithRemote: From<T>,
        {
            self.registry.register_connection(
                mode,
                &site_spec::SiteID::from_str(site_name).unwrap(),
                TrustedConnectionWithRemote::from(uuid),
            );

            self
        }
        pub fn add_imported_connection<T>(mut self, uuid: T) -> Self
        where
            TrustedConnection: From<T>,
        {
            self.registry
                .register_imported_connection(TrustedConnection::from(uuid));

            self
        }

        pub fn fill_registry(self) -> Self {
            self.add_connection(
                &ConnectionMode::Push,
                "server/push-site",
                trusted_connection_with_remote(),
            )
            .add_connection(
                &ConnectionMode::Pull,
                "server/pull-site",
                trusted_connection_with_remote(),
            )
            .add_imported_connection(trusted_connection())
        }
    }

    pub fn trusted_connection_with_remote() -> TrustedConnectionWithRemote {
        TrustedConnectionWithRemote::from(uuid::Uuid::new_v4())
    }

    pub fn trusted_connection() -> TrustedConnection {
        TrustedConnection::from(uuid::Uuid::new_v4())
    }

    impl From<uuid::Uuid> for TrustedConnection {
        fn from(u: uuid::Uuid) -> Self {
            Self {
                uuid: u,
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            }
        }
    }

    impl From<&str> for TrustedConnection {
        fn from(s: &str) -> Self {
            Self::from(uuid::Uuid::from_str(s).unwrap())
        }
    }

    impl From<uuid::Uuid> for TrustedConnectionWithRemote {
        fn from(u: uuid::Uuid) -> Self {
            Self {
                trust: TrustedConnection::from(u),
                receiver_port: 8000,
            }
        }
    }

    impl From<&str> for TrustedConnectionWithRemote {
        fn from(s: &str) -> Self {
            Self::from(uuid::Uuid::from_str(s).unwrap())
        }
    }

    impl Registry {
        pub fn get(&self, site_id: &site_spec::SiteID) -> Option<&TrustedConnectionWithRemote> {
            self.connections
                .pull
                .get(site_id)
                .or_else(|| self.connections.push.get(site_id))
        }
    }
}

#[cfg(test)]
mod test_registration_config {
    use super::*;

    fn registration_connection_opts() -> cli::RegistrationConnectionOpts {
        cli::RegistrationConnectionOpts {
            server_spec: site_spec::ServerSpec {
                server: String::from("server"),
                port: Some(8000),
            },
            site: String::from("site"),
            user: String::from("user"),
            password: None,
            trust_server_cert: false,
            client_opts: cli::ClientOpts {
                detect_proxy: false,
            },
            reg_client_opts: cli::RegistrationClientOpts {
                validate_api_cert: false,
            },
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

    #[test]
    fn test_connection_config() {
        let connection_config =
            RegistrationConnectionConfig::new(runtime_config(), registration_connection_opts())
                .unwrap();
        assert_eq!(connection_config.site_id.server, "server");
        assert_eq!(connection_config.site_id.site, "site");
        assert_eq!(connection_config.receiver_port, 8000);
        assert_eq!(connection_config.username, "user");
        assert!(connection_config.password.is_none());
    }

    #[test]
    fn test_host_name_config() {
        assert_eq!(
            RegisterExistingConfig::new(
                runtime_config(),
                cli::RegisterOpts {
                    connection_opts: registration_connection_opts(),
                    hostname: String::from("host_name"),
                },
            )
            .unwrap()
            .host_name,
            "host_name"
        );
    }

    #[test]
    fn test_automatic_agent_labels() {
        let agent_labels = RegisterNewConfig::new(
            RegistrationConnectionConfig::new(runtime_config(), registration_connection_opts())
                .unwrap(),
            types::AgentLabels::new(),
        )
        .unwrap()
        .agent_labels;

        let mut keys = agent_labels.keys().collect::<Vec<&String>>();
        keys.sort();
        assert_eq!(keys, ["cmk/hostname-simple", "cmk/os-family"]);
    }

    #[test]
    fn test_user_defined_labels() {
        let agent_labels = RegisterNewConfig::new(
            RegistrationConnectionConfig::new(runtime_config(), registration_connection_opts())
                .unwrap(),
            types::AgentLabels::from([
                (
                    String::from("cmk/hostname-simple"),
                    String::from("custom-name"),
                ),
                (String::from("a"), String::from("b")),
            ]),
        )
        .unwrap()
        .agent_labels;

        let mut keys = agent_labels.keys().collect::<Vec<&String>>();
        keys.sort();
        assert_eq!(keys, ["a", "cmk/hostname-simple", "cmk/os-family"]);
        assert_eq!(agent_labels["cmk/hostname-simple"], "custom-name");
        assert_eq!(agent_labels["a"], "b");
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
        lpm.remove().unwrap();
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
        // clean up
        lpm.remove().unwrap();
    }
}

#[cfg(test)]
mod test_client_config {
    use super::*;

    #[test]
    fn test_defaults() {
        let client_config = ClientConfig::new(
            RuntimeConfig {
                allowed_ip: None,
                pull_port: None,
                detect_proxy: None,
                validate_api_cert: None,
            },
            cli::ClientOpts {
                detect_proxy: false,
            },
            None,
        );
        assert!(!client_config.use_proxy);
        assert!(!client_config.validate_api_cert);
    }

    #[test]
    fn test_from_runtime_config() {
        let client_config = ClientConfig::new(
            RuntimeConfig {
                allowed_ip: None,
                pull_port: None,
                detect_proxy: Some(true),
                validate_api_cert: Some(true),
            },
            cli::ClientOpts {
                detect_proxy: false,
            },
            Some(cli::RegistrationClientOpts {
                validate_api_cert: false,
            }),
        );
        assert!(client_config.use_proxy);
        assert!(client_config.validate_api_cert);
    }

    #[test]
    fn test_from_client_opts() {
        let client_config = ClientConfig::new(
            RuntimeConfig {
                allowed_ip: None,
                pull_port: None,
                detect_proxy: None,
                validate_api_cert: None,
            },
            cli::ClientOpts { detect_proxy: true },
            Some(cli::RegistrationClientOpts {
                validate_api_cert: true,
            }),
        );
        assert!(client_config.use_proxy);
        assert!(client_config.validate_api_cert);
    }
}

#[cfg(test)]
mod test_registry {
    use super::*;
    use crate::config::test_helpers::{
        trusted_connection, trusted_connection_with_remote, TestRegistry,
    };
    use std::convert::From;
    use std::str::FromStr;

    #[test]
    fn test_io() {
        let test_registry = TestRegistry::new().fill_registry();
        let reg = &test_registry.registry;
        assert!(!reg.path.exists());

        reg.save().unwrap();
        assert!(reg.path.exists());
        assert!(!reg.make_tmp_path_for_save().exists());
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
        let test_registry = TestRegistry::new().fill_registry();
        let reg = &test_registry.registry;
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
    fn test_new() {
        let reg = Registry::new(tempfile::NamedTempFile::new().unwrap().as_ref()).unwrap();
        assert!(reg.is_pull_empty() && reg.is_push_empty());
        assert!(reg.last_reload.is_none());
    }

    #[test]
    fn test_register_push_connection_new() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.register_connection(
            &ConnectionMode::Push,
            &site_spec::SiteID::from_str("new_server/new-site").unwrap(),
            trusted_connection_with_remote(),
        );
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_push_connection_from_pull() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.register_connection(
            &ConnectionMode::Push,
            &site_spec::SiteID::from_str("server/pull-site").unwrap(),
            trusted_connection_with_remote(),
        );
        assert!(reg.connections.push.len() == 2);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_new() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.register_connection(
            &ConnectionMode::Pull,
            &site_spec::SiteID::from_str("new_server/new-site").unwrap(),
            trusted_connection_with_remote(),
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_pull_connection_from_push() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.register_connection(
            &ConnectionMode::Pull,
            &site_spec::SiteID::from_str("server/push-site").unwrap(),
            trusted_connection_with_remote(),
        );
        assert!(reg.connections.push.is_empty());
        assert!(reg.connections.pull.len() == 2);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_register_imported_connection() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        let conn = trusted_connection();
        let uuid = conn.uuid;
        reg.register_imported_connection(conn);
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 2);
        assert!(reg.connections.pull_imported.contains(&uuid));
    }

    #[test]
    fn test_retrieve_standard_connection_by_uuid() {
        let test_registry = TestRegistry::new().fill_registry();
        let reg = &test_registry.registry;
        let uuid_push = reg.get_push_connections().next().unwrap().1.trust.uuid;
        let uuid_pull = reg
            .get_standard_pull_connections()
            .next()
            .unwrap()
            .1
            .trust
            .uuid;
        let uuid_imported = reg.get_imported_pull_connections().next().unwrap().uuid;

        assert!(
            reg.retrieve_standard_connection_by_uuid(&uuid_push)
                == Some(site_spec::SiteID::from_str("server/push-site").unwrap())
        );
        assert!(
            reg.retrieve_standard_connection_by_uuid(&uuid_pull)
                == Some(site_spec::SiteID::from_str("server/pull-site").unwrap())
        );
        assert!(reg
            .retrieve_standard_connection_by_uuid(&uuid_imported)
            .is_none());
        assert!(reg
            .retrieve_standard_connection_by_uuid(&uuid::Uuid::new_v4())
            .is_none());
    }

    #[test]
    fn test_is_empty() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
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
        let test_registry = TestRegistry::new().fill_registry();
        let reg = &test_registry.registry;
        let pull_conns: Vec<&TrustedConnection> = reg.get_pull_connections().collect();
        assert!(pull_conns.len() == 2);
        assert!(
            pull_conns[0]
                == &reg
                    .connections
                    .pull
                    .get(&site_spec::SiteID::from_str("server/pull-site").unwrap())
                    .unwrap()
                    .trust
        );
        assert!(reg.connections.pull_imported.contains(pull_conns[1]));
    }

    #[test]
    fn test_registered_site_ids() {
        let test_registry = TestRegistry::new().fill_registry();
        let reg = &test_registry.registry;
        let mut reg_site_ids: Vec<String> = reg
            .get_registered_site_ids()
            .map(|s| s.to_string())
            .collect();
        reg_site_ids.sort_unstable();
        assert_eq!(reg_site_ids, vec!["server/pull-site", "server/push-site"]);
    }

    #[test]
    fn test_get_mutable() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        let pull_conn = reg
            .get_standard_pull_connections()
            .next()
            .unwrap()
            .1
            .clone();
        let push_conn = reg.get_push_connections().next().unwrap().1.clone();
        assert_eq!(
            reg.get_connection_as_mut(&site_spec::SiteID::from_str("server/pull-site").unwrap())
                .unwrap(),
            &pull_conn
        );
        assert_eq!(
            reg.get_connection_as_mut(&site_spec::SiteID::from_str("server/push-site").unwrap())
                .unwrap(),
            &push_conn
        );
        assert!(reg
            .get_connection_as_mut(&site_spec::SiteID::from_str("a/b").unwrap())
            .is_none());
    }

    #[test]
    fn test_delete_push() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        assert!(reg
            .delete_standard_connection(&site_spec::SiteID::from_str("server/push-site").unwrap())
            .is_ok());
        assert!(reg.connections.push.is_empty());
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_pull() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        assert!(reg
            .delete_standard_connection(&site_spec::SiteID::from_str("server/pull-site").unwrap())
            .is_ok());
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.is_empty());
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_missing() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        assert_eq!(
            format!(
                "{}",
                reg.delete_standard_connection(
                    &site_spec::SiteID::from_str("wiener_schnitzel/pommes").unwrap()
                )
                .unwrap_err()
            ),
            "Connection 'wiener_schnitzel/pommes' not found"
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_delete_imported_connection_ok() {
        let uuid_first_imported = uuid::Uuid::new_v4();
        let uuid_second_imported = uuid::Uuid::new_v4();
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.connections.pull_imported.clear();
        reg.register_imported_connection(TrustedConnection::from(uuid_first_imported));
        reg.register_imported_connection(TrustedConnection::from(uuid_second_imported));
        assert!(reg.delete_imported_connection(&uuid_first_imported).is_ok());
        assert!(reg.connections.pull_imported.len() == 1);
        assert!(reg
            .connections
            .pull_imported
            .contains(&uuid_second_imported));
    }

    #[test]
    fn test_delete_imported_connection_err() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        let uuid = uuid::Uuid::new_v4();
        assert_eq!(
            format!("{}", reg.delete_imported_connection(&uuid).unwrap_err()),
            format!("Imported pull connection with UUID {uuid} not found"),
        );
        assert!(reg.connections.push.len() == 1);
        assert!(reg.connections.pull.len() == 1);
        assert!(reg.connections.pull_imported.len() == 1);
    }

    #[test]
    fn test_clear() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.clear();
        assert!(reg.is_empty());
    }

    #[test]
    fn test_clear_imported() {
        let mut test_registry = TestRegistry::new().fill_registry();
        let reg = &mut test_registry.registry;
        reg.clear_imported();
        assert!(reg.is_imported_pull_empty());
        assert!(!reg.is_empty());
    }

    #[test]
    fn test_legacy_pull_marker_handling() {
        let mut test_registry = TestRegistry::new();
        let registry = &mut test_registry.registry;
        assert!(!registry.is_legacy_pull_active());
        assert!(registry.activate_legacy_pull().is_ok());
        assert!(registry.is_legacy_pull_active());
        registry.register_connection(
            &ConnectionMode::Push,
            &site_spec::SiteID::from_str("server/push-site").unwrap(),
            trusted_connection_with_remote(),
        );
        assert!(!registry.is_legacy_pull_active());
        assert!(registry.activate_legacy_pull().is_err());
        registry.save().unwrap();
        assert!(!registry.legacy_pull_marker.exists());
    }

    #[test]
    fn test_tmp_path_for_save() {
        let reg = Registry::new(PathBuf::from("/a/b/c.json")).unwrap();
        assert_ne!(reg.path(), reg.make_tmp_path_for_save());
        assert_eq!(reg.path().parent(), reg.make_tmp_path_for_save().parent());
        assert!(reg
            .make_tmp_path_for_save()
            .file_name()
            .unwrap()
            .to_str()
            .unwrap()
            .contains(reg.path().file_name().unwrap().to_str().unwrap()));
    }

    #[test]
    fn test_mode_serialization() {
        assert_eq!(
            serde_json::to_string(&ConnectionMode::Pull).unwrap(),
            "\"pull-agent\""
        );
        assert_eq!(
            serde_json::to_string(&ConnectionMode::Push).unwrap(),
            "\"push-agent\""
        );
        assert_eq!(
            serde_json::from_str::<ConnectionMode>("\"push-agent\"").unwrap(),
            ConnectionMode::Push
        );
        assert_eq!(
            serde_json::from_str::<ConnectionMode>("\"pull-agent\"").unwrap(),
            ConnectionMode::Pull
        );
    }

    #[test]
    fn test_connection_mode_display() {
        assert_eq!("pull-agent", format!("{}", ConnectionMode::Pull));
        assert_eq!("push-agent", format!("{}", ConnectionMode::Push));
    }
}
