// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Choice of the registered connection that may carry the agent updates.
//!
//! The updater has no connection of its own. It reuses what the controller is
//! registered with, so there is no separate registration and no shared secret
//! on the host - the receiver authenticates the host by the client certificate
//! of the connection, whose common name is the connection's UUID.

use crate::config::{ConnectionMode, Registry, TrustedConnectionWithRemote};
use crate::site_spec::SiteID;

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
