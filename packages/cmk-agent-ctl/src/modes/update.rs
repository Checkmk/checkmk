// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The `update` mode: the agent update of this host, driven from the command
//! line instead of by the controller itself.

use crate::agent_receiver_api;
use crate::configuration::config::{ClientConfig, Registry};
#[cfg(unix)]
use crate::updater::InstallOutcome;
use crate::updater::{CheckOutcome, FetchOutcome, SignatureCheck, Updater};
use anyhow::Result as AnyhowResult;
#[cfg(unix)]
use std::path::Path;

/// Ask the site which agent package it has for this host, and report it.
///
/// # Errors
///
/// If the site cannot be asked.
pub fn check(
    updater: &Updater,
    registry: &Registry,
    client_config: &ClientConfig,
) -> AnyhowResult<()> {
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
/// here and refused there.
///
/// # Errors
///
/// If the site cannot be asked, does not deliver the package it offered, if
/// the package fails verification or cannot be spooled, or if the installer
/// cannot be reached.
pub fn update(
    updater: &Updater,
    registry: &Registry,
    client_config: &ClientConfig,
    signature: SignatureCheck,
) -> AnyhowResult<()> {
    let api = agent_receiver_api::Api {
        use_proxy: client_config.use_proxy,
    };
    let fetched = updater.fetch_update(registry, &api, signature)?;
    println!("{}", report_fetch(&fetched));
    #[cfg(unix)]
    if let FetchOutcome::Spooled {
        path, signatures, ..
    } = &fetched
    {
        let outcome = updater.install_update(path, signatures)?;
        println!("{}", report_install(outcome, path));
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
}
