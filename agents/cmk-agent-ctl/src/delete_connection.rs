// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::config;
use anyhow::{anyhow, Context, Result as AnyhowResult};

fn imported_pull_conn_idx_to_delete(connection_id: &str) -> AnyhowResult<Option<usize>> {
    if regex::Regex::new("^imported-[1-9][0-9]*$")?.is_match(connection_id) {
        let idx_str = connection_id.split('-').collect::<Vec<&str>>()[1];
        return Ok(Some(idx_str.parse::<usize>()?));
    }
    Ok(None)
}

pub fn delete(registry: &mut config::Registry, connection_id: &str) -> AnyhowResult<()> {
    if let Some(pull_conn_idx) = imported_pull_conn_idx_to_delete(connection_id)? {
        registry
            .delete_imported_connection_by_idx(pull_conn_idx - 1)
            .context(format!(
                "Imported pull connection '{}' not found",
                connection_id
            ))?;
        registry.save()?;
        return Ok(());
    }
    if registry.delete_connection(connection_id).is_ok() {
        registry.save()?;
        return Ok(());
    }
    Err(anyhow!("Connection '{}' not found", connection_id))
}

pub fn delete_all(registry: &mut config::Registry) -> AnyhowResult<()> {
    registry.clear();
    Ok(registry.save()?)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn registry() -> config::Registry {
        let mut push = std::collections::HashMap::new();
        push.insert(
            String::from("server:8000/push-site"),
            config::Connection {
                uuid: String::from("uuid-push"),
                private_key: String::from("private_key"),
                certificate: String::from("certificate"),
                root_cert: String::from("root_cert"),
            },
        );
        config::Registry::new(
            config::RegisteredConnections {
                push,
                pull: std::collections::HashMap::new(),
                pull_imported: vec![],
            },
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap()
    }

    #[test]
    fn test_imported_pull_conn_idx_to_delete_match() {
        assert!(
            imported_pull_conn_idx_to_delete("imported-2")
                .unwrap()
                .unwrap()
                == 2
        )
    }

    #[test]
    fn test_imported_pull_conn_idx_to_delete_no_match() {
        for conn_id in [
            "imported-03",
            "server:8000/site",
            "504a3dae-343a-4374-a869-067c4a0e11de",
        ] {
            assert!(imported_pull_conn_idx_to_delete(conn_id).unwrap().is_none())
        }
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
        let mut reg = config::Registry::new(
            config::RegisteredConnections {
                push: std::collections::HashMap::new(),
                pull: std::collections::HashMap::new(),
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
        .unwrap();
        assert!(!reg.path().exists());
        assert!(delete(&mut reg, "imported-1").is_ok());
        assert!(reg.imported_pull_connections().next().unwrap().uuid == "uuid-imported-2");
        assert!(reg.path().exists());
    }

    #[test]
    fn test_delete_missing() {
        assert_eq!(
            format!("{}", delete(&mut registry(), "wrong").unwrap_err()),
            "Connection 'wrong' not found"
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
