// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `update` mode: the agent update of this host, driven from the command
//! line instead of by the controller itself.

use crate::agent_receiver_api;
use crate::configuration::config::{ClientConfig, Registry};
use crate::updater::{CheckOutcome, Updater};
use anyhow::{bail, Result as AnyhowResult};

/// Report which agent package the site has for this host.
///
/// # Errors
///
/// If anything but a check is asked for - installing an agent from the
/// controller is not implemented yet - or if the site cannot be asked.
pub fn update(
    updater: &Updater,
    registry: &Registry,
    client_config: &ClientConfig,
    check_only: bool,
) -> AnyhowResult<()> {
    if !check_only {
        bail!("Installing an agent update is not implemented yet, use --check-only");
    }
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    println!("{}", report(updater.check(registry, &api)?));
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
}
