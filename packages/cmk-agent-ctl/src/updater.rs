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
use crate::config::{ClientConfig, Registry, UpdaterRegistration};
use crate::modes::registration::AddedConnection;
use crate::AgentUpdater;
use anyhow::Result as AnyhowResult;
#[cfg(unix)]
pub use backend::InstallOutcome;
pub use backend::{
    AgentInfo, CheckOutcome, FetchOutcome, SignatureCheck, UpdateSource, UpdateState, Updater,
    UpdaterConfig, WritableUpdater,
};
pub use install::{InstallRequest, InstallResult, TrustAnchors};
pub(crate) use python_updater::get_agent_updater_executable;

/// The steps after a run that changed the registered connections.
///
/// The Python updater is registered for every connection of
/// `added_connections`. These registrations don't depend on each other, so a
/// failing one doesn't stop the others.
///
/// # Errors
///
/// The first error. Later ones are logged.
pub fn after_connection_changes(
    added_connections: &[AddedConnection],
    updater_registration: &UpdaterRegistration,
    agent_updater: AgentUpdater,
    client_config: &ClientConfig,
    registry: &Registry,
) -> AnyhowResult<()> {
    let mut outcome = Ok(());
    for connection in added_connections {
        if matches!(agent_updater, AgentUpdater::Integrated) {
            log::info!(
                "Agent updates are handled by the controller, skipping updater registration."
            );
            continue;
        }
        let registered =
            python_updater::register(connection, updater_registration, client_config, registry);
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
