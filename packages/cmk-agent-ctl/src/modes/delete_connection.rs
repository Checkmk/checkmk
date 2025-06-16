// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::str::FromStr;

use crate::{config, site_spec};
use anyhow::{Context, Result as AnyhowResult};

fn delete_by_uuid(uuid: &uuid::Uuid, registry: &mut config::Registry) -> AnyhowResult<()> {
    match registry.retrieve_standard_connection_by_uuid(uuid) {
        Some(site_id) => registry.delete_standard_connection(&site_id),
        None => registry
            .delete_imported_connection(uuid)
            .context(format!("No connection with UUID '{uuid}'")),
    }
}

pub fn delete(registry: &mut config::Registry, connection_id: &str) -> AnyhowResult<()> {
    match site_spec::SiteID::from_str(connection_id) {
        Ok(site_id) => registry.delete_standard_connection(&site_id),
        Err(_) => delete_by_uuid(
            &uuid::Uuid::from_str(connection_id).context(
                "Provided connection identifier is neither a valid site ID nor a valid UUID",
            )?,
            registry,
        ),
    }?;

    registry.save()?;
    Ok(())
}

pub fn delete_all(registry: &mut config::Registry, enable_legacy_mode: bool) -> AnyhowResult<()> {
    registry.clear();
    registry.save()?;
    if enable_legacy_mode {
        registry.activate_legacy_pull()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use crate::modes::delete_connection::{delete, delete_all};
    use crate::*;
    use config::test_helpers::TestRegistry;
    const UUID_PUSH: &str = "0096abd7-83c9-42f8-8b3a-3ffba7ba959d";
    const UUID_PULL: &str = "b3501e4d-2820-433c-8e9c-38c69ac20faa";
    const UUID_PULL_IMP1: &str = "00c21714-5086-46d7-848e-5be72c715cfd";
    const UUID_PULL_IMP2: &str = "3bf83706-8e47-4e38-beb6-b1ce83a4eee1";

    fn registry() -> TestRegistry {
        TestRegistry::new()
            .add_connection(
                &config::ConnectionMode::Push,
                "server/push-site",
                config::TrustedConnectionWithRemote::from(UUID_PUSH),
            )
            .add_connection(
                &config::ConnectionMode::Pull,
                "server/pull-site",
                config::TrustedConnectionWithRemote::from(UUID_PULL),
            )
            .add_imported_connection(config::TrustedConnection::from(UUID_PULL_IMP1))
            .add_imported_connection(config::TrustedConnection::from(UUID_PULL_IMP2))
    }

    #[test]
    fn test_delete_by_site_id_ok() {
        let mut r = registry();
        assert!(!r.registry.path().exists());
        assert!(delete(&mut r.registry, "server/push-site").is_ok());
        assert!(r.registry.path().exists());
    }

    #[test]
    fn test_delete_by_site_id_missing() {
        let mut r = registry();
        assert_eq!(
            format!(
                "{}",
                delete(&mut r.registry, "someserver/site").unwrap_err()
            ),
            "Connection 'someserver/site' not found"
        );
    }

    #[test]
    fn test_delete_pull_by_uuid_ok() {
        let mut r = registry();
        assert!(!r.registry.path().exists());
        assert!(delete(&mut r.registry, UUID_PULL).is_ok());
        assert!(r.registry.is_standard_pull_empty());
        assert!(r.registry.path().exists());
    }

    #[test]
    fn test_delete_push_by_uuid_ok() {
        let mut r = registry();
        assert!(!r.registry.path().exists());
        assert!(delete(&mut r.registry, UUID_PUSH).is_ok());
        assert!(r.registry.is_push_empty());
        assert!(r.registry.path().exists());
    }

    #[test]
    fn test_delete_pull_imported_ok() {
        let mut r = registry();
        assert!(!r.registry.path().exists());
        assert!(delete(&mut r.registry, UUID_PULL_IMP1).is_ok());
        assert!(r.registry.path().exists());
    }

    #[test]
    fn test_delete_by_uuid_missing() {
        let uuid = uuid::Uuid::new_v4();
        let mut r = registry();
        assert_eq!(
            format!(
                "{}",
                delete(&mut r.registry, &uuid.to_string()).unwrap_err()
            ),
            format!("No connection with UUID '{}'", &uuid),
        );
    }

    #[test]
    fn test_delete_all_no_legacy_pull() {
        let mut r = registry();
        assert!(!r.registry.path().exists());
        assert!(delete_all(&mut r.registry, false).is_ok());
        assert!(r.registry.path().exists());
        assert!(!r.registry.is_legacy_pull_active());
    }

    #[test]
    fn test_delete_all_with_legacy_pull() {
        let mut r = registry();
        assert!(!r.registry.path().exists());
        assert!(delete_all(&mut r.registry, true).is_ok());
        assert!(r.registry.path().exists());
        assert!(r.registry.is_legacy_pull_active());
    }
}
