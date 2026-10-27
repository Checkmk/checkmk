// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Configuration and state of the agent updater integrated into the agent
//! controller.
//!
//! The integrated updater is offered for the single-directory agent deployment
//! only - a host in the multi-directory layout keeps the Python updater. The
//! files are located by [`crate::environment::PathResolver`].
//!
//! Three artifacts make up the model:
//!
//! * [`UpdaterConfig`] - baked by the site, read-only for the controller. Its
//!   absence means that agent updates are not configured for this host.
//! * [`UpdateState`] - owned and written by the controller.
//! * [`AgentInfo`] - part of the installed agent package, read-only for the
//!   controller.
//!
//! [`Updater`] loads the three of them together and is the entry point of the
//! updater: [`Updater::handle_update_cycle`].
//!
//! [`InstallRequest`] is not one of them: it is what the controller hands to
//! the privileged install step of Linux, which is a process of its own.
//!
//! [`python_updater`] registers the Python updater, which the controller runs
//! as a subprocess. It shares no code with the integrated updater, and
//! [`after_connection_changes`] is the only place that calls it.

mod backend;
mod connection;
mod install;
mod python_updater;
mod verification;
use crate::config::{Registry, UpdaterRegistration};
use crate::modes::registration::AddedConnection;
use anyhow::Result as AnyhowResult;
#[cfg(unix)]
pub use backend::InstallOutcome;
pub use backend::{
    AgentInfo, CheckOutcome, FetchOutcome, SignatureCheck, UpdateSource, UpdateState, Updater,
    UpdaterConfig, WritableUpdater,
};
pub use install::{InstallRequest, InstallResult, TrustAnchors};
pub use python_updater::PythonUpdater;

/// The steps after a run that changed the registered connections.
///
/// The Python updater, if the package ships one, is registered for every
/// connection of `added_connections`. These registrations don't depend on each
/// other, so a failing one doesn't stop the others.
///
/// # Errors
///
/// The first error. Later ones are logged.
pub fn after_connection_changes(
    added_connections: &[AddedConnection],
    updater_registration: &UpdaterRegistration,
    python_updater: Option<&PythonUpdater>,
    registry: &Registry,
) -> AnyhowResult<()> {
    let mut outcome = Ok(());
    for connection in added_connections {
        let Some(python_updater) = python_updater else {
            log::info!(
                "Agent updates are handled by the controller, skipping updater registration."
            );
            continue;
        };
        let registered =
            python_updater::register(python_updater, connection, updater_registration, registry);
        keep_first_error(&mut outcome, registered);
    }
    outcome
}

fn keep_first_error(outcome: &mut AnyhowResult<()>, result: AnyhowResult<()>) {
    if let Err(error) = result {
        if outcome.is_ok() {
            *outcome = Err(error);
        } else {
            log::error!("{error:#}");
        }
    }
}

#[cfg(windows)]
mod platform;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;
    use crate::types::Credentials;

    fn connection() -> AddedConnection {
        AddedConnection {
            uuid: uuid::Uuid::new_v4(),
            credentials: Credentials::username_password("user", "password"),
        }
    }

    /// CMK-39588 AC8
    #[test]
    fn test_without_a_python_updater_nothing_is_registered() {
        assert!(after_connection_changes(
            &[connection()],
            &UpdaterRegistration::Overwrite,
            None,
            &TestRegistry::new().registry,
        )
        .is_ok());
    }

    /// CMK-39588 AC8: the registration of the Python updater looks up the
    /// connection in the registry first, which fails in an empty registry.
    #[test]
    fn test_a_shipped_python_updater_is_not_skipped() {
        let error = after_connection_changes(
            &[connection()],
            &UpdaterRegistration::Overwrite,
            Some(&PythonUpdater::at("cmk-update-agent")),
            &TestRegistry::new().registry,
        )
        .unwrap_err();

        assert!(format!("{error:#}").contains("No registered connection has the UUID"));
    }
}
