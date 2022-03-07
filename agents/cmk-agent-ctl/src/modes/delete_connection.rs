// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::str::FromStr;

use crate::{config, site_spec};
use anyhow::{Context, Result as AnyhowResult};

fn retrieve_standard_connection_by_uuid(
    uuid: &uuid::Uuid,
    registry: &config::Registry,
) -> Option<site_spec::Coordinates> {
    for (coordinates, connection) in registry
        .push_connections()
        .chain(registry.standard_pull_connections())
    {
        if &connection.uuid == uuid {
            return Some(coordinates.clone());
        }
    }
    None
}

fn delete_by_uuid(uuid: &uuid::Uuid, registry: &mut config::Registry) -> AnyhowResult<()> {
    match retrieve_standard_connection_by_uuid(uuid, registry) {
        Some(coordinates) => registry.delete_standard_connection(&coordinates),
        None => registry
            .delete_imported_connection(uuid)
            .context(format!("No connection with UUID '{}'", uuid)),
    }
}

pub fn delete(registry: &mut config::Registry, connection_id: &str) -> AnyhowResult<()> {
    if let Err(err) = match site_spec::Coordinates::from_str(connection_id) {
        Ok(coordinates) => registry.delete_standard_connection(&coordinates),
        Err(_) => delete_by_uuid(
            &uuid::Uuid::from_str(connection_id).context(
                "Provided connection identifier is neither a valid site address nor a valid UUID",
            )?,
            registry,
        ),
    } {
        return Err(err);
    }
    registry.save()?;
    Ok(())
}

pub fn delete_all(registry: &mut config::Registry) -> AnyhowResult<()> {
    registry.clear();
    Ok(registry.save()?)
}

#[cfg(test)]
mod tests {
    use crate::modes::delete_connection::{delete, delete_all};
    use crate::site_spec;
    use crate::*;
    use std::str::FromStr;
    const UUID_PUSH: &str = "0096abd7-83c9-42f8-8b3a-3ffba7ba959d";
    const UUID_PULL: &str = "b3501e4d-2820-433c-8e9c-38c69ac20faa";
    const UUID_PULL_IMP1: &str = "00c21714-5086-46d7-848e-5be72c715cfd";
    const UUID_PULL_IMP2: &str = "3bf83706-8e47-4e38-beb6-b1ce83a4eee1";

    fn registry() -> config::Registry {
        let mut push = std::collections::HashMap::new();
        let mut pull = std::collections::HashMap::new();
        let mut pull_imported = std::collections::HashSet::new();
        push.insert(
            site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            config::Connection {
                uuid: uuid::Uuid::from_str(UUID_PUSH).unwrap(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );
        pull.insert(
            site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            config::Connection {
                uuid: uuid::Uuid::from_str(UUID_PULL).unwrap(),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );
        pull_imported.insert(config::Connection {
            uuid: uuid::Uuid::from_str(UUID_PULL_IMP1).unwrap(),
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });
        pull_imported.insert(config::Connection {
            uuid: uuid::Uuid::from_str(UUID_PULL_IMP2).unwrap(),
            private_key: String::from("private_key"),
            certificate: String::from("certificate"),
            root_cert: String::from("root_cert"),
        });
        config::Registry::new(
            config::RegisteredConnections {
                push,
                pull,
                pull_imported,
            },
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap()
    }

    #[test]
    fn test_delete_by_coordinates_ok() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, "server:8000/push-site").is_ok());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_by_coordinates_missing() {
        assert_eq!(
            format!(
                "{}",
                delete(&mut registry(), "someserver:123/site").unwrap_err()
            ),
            "Connection 'someserver:123/site' not found"
        );
    }

    #[test]
    fn test_delete_pull_by_uuid_ok() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, UUID_PULL).is_ok());
        assert!(reg.pull_standard_is_empty());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_push_by_uuid_ok() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, UUID_PUSH).is_ok());
        assert!(reg.push_is_empty());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_pull_imported_ok() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, UUID_PULL_IMP1).is_ok());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_by_uuid_missing() {
        let uuid = uuid::Uuid::new_v4();
        assert_eq!(
            format!(
                "{}",
                delete(&mut registry(), &uuid.to_string()).unwrap_err()
            ),
            format!("No connection with UUID '{}'", &uuid),
        );
    }

    #[test]
    fn test_delete_all() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete_all(&mut reg).is_ok());
        assert!(reg.path().exists());
    }
}
