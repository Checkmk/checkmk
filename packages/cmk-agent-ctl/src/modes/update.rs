// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `update` mode: the agent update of this host, driven from the command
//! line instead of by the controller itself.

use crate::agent_receiver_api;
use crate::configuration::config::{ClientConfig, Registry};
use crate::updater::{CheckOutcome, FetchOutcome, Updater};
use anyhow::Result as AnyhowResult;

/// Fetch the agent package the site has for this host, or only report it.
///
/// Without `check_only` the package is downloaded and, once its signature has
/// been checked, spooled for the installer. Installing it is not implemented
/// yet, so the run ends with the package waiting on disk.
///
/// # Errors
///
/// If the site cannot be asked, does not deliver the package it offered, or if
/// the package fails verification or cannot be spooled.
pub fn update(
    updater: &Updater,
    registry: &Registry,
    client_config: &ClientConfig,
    check_only: bool,
) -> AnyhowResult<()> {
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    println!(
        "{}",
        if check_only {
            report(updater.check(registry, &api)?)
        } else {
            report_fetch(updater.fetch_update(registry, &api)?)
        }
    );
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
    }
}

/// The outcome of a fetch in the one line the mode prints.
///
/// The package stops at the spool directory: whoever installs it is a
/// privileged process, and that step does not exist yet. Naming the file is
/// therefore the whole result, not a detail.
///
/// The two outcomes that end without a package read as they do in [`report`]:
/// the same situation must not be worded by whether `--check-only` was passed.
fn report_fetch(outcome: FetchOutcome) -> String {
    match outcome {
        FetchOutcome::NotPossible => {
            String::from("No agent update is possible for this host, run with -v for the reason")
        }
        FetchOutcome::NoPackage => String::from("No agent package available for this host"),
        FetchOutcome::UpToDate(hash) => format!("Agent is up to date: {hash}"),
        FetchOutcome::Spooled { hash, path } => format!(
            "Verified agent package {hash} is ready at {}; installing it is not implemented yet",
            path.display()
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
            report_fetch(FetchOutcome::Spooled {
                hash: TARGET_HASH.parse().unwrap(),
                path: std::path::PathBuf::from("/spool/fedcba9876543210.deb"),
            }),
            "Verified agent package fedcba9876543210 is ready at \
             /spool/fedcba9876543210.deb; installing it is not implemented yet"
        );
    }

    #[test]
    fn test_report_a_fetch_from_a_site_without_a_package() {
        assert_eq!(
            report_fetch(FetchOutcome::NoPackage),
            "No agent package available for this host"
        );
    }

    #[test]
    fn test_report_a_fetch_of_an_agent_that_is_up_to_date() {
        assert_eq!(
            report_fetch(FetchOutcome::UpToDate(INSTALLED_HASH.parse().unwrap())),
            "Agent is up to date: 0123456789abcdef"
        );
    }

    #[test]
    fn test_report_a_fetch_that_could_not_be_made() {
        assert_eq!(
            report_fetch(FetchOutcome::NotPossible),
            "No agent update is possible for this host, run with -v for the reason"
        );
    }
}
