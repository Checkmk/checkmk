// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Choice of the registered connection that may carry the agent updates.
//!
//! The updater has no connection of its own. It reuses what the controller is
//! registered with, so there is no separate registration and no shared secret
//! on the host - the receiver authenticates the host by the client certificate
//! of the connection, whose common name is the connection's UUID.

use super::legacy_registration::LegacyRegistration;
use crate::agent_receiver_api::{RegistrationStatusV2, RegistrationStatusV2Response};
use crate::config::{ConnectionMode, Registry, TrustedConnectionWithRemote};
use crate::site_spec::{self, SiteID};
use anyhow::{bail, Result as AnyhowResult};

/// A registered connection considered for agent updates.
pub struct UpdateConnection<'a> {
    pub mode: ConnectionMode,
    pub site_id: &'a SiteID,
    pub connection: &'a TrustedConnectionWithRemote,
}

/// The registered connections that can reach a site, in no particular order.
pub(super) fn candidates(registry: &Registry) -> impl Iterator<Item = UpdateConnection<'_>> {
    let push = registry
        .get_push_connections()
        .map(|(site_id, connection)| UpdateConnection {
            mode: ConnectionMode::Push,
            site_id,
            connection,
        });
    let pull = registry
        .get_standard_pull_connections()
        .map(|(site_id, connection)| UpdateConnection {
            mode: ConnectionMode::Pull,
            site_id,
            connection,
        });
    push.chain(pull)
}

/// The registered connection that carries `uuid`, the UUID of the update source.
///
/// The registration recorded which connection serves the updates, so there is
/// nothing to choose: the source's UUID names it.
///
/// # Returns
///
/// `None` if no registered connection carries `uuid` anymore, for example after
/// the connection was deleted or replaced by a new registration.
pub fn select(registry: &Registry, uuid: uuid::Uuid) -> Option<UpdateConnection<'_>> {
    candidates(registry).find(|candidate| candidate.connection.trust.uuid == uuid)
}

/// The connection that `registration` was made for, which the migration
/// proves it through: its server and site are the ones of the
/// registration, verbatim, as the controller passes them on to the Python
/// updater (CMK-18329), and its site has registered this host under the same
/// name.
///
/// # Errors
///
/// If no connection matches. The error says what each asked site answered.
pub(super) fn migration_candidate<'a>(
    registry: &'a Registry,
    registration: &LegacyRegistration,
    api: &impl RegistrationStatusV2,
) -> AnyhowResult<UpdateConnection<'a>> {
    let (matching, others): (Vec<_>, Vec<_>) = candidates(registry).partition(|candidate| {
        candidate.site_id.server == registration.server
            && candidate.site_id.site == registration.site
    });
    if matching.is_empty() {
        if others.is_empty() {
            bail!(
                "Could not migrate {registration}: the controller has no registered connection \
                 to migrate it through"
            );
        }
        bail!(
            "Could not migrate {registration}: no registered connection is to {}/{}",
            registration.server,
            registration.site
        );
    }
    let (knowing, not_knowing): (Vec<_>, Vec<_>) = host_names(matching, api)
        .into_iter()
        .partition(|(_, answer)| knows_the_host(answer, registration));
    match knowing.into_iter().next() {
        Some((candidate, _)) => Ok(candidate),
        None => bail!(
            "Could not migrate {registration}: {}",
            described(&not_knowing)
        ),
    }
}

/// A connection, and the host name that its site has registered its UUID for.
type HostNameAnswer<'a> = (UpdateConnection<'a>, AnyhowResult<Option<String>>);

fn host_names<'a>(
    connections: Vec<UpdateConnection<'a>>,
    api: &impl RegistrationStatusV2,
) -> Vec<HostNameAnswer<'a>> {
    connections
        .into_iter()
        .map(|connection| {
            let answer = registered_host_name(connection.site_id, connection.connection, api);
            (connection, answer)
        })
        .collect()
}

fn knows_the_host(
    answer: &AnyhowResult<Option<String>>,
    registration: &LegacyRegistration,
) -> bool {
    matches!(answer, Ok(Some(host_name)) if *host_name == registration.host_name)
}

fn described(answers: &[HostNameAnswer<'_>]) -> String {
    answers
        .iter()
        .map(|(connection, answer)| match answer {
            Ok(Some(host_name)) => {
                format!("{} registered this host as {host_name}", connection.site_id)
            }
            Ok(None) => format!(
                "{} has no registration of this connection",
                connection.site_id
            ),
            Err(error) => format!(
                "could not ask {} for the host name of its connection: {error:#}",
                connection.site_id
            ),
        })
        .collect::<Vec<_>>()
        .join("; ")
}

pub(super) fn registered_host_name(
    site_id: &SiteID,
    connection: &TrustedConnectionWithRemote,
    api: &impl RegistrationStatusV2,
) -> AnyhowResult<Option<String>> {
    let url = site_spec::make_site_url(site_id, &connection.receiver_port)?;
    Ok(match api.registration_status_v2(&url, &connection.trust)? {
        RegistrationStatusV2Response::Registered(registered) => Some(registered.hostname),
        RegistrationStatusV2Response::NotRegistered => None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;

    const UUID_ALPHA: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a01";
    const UUID_BETA: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a02";
    const UUID_IMPORTED: &str = "2da62f8f-9e4a-4b1b-8b3a-1c1a0b0f1a03";

    #[test]
    fn test_select_without_connections() {
        assert!(select(&TestRegistry::new().registry, uuid_of(UUID_ALPHA)).is_none());
    }

    #[test]
    fn test_select_skips_imported_connections() {
        let registry = TestRegistry::new().add_imported_connection(UUID_IMPORTED);

        assert!(select(&registry.registry, uuid_of(UUID_IMPORTED)).is_none());
    }

    #[test]
    fn test_select_push_connection() {
        let registry =
            TestRegistry::new().add_connection(&ConnectionMode::Push, "server/site", UUID_ALPHA);

        let selected = select(&registry.registry, uuid_of(UUID_ALPHA)).unwrap();

        assert_eq!(selected.mode, ConnectionMode::Push);
        assert_eq!(selected.site_id.to_string(), "server/site");
        assert_eq!(selected.connection.trust.uuid.to_string(), UUID_ALPHA);
    }

    #[test]
    fn test_select_pull_connection() {
        let registry =
            TestRegistry::new().add_connection(&ConnectionMode::Pull, "server/site", UUID_ALPHA);

        let selected = select(&registry.registry, uuid_of(UUID_ALPHA)).unwrap();

        assert_eq!(selected.mode, ConnectionMode::Pull);
        assert_eq!(selected.site_id.to_string(), "server/site");
    }

    /// The source decides, not a ranking: its push connection is taken although
    /// a pull connection is registered as well.
    #[test]
    fn test_select_takes_the_connection_of_the_source() {
        let registry = TestRegistry::new()
            .add_connection(&ConnectionMode::Push, "server-a/site", UUID_ALPHA)
            .add_connection(&ConnectionMode::Pull, "server-b/site", UUID_BETA);

        let selected = select(&registry.registry, uuid_of(UUID_ALPHA)).unwrap();

        assert_eq!(selected.site_id.to_string(), "server-a/site");
    }

    #[test]
    fn test_select_without_the_connection_of_the_source() {
        let registry =
            TestRegistry::new().add_connection(&ConnectionMode::Pull, "server/site", UUID_BETA);

        assert!(select(&registry.registry, uuid_of(UUID_ALPHA)).is_none());
    }

    #[test]
    fn test_candidates_counts_only_addressable_connections() {
        let registry = TestRegistry::new()
            .add_connection(&ConnectionMode::Push, "server/push-site", UUID_ALPHA)
            .add_connection(&ConnectionMode::Pull, "server/pull-site", UUID_BETA)
            .add_imported_connection(UUID_IMPORTED);

        assert_eq!(candidates(&registry.registry).count(), 2);
    }

    fn uuid_of(uuid: &str) -> uuid::Uuid {
        uuid::Uuid::parse_str(uuid).unwrap()
    }
}
