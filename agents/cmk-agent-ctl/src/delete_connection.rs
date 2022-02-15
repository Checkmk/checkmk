// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::str::FromStr;

use super::{config, status};
use anyhow::{anyhow, Context, Result as AnyhowResult};

fn connection_name_from_uuid(
    uuid: &str,
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
    if let Err(err) = match status::ConnectionName::from_str(connection_id)
        .or_else(|_| connection_name_from_uuid(connection_id, registry))?
    {
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

    fn registry() -> config::Registry {
        let mut push = std::collections::HashMap::new();
        let mut pull = std::collections::HashMap::new();
        push.insert(
            site_spec::Coordinates::from_str("server:8000/push-site").unwrap(),
            config::Connection {
                uuid: String::from("uuid-push"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );
        pull.insert(
            site_spec::Coordinates::from_str("server:8000/pull-site").unwrap(),
            config::Connection {
                uuid: String::from("uuid-pull"),
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
                        uuid: String::from("uuid-imported-1"),
                        private_key: String::from("private_key"),
                        certificate: String::from("certificate"),
                        root_cert: String::from("root_cert"),
                    },
                    config::Connection {
                        uuid: String::from("uuid-imported-2"),
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
            connection_name_from_uuid("uuid-push", &registry()).unwrap(),
            status::ConnectionName::from_str("server:8000/push-site").unwrap(),
        );
    }

    #[test]
    fn test_connection_name_from_uuid_pull() {
        assert_eq!(
            connection_name_from_uuid("uuid-pull", &registry()).unwrap(),
            status::ConnectionName::from_str("server:8000/pull-site").unwrap(),
        );
    }

    #[test]
    fn test_connection_name_from_uuid_imported_pull() {
        assert_eq!(
            connection_name_from_uuid("uuid-imported-2", &registry()).unwrap(),
            status::ConnectionName::from_str("imported-2").unwrap(),
        );
    }

    #[test]
    fn test_connection_name_from_uuid_missing() {
        assert!(connection_name_from_uuid("uuid-missing", &registry()).is_err());
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
        assert!(reg.imported_pull_connections().next().unwrap().uuid == "uuid-imported-2");
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_missing() {
        assert_eq!(
            format!("{}", delete(&mut registry(), "wrong").unwrap_err()),
            "No connection with UUID 'wrong'"
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
