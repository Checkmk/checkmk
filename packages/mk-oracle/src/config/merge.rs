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

//! Merge a user-provided configuration document on top of the bakery document.
//!
//! The plugin reads the bakery file (`$MK_CONFDIR/mk-oracle.yml`)
//! first and then merges the optional user file
//! (`$MK_LIBDIR/plugins/packages/mk-oracle/user-mk-oracle.yml`) on top of it.
//!
//! Merge rules, applied recursively to the YAML documents:
//! - An empty user document (missing or blank file) never changes the bakery
//!   document.
//! - `connection`, `authentication`, `options`, `discovery`,
//!   `system`/`logging` are merged field by field: a field set in the
//!   user file overrides the bakery field, fields absent in the user file are
//!   inherited from the bakery file.
//! - Scalars and other non-hash values: the user value wins entirely.
//! - `instances` (and `configs`) are arrays,so they fall under the
//!   "user value wins entirely" rule -- if present in the user file the whole
//!   list replaces the bakery list.
//! - `sections` and `custom_metrics` are arrays of single-key maps keyed by the
//!   section/metric name; they are merged by that name, the user entry winning
//!   on a name collision and previously unseen names being appended.
//! - A bare `key:` (null value) in the user file is ignored, so it never blanks
//!   out the corresponding bakery value.
//!
//! Schema note: `sections`/`custom_metrics` are only reachable as mergeable
//! arrays directly under `oracle.main`. Inside `instances` they are
//! never reached because those lists are replaced wholesale (arrays are not
//! recursed into).

use super::defines::keys;
use super::yaml::Yaml;
use yaml_rust2::yaml::Hash;

/// Merge the `over` (user) document on top of the `base` (bakery) document.
///
/// Returns the merged document and the dotted paths the user document overrode.
pub fn merge_documents(base: &Yaml, over: &Yaml) -> (Yaml, Vec<String>) {
    if is_empty_doc(over) {
        return (base.clone(), Vec::new());
    }
    if is_empty_doc(base) {
        return (over.clone(), Vec::new());
    }
    let mut overrides = Vec::new();
    let merged = merge_value(base, over, "", &mut overrides);
    (merged, overrides)
}

fn is_empty_doc(yaml: &Yaml) -> bool {
    matches!(yaml, Yaml::Null | Yaml::BadValue)
}

fn merge_value(base: &Yaml, over: &Yaml, path: &str, overrides: &mut Vec<String>) -> Yaml {
    match (base, over) {
        (Yaml::Hash(base_hash), Yaml::Hash(over_hash)) => {
            Yaml::Hash(merge_hash(base_hash, over_hash, path, overrides))
        }
        _ => {
            push_override(path, overrides);
            over.clone()
        }
    }
}

fn merge_hash(base: &Hash, over: &Hash, path: &str, overrides: &mut Vec<String>) -> Hash {
    let mut merged = Hash::new();

    for (key, base_val) in base.iter() {
        match user_value(over, key) {
            Some(over_val) => {
                let value = merge_entry(key, base_val, over_val, path, overrides);
                merged.insert(key.clone(), value);
            }
            None => {
                merged.insert(key.clone(), base_val.clone());
            }
        }
    }

    for (key, value) in over.iter() {
        if !is_empty_doc(value) && !base.contains_key(key) {
            merged.insert(key.clone(), value.clone());
        }
    }

    merged
}

/// The user's value for `key`, unless it is absent or an empty/null value
fn user_value<'a>(over: &'a Hash, key: &Yaml) -> Option<&'a Yaml> {
    over.get(key).filter(|value| !is_empty_doc(value))
}

fn merge_entry(
    key: &Yaml,
    base_val: &Yaml,
    over_val: &Yaml,
    path: &str,
    overrides: &mut Vec<String>,
) -> Yaml {
    let Some(name) = key.as_str() else {
        return over_val.clone();
    };
    let child_path = join_path(path, name);
    if name == keys::SECTIONS || name == keys::CUSTOM_METRICS {
        return match (base_val.as_vec(), over_val.as_vec()) {
            (Some(base_arr), Some(over_arr)) => {
                merge_named_list(base_arr, over_arr, &child_path, overrides)
            }
            (Some(_), None) | (None, None) => {
                log::warn!("user config: '{child_path}' should be a list, ignoring non-list value");
                base_val.clone()
            }
            (None, Some(_)) => {
                log::warn!(
                    "bakery config: '{child_path}' should be a list, using user value as-is"
                );
                push_override(&child_path, overrides);
                over_val.clone()
            }
        };
    }
    merge_value(base_val, over_val, &child_path, overrides)
}

fn merge_named_list(base: &[Yaml], over: &[Yaml], path: &str, overrides: &mut Vec<String>) -> Yaml {
    let head = base.iter().map(|item| match single_key_name(item) {
        Some(name) => over
            .iter()
            .rev()
            .find(|o| single_key_name(o) == Some(name))
            .unwrap_or(item),
        None => item,
    });
    let tail = over.iter().enumerate().filter_map(|(idx, item)| {
        let keep = match single_key_name(item) {
            Some(name) => !contains_name(base, name) && !contains_name(&over[idx + 1..], name),
            None => true,
        };
        keep.then_some(item)
    });
    let merged: Vec<Yaml> = head.chain(tail).cloned().collect();

    overrides.extend(
        over.iter()
            .filter_map(single_key_name)
            .filter(|name| contains_name(base, name))
            .map(|name| join_path(path, name)),
    );

    Yaml::Array(merged)
}

/// Whether `items` contains a single-key entry named `name`.
fn contains_name(items: &[Yaml], name: &str) -> bool {
    items.iter().any(|item| single_key_name(item) == Some(name))
}

/// Returns the single top-level key name of a `- name: {...}` list entry.
fn single_key_name(item: &Yaml) -> Option<&str> {
    let hash = item.as_hash()?;
    if hash.len() != 1 {
        return None;
    }
    hash.iter().next().and_then(|(k, _)| k.as_str())
}

fn join_path(prefix: &str, key: &str) -> String {
    if prefix.is_empty() {
        key.to_string()
    } else {
        format!("{prefix}.{key}")
    }
}

fn push_override(path: &str, overrides: &mut Vec<String>) {
    if !path.is_empty() {
        overrides.push(path.to_string());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::{test_tools::create_yaml, Get};

    /// Merge two YAML source strings and return (merged_doc, overridden_paths).
    fn merge(base: &str, over: &str) -> (Yaml, Vec<String>) {
        merge_documents(&create_yaml(base), &create_yaml(over))
    }

    /// Navigate `oracle.main` of a merged document.
    fn main_of(doc: &Yaml) -> &Yaml {
        doc.get(keys::ORACLE).get(keys::MAIN)
    }

    const BASE: &str = r#"
oracle:
  main:
    connection:
      hostname: bakery-host
      port: 1521
    authentication:
      username: bakery_user
      password: bakery_pw
      type: standard
    cache_age: 600
    sections:
      - instance:
      - jobs:
          is_async: yes
    custom_metrics:
      - m_shared:
          sql: "select 'bakery' from dual"
      - m_bakery_only:
          sql: "select 'b' from dual"
    instances:
      - sid: BAKERY1
      - sid: BAKERY2
"#;

    #[test]
    fn test_scalar_override_at_main_level() {
        let (merged, overrides) = merge(
            BASE,
            r#"
oracle:
  main:
    cache_age: 123
"#,
        );
        assert_eq!(main_of(&merged).get_int::<u32>(keys::CACHE_AGE), Some(123));
        assert!(overrides.contains(&"oracle.main.cache_age".to_string()));
    }

    #[test]
    fn test_nested_field_override_and_inheritance() {
        let (merged, overrides) = merge(
            BASE,
            r#"
oracle:
  main:
    connection:
      hostname: user-host
"#,
        );
        let conn = main_of(&merged).get(keys::CONNECTION);
        assert_eq!(
            conn.get_string(keys::HOSTNAME).as_deref(),
            Some("user-host")
        );
        assert_eq!(conn.get_int::<u32>(keys::PORT), Some(1521));
        assert!(overrides.contains(&"oracle.main.connection.hostname".to_string()));
        assert!(!overrides.contains(&"oracle.main.connection.port".to_string()));
    }

    #[test]
    fn test_authentication_partial_override() {
        let (merged, _) = merge(
            BASE,
            r#"
oracle:
  main:
    authentication:
      password: user_pw
"#,
        );
        let auth = main_of(&merged).get(keys::AUTHENTICATION);
        assert_eq!(
            auth.get_string(keys::USERNAME).as_deref(),
            Some("bakery_user")
        );
        assert_eq!(auth.get_string(keys::PASSWORD).as_deref(), Some("user_pw"));
    }

    #[test]
    fn test_instances_replaced_wholesale() {
        let (merged, overrides) = merge(
            BASE,
            r#"
oracle:
  main:
    instances:
      - sid: USER_ONLY
"#,
        );
        let instances = main_of(&merged).get(keys::INSTANCES).as_vec().unwrap();
        assert_eq!(instances.len(), 1);
        assert_eq!(
            instances[0].get_string(keys::SID).as_deref(),
            Some("USER_ONLY")
        );
        assert!(overrides.contains(&"oracle.main.instances".to_string()));
    }

    #[test]
    fn test_instances_inner_sections_not_name_merged() {
        let (merged, _) = merge(
            BASE,
            r#"
oracle:
  main:
    instances:
      - sid: USER_ONLY
        sections:
          - instance:
"#,
        );
        let instances = main_of(&merged).get(keys::INSTANCES).as_vec().unwrap();
        assert_eq!(instances.len(), 1);
        let inner = instances[0].get(keys::SECTIONS).as_vec().unwrap();
        assert_eq!(inner.len(), 1);
    }

    #[test]
    fn test_sections_merged_by_name() {
        let (merged, overrides) = merge(
            BASE,
            r#"
oracle:
  main:
    sections:
      - jobs:
          disabled: yes
      - locks:
"#,
        );
        let sections = main_of(&merged).get(keys::SECTIONS).as_vec().unwrap();
        let names: Vec<&str> = sections.iter().filter_map(single_key_name).collect();
        assert_eq!(names, vec!["instance", "jobs", "locks"]);
        let jobs = sections
            .iter()
            .find(|s| single_key_name(s) == Some("jobs"))
            .unwrap()
            .get("jobs");
        assert_eq!(jobs.get_optional_bool(keys::DISABLED), Some(true));
        assert_eq!(jobs.get_optional_bool(keys::IS_ASYNC), None);
        assert!(overrides.contains(&"oracle.main.sections.jobs".to_string()));
        assert!(!overrides.iter().any(|o| o.ends_with(".locks")));
    }

    #[test]
    fn test_custom_metrics_merged_by_name() {
        let (merged, overrides) = merge(
            BASE,
            r#"
oracle:
  main:
    custom_metrics:
      - m_shared:
          sql: "select 'user' from dual"
      - m_user_only:
          sql: "select 'u' from dual"
"#,
        );
        let metrics = main_of(&merged).get(keys::CUSTOM_METRICS).as_vec().unwrap();
        let names: Vec<&str> = metrics.iter().filter_map(single_key_name).collect();
        assert_eq!(names, vec!["m_shared", "m_bakery_only", "m_user_only"]);
        let shared = metrics
            .iter()
            .find(|m| single_key_name(m) == Some("m_shared"))
            .unwrap()
            .get("m_shared");
        assert_eq!(
            shared.get_string(keys::SQL).as_deref(),
            Some("select 'user' from dual")
        );
        assert!(overrides.contains(&"oracle.main.custom_metrics.m_shared".to_string()));
    }

    #[test]
    fn test_logging_is_mergeable() {
        let base = r#"
system:
  logging:
    level: info
    max_count: 5
oracle:
  main:
    authentication:
      username: u
"#;
        let (merged, overrides) = merge(
            base,
            r#"
system:
  logging:
    level: trace
"#,
        );
        let logging = merged.get("system").get("logging");
        assert_eq!(logging.get_string("level").as_deref(), Some("trace"));
        assert_eq!(logging.get_int::<u32>("max_count"), Some(5));
        assert!(overrides.contains(&"system.logging.level".to_string()));
    }

    #[test]
    fn test_empty_user_doc_keeps_bakery() {
        let (merged, overrides) = merge_documents(&create_yaml(BASE), &Yaml::Null);
        assert_eq!(main_of(&merged).get_int::<u32>(keys::CACHE_AGE), Some(600));
        assert!(overrides.is_empty());
    }

    #[test]
    fn test_empty_bakery_doc_uses_user() {
        let user = create_yaml(
            r#"
oracle:
  main:
    cache_age: 42
"#,
        );
        let (merged, overrides) = merge_documents(&Yaml::Null, &user);
        assert_eq!(main_of(&merged).get_int::<u32>(keys::CACHE_AGE), Some(42));
        assert!(overrides.is_empty());
    }

    #[test]
    fn test_added_key_is_not_recorded_as_override() {
        let (merged, overrides) = merge(
            BASE,
            r#"
oracle:
  main:
    piggyback_host: new_pb
"#,
        );
        assert_eq!(
            main_of(&merged).get_string(keys::PIGGYBACK_HOST).as_deref(),
            Some("new_pb")
        );
        assert!(!overrides.iter().any(|o| o.contains("piggyback_host")));
    }

    fn named_entry(name: &str, value: Yaml) -> Yaml {
        let mut h = Hash::new();
        h.insert(Yaml::String(name.to_string()), value);
        Yaml::Hash(h)
    }

    #[test]
    fn test_named_list_collision_replaces_and_records_override() {
        let base = [
            named_entry("alpha", Yaml::Integer(1)),
            named_entry("beta", Yaml::Integer(2)),
        ];
        let over = [named_entry("beta", Yaml::Integer(99))];
        let mut overrides = Vec::new();

        let merged = merge_named_list(&base, &over, "path", &mut overrides);

        let items = merged.as_vec().unwrap();
        let names: Vec<&str> = items.iter().filter_map(single_key_name).collect();
        assert_eq!(names, vec!["alpha", "beta"]);
        assert_eq!(items[1].get("beta"), &Yaml::Integer(99));
        assert_eq!(overrides, vec!["path.beta"]);
    }

    #[test]
    fn test_named_list_new_entry_appended_without_override() {
        let base = [named_entry("alpha", Yaml::Integer(1))];
        let over = [named_entry("gamma", Yaml::Integer(3))];
        let mut overrides = Vec::new();

        let merged = merge_named_list(&base, &over, "p", &mut overrides);

        let names: Vec<&str> = merged
            .as_vec()
            .unwrap()
            .iter()
            .filter_map(single_key_name)
            .collect();
        assert_eq!(names, vec!["alpha", "gamma"]);
        assert!(overrides.is_empty());
    }

    #[test]
    fn test_merged_document_parses_into_config() {
        // The merge must produce a document the real parser accepts, with the
        // user overrides reflected in the parsed Config.
        let (merged, _) = merge(
            BASE,
            r#"
oracle:
  main:
    connection:
      hostname: user-host
    cache_age: 222
    discovery:
      detect: no
    instances:
      - sid: USER_ONLY
"#,
        );
        let config = crate::config::ora_sql::Config::from_yaml(&merged)
            .unwrap()
            .unwrap();
        assert_eq!(config.conn().hostname(), "user-host".to_string().into());
        assert_eq!(config.cache_age(), 222);
        assert_eq!(config.instances().len(), 1);
        assert_eq!(
            config.instances()[0].standalone_sid().unwrap().to_string(),
            "USER_ONLY"
        );
    }
}
