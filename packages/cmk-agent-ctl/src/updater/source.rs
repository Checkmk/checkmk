// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Which registered connection serves the agent updates of this host (TD 4.4).
//!
//! The update source follows the registered connections. Every run that
//! changes them ends with one call of [`super::after_connection_changes`],
//! which sees the registry as the run left it.

use super::backend::UpdateSource;
use crate::agent_receiver_api::AgentUpdateAuthorization;
use crate::config::{Registry, UpdaterRegistration};
use crate::modes::registration::AddedConnection;
use crate::site_spec::SiteID;
use log::Level;

/// The update source after a run that changed the registered connections.
///
/// The recorded source counts only while the registry holds its UUID: the run
/// may have deleted or replaced its connection.
///
/// # Arguments
///
/// * `recorded` - the source in the update state
/// * `added_connections` - the connections this run registered, in order
/// * `updater_registration` - the Registration option of this run
/// * `registry` - the registry as the run left it
pub fn determine_update_source(
    recorded: Option<&UpdateSource>,
    added_connections: &[AddedConnection],
    updater_registration: &UpdaterRegistration,
    registry: &Registry,
) -> Option<UpdateSource> {
    let current = recorded
        .filter(|source| {
            registry
                .retrieve_standard_connection_by_uuid(&source.uuid)
                .is_some()
        })
        .cloned();
    let mut candidates = added_connections
        .iter()
        .filter(|connection| {
            connection.agent_update_authorization == AgentUpdateAuthorization::Authorized
        })
        .map(|connection| UpdateSource {
            uuid: connection.uuid,
            // Only the site, by answering 501, can say that it serves no agent updates.
            available: true,
        });
    match updater_registration {
        UpdaterRegistration::Overwrite => candidates.next_back().or(current),
        UpdaterRegistration::Keep => current.or_else(|| candidates.next()),
        UpdaterRegistration::Manual => current,
    }
}

/// Log what a registration means for agent updates.
///
/// A missing permission is a warning only where the registration could have
/// become the source.
pub fn report(
    connection: &AddedConnection,
    updater_registration: &UpdaterRegistration,
    registry: &Registry,
) {
    let Some(site_id) = registry.retrieve_standard_connection_by_uuid(&connection.uuid) else {
        return;
    };
    match connection.agent_update_authorization {
        AgentUpdateAuthorization::Authorized => {}
        AgentUpdateAuthorization::NotPermitted => {
            let level = match updater_registration {
                UpdaterRegistration::Manual => Level::Info,
                UpdaterRegistration::Keep | UpdaterRegistration::Overwrite => Level::Warn,
            };
            log::log!(level, "{}", not_permitted_message(&site_id));
        }
        AgentUpdateAuthorization::Unavailable => log::info!(
            "The site {} reported no decision about agent updates for this registration. \
             Connection {} does not become the update source.",
            site_id,
            connection.uuid
        ),
    }
}

fn not_permitted_message(site_id: &SiteID) -> String {
    format!(
        "The registration at {site_id} permits no agent updates. The registering user needs \
         the permission \"Enable agent updates on all hosts & download all monitoring agents\" \
         (wato.download_all_agents), or \"Enable agent updates on hosts & download monitoring \
         agents\" (wato.download_agents) as a contact of this host. This connection does not \
         become the update source."
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;
    use crate::config::ConnectionMode;
    use std::str::FromStr;

    const RECORDED: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a01";
    const FIRST: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a02";
    const SECOND: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a03";

    fn source(uuid: &str) -> UpdateSource {
        UpdateSource {
            uuid: uuid::Uuid::from_str(uuid).unwrap(),
            available: true,
        }
    }

    fn connection(uuid: &str, authorization: AgentUpdateAuthorization) -> AddedConnection {
        AddedConnection::new(uuid::Uuid::from_str(uuid).unwrap(), authorization)
    }

    fn authorized(uuid: &str) -> AddedConnection {
        connection(uuid, AgentUpdateAuthorization::Authorized)
    }

    /// A registry holding one connection per UUID, each at a site of its own.
    fn registry_holding(uuids: &[&str]) -> TestRegistry {
        uuids
            .iter()
            .enumerate()
            .fold(TestRegistry::new(), |registry, (index, uuid)| {
                registry.add_connection(
                    &ConnectionMode::Pull,
                    &format!("server/site-{index}"),
                    *uuid,
                )
            })
    }

    /// CMK-39588 AC1
    #[test]
    fn test_a_registration_without_the_permission_is_no_candidate() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[connection(FIRST, AgentUpdateAuthorization::NotPermitted)],
                &UpdaterRegistration::Overwrite,
                &registry_holding(&[RECORDED, FIRST]).registry,
            ),
            Some(source(RECORDED))
        );
    }

    /// CMK-39588 AC1
    #[test]
    fn test_a_registration_without_a_decision_is_no_candidate() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[connection(FIRST, AgentUpdateAuthorization::Unavailable)],
                &UpdaterRegistration::Overwrite,
                &registry_holding(&[RECORDED, FIRST]).registry,
            ),
            Some(source(RECORDED))
        );
    }

    /// CMK-39588 AC2
    #[test]
    fn test_keep_leaves_a_registered_source() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[authorized(FIRST)],
                &UpdaterRegistration::Keep,
                &registry_holding(&[RECORDED, FIRST]).registry,
            ),
            Some(source(RECORDED))
        );
    }

    /// CMK-39588 AC2, AC6
    #[test]
    fn test_keep_takes_the_first_registration_without_a_source() {
        assert_eq!(
            determine_update_source(
                None,
                &[authorized(FIRST), authorized(SECOND)],
                &UpdaterRegistration::Keep,
                &registry_holding(&[FIRST, SECOND]).registry,
            ),
            Some(source(FIRST))
        );
    }

    /// CMK-39588 AC2, AC6
    #[test]
    fn test_overwrite_takes_the_last_registration() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[authorized(FIRST), authorized(SECOND)],
                &UpdaterRegistration::Overwrite,
                &registry_holding(&[RECORDED, FIRST, SECOND]).registry,
            ),
            Some(source(SECOND))
        );
    }

    /// CMK-39588 AC2
    #[test]
    fn test_manual_leaves_the_source_alone() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[authorized(FIRST)],
                &UpdaterRegistration::Manual,
                &registry_holding(&[RECORDED, FIRST]).registry,
            ),
            Some(source(RECORDED))
        );
    }

    /// CMK-39588 AC3: the registration replaced the connection of the source, so
    /// the registry no longer holds the recorded UUID.
    #[test]
    fn test_keep_takes_the_registration_that_replaced_the_source() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[authorized(FIRST)],
                &UpdaterRegistration::Keep,
                &registry_holding(&[FIRST]).registry,
            ),
            Some(source(FIRST))
        );
    }

    #[test]
    fn test_a_source_whose_connection_is_gone_is_dropped() {
        assert_eq!(
            determine_update_source(
                Some(&source(RECORDED)),
                &[],
                &UpdaterRegistration::Manual,
                &registry_holding(&[]).registry,
            ),
            None
        );
    }

    /// CMK-39588 AC5, the text of the message only.
    #[test]
    fn test_the_refusal_names_the_missing_permissions() {
        let message = not_permitted_message(&SiteID::from_str("server/site").unwrap());

        assert!(message.contains("wato.download_all_agents"));
        assert!(message.contains("wato.download_agents"));
    }
}
