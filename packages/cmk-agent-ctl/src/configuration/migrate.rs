// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::site_spec::SiteID;

use super::config;
use anyhow::{bail, Context, Error as AnyhowError, Result as AnyhowResult};
use config::JSONLoaderMissingSafe;
use serde::Deserialize;
use serde_with::DisplayFromStr;
use std::collections::{HashMap, HashSet};
use std::convert::Into;
use std::hash::Hash;
use std::path::Path;
use std::str::FromStr;

pub fn migrate_registered_connections(path: impl AsRef<Path>) -> AnyhowResult<()> {
    if config::Registry::from_file(path.as_ref()).is_ok() {
        return Ok(());
    }

    let registered_connections_legacy = RegisteredConnections::load_missing_safe(path.as_ref())
        .context(format!(
        "Failed to load registered connections from {:?}, both with current and with legacy format",
        path.as_ref()
    ))?;

    let mut migrated_registry = config::Registry::new(path.as_ref())?;

    for (connection_mode, legacy_connections) in [
        (
            config::ConnectionMode::Push,
            registered_connections_legacy.push,
        ),
        (
            config::ConnectionMode::Pull,
            registered_connections_legacy.pull,
        ),
    ] {
        for (coordinates, legacy_connection) in legacy_connections.into_iter() {
            let (site_id, migrated_connection) =
                migrate_standard_connection(coordinates, legacy_connection);
            migrated_registry.register_connection(&connection_mode, &site_id, migrated_connection);
        }
    }

    for migrated_connection in registered_connections_legacy
        .pull_imported
        .into_iter()
        .map(|c| c.into())
    {
        migrated_registry.register_imported_connection(migrated_connection);
    }

    migrated_registry
        .save()
        .context("Failed to save migrated connection registry")
}

#[derive(Deserialize, Default)]
struct RegisteredConnections {
    #[serde(default)]
    push: HashMap<Coordinates, Connection>,

    #[serde(default)]
    pull: HashMap<Coordinates, Connection>,

    #[serde(default)]
    pull_imported: HashSet<Connection>,
}

impl config::JSONLoader for RegisteredConnections {}
impl config::JSONLoaderMissingSafe for RegisteredConnections {}

fn migrate_standard_connection(
    coordinates: Coordinates,
    connection: Connection,
) -> (SiteID, config::TrustedConnectionWithRemote) {
    (
        SiteID {
            server: coordinates.server,
            site: coordinates.site,
        },
        config::TrustedConnectionWithRemote {
            trust: connection.into(),
            receiver_port: coordinates.port,
        },
    )
}

#[derive(PartialEq, Eq, Hash, serde_with::DeserializeFromStr)]
struct Coordinates {
    server: String,
    port: u16,
    site: String,
}

impl FromStr for Coordinates {
    type Err = AnyhowError;

    fn from_str(s: &str) -> AnyhowResult<Coordinates> {
        let outer_components: Vec<&str> = s.split('/').collect();
        if outer_components.len() != 2 {
            bail!("Failed to split into server address and site at '/'");
        }
        let server_components: Vec<&str> = outer_components[0].split(':').collect();
        if server_components.len() != 2 {
            bail!("Failed to split into server and port at ':'");
        }
        Ok(Coordinates {
            server: String::from(server_components[0]),
            port: server_components[1].parse::<u16>()?,
            site: String::from(outer_components[1]),
        })
    }
}

#[serde_with::serde_as]
#[derive(Deserialize)]
struct Connection {
    #[serde_as(as = "DisplayFromStr")]
    uuid: uuid::Uuid,
    private_key: String,
    certificate: String,
    root_cert: String,
}

impl PartialEq for Connection {
    fn eq(&self, other: &Self) -> bool {
        self.uuid == other.uuid
    }
}

impl Eq for Connection {}

impl Hash for Connection {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.uuid.hash(state);
    }
}

#[allow(clippy::from_over_into)]
impl Into<config::TrustedConnection> for Connection {
    fn into(self) -> config::TrustedConnection {
        config::TrustedConnection {
            uuid: self.uuid,
            private_key: self.private_key,
            certificate: self.certificate,
            root_cert: self.root_cert,
        }
    }
}

#[cfg(test)]
mod test {
    use super::*;
    use std::path::PathBuf;

    struct NamedTempPath {
        path: PathBuf,
    }

    impl NamedTempPath {
        fn new() -> Self {
            Self {
                path: tempfile::NamedTempFile::new()
                    .unwrap()
                    .into_temp_path()
                    .to_path_buf(),
            }
        }
    }

    impl AsRef<Path> for NamedTempPath {
        fn as_ref(&self) -> &Path {
            &self.path
        }
    }

    impl Drop for NamedTempPath {
        fn drop(&mut self) {
            if self.path.exists() {
                std::fs::remove_file(&self.path).unwrap();
            }
        }
    }

    fn write_legacy_registry(path: impl AsRef<Path>) {
        std::fs::write(
            path,
            r#"{
            "push": {
              "server:8000/push-site": {
                "uuid": "ca30e826-cf0e-4a7a-9f9d-84b304d61ccb",
                "private_key": "private_key_push",
                "certificate": "certificate_push",
                "root_cert": "root_cert_push"
              }
            },
            "pull": {
              "server:8000/pull-site": {
                "uuid": "9a2c4eb5-35f5-4bf7-82c0-e2f2c06215ea",
                "private_key": "private_key_pull",
                "certificate": "certificate_pull",
                "root_cert": "root_cert_pull"
              }
            },
            "pull_imported": [
              {
                "uuid": "882c9443-4d63-4a11-bdc8-3c1fe8bf1506",
                "private_key": "private_key_imported",
                "certificate": "certificate_imported",
                "root_cert": "root_cert_imported"
              }
            ]
          }"#,
        )
        .unwrap();
    }

    #[test]
    fn test_missing_registry_ok() {
        let tmp_path = NamedTempPath::new();
        assert!(!tmp_path.as_ref().exists());
        assert!(migrate_registered_connections(&tmp_path).is_ok());
        assert!(!tmp_path.as_ref().exists());
    }

    #[test]
    fn test_up_to_date_registry_untouched() {
        let tmp_path = NamedTempPath::new();
        config::Registry::new(&tmp_path).unwrap().save().unwrap();
        let mtime_before_migration = std::fs::metadata(&tmp_path).unwrap().modified().unwrap();
        assert!(migrate_registered_connections(&tmp_path).is_ok());
        let mtime_after_migration = std::fs::metadata(&tmp_path).unwrap().modified().unwrap();
        assert_eq!(mtime_before_migration, mtime_after_migration);
    }

    #[test]
    fn test_legacy_registry_migration() {
        let tmp_path = NamedTempPath::new();
        write_legacy_registry(&tmp_path);
        assert!(migrate_registered_connections(&tmp_path).is_ok());
        let migrated_registry = config::Registry::from_file(&tmp_path).unwrap();

        assert_eq!(migrated_registry.get_push_connections().count(), 1);
        assert_eq!(migrated_registry.get_standard_pull_connections().count(), 1);
        assert_eq!(migrated_registry.get_imported_pull_connections().count(), 1);

        let (site_id_push, connection_push) =
            migrated_registry.get_push_connections().next().unwrap();
        assert_eq!(site_id_push.to_string(), "server/push-site");
        assert_eq!(
            connection_push.trust.uuid.to_string(),
            "ca30e826-cf0e-4a7a-9f9d-84b304d61ccb"
        );
        assert_eq!(
            connection_push.trust.private_key.to_string(),
            "private_key_push"
        );
        assert_eq!(
            connection_push.trust.certificate.to_string(),
            "certificate_push"
        );
        assert_eq!(
            connection_push.trust.root_cert.to_string(),
            "root_cert_push"
        );
        assert_eq!(connection_push.receiver_port, 8000);

        let (site_id_pull, connection_pull) = migrated_registry
            .get_standard_pull_connections()
            .next()
            .unwrap();
        assert_eq!(site_id_pull.to_string(), "server/pull-site");
        assert_eq!(
            connection_pull.trust.uuid.to_string(),
            "9a2c4eb5-35f5-4bf7-82c0-e2f2c06215ea"
        );
        assert_eq!(
            connection_pull.trust.private_key.to_string(),
            "private_key_pull"
        );
        assert_eq!(
            connection_pull.trust.certificate.to_string(),
            "certificate_pull"
        );
        assert_eq!(
            connection_pull.trust.root_cert.to_string(),
            "root_cert_pull"
        );
        assert_eq!(connection_pull.receiver_port, 8000);

        let connection_imported = migrated_registry
            .get_imported_pull_connections()
            .next()
            .unwrap();
        assert_eq!(
            connection_imported.uuid.to_string(),
            "882c9443-4d63-4a11-bdc8-3c1fe8bf1506"
        );
        assert_eq!(
            connection_imported.private_key.to_string(),
            "private_key_imported"
        );
        assert_eq!(
            connection_imported.certificate.to_string(),
            "certificate_imported"
        );
        assert_eq!(
            connection_imported.root_cert.to_string(),
            "root_cert_imported"
        );
    }

    #[test]
    fn test_crash_upon_corrupt_registry() {
        let tmp_path = NamedTempPath::new();
        std::fs::write(&tmp_path, "nonsense").unwrap();
        assert!(migrate_registered_connections(&tmp_path).is_err());
    }
}
