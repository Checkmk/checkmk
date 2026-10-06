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

mod backend;
mod connection;
pub use backend::{AgentInfo, UpdatePackage, UpdateState, Updater, UpdaterConfig};

#[cfg(windows)]
mod platform;
