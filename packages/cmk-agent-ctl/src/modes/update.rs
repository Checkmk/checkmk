// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The update cycle of this host, run once by the `update` mode and at the
//! configured interval by the update thread of the daemon.

use crate::configuration::config::{ClientConfig, Registry};
use crate::environment::PathResolver;
#[cfg(unix)]
use crate::updater::InstallOutcome;
use crate::updater::{CheckOutcome, FetchOutcome, SignatureCheck, Updater, WritableUpdater};
use crate::{agent_receiver_api, misc, setup};
use anyhow::Result as AnyhowResult;
use log::warn;
use rand::Rng;
#[cfg(unix)]
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant, SystemTime};

/// Ask the site which agent package it has for this host, and report it.
///
/// Reads only, so it needs no [`WritableUpdater`] and waits for no update.
///
/// # Errors
///
/// If the site cannot be asked.
pub fn check(
    updater: &Updater,
    registry: &Registry,
    client_config: &ClientConfig,
) -> AnyhowResult<()> {
    if !updater.is_configured()? {
        println!("Agent updates are not configured for this host");
        return Ok(());
    }
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    println!("{}", report(updater.check(registry, &api)?));
    Ok(())
}

/// Fetch the agent package the site has for this host and hand it over.
///
/// The package is downloaded and, once `signature` is satisfied, spooled for
/// the installer and handed to it. The install step runs as root in a unit of
/// its own, so this run ends when that unit does, and the line it prints says
/// what reached it rather than what it installed.
///
/// `signature` carries `--skip-signatures` through. The install step checks
/// the signature again regardless, so a package nobody vouched for is spooled
/// here and refused there. On Windows nothing checks
/// it again, so such a package is not handed over at all.
///
/// A package handed over in an earlier run is settled first: the installed
/// hash says whether its installation took effect.
///
/// An error of the update goes to the update state, where the next status
/// request reports it to the site.
///
/// # Errors
///
/// If the site cannot be asked, does not deliver the package it offered, if
/// the package fails verification or cannot be spooled, or if the installer
/// cannot be reached.
pub fn update(
    updater: &mut WritableUpdater,
    registry: &Registry,
    client_config: &ClientConfig,
    signature: SignatureCheck,
) -> AnyhowResult<()> {
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    update_through(updater, registry, &api, signature)
}

fn update_through(
    updater: &mut WritableUpdater,
    registry: &Registry,
    api: &(impl agent_receiver_api::AgentUpdate + agent_receiver_api::RegistrationStatusV2),
    signature: SignatureCheck,
) -> AnyhowResult<()> {
    if !updater.is_configured()? {
        println!("Agent updates are not configured for this host");
        return Ok(());
    }

    let result = run_cycle(updater, registry, api, signature);
    if let Err(error) = &result {
        if let Err(save_error) = updater.record_error(error) {
            warn!("Could not record the error in the update state: {save_error:#}");
        }
    }
    result
}

/// Settle the pending installation, migrate the registration of the Python
/// updater on a host without an update source, then ask the site, record its
/// answer, and fetch and hand over what it offers.
fn run_cycle(
    updater: &mut WritableUpdater,
    registry: &Registry,
    api: &(impl agent_receiver_api::AgentUpdate + agent_receiver_api::RegistrationStatusV2),
    signature: SignatureCheck,
) -> AnyhowResult<()> {
    updater.settle_pending_install()?;

    if let Some(source) = updater.migrate(registry, api)? {
        println!(
            "Migrated the registration of the Python agent updater, connection {} is the update \
             source",
            source.uuid
        );
    }

    let answer = updater.ask_update_source(registry, api)?;
    updater.record_answer(&answer)?;
    let fetched = updater.fetch_update(answer, api, signature)?;

    println!("{}", report_fetch(&fetched));

    match &fetched {
        FetchOutcome::NotPossible | FetchOutcome::Superseded => {}
        FetchOutcome::UpToDate(_) | FetchOutcome::NoPackage => updater.clear_last_error()?,
        FetchOutcome::SourceUnavailable => updater.record_source_unavailable()?,
        #[cfg(unix)]
        FetchOutcome::Spooled {
            path,
            signatures,
            hash,
            ..
        } => {
            updater.store_pending_hash(hash)?;
            let outcome = updater.install_update(path, signatures);
            if !matches!(outcome, Ok(InstallOutcome::HandedOver)) {
                if let Err(error) = updater.clear_pending_hash() {
                    log::warn!("Could not clear the pending installation: {error:#}");
                }
            }

            println!("{}", report_install(outcome?, path));
        }
        #[cfg(windows)]
        FetchOutcome::Spooled {
            path,
            hash,
            signature,
            ..
        } => match signature {
            SignatureCheck::Required => {
                updater.store_pending_hash(hash)?;
                let handed_over = updater.hand_over_msi(path);
                if handed_over.is_err() {
                    if let Err(error) = updater.clear_pending_hash() {
                        log::warn!("Could not clear the pending installation: {error:#}");
                    }
                }
                println!(
                    "The Windows agent service installs it from {}",
                    handed_over?.display()
                );
            }
            // Nothing on Windows checks the signature again, so an unverified package stays put.
            SignatureCheck::Skip => println!(
                "Unverified packages are not installed on Windows, {} stays where it is",
                path.display()
            ),
        },
    }
    Ok(())
}

/// The outcome of a check in the one line the mode prints.
///
/// The reason behind [`CheckOutcome::NotPossible`] is logged rather than
/// printed: it names the artifacts of the updater, which is more than the
/// question asked here deserves.
fn report(outcome: CheckOutcome) -> String {
    match outcome {
        CheckOutcome::NotPossible => String::from(
            "No agent update check is possible for this host, run with -v for the reason",
        ),
        CheckOutcome::NoPackage => String::from("No agent package available for this host"),
        CheckOutcome::UpToDate(hash) => format!("Agent is up to date: {hash}"),
        CheckOutcome::UpdateAvailable { target, installed } => {
            format!("Agent update available: {target} (installed: {installed})")
        }
        CheckOutcome::SourceUnavailable => {
            String::from("The site of the update source serves no agent updates")
        }
    }
}

/// The outcome of a fetch in the line the mode prints for it.
///
/// A spooled package is named by its file: the privileged step is a process of
/// its own, and [`report_install`] says on the next line what became of the
/// hand-over to it.
///
/// The two outcomes that end without a package read as they do in [`report`]:
/// the same situation must not be worded by whether `--check-only` was passed.
///
/// An unverified package says so. The file on disk carries no such mark, so
/// this line is the only place the two are told apart.
fn report_fetch(outcome: &FetchOutcome) -> String {
    match outcome {
        FetchOutcome::NotPossible => {
            String::from("No agent update is possible for this host, run with -v for the reason")
        }
        FetchOutcome::NoPackage => String::from("No agent package available for this host"),
        FetchOutcome::UpToDate(hash) => format!("Agent is up to date: {hash}"),
        FetchOutcome::SourceUnavailable => {
            String::from("The site of the update source serves no agent updates")
        }
        FetchOutcome::Superseded => String::from(
            "The site replaced the offered agent package, the next update gets the new one",
        ),
        FetchOutcome::Spooled {
            hash,
            path,
            signature,
            ..
        } => format!(
            "{} is ready at {}",
            signature.package_name(hash),
            path.display()
        ),
    }
}

/// The update thread of the daemon: one cycle per interval, while automatic
/// updates are activated. A new host checks after a random delay of up to a
/// minute, then waits a random part of the interval, so hosts started together
/// spread over it. A restart keeps the schedule, except the one an install
/// causes: that host checks within a minute to confirm the install, and its
/// schedule moves to that check. Tests skip the wait at start with
/// `DEBUG_NO_UPDATE_START_DELAY`.
///
/// The lock is taken only for a cycle that runs, so a host without automatic
/// updates never touches the download directory. A failed cycle, a lock that
/// cannot be taken included, is logged and retried at the next interval: only
/// a registry that cannot be reloaded ends the thread, as in the other threads.
pub fn fn_thread(
    paths: PathResolver,
    mut registry: Registry,
    client_config: ClientConfig,
) -> AnyhowResult<()> {
    let updater = Updater::new(&paths);
    if !setup::update_start_delay_disabled() {
        match start_delay(
            updater.next_check(),
            updater.has_pending_install(),
            updater.interval(),
            SystemTime::now(),
        ) {
            Some(delay) => thread::sleep(delay),
            None => misc::sleep_randomly(),
        }
    }

    loop {
        let begin = Instant::now();
        let began_at = SystemTime::now();
        registry.refresh()?;
        let updater = Updater::new(&paths);
        let interval = updater.interval();
        let wait_time = if updater.next_check().is_none() {
            // A random part of the interval: the factor is in 0..1.
            interval.mul_f64(rand::thread_rng().gen::<f64>())
        } else {
            interval
        };

        if updater.handle_update_cycle(&registry) {
            match Updater::writable(&paths) {
                Ok(mut updater) => {
                    // Save this now: installing an agent restarts the controller,
                    // so code after update() may not run.
                    if let Err(error) = updater.record_next_check(began_at + wait_time) {
                        warn!("Could not record the next check. {error:#}");
                    }
                    if let Err(result) = update(
                        &mut updater,
                        &registry,
                        &client_config,
                        SignatureCheck::Required,
                    ) {
                        warn!("Could not update. {result:#}");
                    }
                }
                Err(error) => warn!("Could not lock the updater: {error:#}"),
            }
        }

        thread::sleep(wait_time.saturating_sub(begin.elapsed()));
    }
}

/// Until the recorded next check, at most one interval. None for a new or an
/// overdue host, and for one with an install to confirm: those start after a
/// random delay instead.
fn start_delay(
    next_check: Option<SystemTime>,
    install_pending: bool,
    interval: Duration,
    now: SystemTime,
) -> Option<Duration> {
    if install_pending {
        return None;
    }
    Some(next_check?.duration_since(now).ok()?.min(interval))
}

/// What the hand-over to the privileged install step did, in the line the mode
/// prints after the one of the fetch.
///
/// The step answers nothing yet, so a finished hand-over is all this side
/// knows about it. What it made of the package is in the journal of its unit,
/// and whether the agent moved is what the next check says.
#[cfg(unix)]
fn report_install(outcome: InstallOutcome, path: &Path) -> String {
    match outcome {
        InstallOutcome::NoInstaller => format!(
            "No installer socket is configured, {} stays where it is",
            path.display()
        ),
        InstallOutcome::HandedOver => String::from(
            "The installer has taken it and finished, run with --check-only to see \
             whether the agent moved",
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const HOUR: Duration = Duration::from_secs(3600);

    #[test]
    fn test_a_new_host_starts_after_a_random_delay() {
        assert_eq!(start_delay(None, false, HOUR, SystemTime::now()), None);
    }

    #[test]
    fn test_a_restarted_host_waits_until_its_next_check() {
        let now = SystemTime::now();

        let wait = start_delay(Some(now + Duration::from_secs(600)), false, HOUR, now);

        assert_eq!(wait, Some(Duration::from_secs(600)));
    }

    #[test]
    fn test_a_host_due_now_starts_without_delay() {
        let now = SystemTime::now();

        assert_eq!(
            start_delay(Some(now), false, HOUR, now),
            Some(Duration::ZERO)
        );
    }

    #[test]
    fn test_an_overdue_host_starts_after_a_random_delay() {
        let now = SystemTime::now();

        let wait = start_delay(Some(now - Duration::from_secs(600)), false, HOUR, now);

        assert_eq!(wait, None);
    }

    /// A clock that jumped back, or an interval the rule shortened.
    #[test]
    fn test_a_host_waits_at_most_one_interval() {
        let now = SystemTime::now();

        let wait = start_delay(Some(now + 2 * HOUR), false, HOUR, now);

        assert_eq!(wait, Some(HOUR));
    }

    #[test]
    fn test_a_host_with_an_install_to_confirm_starts_after_a_random_delay() {
        let now = SystemTime::now();

        let wait = start_delay(Some(now + Duration::from_secs(600)), true, HOUR, now);

        assert_eq!(wait, None);
    }

    const TARGET_HASH: &str = "fedcba9876543210";
    const INSTALLED_HASH: &str = "0123456789abcdef";

    #[test]
    fn test_report_an_available_update() {
        assert_eq!(
            report(CheckOutcome::UpdateAvailable {
                target: TARGET_HASH.parse().unwrap(),
                installed: INSTALLED_HASH.parse().unwrap(),
            }),
            "Agent update available: fedcba9876543210 (installed: 0123456789abcdef)"
        );
    }

    #[test]
    fn test_report_an_agent_that_is_up_to_date() {
        assert_eq!(
            report(CheckOutcome::UpToDate(INSTALLED_HASH.parse().unwrap())),
            "Agent is up to date: 0123456789abcdef"
        );
    }

    #[test]
    fn test_report_a_site_without_a_package() {
        assert_eq!(
            report(CheckOutcome::NoPackage),
            "No agent package available for this host"
        );
    }

    #[test]
    fn test_report_a_check_that_could_not_be_made() {
        assert_eq!(
            report(CheckOutcome::NotPossible),
            "No agent update check is possible for this host, run with -v for the reason"
        );
    }

    #[test]
    fn test_report_a_spooled_package() {
        assert_eq!(
            report_fetch(&FetchOutcome::Spooled {
                hash: TARGET_HASH.parse().unwrap(),
                path: std::path::PathBuf::from("/spool/fedcba9876543210.deb"),
                signature: SignatureCheck::Required,
                signatures: vec![],
            }),
            "Verified agent package fedcba9876543210 is ready at \
             /spool/fedcba9876543210.deb"
        );
    }

    /// The file on disk is the same either way, so the line has to carry the
    /// difference.
    #[test]
    fn test_report_a_spooled_package_nobody_vouched_for() {
        assert_eq!(
            report_fetch(&FetchOutcome::Spooled {
                hash: TARGET_HASH.parse().unwrap(),
                path: std::path::PathBuf::from("/spool/fedcba9876543210.deb"),
                signature: SignatureCheck::Skip,
                signatures: vec![],
            }),
            "UNVERIFIED agent package fedcba9876543210 is ready at \
             /spool/fedcba9876543210.deb"
        );
    }

    /// The hand-over is over, and the outcome of the installation is not
    /// this run's to report.
    #[cfg(unix)]
    #[test]
    fn test_report_a_package_the_installer_took() {
        assert_eq!(
            report_install(
                InstallOutcome::HandedOver,
                std::path::Path::new("/spool/fedcba9876543210.deb")
            ),
            "The installer has taken it and finished, run with --check-only to see \
             whether the agent moved"
        );
    }

    /// Without a privileged step the package stays a file, and the line says
    /// where it is rather than leaving the run without an answer.
    #[cfg(unix)]
    #[test]
    fn test_report_a_package_nobody_takes() {
        assert_eq!(
            report_install(
                InstallOutcome::NoInstaller,
                std::path::Path::new("/spool/fedcba9876543210.deb")
            ),
            "No installer socket is configured, /spool/fedcba9876543210.deb stays where it is"
        );
    }

    #[test]
    fn test_report_a_fetch_from_a_site_without_a_package() {
        assert_eq!(
            report_fetch(&FetchOutcome::NoPackage),
            "No agent package available for this host"
        );
    }

    #[test]
    fn test_report_a_fetch_of_an_agent_that_is_up_to_date() {
        assert_eq!(
            report_fetch(&FetchOutcome::UpToDate(INSTALLED_HASH.parse().unwrap())),
            "Agent is up to date: 0123456789abcdef"
        );
    }

    #[test]
    fn test_report_a_fetch_that_could_not_be_made() {
        assert_eq!(
            report_fetch(&FetchOutcome::NotPossible),
            "No agent update is possible for this host, run with -v for the reason"
        );
    }

    /// The update cycle against a mock of the site. The agent info of the
    /// single directory deployment exists on Unix only.
    #[cfg(unix)]
    mod update_cycle {
        use super::*;
        use crate::agent_receiver_api::{
            AgentDownloadBody, AgentUpdate, ApiError, RegistrationStatusV2,
            RegistrationStatusV2Response, RegistrationStatusV2ResponseRegistered, UpdateStatusBody,
            UpdateStatusResponse,
        };
        use crate::config::test_helpers::TestRegistry;
        use crate::config::{ConnectionMode, JSONLoader, TrustedConnection};
        use crate::environment::SetupMode;
        use crate::updater::{UpdateSource, UpdateState};
        use std::cell::RefCell;
        use std::fs;

        const SOURCE_UUID: &str = "8f0e3a1c-5b2d-4e6f-9a7b-0c1d2e3f4a5b";

        /// A site that answers each status request with the next of `answers`,
        /// and records the `last_error` that each request reports.
        struct ScriptedApi {
            answers: RefCell<Vec<Result<UpdateStatusResponse, ApiError>>>,
            reported_errors: RefCell<Vec<Option<String>>>,
            registered_host_name: Option<&'static str>,
        }

        impl ScriptedApi {
            fn new(answers: Vec<Result<UpdateStatusResponse, ApiError>>) -> Self {
                Self {
                    answers: RefCell::new(answers),
                    reported_errors: RefCell::new(Vec::new()),
                    registered_host_name: None,
                }
            }

            /// The site registered the connection for `host_name`.
            fn registering_the_host_as(self, host_name: &'static str) -> Self {
                Self {
                    registered_host_name: Some(host_name),
                    ..self
                }
            }

            fn reported_errors(&self) -> Vec<Option<String>> {
                self.reported_errors.borrow().clone()
            }
        }

        impl AgentUpdate for ScriptedApi {
            fn update_status(
                &self,
                _base_url: &reqwest::Url,
                _connection: &TrustedConnection,
                body: &UpdateStatusBody<'_>,
            ) -> AnyhowResult<UpdateStatusResponse, ApiError> {
                self.reported_errors
                    .borrow_mut()
                    .push(body.last_error.map(String::from));
                let mut answers = self.answers.borrow_mut();
                assert!(!answers.is_empty(), "the site was asked once too often");
                answers.remove(0)
            }

            fn download_agent(
                &self,
                _base_url: &reqwest::Url,
                _connection: &TrustedConnection,
                _body: &AgentDownloadBody<'_>,
            ) -> AnyhowResult<Vec<u8>, ApiError> {
                panic!("the site offered no package")
            }
        }

        impl RegistrationStatusV2 for ScriptedApi {
            fn registration_status_v2(
                &self,
                _base_url: &reqwest::Url,
                _connection: &TrustedConnection,
            ) -> AnyhowResult<RegistrationStatusV2Response> {
                let host_name = self
                    .registered_host_name
                    .expect("the host has an update source, so nothing migrates");
                Ok(RegistrationStatusV2Response::Registered(
                    RegistrationStatusV2ResponseRegistered {
                        hostname: String::from(host_name),
                        connection_mode: ConnectionMode::Pull,
                    },
                ))
            }
        }

        fn no_package() -> Result<UpdateStatusResponse, ApiError> {
            Ok(UpdateStatusResponse { target_agent: None })
        }

        /// A host in a single directory deployment, whose update source is the
        /// one connection of its registry.
        struct Host {
            _dir: tempfile::TempDir,
            paths: PathResolver,
            registry: TestRegistry,
        }

        impl Host {
            fn new() -> Self {
                Self::with_config("activated = true\ninterval = 60\n")
            }

            fn with_config(updater_config: &str) -> Self {
                let dir = tempfile::TempDir::new().unwrap();
                let paths = PathResolver::new(SetupMode::SingleDir, dir.path());
                for path in [
                    &paths.updater_config_path,
                    &paths.updater_state_path,
                    &paths.agent_info_path,
                ] {
                    fs::create_dir_all(path.parent().unwrap()).unwrap();
                }
                fs::write(&paths.updater_config_path, updater_config).unwrap();
                fs::write(
                    &paths.agent_info_path,
                    format!(r#"{{"hash": "{INSTALLED_HASH}", "platform": "linux_deb"}}"#),
                )
                .unwrap();
                let source = UpdateSource {
                    uuid: SOURCE_UUID.parse().unwrap(),
                    available: true,
                };
                let registry = TestRegistry::new().add_connection(
                    &ConnectionMode::Pull,
                    "server/site",
                    source.uuid,
                );
                UpdateState {
                    source: Some(source),
                    ..Default::default()
                }
                .save(&paths.updater_state_path)
                .unwrap();
                Self {
                    _dir: dir,
                    paths,
                    registry,
                }
            }

            /// A host without an update source, whose Python updater was
            /// registered as `host_name` with the site of the one connection.
            fn registered_by_the_python_updater_as(host_name: &str) -> Self {
                let host = Self::new();
                UpdateState::default()
                    .save(&host.paths.updater_state_path)
                    .unwrap();
                let legacy_state = &host.paths.python_updater_state_path;
                fs::create_dir_all(legacy_state.parent().unwrap()).unwrap();
                fs::write(
                    legacy_state,
                    format!(
                        "{{'host_name': '{host_name}', 'server': 'server', 'site': 'site', \
                         'host_secret': 'the-host-secret'}}\n"
                    ),
                )
                .unwrap();
                host
            }

            /// One cycle. The `update` mode and the daemon both load the
            /// updater afresh for each cycle.
            fn cycle(&self, api: &(impl AgentUpdate + RegistrationStatusV2)) -> AnyhowResult<()> {
                let mut updater = Updater::writable(&self.paths).unwrap();
                update_through(
                    &mut updater,
                    &self.registry.registry,
                    api,
                    SignatureCheck::Required,
                )
            }

            fn state(&self) -> UpdateState {
                UpdateState::load(&self.paths.updater_state_path).unwrap()
            }
        }

        /// `activated` gates the daemon only: `update` runs its cycle regardless.
        #[test]
        fn test_update_runs_while_updates_are_deactivated() {
            let host = Host::with_config("activated = false\ninterval = 60\n");
            let site = ScriptedApi::new(vec![no_package()]);

            let cycle = host.cycle(&site);

            assert!(cycle.is_ok(), "{cycle:?}");
            assert_eq!(site.reported_errors().len(), 1);
        }

        /// TC-AU-006: a site that does not answer at all
        #[test]
        fn test_a_site_that_does_not_answer_is_asked_again_by_the_next_cycle() {
            let host = Host::new();
            let first_silent_then_answering = ScriptedApi::new(vec![
                Err(ApiError::Communication(anyhow::anyhow!(
                    "connection refused"
                ))),
                no_package(),
            ]);

            let failed = host.cycle(&first_silent_then_answering);
            let failed_state = host.state();
            let retried = host.cycle(&first_silent_then_answering);

            assert!(failed.is_err(), "{failed:?}");
            let error = failed_state.last_error.clone().unwrap_or_default();
            assert!(error.contains("connection refused"), "{error:?}");
            assert!(
                failed_state.source.as_ref().unwrap().available,
                "{failed_state:?}"
            );
            assert!(retried.is_ok(), "{retried:?}");
            assert_eq!(
                first_silent_then_answering.reported_errors(),
                [None, Some(error)]
            );
            let state = host.state();
            assert_eq!(state.last_error, None);
            assert!(state.source.unwrap().available);
        }

        /// CMK-39594 AC9, TC-AU-068: `last_check` records the last answer of the
        /// site, not the last attempt.
        #[test]
        fn test_a_site_that_does_not_answer_leaves_the_last_check() {
            let host = Host::new();
            UpdateState {
                last_check: Some(1_759_276_800),
                ..host.state()
            }
            .save(&host.paths.updater_state_path)
            .unwrap();
            let silent = ScriptedApi::new(
                (0..3)
                    .map(|_| {
                        Err(ApiError::Communication(anyhow::anyhow!(
                            "connection refused"
                        )))
                    })
                    .collect(),
            );

            for _ in 0..3 {
                assert!(host.cycle(&silent).is_err());
            }

            assert_eq!(host.state().last_check, Some(1_759_276_800));
        }

        /// TC-AU-070: a source latched unavailable by a 501 does not resume when the site answers again
        #[test]
        fn test_a_source_latched_by_501_stays_latched() {
            let host = Host::new();
            let first_501_then_upgraded = ScriptedApi::new(vec![
                Err(ApiError::ResponseStatus {
                    status: http::StatusCode::NOT_IMPLEMENTED,
                    body: None,
                }),
                no_package(),
            ]);

            let first = host.cycle(&first_501_then_upgraded);
            let second = host.cycle(&first_501_then_upgraded);

            assert!(first.is_ok(), "{first:?}");
            assert!(second.is_ok(), "{second:?}");
            assert_eq!(first_501_then_upgraded.reported_errors().len(), 1);
            let state = host.state();
            assert!(!state.source.as_ref().unwrap().available, "{state:?}");
        }

        /// CMK-39502, TC-AU-090: the Python updater registered the host under
        /// its FQDN, the site knows it under its short name. The cycle records
        /// the error and leaves the Python updater's state file alone, so the
        /// next cycle tries again.
        #[test]
        fn test_a_legacy_registration_under_another_host_name_is_retried_by_the_next_cycle() {
            let host = Host::registered_by_the_python_updater_as("myhost.example.com");
            let legacy_state = fs::read(&host.paths.python_updater_state_path).unwrap();
            let site_knowing_the_short_name =
                ScriptedApi::new(vec![]).registering_the_host_as("myhost");

            let failed = host.cycle(&site_knowing_the_short_name);
            let failed_state = host.state();
            let retried = host.cycle(&site_knowing_the_short_name);

            assert!(failed.is_err(), "{failed:?}");
            let error = failed_state.last_error.unwrap_or_default();
            assert!(
                error.contains("server/site registered this host as myhost"),
                "{error:?}"
            );
            assert_eq!(failed_state.source, None);
            assert!(retried.is_err(), "{retried:?}");
            assert_eq!(host.state().last_error, Some(error));
            assert_eq!(
                fs::read(&host.paths.python_updater_state_path).unwrap(),
                legacy_state
            );
        }
    }
}
