// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::str::FromStr;

use super::{config, status};
use anyhow::{anyhow, Context, Result as AnyhowResult};

fn connection_name_from_uuid(
    uuid: uuid::Uuid,
    registry: &config::Registry,
) -> AnyhowResult<status::ConnectionName> {
    for (coordinates, connection) in registry
        .push_connections()
        .chain(registry.standard_pull_connections())
    {
        if connection.uuid == uuid {
            return Ok(status::ConnectionName::Standard(coordinates.clone()));
        }
    }
    for (idx, connection) in registry.imported_pull_connections().enumerate() {
        if connection.uuid == uuid {
            return Ok(status::ConnectionName::Imported(idx));
        }
    }
    Err(anyhow!(format!("No connection with UUID '{}'", uuid)))
}

pub fn delete(registry: &mut config::Registry, connection_id: &str) -> AnyhowResult<()> {
    if let Err(err) = match status::ConnectionName::from_str(connection_id).or_else(|_| {
        connection_name_from_uuid(
            uuid::Uuid::from_str(connection_id)
                .context("Provided connection name is not a valid name and not a valid UUID")?,
            registry,
        )
    })? {
        status::ConnectionName::Standard(coordinates) => {
            registry.delete_standard_connection(&coordinates)
        }
        status::ConnectionName::Imported(idx) => registry.delete_imported_connection(idx).context(
            format!("Imported pull connection '{}' not found", connection_id),
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
    use super::super::site_spec;
    use super::*;
    const UUID_PUSH: &str = "0096abd7-83c9-42f8-8b3a-3ffba7ba959d";
    const UUID_PULL: &str = "b3501e4d-2820-433c-8e9c-38c69ac20faa";
    const UUID_PULL_IMP1: &str = "00c21714-5086-46d7-848e-5be72c715cfd";
    const UUID_PULL_IMP2: &str = "3bf83706-8e47-4e38-beb6-b1ce83a4eee1";

    fn registry() -> config::Registry {
        let mut push = std::collections::HashMap::new();
        let mut pull = std::collections::HashMap::new();
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
        config::Registry::new(
            config::RegisteredConnections {
                push,
                pull,
                pull_imported: vec![
                    config::Connection {
                        uuid: uuid::Uuid::from_str(UUID_PULL_IMP1).unwrap(),
                        private_key: String::from("private_key"),
                        certificate: String::from("certificate"),
                        root_cert: String::from("root_cert"),
                    },
                    config::Connection {
                        uuid: uuid::Uuid::from_str(UUID_PULL_IMP2).unwrap(),
                        private_key: String::from("private_key"),
                        certificate: String::from("certificate"),
                        root_cert: String::from("root_cert"),
                    },
                ],
            },
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap()
    }

    #[test]
    fn test_connection_name_from_uuid_push() {
        assert_eq!(
            connection_name_from_uuid(uuid::Uuid::from_str(UUID_PUSH).unwrap(), &registry())
                .unwrap(),
            status::ConnectionName::from_str("server:8000/push-site").unwrap(),
        );
    }

    #[test]
    fn test_connection_name_from_uuid_pull() {
        assert_eq!(
            connection_name_from_uuid(uuid::Uuid::from_str(UUID_PULL).unwrap(), &registry())
                .unwrap(),
            status::ConnectionName::from_str("server:8000/pull-site").unwrap(),
        );
    }

    #[test]
    fn test_connection_name_from_uuid_imported_pull() {
        assert_eq!(
            connection_name_from_uuid(uuid::Uuid::from_str(UUID_PULL_IMP2).unwrap(), &registry())
                .unwrap(),
            status::ConnectionName::from_str("imported-2").unwrap(),
        );
    }

    #[test]
    fn test_connection_name_from_uuid_missing() {
        assert!(connection_name_from_uuid(uuid::Uuid::new_v4(), &registry()).is_err());
    }

    #[test]
    fn test_delete_ok() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, "server:8000/push-site").is_ok());
        assert!(reg.path().exists());
    }

    #[test]
    fn test_imported_pull_conn_by_idx_ok() {
        let mut reg = registry();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, "imported-1").is_ok());
        assert!(
            reg.imported_pull_connections()
                .next()
                .unwrap()
                .uuid
                .to_string()
                == UUID_PULL_IMP2
        );
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_invalid() {
        assert_eq!(
            format!("{}", delete(&mut registry(), "wrong").unwrap_err()),
            "Provided connection name is not a valid name and not a valid UUID"
        );
    }

    #[test]
    fn test_delete_by_name_missing() {
        assert_eq!(
            format!(
                "{}",
                delete(&mut registry(), "someserver:123/site").unwrap_err()
            ),
            "Connection 'someserver:123/site' not found"
        );
    }

    #[test]
    fn test_delete_by_uuid_missing() {
        assert_eq!(
            format!(
                "{}",
                delete(&mut registry(), "8046d9e4-127a-44e2-a281-30479c93e258").unwrap_err()
            ),
            "No connection with UUID '8046d9e4-127a-44e2-a281-30479c93e258'"
        );
    }

    #[test]
    fn test_delete_imported_pull_conn_by_idx_missing() {
        assert_eq!(
            format!("{}", delete(&mut registry(), "imported-4").unwrap_err()),
            "Imported pull connection 'imported-4' not found"
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
