// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The artifacts of the updater model, their loading and saving, and the entry
//! point that works on them.
//!
//! See [`crate::updater`] for what the three artifacts are and how they relate.

use super::connection;
#[cfg(unix)]
use super::install;
#[cfg(windows)]
use super::platform::parse_key_value;
use super::verification;
use crate::agent_receiver_api;
use crate::config::{
    tmp_path_for_atomical_save, JSONLoader, JSONLoaderMissingSafe, Registry, TOMLLoader,
    UpdaterRegistration,
};
#[cfg(windows)]
use crate::constants;
use crate::environment::PathResolver;
use crate::site_spec;
use crate::types::AgentHash;
use anyhow::{anyhow, bail, Context, Error, Result as AnyhowResult};
use log::{log, Level};
use serde::{Deserialize, Serialize};
use serde_with::DisplayFromStr;
use std::fs;
use std::fs::File;
use std::io;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use x509_parser::certificate::X509Certificate;

/// Fallback update interval, matching the default of the agent updater ruleset.
const DEFAULT_INTERVAL: u64 = 3600;

/// Permissions of the state file: owner only, as for the connection registry.
/// The state carries the last error, which quotes paths and the site address.
/// Without effect on Windows, where the file inherits them from its directory.
const STATE_FILE_MODE: u32 = 0o600;

/// Permissions of a spooled agent package: the controller writes it, the
/// privileged installer reads it, nobody else gets to see it.
/// Without effect on Windows, where the file inherits them from its directory.
const PACKAGE_FILE_MODE: u32 = 0o640;

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

    /// Where the privileged install step of this host listens.
    ///
    /// Linux only: the bakery writes it into the configuration of a package
    /// that ships the installer unit. Absent means a package can be fetched but
    /// not handed over to anybody.
    #[serde(default)]
    pub installer_socket: Option<PathBuf>,
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

/// The connection the updater talks to its site over.
///
/// The updater has no site of its own: it reuses one of the controller's
/// registered connections, where the receiver authenticates this host by the
/// connection's client certificate. Recording which one was taken keeps the
/// choice stable across runs.
///
/// Only the UUID is recorded. The site it belongs to is whatever the registry
/// keys that connection under, looked up when it is needed - a stored site
/// could name a connection that is no longer there.
#[serde_with::serde_as]
#[derive(Serialize, Deserialize, Debug, PartialEq, Eq, Clone)]
pub struct UpdateSource {
    /// UUID of the source connection.
    #[serde_as(as = "DisplayFromStr")]
    pub uuid: uuid::Uuid,

    /// Whether the site serves agent updates. False once it answered 501.
    pub available: bool,
}

/// Operational state of the updater, owned and written by the controller.
///
/// A missing state file is equivalent to the default state, so the first run on
/// a freshly installed host needs no bootstrapping.
#[derive(Serialize, Deserialize, Debug, Default, PartialEq, Eq, Clone)]
pub struct UpdateState {
    /// The connection the updater uses. Absent until one was recorded.
    pub source: Option<UpdateSource>,

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
        write_restricted(
            &tmp_path,
            serde_json::to_string_pretty(self)?.as_bytes(),
            STATE_FILE_MODE,
        )
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
///
/// Cannot be saved
#[derive(Debug)]
pub struct UpdatePackage {
    /// Hash the site named it by, and the name it is spooled under later.
    hash: AgentHash,

    /// Target platform of the package, which decides its file name extension.
    platform: String,

    /// The package itself.
    bytes: Vec<u8>,
}

/// Whether a fetch insists on a signature it can verify.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SignatureCheck {
    /// Refuse a package whose signature does not verify.
    Required,

    /// Spool the package whatever its signature says.
    Skip,
}

impl SignatureCheck {
    /// How a package checked this way is named, wherever it is named: in the
    /// controller log and in the line the update mode prints.
    ///
    /// The spooled file carries no mark of what was checked about it, so these
    /// lines are the only record of it, and both must word it the same way.
    pub fn package_name(self, hash: &AgentHash) -> String {
        let checked = match self {
            Self::Required => "Verified",
            Self::Skip => "UNVERIFIED",
        };
        format!("{checked} agent package {hash}")
    }
}

impl UpdatePackage {
    /// Check the package against the signatures the site delivered with it and
    /// the local certificates.
    ///
    /// _Consumes_ the package: the unverified bytes of a semi-trusted site are
    /// gone afterwards, only the verified package remains.
    ///
    /// # Returns
    ///
    /// The same package as [`VerifiedPackage`].
    ///
    /// # Errors
    ///
    /// If none of `signatures` is a valid signature of the package under one of
    /// `local_certificates`.
    pub fn verify(
        self,
        signatures: &[agent_receiver_api::AgentSignature],
        local_certificates: &[X509Certificate],
    ) -> AnyhowResult<VerifiedPackage> {
        verification::verify(&self.bytes, signatures, local_certificates)?;
        Ok(VerifiedPackage(self))
    }

    /// Take the package as it is, with its signature never looked at.
    ///
    /// The one way to an [`UnverifiedPackage`], and nothing it yields can be
    /// passed where a [`VerifiedPackage`] is asked for. Private on purpose:
    /// only the [`SignatureCheck::Skip`] branch of [`Updater::fetch_update`],
    /// which `--skip-signatures` reaches, may call it.
    ///
    /// In future this API entry may be disabled, removed or limited.
    fn accept_unverified(self) -> UnverifiedPackage {
        log::warn!(
            "Not checking the signature of the agent package {}, as asked: \
             nothing vouches for it",
            self.hash
        );
        UnverifiedPackage(self)
    }
}

/// An agent package a signature of the site vouches for.
///
/// Reached only through [`UpdatePackage::verify`], so a function that asks for
/// one is asking for a package that was checked.
#[derive(Debug)]
pub struct VerifiedPackage(UpdatePackage);

impl VerifiedPackage {
    fn hash(&self) -> &AgentHash {
        &self.0.hash
    }

    /// Write the package to `dir`, as described at [`spool`], and report where
    /// it went.
    ///
    /// The spooled file carries no mark of what was checked about it, so that
    /// line is the only record of it.
    ///
    /// # Returns
    ///
    /// The path the package was written to.
    ///
    /// # Errors
    ///
    /// If no package format is known for the platform, or if the directory or
    /// the package cannot be written.
    pub fn save(&self, dir: &Path) -> AnyhowResult<PathBuf> {
        let path = spool(&self.0, dir)?;
        log::info!("Spooled: {self} at {path:?}, waiting for the installer");
        Ok(path)
    }
}

/// An agent package nothing vouches for.
///
/// It can be spooled - `--skip-signatures` exists for that - but only by
/// [`UnverifiedPackage::save_unverified`], which no caller reaches by reflex
/// or by mistaking it for the checked one.
#[derive(Debug)]
pub struct UnverifiedPackage(UpdatePackage);

impl UnverifiedPackage {
    fn hash(&self) -> &AgentHash {
        &self.0.hash
    }

    /// Write the package to `dir`, as described at [`spool`], although nothing
    /// says the site it came from is the one it claims to come from, and report
    /// where it went.
    ///
    /// The line it writes is a warning, visible without `-v`: the only word
    /// anyone gets that a privileged installer is about to take a package
    /// nobody vouched for.
    ///
    /// # Returns
    ///
    /// The path the package was written to.
    ///
    /// # Errors
    ///
    /// If no package format is known for the platform, or if the directory or
    /// the package cannot be written.
    pub fn save_unverified(&self, dir: &Path) -> AnyhowResult<PathBuf> {
        let path = spool(&self.0, dir)?;
        log::warn!("Spooled: {self} at {path:?}, waiting for the installer");
        Ok(path)
    }
}

impl std::fmt::Display for VerifiedPackage {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", SignatureCheck::Required.package_name(&self.0.hash))
    }
}

impl std::fmt::Display for UnverifiedPackage {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", SignatureCheck::Skip.package_name(&self.0.hash))
    }
}

/// Atomically write `package` to `dir` as `<hash>.<extension>`,
/// `dir` may be created if absent.
///
/// This is the point where bytes delivered by a semi-trusted site turn into a
/// file that a privileged process will install. Private, and reached only
/// through [`VerifiedPackage::save`] or [`UnverifiedPackage::save_unverified`]:
/// the writing is the same, what differs is who may ask for it.
///
/// # Returns
///
/// The path the package was written to.
///
/// # Errors
///
/// If no package format is known for the platform, or if the directory or the
/// package cannot be written.
fn spool(package: &UpdatePackage, dir: &Path) -> AnyhowResult<PathBuf> {
    let path = dir.join(format!(
        "{}.{}",
        package.hash,
        package_extension(&package.platform)?
    ));
    fs::create_dir_all(dir).context(format!("Failed to create {dir:?}"))?;
    let tmp_path = tmp_path_for_atomical_save(&path);
    write_restricted(&tmp_path, &package.bytes, PACKAGE_FILE_MODE)
        .context(format!("Failed to write {tmp_path:?}"))?;
    fs::rename(&tmp_path, &path).context(format!("Failed to move {tmp_path:?} to {path:?}"))?;
    Ok(path)
}

/// File name extension of an agent package, by the platform the bakery names.
///
/// # Errors
///
/// If no package format is known for `platform`, which is what the controller
/// sees when the site offers a package it cannot install.
fn package_extension(platform: &str) -> AnyhowResult<&'static str> {
    match platform {
        "linux_deb" => Ok("deb"),
        "linux_rpm" => Ok("rpm"),
        "windows_msi" => Ok("msi"),
        other => bail!("No agent package format known for the platform {other:?}"),
    }
}

/// Refuse a package verification could not accept, before it is downloaded.
///
/// A pre-check, never an acceptance: [`UpdatePackage::verify`] stays the only
/// thing that passes a package.
///
/// # Errors
///
/// If the site signed the package with nothing, if this host has no usable
/// signature key, or if the site signed with no certificate among those keys.
fn ensure_verifiable(
    offered: &agent_receiver_api::TargetAgent,
    local_certificates: &[X509Certificate],
) -> AnyhowResult<()> {
    if offered.signatures.is_empty() {
        bail!(
            "The site offers the agent package {} but has not signed it",
            offered.aghash
        );
    }
    if local_certificates.is_empty() {
        bail!("No usable signature key is configured for this host");
    }
    if !verification::any_certificate_is_trusted(&offered.signatures, local_certificates) {
        bail!(
            "The site signed the agent package {} with no certificate this host trusts",
            offered.aghash
        );
    }
    Ok(())
}

/// What the site answered a check with. Nothing was changed to learn it.
#[derive(Debug, PartialEq, Eq)]
pub enum CheckOutcome {
    /// No site was asked: the updater is not operational, not activated, or no
    /// registered connection can reach one. The reason is logged.
    NotPossible,

    /// The site has no agent package for this host.
    NoPackage,

    /// The site offers the package this host already runs.
    UpToDate(AgentHash),

    /// The site offers a package other than the installed one.
    UpdateAvailable {
        target: AgentHash,
        installed: AgentHash,
    },
}

/// What a fetch did. Nothing is installed here: the package is spooled for the
/// privileged installer, which is the step after this one.
#[derive(Debug, PartialEq, Eq)]
pub enum FetchOutcome {
    /// No site was asked: the updater is not operational or no registered
    /// connection can reach one. The reason is logged.
    NotPossible,

    /// The site has no agent package for this host.
    NoPackage,

    /// The site offers the package this host already runs.
    UpToDate(AgentHash),

    /// The package is waiting for the installer. `signature` says whether
    /// anything vouched for it: the spooled file itself does not tell them
    /// apart, so the run that produced it has to say so.
    Spooled {
        hash: AgentHash,
        path: PathBuf,
        signature: SignatureCheck,

        /// The signatures the site delivered with the package.
        signatures: Vec<agent_receiver_api::AgentSignature>,
    },
}

/// What the hand-over of a spooled package to the privileged install step did.
#[cfg(unix)]
#[derive(Debug, PartialEq, Eq)]
pub enum InstallOutcome {
    /// The configuration names no installer socket, so this host has no
    /// privileged install step. The package stays where it was spooled.
    NoInstaller,

    /// The install step has taken the package and finished.
    HandedOver,
}

/// What the site offers, as [`Updater::offered_update`] decided it.
///
/// Carries the package itself in the one case a fetch goes on, and which of the
/// two ways it ends without one this is - [`FetchOutcome`] names those for the
/// caller, this one keeps the package out of the public surface.
#[derive(Debug, PartialEq, Eq)]
enum OfferedUpdate<'a> {
    /// The site has no agent package for this host.
    NoPackage,

    /// The site offers the package this host already runs.
    UpToDate(AgentHash),

    /// The site offers a package other than the installed one: fetch it.
    Due(&'a agent_receiver_api::TargetAgent),
}

/// An [`Updater`] that holds `update.lock`, loaded after taking it.
///
/// Only a locked updater changes the update state, so no process writes the
/// state back from a copy that another process changed in the meantime.
/// Dropping it releases the lock.
pub struct WritableUpdater {
    updater: Updater,
    _lock: File,
}

impl std::ops::Deref for WritableUpdater {
    type Target = Updater;

    fn deref(&self) -> &Updater {
        &self.updater
    }
}

impl std::ops::DerefMut for WritableUpdater {
    fn deref_mut(&mut self) -> &mut Updater {
        &mut self.updater
    }
}

impl WritableUpdater {
    /// Record the connection a registration just created as the update source.
    ///
    /// `Keep` fills an empty slot or replaces a source whose connection is
    /// absent from the registry.
    /// `Overwrite` replaces the source in any case.
    /// `Manual` leaves it alone - with it the updater is the operator's business.
    ///
    /// # Arguments
    ///
    /// * `registration` - what the host is configured to do about the updater
    /// * `source` - the connection the registration created
    /// * `registry` - the registry the registration just wrote
    ///
    /// # Errors
    ///
    /// If the registry cannot be read or the state cannot be written.
    pub fn register_update_source(
        &mut self,
        registration: &UpdaterRegistration,
        source: UpdateSource,
        registry: &Registry,
    ) -> AnyhowResult<()> {
        match registration {
            UpdaterRegistration::Overwrite => self.state.source = Some(source),
            UpdaterRegistration::Keep => {
                // The recorded source is replaced when it is absent, or
                // dangling: no registered connection carries its UUID.
                match self.recorded_source_site(registry) {
                    Some(site_id) => log::info!(
                        "Keeping the recorded update source: its connection is still registered at {site_id}"
                    ),
                    None => {
                        log::info!(
                            "Refreshing the update source: no registered connection carries the recorded UUID"
                        );
                        self.state.source = Some(source);
                    }
                }
            }
            UpdaterRegistration::Manual => log::info!(
                "Keeping the recorded update source: updater registration is {registration:?}"
            ),
        }
        self.state.save(&self.state_path)
    }

    /// Drop the recorded update source when its connection is gone from the
    /// registry.
    ///
    /// # Arguments
    ///
    /// * `registry` - the registry as it is after the deletion
    ///
    /// # Errors
    ///
    /// If the state cannot be written.
    pub fn forget_vanished_update_source(&mut self, registry: &Registry) -> AnyhowResult<()> {
        if self.recorded_source_site(registry).is_some() {
            return Ok(());
        }
        let Some(source) = self.state.source.take() else {
            return Ok(());
        };
        log::info!(
            "Dropping the recorded update source: connection {} is not registered anymore",
            source.uuid
        );
        self.state.save(&self.state_path)
    }
}

/// The update configuration, as this run found it.
#[derive(Debug)]
enum ConfigState {
    /// No file: agent updates are not configured for this host.
    Absent,

    /// A file that failed to load.
    Broken(Error),

    Loaded(UpdaterConfig),
}

/// The three updater artifacts of this host, loaded together.
///
/// Fields are private: what is missing or broken is only observable through
/// [`Updater::is_configured`], [`Updater::is_operational`] and
/// [`Updater::summary`].
pub struct Updater {
    config: ConfigState,
    state: UpdateState,
    agent_info: Option<AgentInfo>,
    load_error: Option<Error>,

    /// Where the state was read from, and where it is written back.
    state_path: PathBuf,

    /// Where a verified package is spooled for the privileged installer.
    package_dir: PathBuf,
}

impl Updater {
    pub fn new(paths: &PathResolver) -> Self {
        let mut load_error = None;
        let config = match UpdaterConfig::load_if_configured(&paths.updater_config_path) {
            Ok(None) => ConfigState::Absent,
            Ok(Some(config)) => ConfigState::Loaded(config),
            Err(error) => {
                log::warn!("Continuing without updater configuration: {error:#}");
                ConfigState::Broken(error)
            }
        };
        if !paths.updater_state_path.exists() {
            log::info!(
                "No updater state at {:?}, starting from the default state",
                paths.updater_state_path
            );
        }
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
            state_path: paths.updater_state_path.clone(),
            package_dir: paths.updater_package_dir.clone(),
        }
    }

    /// Wait for `update.lock`, then load: the state is read only once no other
    /// process can change it.
    pub fn writable(paths: &PathResolver) -> AnyhowResult<WritableUpdater> {
        let lock = Self::lock(paths)?;
        Ok(WritableUpdater {
            updater: Self::new(paths),
            _lock: lock,
        })
    }

    fn lock(paths: &PathResolver) -> AnyhowResult<File> {
        fs::create_dir_all(&paths.updater_package_dir)?;
        let file = File::options()
            .create(true)
            .write(true)
            .truncate(false)
            .open(paths.updater_package_dir.join("update.lock"))?;
        file.lock()?;
        Ok(file)
    }

    /// The site of the recorded update source, as the registry keys its
    /// connection.
    ///
    /// # Arguments
    ///
    /// * `registry` - the registry to look the recorded connection up in
    ///
    /// # Returns
    ///
    /// `None` when no source is recorded, or when its connection is not in the
    /// registry anymore.
    fn recorded_source_site(&self, registry: &Registry) -> Option<site_spec::SiteID> {
        self.state
            .source
            .as_ref()
            .and_then(|recorded| registry.retrieve_standard_connection_by_uuid(&recorded.uuid))
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
            match &self.config {
                ConfigState::Absent => String::from("not configured"),
                ConfigState::Broken(error) => format!("broken: {error:#}"),
                ConfigState::Loaded(config) => format!(
                    "activated: {}, interval {}",
                    config.activated, config.interval
                ),
            },
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
        self.load_error.is_none() && self.loaded_config().is_some() && self.agent_info.is_some()
    }

    /// Whether agent updates are configured for this host.
    ///
    /// # Errors
    ///
    /// If a configuration is deployed but failed to load.
    pub fn is_configured(&self) -> AnyhowResult<bool> {
        match &self.config {
            ConfigState::Absent => Ok(false),
            ConfigState::Broken(error) => Err(anyhow!("{error:#}")),
            ConfigState::Loaded(_) => Ok(true),
        }
    }

    /// The configuration, if it loaded.
    fn loaded_config(&self) -> Option<&UpdaterConfig> {
        match &self.config {
            ConfigState::Loaded(config) => Some(config),
            ConfigState::Absent | ConfigState::Broken(_) => None,
        }
    }

    /// Whether this host is supposed to update its agent automatically.
    ///
    /// False when no updater configuration is deployed at all.
    fn is_activated(&self) -> bool {
        self.loaded_config().is_some_and(|config| config.activated)
    }

    /// Integrated updater main action.
    ///
    /// # Returns
    ///
    /// `true` when the updater is in a position to contact a site:
    /// operational, activated, and a connection was selected.
    pub fn handle_update_cycle(&self, registry: &Registry) -> bool {
        if !self.is_activated() {
            log::info!("Skipping the agent update: automatic agent updates are deactivated");
            return false;
        }
        let Some(selected) = self.find_update_connection(registry) else {
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

    /// Ask the site which agent package it has for this host.
    ///
    /// Reports only: nothing is downloaded, and no artifact of the updater is
    /// written - the state keeps the schedule of the automatic check, which a
    /// check made by hand must not shift.
    ///
    /// Deactivated automatic updates do not stand in the way. They say what the
    /// controller may do on its own, not what the site may be asked.
    ///
    /// # Errors
    ///
    /// If the site cannot be reached or does not answer with a status this
    /// controller can parse.
    pub fn check(
        &self,
        registry: &Registry,
        api: &impl agent_receiver_api::AgentUpdate,
    ) -> AnyhowResult<CheckOutcome> {
        let Some(selected) = self.find_update_connection(registry) else {
            return Ok(CheckOutcome::NotPossible);
        };
        let status = self.request_update_status(api, &selected)?;
        let Some(target) = status.target_agent.map(|offered| offered.aghash) else {
            return Ok(CheckOutcome::NoPackage);
        };
        let installed = self
            .agent_info
            .as_ref()
            .context("Cannot check for an agent update without the info of the installed agent")?
            .hash
            .clone();
        Ok(if target == installed {
            CheckOutcome::UpToDate(target)
        } else {
            CheckOutcome::UpdateAvailable { target, installed }
        })
    }

    /// Fetch the package the site offers and spool it for the installer.
    ///
    /// The four steps of an update the controller can do today: ask the site,
    /// refuse what could not be verified anyway, download the rest, and write
    /// it out once its signature has been checked. Installing the spooled
    /// package is not part of it.
    ///
    /// The package is the only thing written: the updater state is left alone,
    /// because a fetch made by hand must not shift the schedule of the
    /// automatic cycle, the same way [`Updater::check`] does not.
    ///
    /// With [`SignatureCheck::Skip`] both the pre-check and the verification
    /// are left out, and a package nothing vouches for is spooled for a
    /// privileged installer that cannot tell the difference. Only
    /// `--skip-signatures` asks for that.
    ///
    /// # Errors
    ///
    /// If the site cannot be reached, offers a package this host could not
    /// verify, does not deliver the package it offered, delivers one that fails
    /// verification, or if the package cannot be spooled.
    pub fn fetch_update(
        &self,
        registry: &Registry,
        api: &impl agent_receiver_api::AgentUpdate,
        signature: SignatureCheck,
    ) -> AnyhowResult<FetchOutcome> {
        let Some(selected) = self.find_update_connection(registry) else {
            return Ok(FetchOutcome::NotPossible);
        };
        let status = self.request_update_status(api, &selected)?;
        let offered = match self.offered_update(&status)? {
            OfferedUpdate::NoPackage => return Ok(FetchOutcome::NoPackage),
            OfferedUpdate::UpToDate(installed) => return Ok(FetchOutcome::UpToDate(installed)),
            OfferedUpdate::Due(offered) => offered,
        };
        // The PEM blocks are kept alive here: the parsed certificates borrow
        // the DER they decode to.
        let blocks = self.signature_key_blocks();
        let local_certificates = verification::certificates(&blocks);
        if signature == SignatureCheck::Required {
            ensure_verifiable(offered, &local_certificates)?;
        }
        let package = self.download_package(api, &selected, offered)?;
        let (hash, path) = match signature {
            SignatureCheck::Required => {
                let package = package.verify(&offered.signatures, &local_certificates)?;
                (package.hash().clone(), package.save(&self.package_dir)?)
            }
            SignatureCheck::Skip => {
                let package = package.accept_unverified();
                (
                    package.hash().clone(),
                    package.save_unverified(&self.package_dir)?,
                )
            }
        };
        Ok(FetchOutcome::Spooled {
            hash,
            path,
            signature,
            signatures: offered.signatures.clone(),
        })
    }

    /// Hand a spooled package to the privileged install step of this host.
    ///
    /// The step is a process of its own, running as root: this side only names
    /// the package and the signatures the site delivered with it, and the unit
    /// verifies both again against trust anchors the agent user cannot write.
    /// Blocks until the step has finished, which is as long as the package
    /// manager takes.
    ///
    /// Writes no artifact of the updater, as [`Updater::fetch_update`] does
    /// not: reconciling the outcome belongs to the automatic cycle, which
    /// compares hashes on a later run.
    ///
    /// # Arguments
    ///
    /// * `package` - the spooled package, as [`Updater::fetch_update`]
    ///   reported it
    /// * `signatures` - the signatures of the status that named the package
    ///
    /// # Returns
    ///
    /// [`InstallOutcome::NoInstaller`] when no installer socket is configured.
    ///
    /// # Errors
    ///
    /// If the installer socket cannot be reached or the request not be
    /// delivered.
    #[cfg(unix)]
    pub fn install_update(
        &self,
        package: &Path,
        signatures: &[agent_receiver_api::AgentSignature],
    ) -> AnyhowResult<InstallOutcome> {
        let Some(socket) = self
            .loaded_config()
            .and_then(|config| config.installer_socket.as_ref())
        else {
            log::info!("No installer socket is configured, leaving {package:?} where it is");
            return Ok(InstallOutcome::NoInstaller);
        };
        log::info!("Handing {package:?} to the installer at {socket:?}");
        install::hand_over(
            socket,
            &install::InstallRequest {
                package: package.to_path_buf(),
                signatures: signatures.to_vec(),
            },
        )?;
        Ok(InstallOutcome::HandedOver)
    }

    /// The connection to run an update over, if the updater may run at all.
    ///
    /// The updater reuses the controller's registration. It picks one of the
    /// registered connections and talks to that site over the connection's mTLS
    /// channel, where the receiver authenticates the host by the client
    /// certificate and resolves its UUID to a host name.
    ///
    /// # Returns
    ///
    /// `None`, with the reason logged, when the updater is not operational or
    /// no registered connection can reach a site. Whether automatic updates are
    /// activated is none of its business - that governs the automatic cycle,
    /// not what an operator may ask for by hand.
    fn find_update_connection<'a>(
        &self,
        registry: &'a Registry,
    ) -> Option<connection::UpdateConnection<'a>> {
        if !self.is_operational() {
            log::info!("No agent update is possible: the updater is not operational");
            return None;
        }

        let Some(source) = &self.state.source else {
            log::info!("No agent update is possible: no update source is recorded");
            return None;
        };

        let Some(selected) = connection::select(registry, source.uuid) else {
            log::info!(
"No agent update is possible: the connection {} of the update source is not registered",
    source.uuid
            );
            return None;
        };
        Some(selected)
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

    /// The package `status` offers, unless there is nothing to fetch.
    ///
    /// The one place that decides whether an update is due, so that the
    /// decision and the transfer cannot disagree about which package is meant.
    ///
    /// # Returns
    ///
    /// The package to fetch, or which of the two ways a fetch ends without one
    /// this is: the site offers no package, or offers the installed one. The
    /// reason is logged as well.
    ///
    /// # Errors
    ///
    /// If nothing is known about the installed agent.
    fn offered_update<'a>(
        &self,
        status: &'a agent_receiver_api::UpdateStatusResponse,
    ) -> AnyhowResult<OfferedUpdate<'a>> {
        let installed = &self
            .agent_info
            .as_ref()
            .context("Cannot decide on an agent update without the info of the installed agent")?
            .hash;
        let Some(offered) = status.target_agent.as_ref() else {
            log::info!("No agent package available for this host");
            return Ok(OfferedUpdate::NoPackage);
        };
        if offered.aghash == *installed {
            log::info!("The installed agent {installed} is the one the site offers");
            return Ok(OfferedUpdate::UpToDate(offered.aghash.clone()));
        }
        Ok(OfferedUpdate::Due(offered))
    }

    /// Download the package `offered`, which is not the installed one.
    ///
    /// The package is not verified here: it is held in memory until its
    /// signature has been checked, and only then written anywhere.
    ///
    /// # Errors
    ///
    /// If nothing is known about the installed agent, if the site address
    /// cannot be assembled, or if the site does not deliver the package.
    fn download_package(
        &self,
        api: &impl agent_receiver_api::AgentUpdate,
        selected: &connection::UpdateConnection<'_>,
        offered: &agent_receiver_api::TargetAgent,
    ) -> AnyhowResult<UpdatePackage> {
        let agent_info = self
            .agent_info
            .as_ref()
            .context("Cannot download an agent update without the info of the installed agent")?;
        let target = &offered.aghash;
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
        Ok(UpdatePackage {
            hash: target.clone(),
            platform: agent_info.platform.clone(),
            bytes,
        })
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
        self.loaded_config()
            .map_or(&[], |config| &config.signature_keys)
    }

    /// The configured signature keys as PEM blocks, which
    /// [`verification::certificates`] turns into certificates.
    fn signature_key_blocks(&self) -> Vec<x509_parser::pem::Pem> {
        verification::pem_blocks(self.signature_keys())
    }

    pub fn platform(&self) -> Option<&str> {
        self.agent_info.as_ref().map(|info| info.platform.as_str())
    }

    /// The error of the last update attempt, not the `load_error` of this run.
    pub fn last_error(&self) -> Option<&str> {
        self.state.last_error.as_deref()
    }
}

/// Write `contents` to `path`, restricted to `mode` from the moment the file
/// comes into existence.
///
/// `mode` applies to the creation only and is masked by the umask, and a
/// temporary file left behind by an interrupted save keeps the mode it was
/// created with - hence the explicit [`fs::set_permissions`] afterwards.
#[cfg(unix)]
fn write_restricted(path: &Path, contents: &[u8], mode: u32) -> io::Result<()> {
    use std::io::Write;
    use std::os::unix::fs::OpenOptionsExt;

    let mut file = fs::OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .mode(mode)
        .open(path)?;
    file.write_all(contents)?;
    file.set_permissions(fs::Permissions::from_mode(mode))
}

/// Write `contents` to `path`. Windows inherits the permissions of the
/// directory, which the installer owns.
#[cfg(windows)]
fn write_restricted(path: &Path, contents: &[u8], _mode: u32) -> io::Result<()> {
    fs::write(path, contents)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;
    use crate::config::{ConnectionMode, TrustedConnection};
    use crate::environment::SetupMode;
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
    use std::cell::RefCell;
    use std::path::PathBuf;
    use std::str::FromStr;
    use std::sync::LazyLock;

    use crate::agent_receiver_api::{TargetAgent, UpdateStatusResponse};

    const INSTALLED_HASH: &str = "0123456789abcdef";
    const TARGET_HASH: &str = "fedcba9876543210";
    const CONNECTION_UUID: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a01";
    const SOURCE_SITE: &str = "server/site";
    const OTHER_SITE: &str = "other-server/site";
    const STATE_FILE: &str = "state.json";
    const PACKAGE_DIR: &str = "update";
    const PACKAGE: &[u8] = b"an agent package";

    /// Length of a signature under the 2048 bit key of [`SITE_SIGNATURE`].
    /// A signature of any other length is rejected before it is verified.
    const RSA_SIGNATURE_LEN: usize = 256;

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
                installer_socket: None,
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
                installer_socket: None,
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
            source: Some(some_source()),
            last_check: Some(1759276800),
            last_update: Some(1759190400),
            pending_hash: Some(String::from("0123456789abcdef")),
            last_error: Some(String::from("boom")),
        };

        state.save(&path).unwrap();

        assert_eq!(UpdateState::load(&path).unwrap(), state);
    }

    /// The source of the one connection the test registry carries.
    fn some_source() -> UpdateSource {
        UpdateSource {
            uuid: uuid::Uuid::from_str(CONNECTION_UUID).unwrap(),
            available: true,
        }
    }

    /// The source of a second registration at another site, to tell a kept
    /// source from a replaced one.
    fn other_source() -> UpdateSource {
        UpdateSource {
            uuid: uuid::Uuid::from_str("8f0e3a1c-5b2d-4e6f-9a7b-0c1d2e3f4a5b").unwrap(),
            available: true,
        }
    }

    /// The source of a second registration at the site of [`some_source`],
    /// whose connection - and with it the UUID - it replaced.
    fn reregistered_source() -> UpdateSource {
        UpdateSource {
            uuid: uuid::Uuid::from_str("3c9d1e7b-6a4f-42c8-9e05-7d8b1f2a3c4d").unwrap(),
            ..some_source()
        }
    }

    /// The source the updater saved to its state file.
    fn saved_source(updater: &Updater) -> Option<UpdateSource> {
        UpdateState::load(&updater.state_path).unwrap().source
    }

    /// A registry holding the connection of every `(site, source)` pair.
    fn registry_with_the_connections_of(sources: &[(&str, &UpdateSource)]) -> TestRegistry {
        sources
            .iter()
            .fold(TestRegistry::new(), |registry, (site, source)| {
                registry.add_connection(&ConnectionMode::Pull, site, source.uuid)
            })
    }

    #[test]
    fn test_register_update_source_into_a_state_without_one() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_the_connections_of(&[(SOURCE_SITE, &some_source())]);
        let mut updater = writable_in(&dir, UpdateState::default());

        updater
            .register_update_source(
                &UpdaterRegistration::Keep,
                some_source(),
                &registry.registry,
            )
            .unwrap();

        assert_eq!(updater.state.source, Some(some_source()));
        assert_eq!(saved_source(&updater), Some(some_source()));
    }

    #[test]
    fn test_register_update_source_keeps_the_recorded_one() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_the_connections_of(&[
            (SOURCE_SITE, &some_source()),
            (OTHER_SITE, &other_source()),
        ]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                ..Default::default()
            },
        );

        updater
            .register_update_source(
                &UpdaterRegistration::Keep,
                other_source(),
                &registry.registry,
            )
            .unwrap();

        assert_eq!(saved_source(&updater), Some(some_source()));
    }

    #[test]
    fn test_register_update_source_refreshes_a_vanished_recorded_one() {
        let dir = tempfile::TempDir::new().unwrap();
        // The registry holds the connection this registration created, which
        // replaced the recorded one at the same site.
        let registry = registry_with_the_connections_of(&[(SOURCE_SITE, &reregistered_source())]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                ..Default::default()
            },
        );

        updater
            .register_update_source(
                &UpdaterRegistration::Keep,
                reregistered_source(),
                &registry.registry,
            )
            .unwrap();

        // Keeping the recorded source would leave it naming the connection this
        // registration replaced.
        assert_eq!(saved_source(&updater), Some(reregistered_source()));
    }

    #[test]
    fn test_register_update_source_overwrites_the_recorded_one() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_the_connections_of(&[
            (SOURCE_SITE, &some_source()),
            (OTHER_SITE, &other_source()),
        ]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                last_check: Some(1759276800),
                ..Default::default()
            },
        );

        // The recorded connection is still registered, and replaced anyway.
        updater
            .register_update_source(
                &UpdaterRegistration::Overwrite,
                other_source(),
                &registry.registry,
            )
            .unwrap();

        let saved = UpdateState::load(&updater.state_path).unwrap();
        assert_eq!(saved.source, Some(other_source()));
        // The rest of the state belongs to the update cycle, not to the registration.
        assert_eq!(saved.last_check, Some(1759276800));
    }

    #[test]
    fn test_forget_vanished_update_source_of_a_deleted_connection() {
        let dir = tempfile::TempDir::new().unwrap();
        // The deletion took the last connection, so the registry is empty.
        let registry = registry_with_the_connections_of(&[]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                last_check: Some(1759276800),
                ..Default::default()
            },
        );

        updater
            .forget_vanished_update_source(&registry.registry)
            .unwrap();

        let saved = UpdateState::load(&updater.state_path).unwrap();
        assert_eq!(saved.source, None);
        // The rest of the state belongs to the update cycle, not to the deletion.
        assert_eq!(saved.last_check, Some(1759276800));
    }

    #[test]
    fn test_forget_vanished_update_source_of_a_re_registered_site() {
        let dir = tempfile::TempDir::new().unwrap();
        // The site is registered again, with a connection of its own.
        let registry = registry_with_the_connections_of(&[(SOURCE_SITE, &reregistered_source())]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                ..Default::default()
            },
        );

        updater
            .forget_vanished_update_source(&registry.registry)
            .unwrap();

        assert_eq!(saved_source(&updater), None);
    }

    #[test]
    fn test_forget_vanished_update_source_keeps_a_registered_one() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_the_connections_of(&[(SOURCE_SITE, &some_source())]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                ..Default::default()
            },
        );

        updater
            .forget_vanished_update_source(&registry.registry)
            .unwrap();

        assert_eq!(updater.state.source, Some(some_source()));
    }

    #[test]
    fn test_forget_vanished_update_source_without_a_recorded_one() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_the_connections_of(&[]);
        let mut updater = writable_in(&dir, UpdateState::default());

        updater
            .forget_vanished_update_source(&registry.registry)
            .unwrap();

        assert_eq!(updater.state.source, None);
    }

    #[test]
    fn test_register_update_source_with_manual_registration() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_the_connections_of(&[
            (SOURCE_SITE, &some_source()),
            (OTHER_SITE, &other_source()),
        ]);
        let mut updater = writable_in(
            &dir,
            UpdateState {
                source: Some(some_source()),
                ..Default::default()
            },
        );

        updater
            .register_update_source(
                &UpdaterRegistration::Manual,
                other_source(),
                &registry.registry,
            )
            .unwrap();

        assert_eq!(saved_source(&updater), Some(some_source()));
    }

    #[test]
    fn test_state_file_keys_the_source_by_uuid() {
        let dir = tempfile::TempDir::new().unwrap();
        let path = dir.path().join("state.json");

        UpdateState {
            source: Some(some_source()),
            ..Default::default()
        }
        .save(&path)
        .unwrap();

        let written = fs::read_to_string(&path).unwrap();
        assert!(written.contains(&format!(r#""uuid": "{CONNECTION_UUID}""#)));
        assert!(written.contains(r#""available": true"#));
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
        assert_eq!(updater.loaded_config().unwrap().interval, 60);
        assert_eq!(updater.state.last_check, Some(1759276800));
        assert_eq!(updater.agent_info.unwrap().hash.as_str(), INSTALLED_HASH);
    }

    #[test]
    fn test_updater_new_tolerates_missing_artifacts() {
        let dir = tempfile::TempDir::new().unwrap();

        let updater = Updater::new(&artifact_paths(&dir));

        assert!(!updater.is_configured().unwrap());
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

    /// A broken configuration must not read as "not configured": the operator
    /// has to learn that it is broken, and which file.
    #[test]
    fn test_updater_new_survives_a_malformed_config() {
        let dir = tempfile::TempDir::new().unwrap();
        let paths = artifact_paths(&dir);
        fs::write(&paths.updater_config_path, "interval = ").unwrap();

        let updater = Updater::new(&paths);

        assert!(!updater.is_operational());
        // The context quotes the path with `{:?}`, which escapes the separators
        // of a Windows path, so the expectation has to be built the same way.
        assert!(updater
            .is_configured()
            .unwrap_err()
            .to_string()
            .contains(&format!("{:?}", paths.updater_config_path)));
    }

    /// The lock is real: no other handle can take it while the writable
    /// updater lives, and one can once it is dropped. `artifact_paths` leaves
    /// the download directory missing, so taking the lock has to create it.
    #[test]
    fn test_writable_holds_the_update_lock_until_dropped() {
        let dir = tempfile::TempDir::new().unwrap();
        let paths = artifact_paths(&dir);
        let lock_path = paths.updater_package_dir.join("update.lock");

        let updater = Updater::writable(&paths).unwrap();

        assert!(File::open(&lock_path).unwrap().try_lock().is_err());

        drop(updater);

        assert!(File::open(&lock_path).unwrap().try_lock().is_ok());
    }

    #[test]
    fn test_summary_without_config_and_agent_info() {
        let summary = updater(None, None).summary();

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
            config: ConfigState::Loaded(UpdaterConfig {
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
            installer_socket: None,
        })
    }

    /// A configuration that accepts what the site signed in [`SITE_SIGNATURE`].
    fn config_trusting_the_signer() -> Option<UpdaterConfig> {
        Some(UpdaterConfig {
            signature_keys: vec![SITE_SIGNATURE.certificate.clone()],
            ..some_config().unwrap()
        })
    }

    /// A configuration whose one signature key signed nothing, to tell "no key
    /// configured" apart from "the key is not the one the site signed with".
    ///
    /// The certificate is for an elliptic curve key - fast
    fn config_trusting_a_stranger() -> Option<UpdaterConfig> {
        let key_pair = rcgen::KeyPair::generate_for(&rcgen::PKCS_ECDSA_P256_SHA256).unwrap();
        let certificate = rcgen::CertificateParams::default()
            .self_signed(&key_pair)
            .unwrap();
        Some(UpdaterConfig {
            signature_keys: vec![pem_rfc7468::encode_string(
                "CERTIFICATE",
                pem_rfc7468::LineEnding::LF,
                certificate.der(),
            )
            .unwrap()],
            ..some_config().unwrap()
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
            config: config.map_or(ConfigState::Absent, ConfigState::Loaded),
            state: UpdateState::default(),
            agent_info,
            load_error: None,
            state_path: PathBuf::from(STATE_FILE),
            package_dir: PathBuf::from(PACKAGE_DIR),
        }
    }

    /// An updater whose registration recorded the connection of
    /// [`registry_with_one_connection`] as its update source.
    fn updater_with_source(
        config: Option<UpdaterConfig>,
        agent_info: Option<AgentInfo>,
    ) -> Updater {
        Updater {
            state: UpdateState {
                source: Some(some_source()),
                ..Default::default()
            },
            ..updater(config, agent_info)
        }
    }

    /// An updater that writes its state into `dir`.
    fn updater_in(dir: &tempfile::TempDir, state: UpdateState) -> Updater {
        Updater {
            state,
            state_path: dir.path().join(STATE_FILE),
            ..updater(some_config(), some_agent_info())
        }
    }

    /// [`updater_in`], allowed to write its state. The lock file is never
    /// locked: nothing else runs against `dir`.
    fn writable_in(dir: &tempfile::TempDir, state: UpdateState) -> WritableUpdater {
        WritableUpdater {
            updater: updater_in(dir, state),
            _lock: File::create(dir.path().join("update.lock")).unwrap(),
        }
    }

    /// An updater that spools the package it fetches into `dir`, and trusts
    /// the certificate the test site signs with.
    fn updater_spooling_into(dir: &tempfile::TempDir) -> Updater {
        Updater {
            package_dir: dir.path().join(PACKAGE_DIR),
            ..updater_with_source(config_trusting_the_signer(), some_agent_info())
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
        registry_with_the_connections_of(&[(SOURCE_SITE, &some_source())])
    }

    #[test]
    fn test_maybe_update_agent_selects_a_connection() {
        let registry = registry_with_one_connection();

        assert!(updater_with_source(some_config(), some_agent_info())
            .handle_update_cycle(&registry.registry));
    }

    #[test]
    fn test_maybe_update_agent_without_a_reachable_site() {
        let registry = TestRegistry::new();

        assert!(!updater_with_source(some_config(), some_agent_info())
            .handle_update_cycle(&registry.registry));
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
            Self::answering(offered(target))
        }

        fn unsigned(target: &str) -> Self {
            Self::answering(unsigned(target))
        }

        /// A site that offers `target` with the certificate this host trusts,
        /// but a signature that does not match the package.
        fn badly_signed(target: &str) -> Self {
            Self::answering(UpdateStatusResponse {
                target_agent: Some(TargetAgent {
                    aghash: target.parse().unwrap(),
                    signatures: vec![agent_receiver_api::AgentSignature {
                        signature: BASE64.encode([0_u8; RSA_SIGNATURE_LEN]),
                        ..SITE_SIGNATURE.clone()
                    }],
                }),
            })
        }

        fn answering(response: agent_receiver_api::UpdateStatusResponse) -> Self {
            Self {
                response,
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
        ) -> AnyhowResult<agent_receiver_api::UpdateStatusResponse, agent_receiver_api::ApiError>
        {
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
        ) -> AnyhowResult<Vec<u8>, agent_receiver_api::ApiError> {
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
        ) -> AnyhowResult<agent_receiver_api::UpdateStatusResponse, agent_receiver_api::ApiError>
        {
            Err(agent_receiver_api::ApiError::Other(Error::msg(
                "connection refused",
            )))
        }

        fn download_agent(
            &self,
            _base_url: &reqwest::Url,
            _connection: &TrustedConnection,
            _body: &agent_receiver_api::AgentDownloadBody<'_>,
        ) -> AnyhowResult<Vec<u8>, agent_receiver_api::ApiError> {
            Err(agent_receiver_api::ApiError::Other(Error::msg(
                "connection refused",
            )))
        }
    }

    /// The status of a site that has `target` for this host, signed with the
    /// certificate [`config_trusting_the_signer`] configures.
    fn offered(target: Option<&str>) -> UpdateStatusResponse {
        UpdateStatusResponse {
            target_agent: target.map(|hash| TargetAgent {
                aghash: hash.parse().unwrap(),
                signatures: vec![SITE_SIGNATURE.clone()],
            }),
        }
    }

    /// The status of a site that has `target` for this host and signed nothing,
    /// which is what a site whose bakery has no signature key answers.
    fn unsigned(target: &str) -> UpdateStatusResponse {
        UpdateStatusResponse {
            target_agent: Some(TargetAgent {
                aghash: target.parse().unwrap(),
                signatures: vec![],
            }),
        }
    }

    /// The signature of [`PACKAGE`] as the site delivers it with the status.
    ///
    /// Made once: generating the RSA key dominates the runtime of these tests.
    /// Which signatures verification accepts is covered in [`super::verification`];
    /// here one that passes is all that is needed.
    static SITE_SIGNATURE: LazyLock<agent_receiver_api::AgentSignature> = LazyLock::new(|| {
        use rsa::pkcs1v15::SigningKey;
        use rsa::pkcs8::EncodePrivateKey;
        use rsa::signature::{SignatureEncoding, Signer};
        use sha2::Sha256;

        let key = rsa::RsaPrivateKey::new(&mut rand::thread_rng(), 2048).unwrap();
        let key_pair = rcgen::KeyPair::from_pkcs8_der_and_sign_algo(
            &rustls::pki_types::PrivatePkcs8KeyDer::from(key.to_pkcs8_der().unwrap().as_bytes()),
            &rcgen::PKCS_RSA_SHA256,
        )
        .unwrap();
        let mut params = rcgen::CertificateParams::default();
        params
            .distinguished_name
            .push(rcgen::DnType::CommonName, "agent package signer");
        let certificate = params.self_signed(&key_pair).unwrap();
        agent_receiver_api::AgentSignature {
            certificate: pem_rfc7468::encode_string(
                "CERTIFICATE",
                pem_rfc7468::LineEnding::LF,
                certificate.der(),
            )
            .unwrap(),
            signature: BASE64.encode(SigningKey::<Sha256>::new(key).sign(PACKAGE).to_bytes()),
        }
    });

    /// An updater whose last update attempt ended in `last_error`.
    fn updater_after(last_error: Option<&str>) -> Updater {
        Updater {
            state: UpdateState {
                source: Some(some_source()),
                last_error: last_error.map(String::from),
                ..Default::default()
            },
            ..updater(some_config(), some_agent_info())
        }
    }

    #[test]
    fn test_request_update_status_reports_the_installed_hash_and_the_last_error() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
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
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
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
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
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
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
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
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();

        let status = updater_after(None)
            .request_update_status(&TestApi::new(Some(TARGET_HASH)), &selected)
            .unwrap();

        assert_eq!(status.target_agent.unwrap().aghash.as_str(), TARGET_HASH);
    }

    #[test]
    fn test_request_update_status_parses_a_site_without_a_package() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();

        let status = updater_after(None)
            .request_update_status(&TestApi::new(None), &selected)
            .unwrap();

        assert!(status.target_agent.is_none());
    }

    #[test]
    fn test_request_update_status_without_agent_info() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();

        let error = updater(some_config(), None)
            .request_update_status(&TestApi::new(None), &selected)
            .unwrap_err();

        assert!(error.to_string().contains("info of the installed agent"));
    }

    #[test]
    fn test_request_update_status_names_the_site_that_did_not_answer() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();

        let error = updater_after(None)
            .request_update_status(&UnreachableApi, &selected)
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Agent update status request to server/site failed"
        );
    }

    #[test]
    fn test_check_reports_a_package_that_is_not_installed() {
        let registry = registry_with_one_connection();

        let outcome = updater_after(None)
            .check(&registry.registry, &TestApi::new(Some(TARGET_HASH)))
            .unwrap();

        assert_eq!(
            outcome,
            CheckOutcome::UpdateAvailable {
                target: TARGET_HASH.parse().unwrap(),
                installed: INSTALLED_HASH.parse().unwrap(),
            }
        );
    }

    #[test]
    fn test_check_reports_the_installed_package() {
        let registry = registry_with_one_connection();

        let outcome = updater_after(None)
            .check(&registry.registry, &TestApi::new(Some(INSTALLED_HASH)))
            .unwrap();

        assert_eq!(
            outcome,
            CheckOutcome::UpToDate(INSTALLED_HASH.parse().unwrap())
        );
    }

    #[test]
    fn test_check_reports_a_site_without_a_package() {
        let registry = registry_with_one_connection();

        let outcome = updater_after(None)
            .check(&registry.registry, &TestApi::new(None))
            .unwrap();

        assert_eq!(outcome, CheckOutcome::NoPackage);
    }

    /// Nothing is asked when nothing may be updated, and the site is left
    /// alone - the updater does not even open a connection.
    #[test]
    fn test_check_without_a_connection_asks_nobody() {
        let registry = TestRegistry::new();
        let api = TestApi::new(Some(TARGET_HASH));

        let outcome = updater_after(None).check(&registry.registry, &api).unwrap();

        assert_eq!(outcome, CheckOutcome::NotPossible);
        assert!(api.request.borrow().is_none());
    }

    #[test]
    fn test_check_without_a_recorded_source_asks_nobody() {
        let registry = registry_with_one_connection();
        let api = TestApi::new(Some(TARGET_HASH));

        let outcome = updater(some_config(), some_agent_info())
            .check(&registry.registry, &api)
            .unwrap();

        assert_eq!(outcome, CheckOutcome::NotPossible);
        assert!(api.request.borrow().is_none());
    }

    /// Another registered connection does not stand in for a source whose own
    /// connection is gone.
    #[test]
    fn test_check_whose_source_connection_is_gone_asks_nobody() {
        let registry = registry_with_the_connections_of(&[(OTHER_SITE, &other_source())]);
        let api = TestApi::new(Some(TARGET_HASH));

        let outcome = updater_with_source(some_config(), some_agent_info())
            .check(&registry.registry, &api)
            .unwrap();

        assert_eq!(outcome, CheckOutcome::NotPossible);
        assert!(api.request.borrow().is_none());
    }

    /// A host that may not update itself can still be asked what it would
    /// update to: an admin wants to see that before activating anything.
    #[test]
    fn test_check_when_deactivated_asks_the_site_anyway() {
        let registry = registry_with_one_connection();
        let config = UpdaterConfig {
            activated: false,
            ..some_config().unwrap()
        };

        let outcome = updater_with_source(Some(config), some_agent_info())
            .check(&registry.registry, &TestApi::new(Some(TARGET_HASH)))
            .unwrap();

        assert_eq!(
            outcome,
            CheckOutcome::UpdateAvailable {
                target: TARGET_HASH.parse().unwrap(),
                installed: INSTALLED_HASH.parse().unwrap(),
            }
        );
    }

    #[test]
    fn test_check_when_not_operational() {
        let registry = registry_with_one_connection();

        let outcome = updater(some_config(), None)
            .check(&registry.registry, &TestApi::new(Some(TARGET_HASH)))
            .unwrap();

        assert_eq!(outcome, CheckOutcome::NotPossible);
    }

    #[test]
    fn test_check_names_the_site_that_did_not_answer() {
        let registry = registry_with_one_connection();

        let error = updater_after(None)
            .check(&registry.registry, &UnreachableApi)
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Agent update status request to server/site failed"
        );
    }

    /// The package [`offered`] carries, for the functions that take it alone.
    fn target_agent(status: &UpdateStatusResponse) -> &TargetAgent {
        status.target_agent.as_ref().unwrap()
    }

    #[test]
    fn test_offered_update_is_a_package_that_is_not_installed() {
        let status = offered(Some(TARGET_HASH));

        let offered = updater_after(None).offered_update(&status).unwrap();

        assert_eq!(offered, OfferedUpdate::Due(target_agent(&status)));
    }

    #[test]
    fn test_offered_update_when_the_offered_package_is_the_installed_one() {
        let status = offered(Some(INSTALLED_HASH));

        assert_eq!(
            updater_after(None).offered_update(&status).unwrap(),
            OfferedUpdate::UpToDate(INSTALLED_HASH.parse().unwrap())
        );
    }

    #[test]
    fn test_offered_update_without_an_offered_package() {
        let status = offered(None);

        assert_eq!(
            updater_after(None).offered_update(&status).unwrap(),
            OfferedUpdate::NoPackage
        );
    }

    #[test]
    fn test_offered_update_without_agent_info() {
        let status = offered(Some(TARGET_HASH));

        let error = updater(some_config(), None)
            .offered_update(&status)
            .unwrap_err();

        assert!(error.to_string().contains("info of the installed agent"));
    }

    #[test]
    fn test_download_package_fetches_the_offered_package() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
        let api = TestApi::new(None);
        let status = offered(Some(TARGET_HASH));

        let package = updater_after(None)
            .download_package(&api, &selected, target_agent(&status))
            .unwrap();

        assert_eq!(package.hash.as_str(), TARGET_HASH);
        assert_eq!(package.platform, "linux_deb");
        assert_eq!(package.bytes, PACKAGE);
        let download = api.download().unwrap();
        assert_eq!(download.url, "https://server:8000/site");
        assert_eq!(download.uuid, CONNECTION_UUID);
        assert_eq!(download.platform, "linux_deb");
        assert_eq!(download.aghash, TARGET_HASH);
    }

    #[test]
    fn test_download_package_without_agent_info() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
        let status = offered(Some(TARGET_HASH));

        let error = updater(some_config(), None)
            .download_package(&TestApi::new(None), &selected, target_agent(&status))
            .unwrap_err();

        assert!(error.to_string().contains("info of the installed agent"));
    }

    #[test]
    fn test_download_package_names_the_package_and_the_site_that_failed() {
        let registry = registry_with_one_connection();
        let selected = connection::select(&registry.registry, some_source().uuid).unwrap();
        let status = offered(Some(TARGET_HASH));

        let error = updater_after(None)
            .download_package(&UnreachableApi, &selected, target_agent(&status))
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Agent update download of fedcba9876543210 from server/site failed"
        );
    }

    #[test]
    fn test_a_signed_package_this_host_trusts_is_verifiable() {
        let blocks =
            updater(config_trusting_the_signer(), some_agent_info()).signature_key_blocks();
        let status = offered(Some(TARGET_HASH));

        assert!(
            ensure_verifiable(target_agent(&status), &verification::certificates(&blocks)).is_ok()
        );
    }

    #[test]
    fn test_an_unsigned_package_is_not_verifiable() {
        let blocks =
            updater(config_trusting_the_signer(), some_agent_info()).signature_key_blocks();
        let status = unsigned(TARGET_HASH);

        let error = ensure_verifiable(target_agent(&status), &verification::certificates(&blocks))
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "The site offers the agent package fedcba9876543210 but has not signed it"
        );
    }

    #[test]
    fn test_a_package_is_not_verifiable_without_a_signature_key() {
        let status = offered(Some(TARGET_HASH));

        let error = ensure_verifiable(target_agent(&status), &[]).unwrap_err();

        assert_eq!(
            error.to_string(),
            "No usable signature key is configured for this host"
        );
    }

    /// The host has a key, the site signed with another: nothing the download
    /// could add would make the package verifiable.
    #[test]
    fn test_a_package_signed_by_a_stranger_is_not_verifiable() {
        let blocks =
            updater(config_trusting_a_stranger(), some_agent_info()).signature_key_blocks();
        let status = offered(Some(TARGET_HASH));

        let error = ensure_verifiable(target_agent(&status), &verification::certificates(&blocks))
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "The site signed the agent package fedcba9876543210 with no certificate \
             this host trusts"
        );
    }

    #[test]
    fn test_fetch_update_spools_the_package_the_site_offers() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::new(Some(TARGET_HASH)),
                SignatureCheck::Required,
            )
            .unwrap();

        let FetchOutcome::Spooled {
            hash,
            path,
            signature,
            ..
        } = outcome
        else {
            panic!("expected a spooled package, got {outcome:?}");
        };
        assert_eq!(signature, SignatureCheck::Required);
        assert_eq!(hash.as_str(), TARGET_HASH);
        assert_eq!(
            path,
            dir.path().join(PACKAGE_DIR).join("fedcba9876543210.deb")
        );
        assert_eq!(fs::read(&path).unwrap(), PACKAGE);
    }

    #[test]
    fn test_fetch_update_reports_the_signatures_the_site_delivered() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::new(Some(TARGET_HASH)),
                SignatureCheck::Required,
            )
            .unwrap();

        let FetchOutcome::Spooled { signatures, .. } = outcome else {
            panic!("expected a spooled package, got {outcome:?}");
        };
        assert_eq!(signatures, vec![SITE_SIGNATURE.clone()]);
    }

    #[cfg(unix)]
    #[test]
    fn test_install_update_without_an_installer_socket() {
        let updater = updater(some_config(), some_agent_info());

        assert_eq!(
            updater
                .install_update(Path::new("/spool/fedcba9876543210.deb"), &[])
                .unwrap(),
            InstallOutcome::NoInstaller
        );
    }

    #[cfg(unix)]
    #[test]
    fn test_install_update_hands_the_package_to_the_configured_socket() {
        use std::io::Read;

        let dir = tempfile::TempDir::new().unwrap();
        let socket = dir.path().join("cmk-agent-installer.sock");
        let listener = std::os::unix::net::UnixListener::bind(&socket).unwrap();
        let installer = std::thread::spawn(move || {
            let (mut connection, _) = listener.accept().unwrap();
            let mut request = String::new();
            connection.read_to_string(&mut request).unwrap();
            request
        });
        let updater = updater(
            Some(UpdaterConfig {
                installer_socket: Some(socket),
                ..some_config().unwrap()
            }),
            some_agent_info(),
        );

        let outcome = updater
            .install_update(Path::new("/spool/fedcba9876543210.deb"), &[])
            .unwrap();

        assert_eq!(outcome, InstallOutcome::HandedOver);
        assert!(installer
            .join()
            .unwrap()
            .contains("/spool/fedcba9876543210.deb"));
    }

    #[test]
    fn test_fetch_update_when_the_site_offers_the_installed_package() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::new(Some(INSTALLED_HASH)),
                SignatureCheck::Required,
            )
            .unwrap();

        assert_eq!(
            outcome,
            FetchOutcome::UpToDate(INSTALLED_HASH.parse().unwrap())
        );
        assert!(!dir.path().join(PACKAGE_DIR).exists());
    }

    #[test]
    fn test_fetch_update_without_a_package() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::new(None),
                SignatureCheck::Required,
            )
            .unwrap();

        assert_eq!(outcome, FetchOutcome::NoPackage);
        assert!(!dir.path().join(PACKAGE_DIR).exists());
    }

    #[test]
    fn test_fetch_update_when_not_operational() {
        let registry = registry_with_one_connection();

        let outcome = updater(some_config(), None)
            .fetch_update(
                &registry.registry,
                &TestApi::new(Some(TARGET_HASH)),
                SignatureCheck::Required,
            )
            .unwrap();

        assert_eq!(outcome, FetchOutcome::NotPossible);
    }

    /// The pre-check refuses before the transfer, so the site is never asked
    /// for the package.
    #[test]
    fn test_fetch_update_does_not_download_an_unsigned_package() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);
        let api = TestApi::unsigned(TARGET_HASH);

        let error = updater
            .fetch_update(&registry.registry, &api, SignatureCheck::Required)
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "The site offers the agent package fedcba9876543210 but has not signed it"
        );
        assert!(api.download().is_none());
        assert!(!dir.path().join(PACKAGE_DIR).exists());
    }

    /// The pre-check lets a package through on the certificate alone, so
    /// verification is still what rejects a signature that does not match.
    #[test]
    fn test_fetch_update_rejects_a_package_the_signature_does_not_match() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);
        let api = TestApi::badly_signed(TARGET_HASH);

        let error = updater
            .fetch_update(&registry.registry, &api, SignatureCheck::Required)
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Could not verify the signature of this package"
        );
        assert!(api.download().is_some());
        assert!(!dir.path().join(PACKAGE_DIR).exists());
    }

    /// What `--skip-signatures` is for: the host has no signature key yet, and
    /// the package is spooled anyway.
    #[test]
    fn test_fetch_update_spools_an_unsigned_package_when_asked_to_skip() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = Updater {
            package_dir: dir.path().join(PACKAGE_DIR),
            ..updater_with_source(some_config(), some_agent_info())
        };

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::unsigned(TARGET_HASH),
                SignatureCheck::Skip,
            )
            .unwrap();

        let FetchOutcome::Spooled {
            hash,
            path,
            signature,
            ..
        } = outcome
        else {
            panic!("expected a spooled package, got {outcome:?}");
        };
        assert_eq!(signature, SignatureCheck::Skip);
        assert_eq!(hash.as_str(), TARGET_HASH);
        assert_eq!(fs::read(&path).unwrap(), PACKAGE);
    }

    /// Skipping overrides the verification too, not only the pre-check: this
    /// package carries a signature that does not match it.
    #[test]
    fn test_fetch_update_spools_a_badly_signed_package_when_asked_to_skip() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::badly_signed(TARGET_HASH),
                SignatureCheck::Skip,
            )
            .unwrap();

        assert!(matches!(
            outcome,
            FetchOutcome::Spooled {
                signature: SignatureCheck::Skip,
                ..
            }
        ));
    }

    /// Skipping says nothing about which package is due: an up-to-date host
    /// still fetches nothing.
    #[test]
    fn test_fetch_update_skipping_still_fetches_nothing_when_up_to_date() {
        let dir = tempfile::TempDir::new().unwrap();
        let registry = registry_with_one_connection();
        let updater = updater_spooling_into(&dir);

        let outcome = updater
            .fetch_update(
                &registry.registry,
                &TestApi::new(Some(INSTALLED_HASH)),
                SignatureCheck::Skip,
            )
            .unwrap();

        assert_eq!(
            outcome,
            FetchOutcome::UpToDate(INSTALLED_HASH.parse().unwrap())
        );
        assert!(!dir.path().join(PACKAGE_DIR).exists());
    }

    #[test]
    fn test_fetch_update_names_the_site_that_did_not_answer() {
        let registry = registry_with_one_connection();

        let error = updater_with_source(some_config(), some_agent_info())
            .fetch_update(
                &registry.registry,
                &UnreachableApi,
                SignatureCheck::Required,
            )
            .unwrap_err();

        assert_eq!(
            error.to_string(),
            "Agent update status request to server/site failed"
        );
    }

    /// A downloaded package of `platform`, as the site delivered it.
    fn downloaded(platform: &str) -> UpdatePackage {
        UpdatePackage {
            hash: TARGET_HASH.parse().unwrap(),
            platform: String::from(platform),
            bytes: PACKAGE.to_vec(),
        }
    }

    /// A downloaded package of `platform`, verified and ready to be saved.
    fn verified(platform: &str) -> VerifiedPackage {
        VerifiedPackage(downloaded(platform))
    }

    #[test]
    fn test_save_package_of_a_deb_host() {
        let dir = tempfile::TempDir::new().unwrap();

        let path = verified("linux_deb").save(dir.path()).unwrap();

        assert_eq!(path, dir.path().join("fedcba9876543210.deb"));
        assert_eq!(fs::read(&path).unwrap(), PACKAGE);
    }

    #[test]
    fn test_save_package_of_an_rpm_host() {
        let dir = tempfile::TempDir::new().unwrap();

        let path = verified("linux_rpm").save(dir.path()).unwrap();

        assert_eq!(path, dir.path().join("fedcba9876543210.rpm"));
    }

    #[test]
    fn test_save_package_of_a_windows_host() {
        let dir = tempfile::TempDir::new().unwrap();

        let path = verified("windows_msi").save(dir.path()).unwrap();

        assert_eq!(path, dir.path().join("fedcba9876543210.msi"));
    }

    #[test]
    fn test_save_package_of_a_platform_without_a_package_format() {
        let dir = tempfile::TempDir::new().unwrap();

        let error = verified("linux_tgz").save(dir.path()).unwrap_err();

        assert_eq!(
            error.to_string(),
            "No agent package format known for the platform \"linux_tgz\""
        );
    }

    /// A package that cannot be named is not written, and does not even bring
    /// the directory it would have gone into into existence.
    #[test]
    fn test_save_package_of_an_unknown_platform_writes_nothing() {
        let dir = tempfile::TempDir::new().unwrap();
        let package_dir = dir.path().join("update");

        assert!(verified("linux_tgz").save(&package_dir).is_err());

        assert!(!package_dir.exists());
    }

    /// The package directory is part of no package: the first update creates it.
    #[test]
    fn test_save_package_creates_the_package_directory() {
        let dir = tempfile::TempDir::new().unwrap();
        let package_dir = dir.path().join("runtime").join("controller").join("update");

        let path = verified("linux_deb").save(&package_dir).unwrap();

        assert_eq!(path, package_dir.join("fedcba9876543210.deb"));
    }

    #[test]
    fn test_save_package_leaves_no_temporary_file_behind() {
        let dir = tempfile::TempDir::new().unwrap();

        let path = verified("linux_deb").save(dir.path()).unwrap();

        assert!(!tmp_path_for_atomical_save(&path).exists());
    }

    /// The same package is downloaded again after a failed installation.
    #[test]
    fn test_save_package_replaces_a_previous_one() {
        let dir = tempfile::TempDir::new().unwrap();
        write(&dir, "fedcba9876543210.deb", "a stale package");

        let path = verified("linux_deb").save(dir.path()).unwrap();

        assert_eq!(fs::read(&path).unwrap(), PACKAGE);
    }

    #[cfg(unix)]
    #[test]
    fn test_save_package_is_readable_by_the_installer_only() {
        let dir = tempfile::TempDir::new().unwrap();

        let path = verified("linux_deb").save(dir.path()).unwrap();

        assert_eq!(
            fs::metadata(&path).unwrap().permissions().mode() & 0o777,
            PACKAGE_FILE_MODE
        );
    }

    #[test]
    fn test_a_verified_package_is_named_verified() {
        assert_eq!(
            verified("linux_deb").to_string(),
            "Verified agent package fedcba9876543210"
        );
    }

    #[test]
    fn test_an_unverified_package_says_so_in_capitals() {
        assert_eq!(
            downloaded("linux_deb").accept_unverified().to_string(),
            "UNVERIFIED agent package fedcba9876543210"
        );
    }

    /// The file an unverified package leaves behind is the same file: only the
    /// method that asks for it, and the line that reports it, differ.
    #[test]
    fn test_save_an_unverified_package() {
        let dir = tempfile::TempDir::new().unwrap();

        let path = downloaded("linux_deb")
            .accept_unverified()
            .save_unverified(dir.path())
            .unwrap();

        assert_eq!(path, dir.path().join("fedcba9876543210.deb"));
        assert_eq!(fs::read(&path).unwrap(), PACKAGE);
    }
}
