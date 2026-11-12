// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The update cycle of this host, run once by the `update` mode and at the
//! configured interval by the update thread of the daemon.

use crate::agent_receiver_api::{AgentUpdateAuthorization, NoAgentUpdates};
use crate::configuration::config::{ClientConfig, Registry, TrustedConnectionWithRemote};
use crate::constants::CMK_UPDATE_AGENT_CMD;
use crate::environment::{PathResolver, SetupMode};
use crate::site_spec::SiteID;
#[cfg(unix)]
use crate::updater::Installation;
use crate::updater::{
    no_agent_updates_message, refusal_message, CheckOutcome, FetchOutcome, Obstacle, PythonUpdater,
    SignatureCheck, Spooled, Updater, WritableUpdater,
};
use crate::{agent_receiver_api, misc, setup};
#[cfg(unix)]
use anyhow::anyhow;
use anyhow::Result as AnyhowResult;
use log::warn;
use rand::Rng;
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
    python_updater: Option<&PythonUpdater>,
    setup_mode: SetupMode,
) -> AnyhowResult<()> {
    if !updater.is_configured()? {
        println!(
            "{}",
            report_unconfigured(python_updater, setup_mode, registry)
        );
        return Ok(());
    }
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    println!("{}", report(updater.check(registry, &api)?, registry));
    Ok(())
}

/// Fetch the agent package the site has for this host and hand it over.
///
/// On Linux the package is streamed to the install step, which runs as root in
/// a unit of its own, verifies the package and installs it. This run ends when
/// that unit does, unless the installation ends this process first. On
/// Windows the package is verified, spooled and handed to the agent service.
///
/// `signature` carries `--skip-signatures` through. On Linux it skips only the
/// check before the download, because the install step verifies the package
/// regardless. On Windows nothing checks it again, so a package nobody vouched
/// for is not handed over at all.
///
/// A package handed over in an earlier run is settled first: the installed
/// hash says whether its installation took effect.
///
/// An error of the update goes to the update state, where the next status
/// request reports it to the site.
///
/// # Errors
///
/// If the site cannot be asked or does not deliver the package it offered, if
/// the package fails verification, cannot be spooled or is refused, if the
/// installer cannot be reached, or if the installation fails.
pub fn update(
    updater: &mut WritableUpdater,
    registry: &Registry,
    client_config: &ClientConfig,
    signature: SignatureCheck,
    python_updater: Option<&PythonUpdater>,
    setup_mode: SetupMode,
) -> AnyhowResult<()> {
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    update_through(
        updater,
        registry,
        &api,
        signature,
        python_updater,
        setup_mode,
    )
}

fn update_through(
    updater: &mut WritableUpdater,
    registry: &Registry,
    api: &(impl agent_receiver_api::AgentUpdate + agent_receiver_api::RegistrationStatusV2),
    signature: SignatureCheck,
    python_updater: Option<&PythonUpdater>,
    setup_mode: SetupMode,
) -> AnyhowResult<()> {
    if !updater.is_configured()? {
        println!(
            "{}",
            report_unconfigured(python_updater, setup_mode, registry)
        );
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
    #[cfg(unix)]
    let fetched = updater.fetch_and_install(answer, api, signature)?;
    #[cfg(windows)]
    let fetched = updater.fetch_update(answer, api, signature)?;

    println!("{}", report_fetch(&fetched, registry));

    match &fetched {
        FetchOutcome::NotPossible(_) | FetchOutcome::Superseded => {}
        FetchOutcome::UpToDate(_) | FetchOutcome::NoPackage => updater.clear_last_error()?,
        FetchOutcome::SourceUnavailable { reason, .. } => match reason {
            NoAgentUpdates::CommunityEdition => updater.record_source_unavailable(*reason)?,
            // A license can come back while nobody touches the host.
            NoAgentUpdates::NotLicensed => {}
        },
        #[cfg(unix)]
        FetchOutcome::Due(installation) => installation_outcome(installation)?,
        #[cfg(windows)]
        FetchOutcome::Due(Spooled {
            path,
            hash,
            signature,
        }) => match signature {
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

/// What a host without an update configuration is told.
///
/// The bakery ships the Python updater only under a rule that enables agent
/// updates, so a package with it and without an update configuration is
/// updated by the Python updater.
fn report_unconfigured(
    python_updater: Option<&PythonUpdater>,
    setup_mode: SetupMode,
    registry: &Registry,
) -> String {
    if python_updater.is_none() {
        return report_without_updater(registry);
    }
    let command = if cfg!(windows) {
        format!("{CMK_UPDATE_AGENT_CMD} updater")
    } else {
        String::from(CMK_UPDATE_AGENT_CMD)
    };
    let mut report = format!(
        "Agent updates of this host are handled by the legacy updater\n\
         ({command}), not by the Agent Controller."
    );
    // Windows knows the classic mode only, and the integrated updater runs in it.
    if cfg!(unix) && setup_mode == SetupMode::Classic {
        report.push_str(
            "\n\n\
             The Agent Controller can only update agents that use the single-directory\n\
             deployment. This agent uses the classic file deployment.\n\
             To switch, see https://checkmk.com/werk/19234",
        );
    }
    report
}

const BAKERY_HINT: &str = "Agent updates need an agent package from the Agent Bakery, baked with \
    the rule \"Agent updater (Linux, Windows, Solaris)\". The Agent Bakery is part of the \
    commercial editions (see https://checkmk.com/pricing#feature-table).";

/// A plain registration sets no update source under the Registration option
/// "manual", which is the default.
const REGISTER_HINT: &str =
    "Register the agent controller with --automatic-updates to set an update source.";

/// The connections that can reach a site. The registry holds them in hash
/// maps, so they are sorted by site for a stable output.
fn standard_connections(registry: &Registry) -> Vec<(&SiteID, &TrustedConnectionWithRemote)> {
    let mut connections: Vec<_> = registry
        .get_push_connections()
        .chain(registry.get_standard_pull_connections())
        .collect();
    connections.sort_by_key(|(site_id, _)| *site_id);
    connections
}

/// What a host whose package ships no updater is told.
fn report_without_updater(registry: &Registry) -> String {
    report_with_refusals(
        "Agent updates are not configured for this host.",
        BAKERY_HINT,
        registry,
        |site_id, authorization| {
            Some(no_agent_updates_message(
                site_id,
                authorization.no_agent_updates()?,
            ))
        },
    )
}

/// `first_line`, the refusals of the registered sites, and `hint`.
///
/// The hint helps only where a site may serve agent updates, so it is left
/// out when every registered site refused.
fn report_with_refusals(
    first_line: &str,
    hint: &str,
    registry: &Registry,
    refusal: impl Fn(&SiteID, AgentUpdateAuthorization) -> Option<String>,
) -> String {
    let connections = standard_connections(registry);
    let refusals: Vec<String> = connections
        .iter()
        .filter_map(|(site_id, connection)| refusal(site_id, connection.agent_update_authorization))
        .collect();
    let every_site_refused = !connections.is_empty() && refusals.len() == connections.len();

    let mut lines = vec![String::from(first_line)];
    lines.extend(refusals);
    if !every_site_refused {
        lines.push(String::from(hint));
    }
    lines.join("\n")
}

/// Why no site was asked, with the remedy where the controller knows one.
fn report_obstacle(obstacle: &Obstacle, registry: &Registry) -> String {
    match obstacle {
        Obstacle::NotOperational(_) => {
            format!("No agent update is possible for this host: {obstacle}")
        }
        Obstacle::NoSource => report_with_refusals(
            &format!("No agent update is possible for this host: {obstacle}."),
            REGISTER_HINT,
            registry,
            refusal_message,
        ),
        Obstacle::SourceNotRegistered(_) => {
            format!("No agent update is possible for this host: {obstacle}. {REGISTER_HINT}")
        }
        Obstacle::NoAgentUpdates { site_id, reason } => no_agent_updates_message(site_id, *reason),
    }
}

/// What the site of the update source answered to this run.
///
/// A site without the license keeps the authorization of the source, so its
/// line asks for no registration.
fn report_source_unavailable(site_id: &SiteID, reason: NoAgentUpdates) -> String {
    match reason {
        NoAgentUpdates::CommunityEdition => no_agent_updates_message(site_id, reason),
        NoAgentUpdates::NotLicensed => format!(
            "{site_id}: The license of this site does not include agent updates. This host \
             gets agent updates again once the license includes them."
        ),
    }
}

/// The outcome of a check in the lines the mode prints.
fn report(outcome: CheckOutcome, registry: &Registry) -> String {
    match outcome {
        CheckOutcome::NotPossible(obstacle) => report_obstacle(&obstacle, registry),
        CheckOutcome::NoPackage => String::from("No agent package available for this host"),
        CheckOutcome::UpToDate(hash) => format!("Agent is up to date: {hash}"),
        CheckOutcome::UpdateAvailable { target, installed } => {
            format!("Agent update available: {target} (installed: {installed})")
        }
        CheckOutcome::SourceUnavailable { site_id, reason } => {
            report_source_unavailable(&site_id, reason)
        }
    }
}

/// The outcome of a fetch in the line the mode prints for it.
///
/// The two outcomes that end without a package read as they do in [`report`]:
/// the same situation must not be worded by whether `--check-only` was passed.
fn report_fetch(outcome: &FetchOutcome<impl Report>, registry: &Registry) -> String {
    match outcome {
        FetchOutcome::NotPossible(obstacle) => report_obstacle(obstacle, registry),
        FetchOutcome::NoPackage => String::from("No agent package available for this host"),
        FetchOutcome::UpToDate(hash) => format!("Agent is up to date: {hash}"),
        FetchOutcome::SourceUnavailable { site_id, reason } => {
            report_source_unavailable(site_id, *reason)
        }
        FetchOutcome::Superseded => String::from(
            "The site replaced the offered agent package, the next update gets the new one",
        ),
        FetchOutcome::Due(due) => due.report(),
    }
}

/// The line [`report_fetch`] prints for a package that the site offers.
trait Report {
    fn report(&self) -> String;
}

/// A spooled package is named by its file. On Windows, the next line says what
/// became of the hand-over to the agent service.
///
/// An unverified package says so. The file on disk carries no such mark, so
/// this line is the only place the two are told apart.
impl Report for Spooled {
    fn report(&self) -> String {
        format!(
            "{} is ready at {}",
            self.signature.package_name(&self.hash),
            self.path.display()
        )
    }
}

#[cfg(unix)]
impl Report for Installation {
    fn report(&self) -> String {
        match self {
            Installation::NoInstaller(hash) => {
                format!("No installer socket is configured, agent package {hash} is not downloaded")
            }
            Installation::Installed {
                hash,
                result: Some(result),
            } => {
                if result.success {
                    format!("Agent package {hash} is installed")
                } else {
                    format!("The installer could not install agent package {hash}")
                }
            }
            Installation::Installed { hash, result: None } => format!(
                "The installer sent no result for agent package {hash}, run with --check-only \
                 to see whether the agent moved"
            ),
        }
    }
}

/// The update thread of the daemon: one cycle per interval, while automatic
/// updates are activated. A new host checks after a random delay of up to a
/// minute, then waits a random part of the interval, so hosts started together
/// spread over it. A restart keeps the schedule, except the one an install
/// causes: that host checks within a minute to confirm the install, and its
/// schedule moves to that check. Tests skip the wait at start with
/// `DEBUG_NO_UPDATE_START_DELAY`, and the cycles with `DEBUG_NO_UPDATE_THREAD`.
/// With `DEBUG_NO_UPDATE_THREAD`, the thread parks instead of returning,
/// because the daemon ends when one of its threads returns.
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
    if setup::update_thread_disabled() {
        loop {
            thread::park();
        }
    }
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
                        // A cycle runs only with an update configuration, and the
                        // Python updater is named only without one.
                        None,
                        paths.setup_mode,
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

/// A failed installation as the error of the run.
///
/// The pending hash stays: the next cycle settles the installation, from the
/// installed hash and the install result file.
#[cfg(unix)]
fn installation_outcome(installation: &Installation) -> AnyhowResult<()> {
    let Installation::Installed {
        hash,
        result: Some(result),
    } = installation
    else {
        return Ok(());
    };
    if result.success {
        return Ok(());
    }
    Err(anyhow!(result.error.clone().unwrap_or_else(|| format!(
        "The installation of agent package {hash} failed"
    ))))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;
    use crate::config::ConnectionMode;
    use crate::updater::not_permitted_message;
    #[cfg(unix)]
    use crate::updater::InstallResult;

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
            report(
                CheckOutcome::UpdateAvailable {
                    target: TARGET_HASH.parse().unwrap(),
                    installed: INSTALLED_HASH.parse().unwrap(),
                },
                &TestRegistry::new().registry
            ),
            "Agent update available: fedcba9876543210 (installed: 0123456789abcdef)"
        );
    }

    #[test]
    fn test_report_an_agent_that_is_up_to_date() {
        assert_eq!(
            report(
                CheckOutcome::UpToDate(INSTALLED_HASH.parse().unwrap()),
                &TestRegistry::new().registry
            ),
            "Agent is up to date: 0123456789abcdef"
        );
    }

    #[test]
    fn test_report_a_site_without_a_package() {
        assert_eq!(
            report(CheckOutcome::NoPackage, &TestRegistry::new().registry),
            "No agent package available for this host"
        );
    }

    /// CMK-42015: a host that the legacy updater updates is not unconfigured.
    #[cfg(unix)]
    #[test]
    fn test_report_a_host_updated_by_the_legacy_updater() {
        assert_eq!(
            report_unconfigured(
                Some(&PythonUpdater::at("cmk-update-agent")),
                SetupMode::SingleDir,
                &TestRegistry::new().registry
            ),
            "Agent updates of this host are handled by the legacy updater\n\
             (cmk-update-agent), not by the Agent Controller."
        );
    }

    /// CMK-42015: the classic layout keeps a host on the legacy updater.
    #[cfg(unix)]
    #[test]
    fn test_report_the_layout_of_a_classic_host_updated_by_the_legacy_updater() {
        assert_eq!(
            report_unconfigured(
                Some(&PythonUpdater::at("cmk-update-agent")),
                SetupMode::Classic,
                &TestRegistry::new().registry
            ),
            "Agent updates of this host are handled by the legacy updater\n\
             (cmk-update-agent), not by the Agent Controller.\n\
             \n\
             The Agent Controller can only update agents that use the single-directory\n\
             deployment. This agent uses the classic file deployment.\n\
             To switch, see https://checkmk.com/werk/19234"
        );
    }

    /// CMK-42015: on Windows the legacy updater is a command of the agent, and
    /// the classic mode is no reason to keep it.
    #[cfg(windows)]
    #[test]
    fn test_report_a_host_updated_by_the_legacy_updater() {
        assert_eq!(
            report_unconfigured(
                Some(&PythonUpdater::at("check_mk_agent.exe")),
                SetupMode::Classic,
                &TestRegistry::new().registry
            ),
            "Agent updates of this host are handled by the legacy updater\n\
             (check_mk_agent.exe updater), not by the Agent Controller."
        );
    }

    #[test]
    fn test_report_a_spooled_package() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::Due(Spooled {
                    hash: TARGET_HASH.parse().unwrap(),
                    path: std::path::PathBuf::from("/spool/fedcba9876543210.deb"),
                    signature: SignatureCheck::Required,
                }),
                &TestRegistry::new().registry
            ),
            "Verified agent package fedcba9876543210 is ready at \
             /spool/fedcba9876543210.deb"
        );
    }

    /// The file on disk is the same either way, so the line has to carry the
    /// difference.
    #[test]
    fn test_report_a_spooled_package_nobody_vouched_for() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::Due(Spooled {
                    hash: TARGET_HASH.parse().unwrap(),
                    path: std::path::PathBuf::from("/spool/fedcba9876543210.deb"),
                    signature: SignatureCheck::Skip,
                }),
                &TestRegistry::new().registry
            ),
            "UNVERIFIED agent package fedcba9876543210 is ready at \
             /spool/fedcba9876543210.deb"
        );
    }

    #[cfg(unix)]
    fn a_result(success: bool) -> InstallResult {
        InstallResult {
            aghash: TARGET_HASH.parse().unwrap(),
            success,
            error: None,
            finished: 1_760_000_000,
        }
    }

    #[cfg(unix)]
    #[test]
    fn test_report_an_installed_package() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::Due(Installation::Installed {
                    hash: TARGET_HASH.parse().unwrap(),
                    result: Some(a_result(true)),
                }),
                &TestRegistry::new().registry
            ),
            "Agent package fedcba9876543210 is installed"
        );
    }

    /// The reason follows as the error of the run.
    #[cfg(unix)]
    #[test]
    fn test_report_a_package_that_failed_to_install() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::Due(Installation::Installed {
                    hash: TARGET_HASH.parse().unwrap(),
                    result: Some(a_result(false)),
                }),
                &TestRegistry::new().registry
            ),
            "The installer could not install agent package fedcba9876543210"
        );
    }

    /// A unit that ended abnormally sends no result.
    #[cfg(unix)]
    #[test]
    fn test_report_an_installation_without_a_result() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::Due(Installation::Installed {
                    hash: TARGET_HASH.parse().unwrap(),
                    result: None,
                }),
                &TestRegistry::new().registry
            ),
            "The installer sent no result for agent package fedcba9876543210, run with \
             --check-only to see whether the agent moved"
        );
    }

    #[cfg(unix)]
    #[test]
    fn test_report_a_package_nobody_could_install() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::Due(Installation::NoInstaller(TARGET_HASH.parse().unwrap())),
                &TestRegistry::new().registry
            ),
            "No installer socket is configured, agent package fedcba9876543210 is not \
             downloaded"
        );
    }

    #[cfg(unix)]
    #[test]
    fn test_a_failed_installation_fails_the_run() {
        let error = installation_outcome(&Installation::Installed {
            hash: TARGET_HASH.parse().unwrap(),
            result: Some(InstallResult {
                error: Some(String::from("Installing failed, exit status: 1")),
                ..a_result(false)
            }),
        })
        .unwrap_err();

        assert_eq!(error.to_string(), "Installing failed, exit status: 1");
    }

    #[cfg(unix)]
    #[test]
    fn test_a_successful_installation_passes_the_run() {
        assert!(installation_outcome(&Installation::Installed {
            hash: TARGET_HASH.parse().unwrap(),
            result: Some(a_result(true)),
        })
        .is_ok());
    }

    #[test]
    fn test_report_a_fetch_from_a_site_without_a_package() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::<Spooled>::NoPackage,
                &TestRegistry::new().registry
            ),
            "No agent package available for this host"
        );
    }

    #[test]
    fn test_report_a_fetch_of_an_agent_that_is_up_to_date() {
        assert_eq!(
            report_fetch(
                &FetchOutcome::<Spooled>::UpToDate(INSTALLED_HASH.parse().unwrap()),
                &TestRegistry::new().registry
            ),
            "Agent is up to date: 0123456789abcdef"
        );
    }

    /// A registry with a connection to each site, whose registration got the
    /// given answer about agent updates.
    fn registry_with(answers: &[(&str, AgentUpdateAuthorization)]) -> TestRegistry {
        let mut registry = TestRegistry::new();
        for (site, answer) in answers {
            registry.registry.register_connection(
                &ConnectionMode::Pull,
                &site.parse().unwrap(),
                TrustedConnectionWithRemote {
                    agent_update_authorization: *answer,
                    ..TrustedConnectionWithRemote::from(uuid::Uuid::new_v4())
                },
            );
        }
        registry
    }

    fn community_line(site: &str) -> String {
        no_agent_updates_message(&site.parse().unwrap(), NoAgentUpdates::CommunityEdition)
    }

    /// CMK-41723 AC4
    #[test]
    fn test_without_configuration_a_community_site_is_named() {
        let registry =
            registry_with(&[("server/site", AgentUpdateAuthorization::CommunityEdition)]);

        assert_eq!(
            report_without_updater(&registry.registry),
            format!(
                "Agent updates are not configured for this host.\n{}",
                community_line("server/site")
            )
        );
    }

    /// CMK-41723 AC5
    #[test]
    fn test_without_configuration_the_bakery_is_named() {
        let registry = registry_with(&[("server/site", AgentUpdateAuthorization::Unavailable)]);

        assert_eq!(
            report_without_updater(&registry.registry),
            format!("Agent updates are not configured for this host.\n{BAKERY_HINT}")
        );
    }

    /// CMK-41723 AC5
    #[test]
    fn test_without_configuration_an_unregistered_host_gets_the_bakery_named() {
        assert_eq!(
            report_without_updater(&TestRegistry::new().registry),
            format!("Agent updates are not configured for this host.\n{BAKERY_HINT}")
        );
    }

    /// CMK-41723 AC4, AC5
    #[test]
    fn test_without_configuration_one_site_with_agent_updates_keeps_the_bakery_named() {
        let registry = registry_with(&[
            (
                "server/community",
                AgentUpdateAuthorization::CommunityEdition,
            ),
            ("server/pro", AgentUpdateAuthorization::Authorized),
        ]);

        assert_eq!(
            report_without_updater(&registry.registry),
            format!(
                "Agent updates are not configured for this host.\n{}\n{BAKERY_HINT}",
                community_line("server/community")
            )
        );
    }

    /// CMK-41723 AC6
    #[test]
    fn test_report_an_updater_that_is_not_operational() {
        assert_eq!(
            report(
                CheckOutcome::NotPossible(Obstacle::NotOperational(String::from(
                    "Failed to load the agent info"
                ))),
                &TestRegistry::new().registry
            ),
            "No agent update is possible for this host: Failed to load the agent info"
        );
    }

    /// CMK-41723 AC6
    #[test]
    fn test_report_a_host_without_an_update_source() {
        let registry = registry_with(&[("server/site", AgentUpdateAuthorization::Unavailable)]);

        assert_eq!(
            report(
                CheckOutcome::NotPossible(Obstacle::NoSource),
                &registry.registry
            ),
            format!(
                "No agent update is possible for this host: no update source is recorded.\n\
                 {REGISTER_HINT}"
            )
        );
    }

    /// CMK-41723 AC6: a site that offers no agent updates must not hide that
    /// the other site may serve them.
    #[test]
    fn test_report_a_host_without_an_update_source_whose_other_site_may_serve_updates() {
        let registry = registry_with(&[
            (
                "server/community",
                AgentUpdateAuthorization::CommunityEdition,
            ),
            ("server/pro", AgentUpdateAuthorization::Authorized),
        ]);

        assert_eq!(
            report(
                CheckOutcome::NotPossible(Obstacle::NoSource),
                &registry.registry
            ),
            format!(
                "No agent update is possible for this host: no update source is recorded.\n\
                 {}\n{REGISTER_HINT}",
                community_line("server/community")
            )
        );
    }

    /// CMK-41723 AC6
    #[test]
    fn test_report_a_host_whose_registration_permits_no_agent_updates() {
        let registry = registry_with(&[("server/site", AgentUpdateAuthorization::NotPermitted)]);

        assert_eq!(
            report(
                CheckOutcome::NotPossible(Obstacle::NoSource),
                &registry.registry
            ),
            format!(
                "No agent update is possible for this host: no update source is recorded.\n{}",
                not_permitted_message(&"server/site".parse().unwrap())
            )
        );
    }

    /// CMK-41723 AC4
    #[test]
    fn test_report_a_host_without_an_update_source_at_a_community_site() {
        let registry =
            registry_with(&[("server/site", AgentUpdateAuthorization::CommunityEdition)]);

        assert_eq!(
            report(
                CheckOutcome::NotPossible(Obstacle::NoSource),
                &registry.registry
            ),
            format!(
                "No agent update is possible for this host: no update source is recorded.\n{}",
                community_line("server/site")
            )
        );
    }

    /// CMK-41723 AC6
    #[test]
    fn test_report_an_update_source_whose_connection_is_gone() {
        assert_eq!(
            report(
                CheckOutcome::NotPossible(Obstacle::SourceNotRegistered(
                    "8f0e3a1c-5b2d-4e6f-9a7b-0c1d2e3f4a5b".parse().unwrap()
                )),
                &TestRegistry::new().registry
            ),
            format!(
                "No agent update is possible for this host: the connection \
                 8f0e3a1c-5b2d-4e6f-9a7b-0c1d2e3f4a5b of the update source is no longer \
                 registered. {REGISTER_HINT}"
            )
        );
    }

    /// CMK-41723 AC4: the run that gets the statement of the site and the later
    /// runs print the same line.
    #[test]
    fn test_report_a_site_without_agent_updates_alike_in_every_run() {
        let site_id: SiteID = "server/site".parse().unwrap();
        let registry = TestRegistry::new();

        let first_run = report_fetch(
            &FetchOutcome::<Spooled>::SourceUnavailable {
                site_id: site_id.clone(),
                reason: NoAgentUpdates::CommunityEdition,
            },
            &registry.registry,
        );
        let later_run = report_fetch(
            &FetchOutcome::<Spooled>::NotPossible(Obstacle::NoAgentUpdates {
                site_id,
                reason: NoAgentUpdates::CommunityEdition,
            }),
            &registry.registry,
        );

        assert_eq!(first_run, community_line("server/site"));
        assert_eq!(later_run, first_run);
    }

    /// CMK-41723 AC4
    #[test]
    fn test_report_an_update_source_whose_site_has_no_license() {
        let site_id: SiteID = "server/site".parse().unwrap();
        let registry = TestRegistry::new();

        let checked = report(
            CheckOutcome::SourceUnavailable {
                site_id: site_id.clone(),
                reason: NoAgentUpdates::NotLicensed,
            },
            &registry.registry,
        );
        let fetched = report_fetch(
            &FetchOutcome::<Spooled>::SourceUnavailable {
                site_id,
                reason: NoAgentUpdates::NotLicensed,
            },
            &registry.registry,
        );

        assert_eq!(
            checked,
            "server/site: The license of this site does not include agent updates. This host \
             gets agent updates again once the license includes them."
        );
        assert_eq!(fetched, checked);
    }

    /// The update cycle against a mock of the site. The agent info of the
    /// single-directory deployment exists on Unix only.
    #[cfg(unix)]
    mod update_cycle {
        use super::*;
        use crate::agent_receiver_api::{
            AgentDownloadBody, AgentUpdate, ApiError, RegistrationStatusV2,
            RegistrationStatusV2Response, RegistrationStatusV2ResponseRegistered, UpdateStatusBody,
            UpdateStatusResponse,
        };
        use crate::config::test_helpers::TestRegistry;
        use crate::config::{ConnectionMode, JSONLoader, TrustedConnection, UpdaterRegistration};
        use crate::environment::SetupMode;
        use crate::modes::delete_connection;
        use crate::updater::{after_connection_changes, UpdateSource, UpdateState};
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
            ) -> AnyhowResult<agent_receiver_api::AgentPackageStream, ApiError> {
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

        /// A host in a single-directory deployment, whose update source is the
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
                    no_agent_updates: None,
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
                    None,
                    self.paths.setup_mode,
                )
            }

            /// The two steps of the `delete` mode, for the connection of the update source.
            fn delete_the_source_connection(&mut self) {
                delete_connection::delete(&mut self.registry.registry, SOURCE_UUID).unwrap();
                after_connection_changes(
                    &self.paths,
                    &[],
                    &UpdaterRegistration::default(),
                    None,
                    &self.registry.registry,
                )
                .unwrap();
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
            assert_eq!(
                failed_state.source.as_ref().unwrap().no_agent_updates,
                None,
                "{failed_state:?}"
            );
            assert!(retried.is_ok(), "{retried:?}");
            assert_eq!(
                first_silent_then_answering.reported_errors(),
                [None, Some(error)]
            );
            let state = host.state();
            assert_eq!(state.last_error, None);
            assert_eq!(state.source.unwrap().no_agent_updates, None);
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
                Err(ApiError::stating_no_agent_updates("community_edition")),
                no_package(),
            ]);

            let first = host.cycle(&first_501_then_upgraded);
            let second = host.cycle(&first_501_then_upgraded);

            assert!(first.is_ok(), "{first:?}");
            assert!(second.is_ok(), "{second:?}");
            assert_eq!(first_501_then_upgraded.reported_errors().len(), 1);
            assert_eq!(
                host.state().source.unwrap().no_agent_updates,
                Some(NoAgentUpdates::CommunityEdition)
            );
        }

        /// CMK-41723 AC3: only the statement of the site latches its source.
        #[test]
        fn test_a_501_without_a_statement_is_asked_again_by_the_next_cycle() {
            let host = Host::new();
            let first_501_then_answering = ScriptedApi::new(vec![
                Err(ApiError::ResponseStatus {
                    status: http::StatusCode::NOT_IMPLEMENTED,
                    body: Some(String::from(r#"{"detail": "Not Implemented"}"#)),
                }),
                no_package(),
            ]);

            let failed = host.cycle(&first_501_then_answering);
            let retried = host.cycle(&first_501_then_answering);

            assert!(failed.is_err(), "{failed:?}");
            assert!(retried.is_ok(), "{retried:?}");
            assert_eq!(host.state().source.unwrap().no_agent_updates, None);
        }

        /// CMK-41723 AC3
        #[test]
        fn test_a_site_without_the_license_is_asked_again_by_the_next_cycle() {
            let host = Host::new();
            let first_unlicensed_then_licensed = ScriptedApi::new(vec![
                Err(ApiError::stating_no_agent_updates("not_licensed")),
                no_package(),
            ]);

            let unlicensed = host.cycle(&first_unlicensed_then_licensed);
            let licensed = host.cycle(&first_unlicensed_then_licensed);

            assert!(unlicensed.is_ok(), "{unlicensed:?}");
            assert!(licensed.is_ok(), "{licensed:?}");
            assert_eq!(first_unlicensed_then_licensed.reported_errors().len(), 2);
            assert_eq!(host.state().source.unwrap().no_agent_updates, None);
        }

        /// TC-AU-025: a removed TLS registration is refused with 403
        #[test]
        fn test_a_refusal_with_403_is_recorded_and_keeps_the_source() {
            let host = Host::new();
            let refusing = ScriptedApi::new(vec![Err(ApiError::ResponseStatus {
                status: http::StatusCode::FORBIDDEN,
                body: Some(String::from(r#"{"detail": "Host is not registered"}"#)),
            })]);

            let refused = host.cycle(&refusing);

            assert!(refused.is_err(), "{refused:?}");
            let state = host.state();
            let error = state.last_error.unwrap_or_default();
            assert!(
                error.contains("403 Forbidden: Host is not registered"),
                "{error:?}"
            );
            assert_eq!(
                state.source,
                Some(UpdateSource {
                    uuid: SOURCE_UUID.parse().unwrap(),
                    no_agent_updates: None,
                })
            );
        }

        /// TC-AU-078: after `cmk-agent-ctl delete`, the host has no update source and no
        /// error against one
        #[test]
        fn test_a_deleted_source_connection_leaves_no_source_and_no_error() {
            let mut host = Host::new();
            UpdateState {
                last_error: Some(String::from(
                    "Agent update status request to server/site failed",
                )),
                ..host.state()
            }
            .save(&host.paths.updater_state_path)
            .unwrap();
            let site = ScriptedApi::new(vec![]);

            host.delete_the_source_connection();
            let cycle = host.cycle(&site);

            assert!(cycle.is_ok(), "{cycle:?}");
            assert!(site.reported_errors().is_empty());
            let state = host.state();
            assert_eq!(state.source, None);
            assert_eq!(state.last_error, None);
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
