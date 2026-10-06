// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The artifacts of the updater model, their loading and saving, and the entry
//! point that works on them.
//!
//! See [`crate::updater`] for what the three artifacts are and how they relate.

use super::connection;
use crate::agent_receiver_api;
use crate::config::{
    tmp_path_for_atomical_save, JSONLoader, JSONLoaderMissingSafe, Registry, TOMLLoader,
};
use crate::environment::PathResolver;
use crate::site_spec;
use crate::types::AgentHash;
use anyhow::{Context, Error, Result as AnyhowResult};
use log::{log, Level};
use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::Path;

#[cfg(windows)]
use super::platform::parse_key_value;
#[cfg(windows)]
use crate::constants;

/// Fallback update interval, matching the default of the agent updater ruleset.
const DEFAULT_INTERVAL: u64 = 3600;

/// Permissions of the state file: owner only, as for the connection registry.
/// The state carries the last error, which quotes paths and the site address.
#[cfg(unix)]
const STATE_FILE_MODE: u32 = 0o600;

/// Longest last error reported to the site, in characters. The state file may
/// hold a longer one - the site only quotes it back in its deployment views.
const LAST_ERROR_MAX_LEN: usize = 512;

fn default_activated() -> bool {
    true
}

fn default_interval() -> u64 {
    DEFAULT_INTERVAL
}

/// The updater configuration deployed by the bakery.
///
/// Every field has a default and unknown keys are ignored, so that a newer
/// Checkmk site can bake a configuration for an older controller.
#[derive(Deserialize, Debug, PartialEq, Eq)]
pub struct UpdaterConfig {
    /// Whether this host is supposed to update its agent automatically.
    #[serde(default = "default_activated")]
    pub activated: bool,

    /// Seconds between two update checks.
    #[serde(default = "default_interval")]
    pub interval: u64,

    /// PEM-encoded certificates whose signatures are accepted for an agent package. .
    #[serde(default)]
    pub signature_keys: Vec<String>,
}

impl TOMLLoader for UpdaterConfig {}

impl UpdaterConfig {
    /// Load the updater configuration from `path`.
    ///
    /// # Returns
    ///
    /// `None` if the file does not exist, which means that agent updates are
    /// not configured for this host. An inaccessible file counts as absent.
    ///
    /// # Errors
    ///
    /// Returns an error if the file exists but cannot be read or parsed.
    pub fn load_if_configured(path: &Path) -> AnyhowResult<Option<Self>> {
        if !path.exists() {
            return Ok(None);
        }
        Ok(Some(<Self as TOMLLoader>::load(path).context(format!(
            "Failed to load the updater configuration from {path:?}"
        ))?))
    }
}

/// Operational state of the updater, owned and written by the controller.
///
/// A missing state file is equivalent to the default state, so the first run on
/// a freshly installed host needs no bootstrapping.
#[derive(Serialize, Deserialize, Debug, Default, PartialEq, Eq, Clone)]
pub struct UpdateState {
    /// Unix timestamp of the last check against the site.
    pub last_check: Option<u64>,

    /// Unix timestamp of the last completed agent installation.
    pub last_update: Option<u64>,

    /// Hash of a package whose installation has been triggered but whose
    /// outcome is not known yet. The installation restarts the controller, so
    /// the outcome can only be reconciled on a later run.
    pub pending_hash: Option<String>,

    /// Last error, reported back to the site on the next check.
    pub last_error: Option<String>,
}

impl JSONLoader for UpdateState {}
impl JSONLoaderMissingSafe for UpdateState {}

impl UpdateState {
    /// Write the state to `path` atomically.
    ///
    /// # Errors
    ///
    /// Returns an error if the state cannot be serialized, written or renamed.
    pub fn save(&self, path: &Path) -> AnyhowResult<()> {
        let tmp_path = tmp_path_for_atomical_save(path);
        write_restricted(&tmp_path, &serde_json::to_string_pretty(self)?)
            .context(format!("Failed to write {tmp_path:?}"))?;
        fs::rename(&tmp_path, path).context(format!("Failed to move {tmp_path:?} to {path:?}"))
    }
}

/// Information about the installed agent package, written into the package by
/// the bakery.
///
/// The bakery writes two different artifacts, located by
/// [`crate::environment::PathResolver::agent_info_path`]:
///
/// * `agent_info.json` on Unix - JSON, carrying hash and platform.
/// * `checkmk.dat` on Windows - YAML, `hash: value` line
#[derive(Deserialize, Debug, PartialEq, Eq)]
pub struct AgentInfo {
    /// Hash of the baked agent package, as the site knows it.
    pub hash: AgentHash,

    /// Target platform of the package, for example "linux_deb".
    /// Constant on Windows, the artifact carries none.
    pub platform: String,
}

impl AgentInfo {
    /// Load the info of the installed agent package from `path`.
    ///
    /// # Errors
    ///
    /// If the file cannot be read or parsed.
    #[cfg(unix)]
    pub fn load(path: &Path) -> AnyhowResult<Self> {
        <Self as JSONLoader>::load(path)
            .context(format!("Failed to load the agent info from {path:?}"))
    }

    /// Load the info of the installed agent package from `path`.
    ///
    /// # Errors
    ///
    /// If the file cannot be read or carries no usable hash.
    #[cfg(windows)]
    pub fn load(path: &Path) -> AnyhowResult<Self> {
        let content = fs::read_to_string(path)
            .context(format!("Failed to read the agent info from {path:?}"))?;
        Ok(Self {
            hash: AgentHash::try_from(
                parse_key_value(&content)
                    .remove(AGENT_HASH_KEY)
                    .context(format!("No {AGENT_HASH_KEY:?} in {path:?}"))?,
            )
            .context(format!("Unusable {AGENT_HASH_KEY:?} in {path:?}"))?,
            platform: String::from(constants::WINDOWS_PLATFORM),
        })
    }
}

#[cfg(unix)]
impl JSONLoader for AgentInfo {}

/// Key of the agent hash in `checkmk.dat`.
#[cfg(windows)]
const AGENT_HASH_KEY: &str = "hash";

/// An agent package as the site delivered it, not verified yet.
#[derive(Debug)]
pub struct UpdatePackage {
    /// Hash the site named it by, and the name it is spooled under later.
    pub hash: AgentHash,

    /// The package itself.
    pub bytes: Vec<u8>,
}

/// The three updater artifacts of this host, loaded together.
///
/// Fields are private: what is missing or broken is only observable through
/// [`Updater::is_operational`] and [`Updater::summary`].
pub struct Updater {
    config: Option<UpdaterConfig>,
    state: UpdateState,
    agent_info: Option<AgentInfo>,
    load_error: Option<Error>,
}

impl Updater {
    pub fn new(paths: &PathResolver) -> Self {
        let mut load_error = None;
        let config = Self::load_or_log(
            "updater configuration",
            Level::Warn,
            UpdaterConfig::load_if_configured(&paths.updater_config_path),
            &mut load_error,
        )
        .flatten();
        // Unparsable state means a broken controller: non-operational by design.
        let state = Self::load_or_log(
            "updater state",
            Level::Warn,
            UpdateState::load_missing_safe(&paths.updater_state_path).context(format!(
                "Failed to load the updater state from {:?}",
                paths.updater_state_path
            )),
            &mut load_error,
        )
        .unwrap_or_default();
        let agent_info = Self::load_or_log(
            "agent info",
            Level::Info,
            AgentInfo::load(&paths.agent_info_path),
            &mut load_error,
        );

        Self {
            config,
            state,
            agent_info,
            load_error,
        }
    }

    /// Keeps the *first* error: the artifacts fail independently, so the first
    /// one is simply the stable choice for a line to diff across hosts.
    fn load_or_log<T>(
        what: &str,
        level: Level,
        result: AnyhowResult<T>,
        load_error: &mut Option<Error>,
    ) -> Option<T> {
        match result {
            Ok(value) => Some(value),
            Err(error) => {
                log!(level, "Continuing without {what}: {error:#}");
                load_error.get_or_insert(error);
                None
            }
        }
    }

    /// One-liner for logging/tracing.
    pub fn summary(&self) -> String {
        format!(
            "operational: {}{}, config '{}', state {:?}, agent hash '{}'",
            self.is_operational(),
            self.load_error
                .as_ref()
                .map_or_else(String::new, |error| format!(", error '{error:#}'")),
            self.config
                .as_ref()
                .map(|config| format!(
                    "activated: {}, interval {}",
                    config.activated, config.interval
                ))
                .unwrap_or_else(|| String::from("not configured")),
            self.state,
            self.agent_info
                .as_ref()
                .map_or("unknown", |info| info.hash.as_str())
        )
    }

    /// In some cases Updater can't work, for example, when agent hash is unknown
    /// or config file is absent/broken
    ///
    /// True even when the config has `activated = false`: by design.
    pub fn is_operational(&self) -> bool {
        self.load_error.is_none() && self.config.is_some() && self.agent_info.is_some()
    }

    /// Whether this host is supposed to update its agent automatically.
    ///
    /// False when no updater configuration is deployed at all.
    fn is_activated(&self) -> bool {
        self.config.as_ref().is_some_and(|config| config.activated)
    }

    // TODO(sk): Split this function into `if check_***() then update_***()`
    /// Integrated updater main action.
    ///
    /// The updater reuses the controller's registration. It picks one of the
    /// registered connections and talks to that site over the connection's mTLS
    /// channel, where the receiver authenticates the host by the client
    /// certificate and resolves its UUID to a host name.
    ///
    /// # Returns
    ///
    /// `true` when the updater is in a position to contact a site:
    /// operational, activated, and a connection was selected.
    pub fn handle_update_cycle(&self, registry: &Registry) -> bool {
        if !self.is_operational() {
            log::info!("Skipping the agent update: the updater is not operational");
            return false;
        }
        if !self.is_activated() {
            log::info!("Skipping the agent update: automatic agent updates are deactivated");
            return false;
        }
        let Some(selected) = connection::select(registry) else {
            log::info!(
                "Skipping the agent update: none of the registered connections carries a \
                 site address (imported connections cannot serve updates)"
            );
            return false;
        };
        log::info!(
            "{} of the registered connections can serve agent updates, using the {} \
             connection to {}: the site authenticates this host by the client \
             certificate of {}, so the updater needs neither a registration nor a \
             secret of its own",
            connection::candidates(registry).count(),
            selected.mode,
            selected.site_id,
            selected.connection.trust.uuid
        );
        true
    }

    /// Ask the site behind `selected` which agent package it has for this host.
    ///
    /// The request carries the hash of the installed package and the error of
    /// the last update attempt: the site keeps no state about the host beyond
    /// what the host reports. It is authenticated by the client certificate of
    /// the connection alone - see [`super::connection`].
    ///
    /// # Errors
    ///
    /// If nothing is known about the installed agent, if the site address
    /// cannot be assembled, or if the site does not answer with a status this
    /// controller can parse.
    pub fn request_update_status(
        &self,
        api: &impl agent_receiver_api::AgentUpdate,
        selected: &connection::UpdateConnection<'_>,
    ) -> AnyhowResult<agent_receiver_api::UpdateStatusResponse> {
        let agent_info = self
            .agent_info
            .as_ref()
            .context("Cannot ask for an agent update without the info of the installed agent")?;
        let url = site_spec::make_site_url(selected.site_id, &selected.connection.receiver_port)?;
        api.update_status(
            &url,
            &selected.connection.trust,
            &agent_receiver_api::UpdateStatusBody {
                platform: &agent_info.platform,
                installed_aghash: &agent_info.hash,
                last_error: self.reported_last_error(),
            },
        )
        .context(format!(
            "Agent update status request to {} failed",
            selected.site_id
        ))
    }

    /// Fetch the package `status` offers, unless it is the installed one.
    ///
    /// The package is not verified here: it is held in memory until its
    /// signature has been checked, and only then written anywhere.
    ///
    /// # Returns
    ///
    /// `None` when the site offers no package, or offers the installed one -
    /// the two ways a check ends without an update.
    ///
    /// # Errors
    ///
    /// If nothing is known about the installed agent, if the site address
    /// cannot be assembled, or if the site does not deliver the package.
    pub fn download_update(
        &self,
        api: &impl agent_receiver_api::AgentUpdate,
        selected: &connection::UpdateConnection<'_>,
        status: &agent_receiver_api::UpdateStatusResponse,
    ) -> AnyhowResult<Option<UpdatePackage>> {
        let agent_info = self
            .agent_info
            .as_ref()
            .context("Cannot download an agent update without the info of the installed agent")?;
        let Some(target) = status.target_agent.as_ref().map(|offered| &offered.aghash) else {
            log::info!("No agent package available for this host");
            return Ok(None);
        };
        if *target == agent_info.hash {
            log::info!("The installed agent {target} is the one the site offers");
            return Ok(None);
        }
        let url = site_spec::make_site_url(selected.site_id, &selected.connection.receiver_port)?;
        let bytes = api
            .download_agent(
                &url,
                &selected.connection.trust,
                &agent_receiver_api::AgentDownloadBody {
                    platform: &agent_info.platform,
                    aghash: target,
                },
            )
            .context(format!(
                "Agent update download of {target} from {} failed",
                selected.site_id
            ))?;
        log::info!(
            "Downloaded the agent package {target} ({} bytes) from {}, installed is {}",
            bytes.len(),
            selected.site_id,
            agent_info.hash
        );
        Ok(Some(UpdatePackage {
            hash: target.clone(),
            bytes,
        }))
    }

    /// The last error in the form the site gets it.
    fn reported_last_error(&self) -> Option<&str> {
        let error = self.state.last_error.as_deref()?;
        // By character, not by byte: slicing in the middle of a multi-byte
        // character would panic.
        let end = error
            .char_indices()
            .nth(LAST_ERROR_MAX_LEN)
            .map_or(error.len(), |(index, _)| index);
        Some(&error[..end])
    }

    pub fn signature_keys(&self) -> &[String] {
        self.config
            .as_ref()
            .map_or(&[], |config| &config.signature_keys)
    }

    pub fn platform(&self) -> Option<&str> {
        self.agent_info.as_ref().map(|info| info.platform.as_str())
    }

    /// The error of the last update attempt, not the `load_error` of this run.
    pub fn last_error(&self) -> Option<&str> {
        self.state.last_error.as_deref()
    }
}

/// Write `contents` to `path`, owner-readable only from the moment the file
/// comes into existence.
///
/// `mode` applies to the creation only and is masked by the umask, and a
/// temporary file left behind by an interrupted save keeps the mode it was
/// created with - hence the explicit [`fs::set_permissions`] afterwards.
#[cfg(unix)]
fn write_restricted(path: &Path, contents: &str) -> io::Result<()> {
    use std::io::Write;
    use std::os::unix::fs::OpenOptionsExt;

    let mut file = fs::OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .mode(STATE_FILE_MODE)
        .open(path)?;
    file.write_all(contents.as_bytes())?;
    file.set_permissions(fs::Permissions::from_mode(STATE_FILE_MODE))
}

/// Write `contents` to `path`. Windows inherits the permissions of the
/// directory, which the installer owns.
#[cfg(windows)]
fn write_restricted(path: &Path, contents: &str) -> io::Result<()> {
    fs::write(path, contents)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;
    use crate::config::{ConnectionMode, TrustedConnection};
    use crate::environment::SetupMode;
    use std::cell::RefCell;
    use std::path::PathBuf;

    use crate::agent_receiver_api::{TargetAgent, UpdateStatusResponse};

    const INSTALLED_HASH: &str = "0123456789abcdef";
    const TARGET_HASH: &str = "fedcba9876543210";
    const CONNECTION_UUID: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a01";
    const PACKAGE: &[u8] = b"an agent package";

    const UPDATER_CONFIG_TOML: &str = "\
activated = false
interval = 60
signature_keys = [\"-----BEGIN CERTIFICATE-----\\nabc\\n-----END CERTIFICATE-----\\n\"]
";

    /// `checkmk.dat` as the bakery writes it: the agent file header, then the
    /// hash, with CRLF line endings throughout.
    #[cfg(windows)]
    const CHECKMK_DAT: &str = concat!(
        "# Created by Check_MK Agent Bakery.\r\n",
        "# This file is managed via WATO, do not edit manually or you\r\n",
        "# lose your changes next time when you update the agent.\r\n",
        "\r\n",
        "hash: 0123456789abcdef\r\n",
    );

    /// The agent info of the installed package, in the form the bakery writes it
    /// for the platform under test. Both carry the same hash.
    #[cfg(unix)]
    const AGENT_INFO: &str = r#"{"hash": "0123456789abcdef", "platform": "linux_deb"}"#;
    #[cfg(windows)]
    const AGENT_INFO: &str = CHECKMK_DAT;
    #[cfg(unix)]
    const SETUP_MODE: SetupMode = SetupMode::SingleDir;
    #[cfg(windows)]
    const SETUP_MODE: SetupMode = SetupMode::Classic;

    const SIGNATURE_KEY: &str = "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n";

    fn write(dir: &tempfile::TempDir, name: &str, content: &str) -> PathBuf {
        let path = dir.path().join(name);
        fs::write(&path, content).unwrap();
        path
    }

    #[test]
    fn test_load_config() {
        let dir = tempfile::TempDir::new().unwrap();
        assert_eq!(
            UpdaterConfig::load_if_configured(&write(&dir, "config.toml", UPDATER_CONFIG_TOML))
                .unwrap()
                .unwrap(),
            UpdaterConfig {
                activated: false,
                interval: 60,
                signature_keys: vec![String::from(
                    "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n"
                )],
            }
        );
    }

    #[test]
    fn test_load_config_missing_file_is_not_configured() {
        let dir = tempfile::TempDir::new().unwrap();
        assert!(
            UpdaterConfig::load_if_configured(&dir.path().join("config.toml"))
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn test_load_config_applies_defaults() {
        let dir = tempfile::TempDir::new().unwrap();
        assert_eq!(
            UpdaterConfig::load_if_configured(&write(&dir, "config.toml", ""))
                .unwrap()
                .unwrap(),
            UpdaterConfig {
                activated: true,
                interval: DEFAULT_INTERVAL,
                signature_keys: vec![],
            }
        );
    }

    #[test]
    fn test_load_config_ignores_unknown_keys() {
        let dir = tempfile::TempDir::new().unwrap();
        let config = UpdaterConfig::load_if_configured(&write(
            &dir,
            "config.toml",
            "interval = 60\nbaked_by_a_newer_site = \"whatever\"\n",
        ))
        .unwrap()
        .unwrap();
        assert_eq!(config.interval, 60);
    }

    #[test]
    fn test_load_config_malformed() {
        let dir = tempfile::TempDir::new().unwrap();
        assert!(
            UpdaterConfig::load_if_configured(&write(&dir, "config.toml", "interval = "))
                .unwrap_err()
                .to_string()
                .contains("Failed to load the updater configuration")
        );
    }

    #[test]
    fn test_load_state_missing_file_is_default() {
        let dir = tempfile::TempDir::new().unwrap();
        assert_eq!(
            UpdateState::load_missing_safe(&dir.path().join("state.json")).unwrap(),
            UpdateState::default()
        );
    }

    #[test]
    fn test_save_and_load_state() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("state.json");
        let state = UpdateState {
            last_check: Some(1759276800),
            last_update: Some(1759190400),
            pending_hash: Some(String::from("0123456789abcdef")),
            last_error: Some(String::from("boom")),
        };

        state.save(&path).unwrap();

        assert_eq!(UpdateState::load(&path).unwrap(), state);
    }

    #[test]
    fn test_save_state_overwrites_previous_state() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("state.json");
        UpdateState {
            last_check: Some(1759276800),
            ..Default::default()
        }
        .save(&path)
        .unwrap();

        UpdateState::default().save(&path).unwrap();

        assert_eq!(UpdateState::load(&path).unwrap(), UpdateState::default());
    }

    #[test]
    fn test_save_state_leaves_no_temporary_file_behind() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("state.json");

        UpdateState::default().save(&path).unwrap();

        assert!(!tmp_path_for_atomical_save(&path).exists());
    }

    #[test]
    fn test_save_state_to_missing_directory() {
        let dir = tempfile::TempDir::new().unwrap();

        assert!(UpdateState::default()
            .save(&dir.path().join("nowhere").join("state.json"))
            .is_err());
    }

    #[cfg(unix)]
    #[test]
    fn test_load_agent_info() {
        let dir = tempfile::TempDir::new().unwrap();
        assert_eq!(
            AgentInfo::load(&write(
                &dir,
                "agent_info.json",
                // agent_controller_user is written by the bakery, but of no
                // interest to the controller - it runs as that user.
                r#"{"hash": "0123456789abcdef", "platform": "linux_deb", "agent_controller_user": "cmk-agent"}"#,
            ))
            .unwrap(),
            AgentInfo {
                hash: INSTALLED_HASH.parse().unwrap(),
                platform: String::from("linux_deb"),
            }
        );
    }

    #[test]
    fn test_load_agent_info_missing_file() {
        let dir = tempfile::TempDir::new().unwrap();
        assert!(AgentInfo::load(&dir.path().join("missing")).is_err());
    }

    #[cfg(windows)]
    #[test]
    fn test_load_agent_info_from_dat() {
        let dir = tempfile::TempDir::new().unwrap();
        assert_eq!(
            AgentInfo::load(&write(&dir, "checkmk.dat", CHECKMK_DAT)).unwrap(),
            AgentInfo {
                hash: INSTALLED_HASH.parse().unwrap(),
                platform: String::from("windows_msi"),
            }
        );
    }

    #[cfg(windows)]
    #[test]
    fn test_load_agent_info_without_hash() {
        let dir = tempfile::TempDir::new().unwrap();
        assert!(
            AgentInfo::load(&write(&dir, "checkmk.dat", "# just a comment\r\n"))
                .unwrap_err()
                .to_string()
                .contains("No \"hash\"")
        );
    }

    #[cfg(windows)]
    #[test]
    fn test_load_agent_info_with_an_empty_hash() {
        let dir = tempfile::TempDir::new().unwrap();
        assert!(AgentInfo::load(&write(&dir, "checkmk.dat", "hash:\r\n")).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn test_save_state_is_readable_by_the_owner_only() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("state.json");

        UpdateState::default().save(&path).unwrap();

        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            STATE_FILE_MODE
        );
    }

    /// A temporary file left behind by an interrupted save is reused, and
    /// `mode` has no effect on an existing file - so the save has to narrow it.
    #[cfg(unix)]
    #[test]
    fn test_save_state_narrows_a_leftover_temporary_file() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("state.json");
        let tmp_path = write(&dir, "state.json.tmp", "leftover");
        fs::set_permissions(&tmp_path, fs::Permissions::from_mode(0o644)).unwrap();

        UpdateState::default().save(&path).unwrap();

        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            STATE_FILE_MODE
        );
    }

    /// The layout that keeps all three artifacts below one directory, so that it
    /// can be set up in a temporary one: the single directory layout on Unix, the
    /// classic layout on Windows, where the agent info sits in `install` below
    /// the controller's home.
    fn artifact_paths(dir: &tempfile::TempDir) -> PathResolver {
        let paths = PathResolver::new(SETUP_MODE, dir.path());
        for path in [
            &paths.updater_config_path,
            &paths.updater_state_path,
            &paths.agent_info_path,
        ] {
            fs::create_dir_all(path.parent().unwrap()).unwrap();
        }
        paths
    }

    #[test]
    fn test_updater_new_loads_the_three_artifacts() {
        let dir = tempfile::TempDir::new().unwrap();
        let paths = artifact_paths(&dir);
        fs::write(&paths.updater_config_path, UPDATER_CONFIG_TOML).unwrap();
        UpdateState {
            last_check: Some(1759276800),
            ..Default::default()
        }
        .save(&paths.updater_state_path)
        .unwrap();
        fs::write(&paths.agent_info_path, AGENT_INFO).unwrap();

        let updater = Updater::new(&paths);

        assert!(updater.load_error.is_none());
        assert_eq!(updater.config.unwrap().interval, 60);
        assert_eq!(updater.state.last_check, Some(1759276800));
        assert_eq!(updater.agent_info.unwrap().hash.as_str(), INSTALLED_HASH);
    }

    #[test]
    fn test_updater_new_tolerates_missing_artifacts() {
        let dir = tempfile::TempDir::new().unwrap();

        let updater = Updater::new(&artifact_paths(&dir));

        assert!(updater.config.is_none());
        assert_eq!(updater.state, UpdateState::default());
        assert!(updater.agent_info.is_none());
    }

    /// A missing agent info is the only load failure on a host without any
    /// updater artifacts: config and state have a defined absent state.
    #[test]
    fn test_updater_new_without_artifacts_is_not_operational() {
        let dir = tempfile::TempDir::new().unwrap();

        let updater = Updater::new(&artifact_paths(&dir));

        assert!(updater.load_error.is_some());
        assert!(!updater.is_operational());
    }

    #[test]
    fn test_updater_new_survives_a_malformed_config() {
        let dir = tempfile::TempDir::new().unwrap();
        let paths = artifact_paths(&dir);
        fs::write(&paths.updater_config_path, "interval = ").unwrap();

        let updater = Updater::new(&paths);

        assert!(updater.config.is_none());
        assert!(!updater.is_operational());
        // The agent info fails to load afterwards, but the config error is kept.
        // The context quotes the path with `{:?}`, which escapes the separators
        // of a Windows path, so the expectation has to be built the same way.
        assert!(updater
            .load_error
            .unwrap()
            .to_string()
            .contains(&format!("{:?}", paths.updater_config_path)));
    }

    #[test]
    fn test_summary_without_config_and_agent_info() {
        let summary = Updater {
            config: None,
            state: UpdateState::default(),
            agent_info: None,
            load_error: None,
        }
        .summary();

        assert!(summary.starts_with("operational: false, config 'not configured'"));
        assert!(summary.contains("agent hash 'unknown'"));
    }

    #[test]
    fn test_summary_reports_the_state() {
        let summary = Updater {
            state: UpdateState {
                last_check: Some(1759276800),
                last_error: Some(String::from("https://site.example/check_mk is unreachable")),
                ..Default::default()
            },
            ..updater(some_config(), some_agent_info())
        }
        .summary();

        assert!(summary.contains("last_check: Some(1759276800)"));
        assert!(summary.contains("site.example"));
    }

    #[test]
    fn test_summary_reports_the_load_error() {
        let summary = Updater {
            load_error: Some(Error::msg("broken artifact")),
            ..updater(some_config(), some_agent_info())
        }
        .summary();

        assert!(summary.starts_with("operational: false, error 'broken artifact', config '"));
    }

    #[test]
    fn test_summary_reports_config_and_hash_but_no_signature_keys() {
        let updater = Updater {
            config: Some(UpdaterConfig {
                signature_keys: vec![String::from(SIGNATURE_KEY)],
                ..some_config().unwrap()
            }),
            ..updater(some_config(), some_agent_info())
        };

        let summary = updater.summary();

        assert!(summary.starts_with("operational: true, config '"));
        assert!(summary.contains("activated: true, interval 60"));
        assert!(summary.contains("0123456789abcdef"));
        // Carried by the updater, deliberately kept out of the log line.
        assert_eq!(updater.signature_keys(), [String::from(SIGNATURE_KEY)]);
        assert!(!summary.contains("BEGIN CERTIFICATE"));
    }

    #[test]
    fn test_signature_keys_without_a_config() {
        assert!(updater(None, some_agent_info()).signature_keys().is_empty());
    }

    #[test]
    fn test_platform_of_the_installed_package() {
        assert_eq!(
            updater(some_config(), some_agent_info()).platform(),
            Some("linux_deb")
        );
        assert_eq!(updater(some_config(), None).platform(), None);
    }

    #[test]
    fn test_last_error_of_the_state() {
        let updater = Updater {
            state: UpdateState {
                last_error: Some(String::from("https://site.example/check_mk is unreachable")),
                ..Default::default()
            },
            ..updater(some_config(), some_agent_info())
        };

        assert_eq!(
            updater.last_error(),
            Some("https://site.example/check_mk is unreachable")
        );
    }

    #[test]
    fn test_last_error_of_a_state_without_one() {
        assert_eq!(updater(some_config(), some_agent_info()).last_error(), None);
    }

    fn some_config() -> Option<UpdaterConfig> {
        Some(UpdaterConfig {
            activated: true,
            interval: 60,
            signature_keys: vec![],
        })
    }

    fn some_agent_info() -> Option<AgentInfo> {
        Some(AgentInfo {
            hash: INSTALLED_HASH.parse().unwrap(),
            platform: String::from("linux_deb"),
        })
    }

    /// The state plays no role for [`Updater::is_operational`].
    fn updater(config: Option<UpdaterConfig>, agent_info: Option<AgentInfo>) -> Updater {
        Updater {
            config,
            state: UpdateState::default(),
            agent_info,
            load_error: None,
        }
    }

    #[test]
    fn test_is_operational_with_config_and_agent_info() {
        assert!(updater(some_config(), some_agent_info()).is_operational());
    }

    #[test]
    fn test_is_not_operational_without_config_or_agent_info() {
        assert!(!updater(some_config(), None).is_operational());
        assert!(!updater(None, some_agent_info()).is_operational());
        assert!(!updater(None, None).is_operational());
    }

    #[test]
    fn test_is_not_operational_after_a_load_error() {
        let updater = Updater {
            load_error: Some(Error::msg("broken artifact")),
            ..updater(some_config(), some_agent_info())
        };

        assert!(!updater.is_operational());
    }

    #[test]
    fn test_is_operational_when_not_activated() {
        let config = UpdaterConfig {
            activated: false,
            ..some_config().unwrap()
        };

        assert!(updater(Some(config), some_agent_info()).is_operational());
    }

    #[test]
    fn test_is_activated() {
        assert!(updater(some_config(), some_agent_info()).is_activated());
    }

    #[test]
    fn test_is_not_activated_without_config() {
        assert!(!updater(None, some_agent_info()).is_activated());
    }

    /// A registry holding the one connection that could serve agent updates.
    fn registry_with_one_connection() -> TestRegistry {
        TestRegistry::new().add_connection(&ConnectionMode::Pull, "server/site", CONNECTION_UUID)
    }

    #[test]
    fn test_maybe_update_agent_selects_a_connection() {
        let registry = registry_with_one_connection();

        assert!(updater(some_config(), some_agent_info()).handle_update_cycle(&registry.registry));
    }

    #[test]
    fn test_maybe_update_agent_without_a_reachable_site() {
        let registry = TestRegistry::new();

        assert!(!updater(some_config(), some_agent_info()).handle_update_cycle(&registry.registry));
    }

    #[test]
    fn test_maybe_update_agent_when_not_operational() {
        let registry = registry_with_one_connection();

        assert!(!updater(some_config(), None).handle_update_cycle(&registry.registry));
    }

    #[test]
    fn test_maybe_update_agent_when_deactivated() {
        let registry = registry_with_one_connection();
        let config = UpdaterConfig {
            activated: false,
            ..some_config().unwrap()
        };

        assert!(!updater(Some(config), some_agent_info()).handle_update_cycle(&registry.registry));
    }

    /// The parts of a status request a test looks at, owned: the body borrows
    /// the updater's artifacts and does not outlive the call.
    struct RecordedRequest {
        url: String,
        uuid: String,
        platform: String,
        installed_aghash: String,
        last_error: Option<String>,
    }

    /// The parts of a download request a test looks at.
    struct RecordedDownload {
        url: String,
        uuid: String,
        platform: String,
        aghash: String,
    }

    /// Fake Site with a canned status and package, and remembers what it was asked.
    struct TestApi {
        response: agent_receiver_api::UpdateStatusResponse,
        request: RefCell<Option<RecordedRequest>>, // internally mutable
        download: RefCell<Option<RecordedDownload>>, // internally mutable
    }

    impl TestApi {
        fn new(target: Option<&str>) -> Self {
            Self {
                response: offered(target),
                request: RefCell::new(None),
                download: RefCell::new(None),
            }
        }

        /// The request of the one call made, consumed by the assertions.
        fn request(&self) -> RecordedRequest {
            self.request
                .borrow_mut()
                .take()
                .expect("no request was made")
        }

        /// The download of the one call made, if the updater made one at all.
        fn download(&self) -> Option<RecordedDownload> {
            self.download.borrow_mut().take()
        }
    }

    impl agent_receiver_api::AgentUpdate for TestApi {
        fn update_status(
            &self,
            base_url: &reqwest::Url,
            connection: &TrustedConnection,
            body: &agent_receiver_api::UpdateStatusBody<'_>,
        ) -> AnyhowResult<agent_receiver_api::UpdateStatusResponse> {
            *self.request.borrow_mut() = Some(RecordedRequest {
                url: base_url.to_string(),
                uuid: connection.uuid.to_string(),
                platform: String::from(body.platform),
                installed_aghash: String::from(body.installed_aghash.as_str()),
                last_error: body.last_error.map(String::from),
            });
            Ok(self.response.clone())
        }

        fn download_agent(
            &self,
            base_url: &reqwest::Url,
            connection: &TrustedConnection,
            body: &agent_receiver_api::AgentDownloadBody<'_>,
        ) -> AnyhowResult<Vec<u8>> {
            *self.download.borrow_mut() = Some(RecordedDownload {
                url: base_url.to_string(),
                uuid: connection.uuid.to_string(),
                platform: String::from(body.platform),
                aghash: String::from(body.aghash.as_str()),
            });
            Ok(PACKAGE.to_vec())
        }
    }

    /// A site that cannot be reached.
    struct UnreachableApi;

    impl agent_receiver_api::AgentUpdate for UnreachableApi {
        fn update_status(
            &self,
            _base_url: &reqwest::Url,
            _connection: &TrustedConnection,
            _body: &agent_receiver_api::UpdateStatusBody<'_>,
        ) -> AnyhowResult<agent_receiver_api::UpdateStatusResponse> {
            Err(Error::msg("connection refused"))
        }

        fn download_agent(
            &self,
            _base_url: &reqwest::Url,
            _connection: &TrustedConnection,
            _body: &agent_receiver_api::AgentDownloadBody<'_>,
        ) -> AnyhowResult<Vec<u8>> {
            Err(Error::msg("connection refused"))
        }
    }

    /// The status of a site that has `target` for this host.
    fn offered(target: Option<&str>) -> UpdateStatusResponse {
        UpdateStatusResponse {
            target_agent: target.map(|hash| TargetAgent {
                aghash: hash.parse().unwrap(),
                signatures: vec![],
            }),
        }
    }

    /// An updater whose last update attempt ended in `last_error`.
    fn updater_after(last_error: Option<&str>) -> Updater {
        Updater {
            state: UpdateState {
                last_error: last_error.map(String::from),
                ..Default::default()
            },
            ..updater(some_config(), some_agent_info())
        }
    }

    #[test]
    fn test_request_update_status_reports_the_installed_hash_and_the_last_error() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(Some(TARGET_HASH));

        updater_after(Some("boom"))
            .request_update_status(&api, &selected)
            .unwrap();

        let request = api.request();
        assert_eq!(request.url, "https://server:8000/site");
        assert_eq!(request.uuid, CONNECTION_UUID);
        assert_eq!(request.platform, "linux_deb");
        assert_eq!(request.installed_aghash, INSTALLED_HASH);
        assert_eq!(request.last_error.unwrap(), "boom");
    }

    #[test]
    fn test_request_update_status_after_a_successful_cycle_reports_no_error() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(None);

        updater_after(None)
            .request_update_status(&api, &selected)
            .unwrap();

        assert!(api.request().last_error.is_none());
    }

    /// The state file may hold an arbitrarily long error; the site gets a
    /// bounded one.
    #[test]
    fn test_request_update_status_truncates_a_long_last_error() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(None);
        // Two bytes per character: truncating by byte would split one.
        let last_error = "ä".repeat(LAST_ERROR_MAX_LEN + 10);

        updater_after(Some(&last_error))
            .request_update_status(&api, &selected)
            .unwrap();

        assert_eq!(
            api.request().last_error.unwrap().chars().count(),
            LAST_ERROR_MAX_LEN
        );
    }

    #[test]
    fn test_request_update_status_keeps_a_short_last_error_whole() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(None);
        let last_error = "e".repeat(LAST_ERROR_MAX_LEN);

        updater_after(Some(&last_error))
            .request_update_status(&api, &selected)
            .unwrap();

        assert_eq!(api.request().last_error.unwrap(), last_error);
    }

    #[test]
    fn test_request_update_status_parses_the_offered_package() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();

        let status = updater_after(None)
            .request_update_status(&TestApi::new(Some(TARGET_HASH)), &selected)
            .unwrap();

        assert_eq!(status.target_agent.unwrap().aghash.as_str(), TARGET_HASH);
    }

    #[test]
    fn test_request_update_status_parses_a_site_without_a_package() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();

        let status = updater_after(None)
            .request_update_status(&TestApi::new(None), &selected)
            .unwrap();

        assert!(status.target_agent.is_none());
    }

    #[test]
    fn test_request_update_status_without_agent_info() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();

        let error = updater(some_config(), None)
            .request_update_status(&TestApi::new(None), &selected)
            .unwrap_err();

        assert!(error.to_string().contains("info of the installed agent"));
    }

    #[test]
    fn test_request_update_status_names_the_site_that_did_not_answer() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();

        let error = updater_after(None)
            .request_update_status(&UnreachableApi, &selected)
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Agent update status request to server/site failed"
        );
    }

    #[test]
    fn test_download_update_fetches_a_package_that_is_not_installed() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(None);

        let package = updater_after(None)
            .download_update(&api, &selected, &offered(Some(TARGET_HASH)))
            .unwrap()
            .unwrap();

        assert_eq!(package.hash.as_str(), TARGET_HASH);
        assert_eq!(package.bytes, PACKAGE);
        let download = api.download().unwrap();
        assert_eq!(download.url, "https://server:8000/site");
        assert_eq!(download.uuid, CONNECTION_UUID);
        assert_eq!(download.platform, "linux_deb");
        assert_eq!(download.aghash, TARGET_HASH);
    }

    #[test]
    fn test_download_update_when_the_offered_package_is_the_installed_one() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(None);

        assert!(updater_after(None)
            .download_update(&api, &selected, &offered(Some(INSTALLED_HASH)))
            .unwrap()
            .is_none());
        assert!(api.download().is_none());
    }

    #[test]
    fn test_download_update_without_an_offered_package() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();
        let api = TestApi::new(None);

        assert!(updater_after(None)
            .download_update(&api, &selected, &offered(None))
            .unwrap()
            .is_none());
        assert!(api.download().is_none());
    }

    #[test]
    fn test_download_update_without_agent_info() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();

        let error = updater(some_config(), None)
            .download_update(&TestApi::new(None), &selected, &offered(Some(TARGET_HASH)))
            .unwrap_err();

        assert!(error.to_string().contains("info of the installed agent"));
    }

    #[test]
    fn test_download_update_names_the_package_and_the_site_that_failed() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry).unwrap();

        let error = updater_after(None)
            .download_update(&UnreachableApi, &selected, &offered(Some(TARGET_HASH)))
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Agent update download of fedcba9876543210 from server/site failed"
        );
    }
}
