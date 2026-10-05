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

// TODO(sk): API(function signature) will be changed in the future, for now it is simplified
/// Select the connection to use for agent updates.
///
/// A host may be registered at several sites while only one of them bakes its
/// agent, and nothing in the registry says which. The choice is therefore
/// arbitrary - but it must not be *random*: the registry keeps its connections
/// in hash maps, whose iteration order is seeded per process and differs
/// between runs of the same binary on the same host. Ranking the candidates by
/// mode and site makes consecutive runs agree on one site, which is what turns
/// a silent coin flip into something an operator can observe and correct.
///
/// A pull connection outranks a push one. That order is a convention rather
/// than a constraint - the receiver serves both alike - but it has to be
/// written down somewhere to be reproducible.
///
/// # Returns
///
/// `None` if the host has no connection that can reach a site, in which case no
/// update is possible.
pub fn select(registry: &Registry) -> Option<UpdateConnection<'_>> {
    candidates(registry).min_by(|left, right| order_key(left).cmp(&order_key(right)))
}

/// Rank of a candidate: pull before push, then by site.
fn order_key<'a>(candidate: &UpdateConnection<'a>) -> (u8, &'a str, &'a str) {
    let mode_rank = match &candidate.mode {
        ConnectionMode::Pull => 0,
        ConnectionMode::Push => 1,
    };
    (
        mode_rank,
        &candidate.site_id.server,
        &candidate.site_id.site,
    )
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
        assert!(select(&TestRegistry::new().registry).is_none());
    }

    #[test]
    fn test_select_skips_imported_connections() {
        let registry = TestRegistry::new().add_imported_connection(UUID_IMPORTED);

        assert!(select(&registry.registry).is_none());
    }

    #[test]
    fn test_select_push_connection() {
        let registry =
            TestRegistry::new().add_connection(&ConnectionMode::Push, "server/site", UUID_ALPHA);

        let selected = select(&registry.registry).unwrap();

        assert_eq!(selected.mode, ConnectionMode::Push);
        assert_eq!(selected.site_id.to_string(), "server/site");
        assert_eq!(selected.connection.trust.uuid.to_string(), UUID_ALPHA);
    }

    #[test]
    fn test_select_pull_connection() {
        let registry =
            TestRegistry::new().add_connection(&ConnectionMode::Pull, "server/site", UUID_ALPHA);

        let selected = select(&registry.registry).unwrap();

        assert_eq!(selected.mode, ConnectionMode::Pull);
        assert_eq!(selected.site_id.to_string(), "server/site");
    }

    /// A pull connection is taken even when a push connection points at a site
    /// that sorts first: the mode outranks the site.
    #[test]
    fn test_select_prefers_pull_over_push() {
        let registry = TestRegistry::new()
            .add_connection(&ConnectionMode::Push, "server-a/site", UUID_ALPHA)
            .add_connection(&ConnectionMode::Pull, "server-b/site", UUID_BETA);

        let selected = select(&registry.registry).unwrap();

        assert_eq!(selected.mode, ConnectionMode::Pull);
        assert_eq!(selected.site_id.to_string(), "server-b/site");
    }

    /// The same set of sites has to yield the same choice regardless of the
    /// order the connections were registered in.
    #[test]
    fn test_select_is_independent_of_registration_order() {
        let first = TestRegistry::new()
            .add_connection(&ConnectionMode::Pull, "server-b/site", UUID_ALPHA)
            .add_connection(&ConnectionMode::Pull, "server-a/site", UUID_BETA);
        let second = TestRegistry::new()
            .add_connection(&ConnectionMode::Pull, "server-a/site", UUID_BETA)
            .add_connection(&ConnectionMode::Pull, "server-b/site", UUID_ALPHA);

        assert_eq!(
            select(&first.registry).unwrap().site_id.to_string(),
            "server-a/site"
        );
        assert_eq!(
            select(&second.registry).unwrap().site_id.to_string(),
            "server-a/site"
        );
    }

    /// Sites on one server are told apart by the site name.
    #[test]
    fn test_select_orders_by_site_name_within_a_server() {
        let registry = TestRegistry::new()
            .add_connection(&ConnectionMode::Push, "server/site-b", UUID_ALPHA)
            .add_connection(&ConnectionMode::Push, "server/site-a", UUID_BETA);

        assert_eq!(
            select(&registry.registry).unwrap().site_id.to_string(),
            "server/site-a"
        );
    }

    #[test]
    fn test_candidates_counts_only_addressable_connections() {
        let registry = TestRegistry::new()
            .add_connection(&ConnectionMode::Push, "server/push-site", UUID_ALPHA)
            .add_connection(&ConnectionMode::Pull, "server/pull-site", UUID_BETA)
            .add_imported_connection(UUID_IMPORTED);

        assert_eq!(candidates(&registry.registry).count(), 2);
    }
}
