// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::modes::registration;
use crate::{cli, config};
use anyhow::{Context, Result as AnyhowResult};

trait JSONProvider {
    fn provide(&self) -> AnyhowResult<String>;
}

struct JSONFromFile {
    path: std::path::PathBuf,
}

impl JSONProvider for JSONFromFile {
    fn provide(&self) -> AnyhowResult<String> {
        std::fs::read_to_string(&self.path)
            .context(format!("Failed to read file {}", &self.path.display()))
    }
}

struct JSONFromStdin {}

impl JSONProvider for JSONFromStdin {
    fn provide(&self) -> AnyhowResult<String> {
        let mut buffer = String::new();
        std::io::stdin()
            .read_line(&mut buffer)
            .context("Failed to read from stdin")?;
        Ok(buffer)
    }
}

fn _import(registry: &mut config::Registry, json_provider: impl JSONProvider) -> AnyhowResult<()> {
    let json = json_provider.provide()?;
    registry.register_imported_connection(
        serde_json::from_str::<registration::ProxyPullData>(&json)
            .context(format!("Failed to deserialize JSON data:\n{}", &json))?
            .connection,
    );
    registry.save()?;
    Ok(())
}

pub fn import(registry: &mut config::Registry, import_args: &cli::ImportArgs) -> AnyhowResult<()> {
    match &import_args.conn_file {
        Some(path) => _import(
            registry,
            JSONFromFile {
                path: std::path::PathBuf::from(path),
            },
        ),
        None => _import(registry, JSONFromStdin {}),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct MockJSONProvider {}

    impl JSONProvider for MockJSONProvider {
        fn provide(&self) -> AnyhowResult<String> {
            Ok(String::from(
                r#"{"agent_controller_version":"0.1.0","connection":{
                    "uuid":"2da53af5-5c06-4195-ab6f-668875710bec",
                    "private_key": "fake private key",
                    "certificate":"fake cert",
                    "root_cert": "fake root cert"}}"#,
            ))
        }
    }

    #[test]
    fn test_import() {
        let mut reg = config::Registry::new(
            config::RegisteredConnections {
                push: std::collections::HashMap::new(),
                pull: std::collections::HashMap::new(),
                pull_imported: std::collections::HashSet::new(),
            },
            tempfile::NamedTempFile::new().unwrap(),
        )
        .unwrap();
        assert!(reg.is_empty());
        assert!(!reg.path().exists());
        assert!(_import(&mut reg, MockJSONProvider {}).is_ok());
        assert!(!reg.is_empty());
        assert!(reg.path().exists());
    }
}
