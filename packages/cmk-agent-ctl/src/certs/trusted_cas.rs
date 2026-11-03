// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config;
use log::{error, info};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// PEM encoded CAs, keyed by the name of the site whose connections should trust them.
pub type BakedCAs = HashMap<String, Vec<String>>;

/// Load the CAs baked into the agent package by the "Embed certificates in the agent" rule.
///
/// A missing file is the normal case: the rule is optional and independent of the pre-configured
/// connections.
pub fn load_baked_cas(path: &Path) -> BakedCAs {
    let content = match fs::read_to_string(path) {
        Ok(content) => content,
        Err(err) => {
            info!("Could not load baked CAs from {:?}: {}", path, err);
            return BakedCAs::new();
        }
    };
    serde_json::from_str(&content).unwrap_or_else(|err| {
        error!("Ignoring baked CAs from {:?}: {}", path, err);
        BakedCAs::new()
    })
}

/// Trust the baked CAs on the registered connections to their site.
///
/// This is what keeps a host trusting its site across a SiteCA rotation without re-registering,
/// also if the connection was not created by the "Agent controller connections" rule.
///
/// CAs are only ever added: a CA that vanished from the file stays trusted, because the CA
/// obtained during registration is not part of the file and must not be dropped.
pub fn trust_baked_cas(baked_cas: &BakedCAs, registry: &mut config::Registry) {
    if baked_cas.is_empty() {
        return;
    }

    let mut added_any = false;
    for (site_id, connection) in registry.get_standard_connections_as_mut() {
        let Some(site_cas) = baked_cas.get(&site_id.site) else {
            continue;
        };
        if config::add_missing_root_certs(&mut connection.trust.root_certs, site_cas) {
            info!(
                "Added baked CAs to the trusted CAs of connection {}",
                site_id
            );
            added_any = true;
        }
    }

    if added_any {
        if let Err(err) = registry.save() {
            error!("Failed to save registered connections: {}", err)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::test_helpers::TestRegistry;
    use crate::site_spec::SiteID;
    use std::str::FromStr;

    const SITE_ID: &str = "server/site";
    const OTHER_SITE_ID: &str = "server/other_site";

    fn test_registry() -> TestRegistry {
        TestRegistry::new()
            .add_connection(&config::ConnectionMode::Pull, SITE_ID, uuid::Uuid::new_v4())
            .add_connection(
                &config::ConnectionMode::Pull,
                OTHER_SITE_ID,
                uuid::Uuid::new_v4(),
            )
    }

    fn baked_cas() -> BakedCAs {
        BakedCAs::from([(String::from("site"), vec![String::from("upcoming_site_ca")])])
    }

    fn root_certs_of(registry: &mut config::Registry, site_id: &str) -> Vec<String> {
        registry
            .get_connection_as_mut(&SiteID::from_str(site_id).unwrap())
            .unwrap()
            .trust
            .root_certs
            .clone()
    }

    #[test]
    fn test_trust_baked_cas_only_for_their_site() {
        let mut test_registry = test_registry();
        trust_baked_cas(&baked_cas(), &mut test_registry.registry);
        assert_eq!(
            root_certs_of(&mut test_registry.registry, SITE_ID),
            ["root_cert", "upcoming_site_ca"]
        );
        assert_eq!(
            root_certs_of(&mut test_registry.registry, OTHER_SITE_ID),
            ["root_cert"]
        );
    }

    #[test]
    fn test_trust_baked_cas_is_idempotent() {
        let mut test_registry = test_registry();
        trust_baked_cas(&baked_cas(), &mut test_registry.registry);
        trust_baked_cas(&baked_cas(), &mut test_registry.registry);
        assert_eq!(
            root_certs_of(&mut test_registry.registry, SITE_ID),
            ["root_cert", "upcoming_site_ca"]
        );
    }

    #[test]
    fn test_load_baked_cas_missing_file() {
        assert!(load_baked_cas(Path::new("/this/does/not/exist.json")).is_empty());
    }
}
