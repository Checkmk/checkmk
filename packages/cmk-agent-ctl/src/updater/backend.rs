// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The artifacts of the updater model and their loading and saving.
//!
//! See [`crate::updater`] for what the three artifacts are and how they relate.

use crate::config::{tmp_path_for_atomical_save, JSONLoader, JSONLoaderMissingSafe, TOMLLoader};
use anyhow::{Context, Result as AnyhowResult};
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
    /// not configured for this host.
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
#[derive(Serialize, Deserialize, Default, Debug, PartialEq, Eq, Clone)]
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
    pub hash: String,

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
            hash: parse_key_value(&content)
                .remove(AGENT_HASH_KEY)
                .filter(|hash| !hash.is_empty())
                .context(format!("No {AGENT_HASH_KEY:?} in {path:?}"))?,
            platform: String::from(constants::WINDOWS_PLATFORM),
        })
    }
}

#[cfg(unix)]
impl JSONLoader for AgentInfo {}

/// Key of the agent hash in `checkmk.dat`.
#[cfg(windows)]
const AGENT_HASH_KEY: &str = "hash";

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
    use std::path::PathBuf;

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
                hash: String::from("0123456789abcdef"),
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
                hash: String::from("0123456789abcdef"),
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
}
