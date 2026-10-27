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
mod source;
mod verification;
use crate::config::{Registry, UpdaterRegistration};
use crate::environment::PathResolver;
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

/// The steps after a run that changed the registered connections, one per
/// agent updater:
///
/// 1. Integrated updater: the update source follows the registered
///    connections.
/// 2. Python updater: if the package ships one, it is registered for one of
///    `added_connections`.
///
/// `added_connections` are the connections that the run added, in order.
/// `registry` is the registry as the run left it. The two steps don't depend on
/// each other, so a failing one doesn't stop the other.
///
/// # Errors
///
/// The error of the first step, or else the one of the second. When both fail,
/// the second one is logged.
pub fn after_connection_changes(
    paths: &PathResolver,
    added_connections: &[AddedConnection],
    updater_registration: &UpdaterRegistration,
    python_updater: Option<&PythonUpdater>,
    registry: &Registry,
) -> AnyhowResult<()> {
    let reconciled =
        Updater::determine_source(paths, added_connections, updater_registration, registry);
    let registered = python_updater::register(
        python_updater,
        added_connections,
        updater_registration,
        registry,
    );
    if let (Err(_), Err(error)) = (&reconciled, &registered) {
        log::error!("{error:#}");
    }
    reconciled.and(registered)
}

#[cfg(windows)]
mod platform;

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent_receiver_api::AgentUpdateAuthorization;
    use crate::config::test_helpers::TestRegistry;
    use crate::config::JSONLoader;
    use crate::environment::SetupMode;

    fn connection() -> AddedConnection {
        AddedConnection::new(uuid::Uuid::new_v4(), AgentUpdateAuthorization::Authorized)
    }

    /// CMK-39588 AC8
    #[test]
    fn test_without_a_python_updater_nothing_is_registered() {
        let dir = tempfile::TempDir::new().unwrap();

        assert!(after_connection_changes(
            &PathResolver::new(SetupMode::Classic, dir.path()),
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
        let dir = tempfile::TempDir::new().unwrap();

        let error = after_connection_changes(
            &PathResolver::new(SetupMode::Classic, dir.path()),
            &[connection()],
            &UpdaterRegistration::Overwrite,
            Some(&PythonUpdater::at("cmk-update-agent")),
            &TestRegistry::new().registry,
        )
        .unwrap_err();

        assert!(format!("{error:#}").contains("No registered connection has the UUID"));
    }

    /// Without the connections in the registry, every registration of the Python
    /// updater fails at the lookup. The error names the UUID of the last attempt.
    #[test]
    fn test_keep_falls_back_to_the_next_connection() {
        let dir = tempfile::TempDir::new().unwrap();
        let (first, next) = (connection(), connection());
        let (first_uuid, next_uuid) = (first.uuid.to_string(), next.uuid.to_string());

        let error = after_connection_changes(
            &PathResolver::new(SetupMode::Classic, dir.path()),
            &[first, next],
            &UpdaterRegistration::Keep,
            Some(&PythonUpdater::at("cmk-update-agent")),
            &TestRegistry::new().registry,
        )
        .unwrap_err();

        let error = format!("{error:#}");
        assert!(error.contains(&next_uuid));
        assert!(!error.contains(&first_uuid));
    }

    /// See `test_keep_falls_back_to_the_next_connection`.
    #[test]
    fn test_overwrite_falls_back_to_the_previous_connection() {
        let dir = tempfile::TempDir::new().unwrap();
        let (previous, last) = (connection(), connection());
        let (previous_uuid, last_uuid) = (previous.uuid.to_string(), last.uuid.to_string());

        let error = after_connection_changes(
            &PathResolver::new(SetupMode::Classic, dir.path()),
            &[previous, last],
            &UpdaterRegistration::Overwrite,
            Some(&PythonUpdater::at("cmk-update-agent")),
            &TestRegistry::new().registry,
        )
        .unwrap_err();

        let error = format!("{error:#}");
        assert!(error.contains(&previous_uuid));
        assert!(!error.contains(&last_uuid));
    }

    /// CMK-39588 AC8
    #[test]
    fn test_the_source_is_recorded_although_the_python_updater_fails() {
        let dir = tempfile::TempDir::new().unwrap();
        let paths = PathResolver::new(SetupMode::Classic, dir.path());
        let connection = connection();
        let uuid = connection.uuid;

        // Without the connection in the registry, the Python updater fails at the lookup.
        let _ = after_connection_changes(
            &paths,
            &[connection],
            &UpdaterRegistration::Overwrite,
            Some(&PythonUpdater::at("cmk-update-agent")),
            &TestRegistry::new().registry,
        );

        assert_eq!(
            UpdateState::load(&paths.updater_state_path)
                .unwrap()
                .source
                .unwrap()
                .uuid,
            uuid
        );
    }
}
