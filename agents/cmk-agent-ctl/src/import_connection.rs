// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::{cli, config, registration};
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

fn _import(
    registry: &mut config::Registry,
    json_provider: impl JSONProvider,
    verbose: bool,
) -> AnyhowResult<()> {
    let json = json_provider.provide()?;
    registry.register_imported_connection(
        serde_json::from_str::<registration::SurrogatePullData>(&json)
            .context(if verbose {
                format!("Failed to deserialize JSON data:\n{}", &json)
            } else {
                String::from("Failed to deserialize JSON data")
            })?
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
            import_args.verbose,
        ),
        None => _import(registry, JSONFromStdin {}, import_args.verbose),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct MockJSONProvider {}

    impl JSONProvider for MockJSONProvider {
        fn provide(&self) -> AnyhowResult<String> {
            Ok(String::from(
                r#"{"agent_controller_version":"0.1.0","connection":{"uuid":"short-uuid",
                  "private_key": "fake private key","certificate":"fake cert","root_cert":
                  "fake root cert"}}"#,
            ))
        }
    }

    #[test]
    fn test_import() {
        let mut reg = config::Registry::new(
            config::RegisteredConnections {
                push: std::collections::HashMap::new(),
                pull: std::collections::HashMap::new(),
                pull_imported: vec![],
            },
            std::path::PathBuf::from(&tempfile::NamedTempFile::new().unwrap().into_temp_path()),
        )
        .unwrap();
        assert!(reg.is_empty());
        assert!(!reg.path().exists());
        assert!(_import(&mut reg, MockJSONProvider {}, false).is_ok());
        assert!(!reg.is_empty());
        assert!(reg.path().exists());
    }
}
