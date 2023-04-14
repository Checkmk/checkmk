// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
    use crate::site_spec;
    use crate::*;
    use config::test_helpers::TestRegistryDir;
    use std::str::FromStr;
    const UUID_PUSH: &str = "0096abd7-83c9-42f8-8b3a-3ffba7ba959d";
    const UUID_PULL: &str = "b3501e4d-2820-433c-8e9c-38c69ac20faa";
    const UUID_PULL_IMP1: &str = "00c21714-5086-46d7-848e-5be72c715cfd";
    const UUID_PULL_IMP2: &str = "3bf83706-8e47-4e38-beb6-b1ce83a4eee1";

    fn registry() -> (TestRegistryDir, config::Registry) {
        let registry_dir = TestRegistryDir::new();
        let mut registry = registry_dir.create_registry();
        registry.register_connection(
            &config::ConnectionMode::Push,
            &site_spec::SiteID::from_str("server/push-site").unwrap(),
            config::TrustedConnectionWithRemote::from(UUID_PUSH),
        );
        registry.register_connection(
            &config::ConnectionMode::Pull,
            &site_spec::SiteID::from_str("server/pull-site").unwrap(),
            config::TrustedConnectionWithRemote::from(UUID_PULL),
        );
        registry.register_imported_connection(config::TrustedConnection::from(UUID_PULL_IMP1));
        registry.register_imported_connection(config::TrustedConnection::from(UUID_PULL_IMP2));
        (registry_dir, registry)
    }

    #[test]
    fn test_delete_by_site_id_ok() {
        let (_reg_dir, mut reg) = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, "server/push-site").is_ok());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_by_site_id_missing() {
        let (_reg_dir, mut reg) = registry();
        assert_eq!(
            format!("{}", delete(&mut reg, "someserver/site").unwrap_err()),
            "Connection 'someserver/site' not found"
        );
    }

    #[test]
    fn test_delete_pull_by_uuid_ok() {
        let (_reg_dir, mut reg) = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, UUID_PULL).is_ok());
        assert!(reg.pull_standard_is_empty());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_push_by_uuid_ok() {
        let (_reg_dir, mut reg) = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, UUID_PUSH).is_ok());
        assert!(reg.push_is_empty());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_pull_imported_ok() {
        let (_reg_dir, mut reg) = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, UUID_PULL_IMP1).is_ok());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_by_uuid_missing() {
        let uuid = uuid::Uuid::new_v4();
        let (_reg_dir, mut reg) = registry();
        assert_eq!(
            format!("{}", delete(&mut reg, &uuid.to_string()).unwrap_err()),
            format!("No connection with UUID '{}'", &uuid),
        );
    }

    #[test]
    fn test_delete_all_no_legacy_pull() {
        let (_reg_dir, mut reg) = registry();
        assert!(!reg.path().exists());
        assert!(delete_all(&mut reg, false).is_ok());
        assert!(reg.path().exists());
        assert!(!reg.legacy_pull_active());
    }

    #[test]
    fn test_delete_all_with_legacy_pull() {
        let (_reg_dir, mut reg) = registry();
        assert!(!reg.path().exists());
        assert!(delete_all(&mut reg, true).is_ok());
        assert!(reg.path().exists());
        assert!(reg.legacy_pull_active());
    }
}
