// Copyright (C) 2026 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

use anyhow::Result;
use std::path::Path;

/// Read legacy config from `input`, write generated mk-oracle.yml to `output`.
pub fn migrate(input: &Path, output: &Path) -> Result<()> {
    let legacy = std::fs::read_to_string(input)?;
    let yml = convert(&legacy)?;
    std::fs::write(output, yml)?;
    Ok(())
}

/// Convert legacy Oracle plugin configuration to mk-oracle.yml content.
///
/// Returns a YAML string with the base structure and the original legacy
/// configuration appended as comments for reference.
pub fn convert(legacy: &str) -> Result<String> {
    let mut out = String::from(
        r#"---
# Migrated from legacy mk_oracle configuration.
# Review and adjust before use.
oracle:
  main:
    connection:
      hostname: localhost
      port: 1521
    authentication:
      username: CHANGE_ME
      type: standard
"#,
    );

    out.push_str("\n# --- Original legacy configuration ---\n");
    for line in legacy.lines() {
        out.push_str("# ");
        out.push_str(line);
        out.push('\n');
    }

    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_convert_minimal() {
        let legacy = "DBUSER='checkmk:secret::localhost::XE'\nCACHE_MAXAGE=600\n";
        let result = convert(legacy).unwrap();
        assert!(result.starts_with("---\n"));
        assert!(result.contains("oracle:\n"));
        assert!(result.contains("main:\n"));
        assert!(result.contains("connection:\n"));
        assert!(result.contains("authentication:\n"));
        assert!(result.contains("# DBUSER='checkmk:secret::localhost::XE'"));
        assert!(result.contains("# CACHE_MAXAGE=600"));
    }

    #[test]
    fn test_convert_empty() {
        let result = convert("").unwrap();
        assert!(result.contains("oracle:\n"));
        assert!(result.contains("# --- Original legacy configuration ---\n"));
    }

    #[test]
    fn test_convert_preserves_all_lines() {
        let legacy = "DBUSER='user:pass:::'\n\
                       ASMUSER='/::SYSASM:::'\n\
                       CACHE_MAXAGE=600\n\
                       REMOTE_INSTANCE_XE='user:pass::host:1521::XE::'\n";
        let result = convert(legacy).unwrap();
        for line in legacy.lines() {
            assert!(result.contains(&format!("# {line}")), "missing: {line}");
        }
    }

    #[test]
    fn test_convert_result_is_valid_yaml() {
        let legacy = "DBUSER='checkmk:secret:::'\n";
        let result = convert(legacy).unwrap();
        let config = super::super::OracleConfig::load_str(&result);
        assert!(config.is_ok(), "generated YAML must be loadable: {result}");
        assert!(config.unwrap().ora_sql().is_some());
    }
}
