// Copyright (C) 2025 Checkmk GmbH
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

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use crate::types::{ItemValue, SectionAffinity, SectionFilter, SectionName};
use anyhow::Result;
use log;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

// "tablespaces", "rman", "jobs", "ts_quotas", "resumable", "locks"
pub mod names {
    pub const INSTANCE: &str = "instance";
    pub const ASM_INSTANCE: &str = "asm_instance"; // virtual section
    pub const SESSIONS: &str = "sessions";
    pub const LOG_SWITCHES: &str = "logswitches";
    pub const UNDO_STAT: &str = "undostat";
    pub const RECOVERY_AREA: &str = "recovery_area";
    pub const PROCESSES: &str = "processes";
    pub const RECOVERY_STATUS: &str = "recovery_status";
    pub const LONG_ACTIVE_SESSIONS: &str = "longactivesessions";
    pub const DATAGUARD_STATS: &str = "dataguard_stats";
    pub const PERFORMANCE: &str = "performance";
    pub const SYSTEM_PARAMETER: &str = "systemparameter";
    pub const LOCKS: &str = "locks";
    pub const TABLESPACES: &str = "tablespaces";
    pub const RMAN: &str = "rman";
    pub const JOBS: &str = "jobs";
    pub const RESUMABLE: &str = "resumable";
    pub const IO_STATS: &str = "iostats";
    pub const ASM_DISK_GROUP: &str = "asm_diskgroup";
    pub const TS_QUOTAS: &str = "ts_quotas";
    pub const CUSTOM_METRIC: &str = "sql";
}

static DEFAULT_AFFINITY_MAP: LazyLock<HashMap<&str, SectionAffinity>> = LazyLock::new(|| {
    HashMap::from([
        ("instance", SectionAffinity::Db),
        ("asm_instance", SectionAffinity::Asm),
        ("sessions", SectionAffinity::Db),
        ("logswitches", SectionAffinity::Db),
        ("undostat", SectionAffinity::Db),
        ("recovery_area", SectionAffinity::Db),
        ("processes", SectionAffinity::All),
        ("recovery_status", SectionAffinity::Db),
        ("longactivesessions", SectionAffinity::Db),
        ("dataguard_stats", SectionAffinity::Db),
        ("performance", SectionAffinity::Db),
        ("systemparameter", SectionAffinity::Db),
        ("locks", SectionAffinity::Db),
        ("tablespaces", SectionAffinity::Db),
        ("rman", SectionAffinity::Db),
        ("jobs", SectionAffinity::Db),
        ("resumable", SectionAffinity::Db),
        ("iostats", SectionAffinity::Db),
        ("asm_diskgroup", SectionAffinity::Asm),
        ("ts_quotas", SectionAffinity::Db),
    ])
});

#[derive(Debug, PartialEq, Copy, Clone)]
pub enum SectionKind {
    Sync,
    Async,
    Disabled,
}

const PREDEFINED_SECTIONS: [&str; 20] = [
    names::INSTANCE,
    names::ASM_INSTANCE,
    names::SESSIONS,
    names::LOG_SWITCHES,
    names::UNDO_STAT,
    names::RECOVERY_AREA,
    names::PROCESSES,
    names::RECOVERY_STATUS,
    names::LONG_ACTIVE_SESSIONS,
    names::DATAGUARD_STATS,
    names::PERFORMANCE,
    names::SYSTEM_PARAMETER,
    names::LOCKS,
    names::TABLESPACES,
    names::RMAN,
    names::JOBS,
    names::RESUMABLE,
    names::IO_STATS,
    names::ASM_DISK_GROUP,
    names::TS_QUOTAS,
];

const PREDEFINED_ASYNC_SECTIONS: [&str; 6] = [
    names::TABLESPACES,
    names::RMAN,
    names::JOBS,
    names::RESUMABLE,
    names::IO_STATS,
    names::ASM_DISK_GROUP,
];

impl SectionAffinity {
    pub fn from_text<T: AsRef<str>>(s: T) -> Self {
        match s.as_ref().to_lowercase().as_str() {
            "all" => SectionAffinity::All,
            "asm" => SectionAffinity::Asm,
            "db" => SectionAffinity::Db,
            _ => {
                log::error!("Invalid section type: {}", s.as_ref());
                SectionAffinity::Db
            }
        }
    }
}

pub struct SectionBuilder {
    name: String,
    sep: char,
    is_async: bool,
    is_disabled: bool,
    sql: Option<String>,
    sql_params: Vec<(String, String)>,
    path: Option<PathBuf>,
    affinity: SectionAffinity,
    item_value: Option<ItemValue>, // [PROD|locks]
    pdb_patterns: Vec<String>,
}

impl SectionBuilder {
    pub fn new<S: Into<String>>(name: S) -> Self {
        let name = name.into();
        let is_async = PREDEFINED_ASYNC_SECTIONS.contains(&name.as_str());
        Self {
            name: name.clone(),
            sep: defaults::SECTION_SEPARATOR,
            is_async,
            is_disabled: false,
            sql: None,
            sql_params: Vec::new(),
            path: None,
            affinity: DEFAULT_AFFINITY_MAP
                .get(name.as_str())
                .cloned()
                .unwrap_or(SectionAffinity::Db),
            item_value: None,
            pdb_patterns: Vec::new(),
        }
    }
    pub fn sep(mut self, sep: Option<char>) -> Self {
        if let Some(c) = sep {
            self.sep = c;
        }
        self
    }

    pub fn set_async(mut self, value: bool) -> Self {
        self.is_async = value;
        self
    }

    pub fn set_item_value(mut self, value: ItemValue) -> Self {
        self.item_value = Some(value);
        self
    }

    pub fn set_affinity(mut self, value: SectionAffinity) -> Self {
        self.affinity = value;
        self
    }

    pub fn set_disabled(mut self) -> Self {
        self.is_disabled = true;
        self
    }

    pub fn sql<S: Into<String>>(mut self, sql: S) -> Self {
        self.sql = Some(sql.into());
        self
    }

    pub fn sql_params(mut self, params: Vec<(String, String)>) -> Self {
        self.sql_params = params;
        self
    }

    pub fn path<P: Into<PathBuf>>(mut self, path: P) -> Self {
        self.path = Some(path.into());
        self
    }

    pub fn set_pdb_patterns(mut self, p: Vec<String>) -> Self {
        self.pdb_patterns = p;
        self
    }

    pub fn build(self) -> Section {
        let (name, sep) = if self.item_value.is_some() {
            (
                names::CUSTOM_METRIC.to_string(),
                defaults::CUSTOM_METRIC_SEPARATOR,
            )
        } else {
            (self.name, self.sep)
        };
        Section {
            name: SectionName::from(name),
            sep,
            kind: if self.is_disabled {
                SectionKind::Disabled
            } else if self.is_async {
                SectionKind::Async
            } else {
                SectionKind::Sync
            },
            sql: self.sql,
            sql_params: self.sql_params,
            path: self.path,
            affinity: self.affinity,
            item_value: self.item_value,
            pdb_patterns: self.pdb_patterns,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Section {
    name: SectionName,
    sep: char,
    kind: SectionKind,
    sql: Option<String>,
    sql_params: Vec<(String, String)>,
    path: Option<PathBuf>,
    affinity: SectionAffinity,
    item_value: Option<ItemValue>, // part of [SID|item_value]
    pdb_patterns: Vec<String>,
}

impl Section {
    pub fn new<S: Into<String>>(name: S) -> Self {
        SectionBuilder::new(name.into()).build()
    }

    pub fn name(&self) -> &SectionName {
        &self.name
    }

    pub fn pdb_patterns(&self) -> &Vec<String> {
        &self.pdb_patterns
    }

    pub fn item_value(&self) -> Option<&ItemValue> {
        self.item_value.as_ref()
    }

    pub fn sep(&self) -> char {
        self.sep
    }

    pub fn kind(&self) -> SectionKind {
        self.kind
    }

    pub fn sql(&self) -> Option<&str> {
        self.sql.as_deref()
    }

    pub fn sql_params(&self) -> &[(String, String)] {
        &self.sql_params
    }

    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
    }

    pub fn affinity(&self) -> &SectionAffinity {
        &self.affinity
    }

    pub fn is_allowed(&self, filter: SectionFilter) -> bool {
        match filter {
            SectionFilter::Sync => self.kind == SectionKind::Sync,
            SectionFilter::AsyncAll => self.kind == SectionKind::Async,
            SectionFilter::All => self.kind != SectionKind::Disabled,
            SectionFilter::AsyncBuiltinSections => {
                self.kind == SectionKind::Async && !self.is_custom_metric()
            }
            SectionFilter::AsyncCustomMetrics => {
                self.kind == SectionKind::Async && self.is_custom_metric()
            }
        }
    }

    pub fn is_custom_metric(&self) -> bool {
        self.item_value.is_some()
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Sections {
    sections: Vec<Section>,
    cache_age: u32,
    custom_metrics_cache_age: u32,
}

impl Default for Sections {
    fn default() -> Self {
        Self {
            sections: get_predefined_sections(),
            cache_age: defaults::SECTIONS_CACHE_AGE,
            custom_metrics_cache_age: defaults::CUSTOM_METRICS_CACHE_AGE,
        }
    }
}

fn get_predefined_sections() -> Vec<Section> {
    PREDEFINED_SECTIONS
        .iter()
        .map(|&s| Section::new(s))
        .collect()
}

impl Section {
    /// Converts entry to Section
    /// - databases:     # name
    ///   is_async: true # option
    ///   disabled: true # option
    ///
    /// Note: yaml_rust2 represents such entry as a LinkedHashMap
    pub fn from_yaml(entry: &Yaml) -> Result<Self> {
        let mut section = entry
            .as_hash()
            .unwrap()
            .iter()
            .filter_map(|(n, yaml)| {
                if let Some(name) = n.as_str() {
                    Some(Section::from_yaml_entry(name, yaml))
                } else {
                    log::error!("Empty or malformed section name");
                    None
                }
            })
            .collect::<Vec<Section>>();
        // for some not clear reason the entry is a LinkedHashMap:
        // we take first entry only and ignore the rest
        section
            .pop()
            .ok_or_else(|| anyhow::anyhow!("Empty section"))
    }
    fn from_yaml_entry(name: &str, yaml: &Yaml) -> Self {
        let c = yaml.get_string(keys::SEP).and_then(|s| s.chars().next());
        let mut builder = SectionBuilder::new(name)
            .sep(c)
            .sql_params(parse_sql_params(yaml.get(keys::SQL_PARAMS)));
        if let Some(sql_text) = yaml.get_string(keys::SQL) {
            builder = builder.sql(sql_text);
        }
        if let Some(path_text) = yaml.get_string(keys::PATH) {
            builder = builder.path(path_text);
        }

        let affinity = yaml
            .get_string(keys::AFFINITY)
            .map(SectionAffinity::from_text)
            .unwrap_or_else(|| {
                DEFAULT_AFFINITY_MAP
                    .get(name)
                    .unwrap_or(&SectionAffinity::Db)
                    .clone()
            });

        let pdbs = yaml.get_string_vector(keys::PDBS, &[]);

        if !pdbs.is_empty() {
            builder.set_pdb_patterns(pdbs)
        } else if yaml.get_optional_bool(keys::DISABLED) == Some(true) {
            builder.set_disabled()
        } else if let Some(v) = yaml.get_optional_bool(keys::IS_ASYNC) {
            builder.set_async(v)
        } else {
            builder
        }
        .set_affinity(affinity)
        .build()
    }
}

/// Parse the `sql_params` mapping of a section entry into
/// `(name, value)` pairs. Values may reference environment variables
/// (`$VAR` or `${VAR}`); a parameter whose referenced variable is not set
/// is skipped with a warning, leaving its `${name}` placeholder unpatched.
fn parse_sql_params(yaml: &Yaml) -> Vec<(String, String)> {
    let Some(hash) = yaml.as_hash() else {
        if !yaml.is_badvalue() {
            log::error!("sql_params must be a mapping");
        }
        return Vec::new();
    };
    hash.iter()
        .filter_map(|(name, value)| {
            let Some(name) = name.as_str() else {
                log::error!("sql_params: parameter name must be a string, got {name:?}");
                return None;
            };
            let Some(value) = yaml_scalar_to_string(value) else {
                log::error!("sql_params: value of parameter '{name}' must be a scalar");
                return None;
            };
            match shellexpand::env(&value) {
                Ok(expanded) => Some((name.to_string(), expanded.into_owned())),
                Err(e) => {
                    log::warn!(
                        "sql_params: env var '{}' referenced by parameter '{name}' is not set, skipping",
                        e.var_name
                    );
                    None
                }
            }
        })
        .collect()
}

fn yaml_scalar_to_string(value: &Yaml) -> Option<String> {
    match value {
        Yaml::String(s) => Some(s.clone()),
        Yaml::Real(r) => Some(r.clone()),
        Yaml::Integer(i) => Some(i.to_string()),
        Yaml::Boolean(b) => Some(b.to_string()),
        _ => None,
    }
}

impl Sections {
    pub fn from_yaml(yaml: &Yaml, default: &Sections) -> Result<Self> {
        let cache_age = yaml.get_int::<u32>(keys::CACHE_AGE).unwrap_or_else(|| {
            log::debug!("Using default cache age");
            default.cache_age()
        });
        let custom_metrics_cache_age = yaml
            .get_int::<u32>(keys::CUSTOM_METRICS_CACHE_AGE)
            .unwrap_or_else(|| {
                log::debug!("Using default metrics cache age");
                default.custom_metrics_cache_age()
            });
        let mut sections = Sections::get_sections(yaml.get(keys::SECTIONS), None, None)
            .unwrap_or_else(|| {
                log::debug!("Using default sections");
                default.sections().clone()
            });
        sections.extend(
            Sections::get_sections(
                yaml.get(keys::CUSTOM_METRICS),
                Some(defaults::CUSTOM_METRIC_SEPARATOR),
                Some(&SectionName::from(names::CUSTOM_METRIC.to_string())),
            )
            .unwrap_or_default(),
        );
        Ok(Self {
            sections,
            cache_age,
            custom_metrics_cache_age,
        })
    }

    pub fn get_sections(
        yaml: &Yaml,
        sep_override: Option<char>,
        section_name_override: Option<&SectionName>,
    ) -> Option<Vec<Section>> {
        if yaml.is_badvalue() {
            return None;
        }
        let entries = yaml.as_vec()?;
        let sections = entries.iter().flat_map(Section::from_yaml);
        Some(match section_name_override {
            Some(section_name) => sections
                .map(|s| Section {
                    item_value: Some(ItemValue::from(s.name().as_str().to_string())),
                    name: section_name.clone(),
                    sep: sep_override.unwrap_or(s.sep),
                    ..s
                })
                .collect(),
            None => sections.collect(),
        })
    }

    pub fn sections(&self) -> &Vec<Section> {
        &self.sections
    }

    pub fn cache_age(&self) -> u32 {
        self.cache_age
    }

    pub fn custom_metrics_cache_age(&self) -> u32 {
        self.custom_metrics_cache_age
    }

    pub fn select(&self, kinds: &[SectionKind]) -> Vec<&Section> {
        self.sections()
            .iter()
            .filter(|s| kinds.contains(&s.kind()))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::test_tools::create_yaml;
    use std::collections::HashSet;

    #[test]
    fn test_async_section_allowed() {
        let async_section = SectionBuilder::new("async").set_async(true).build();
        assert!(async_section.is_allowed(SectionFilter::All));
        assert!(!async_section.is_allowed(SectionFilter::Sync));
        assert!(async_section.is_allowed(SectionFilter::AsyncAll));
        assert!(async_section.is_allowed(SectionFilter::AsyncBuiltinSections));
        assert!(!async_section.is_allowed(SectionFilter::AsyncCustomMetrics));
    }

    #[test]
    fn test_async_metric_allowed() {
        let async_section = SectionBuilder::new("async")
            .set_async(true)
            .set_item_value(ItemValue::from("AAA".to_string()))
            .build();
        assert!(async_section.is_allowed(SectionFilter::All));
        assert!(!async_section.is_allowed(SectionFilter::Sync));
        assert!(async_section.is_allowed(SectionFilter::AsyncAll));
        assert!(!async_section.is_allowed(SectionFilter::AsyncBuiltinSections));
        assert!(async_section.is_allowed(SectionFilter::AsyncCustomMetrics));
    }

    #[test]
    fn test_sync_section_allowed() {
        let sync_section = SectionBuilder::new("sync").set_async(false).build();
        assert!(sync_section.is_allowed(SectionFilter::All));
        assert!(sync_section.is_allowed(SectionFilter::Sync));
        assert!(!sync_section.is_allowed(SectionFilter::AsyncAll));
        assert!(!sync_section.is_allowed(SectionFilter::AsyncBuiltinSections));
        assert!(!sync_section.is_allowed(SectionFilter::AsyncCustomMetrics));
    }

    #[test]
    fn test_disabled_section_allowed() {
        let disabled = SectionBuilder::new("disabled").set_disabled().build();
        assert!(!disabled.is_allowed(SectionFilter::All));
        assert!(!disabled.is_allowed(SectionFilter::Sync));
        assert!(!disabled.is_allowed(SectionFilter::AsyncAll));
        assert!(!disabled.is_allowed(SectionFilter::AsyncBuiltinSections));
        assert!(!disabled.is_allowed(SectionFilter::AsyncCustomMetrics));
    }
    #[test]
    fn test_section_affinity() {
        assert_eq!(SectionAffinity::from_text("all"), SectionAffinity::All);
        assert_eq!(SectionAffinity::from_text("ASM"), SectionAffinity::Asm);
        assert_eq!(SectionAffinity::from_text(""), SectionAffinity::Db);
    }

    fn hash_set<T: AsRef<str>>(v: &[T]) -> HashSet<String> {
        HashSet::from_iter(v.iter().map(|s| s.as_ref().to_string()))
    }

    pub const SECTIONS_FULL: &str = r#"
sections:
- aaa:
    sep: '.'
- bbb:
    sep: "|ss"
- ccc:
    is_async: yes
    sep: |
- ddd:
    is_async: yes
    affinity: asm
- "eee":
    sep: "|ss"
    disabled: yes
    affinity: all
"#;

    #[test]
    fn test_sections_from_yaml_full() {
        fn make_section_vector<'a>(s: &'a Sections, kinds: &[SectionKind]) -> Vec<(&'a str, char)> {
            s.select(kinds)
                .iter()
                .map(|s| (s.name().as_str(), s.sep()))
                .collect::<Vec<(&str, char)>>()
        }
        let s = Sections::from_yaml(&create_yaml(SECTIONS_FULL), &Sections::default()).unwrap();
        assert_eq!(
            make_section_vector(&s, &[SectionKind::Sync]),
            [("aaa", '.'), ("bbb", '|')]
        );
        assert_eq!(
            make_section_vector(&s, &[SectionKind::Async]),
            [("ccc", '|'), ("ddd", '|')]
        );
        assert_eq!(
            make_section_vector(&s, &[SectionKind::Disabled]),
            [("eee", '|')]
        );
        let mut all = s
            .sections()
            .iter()
            .map(|s| format!("{}:{:?}", s.name(), s.affinity()))
            .collect::<Vec<String>>();
        all.sort();
        assert_eq!(
            all,
            vec!["aaa:Db", "bbb:Db", "ccc:Db", "ddd:Asm", "eee:All"]
        );
    }

    #[test]
    fn test_sections_from_yaml_default() {
        let s = Sections::from_yaml(&create_sections_yaml_default(), &Sections::default()).unwrap();
        let syncs = HashSet::from_iter(
            s.select(&[SectionKind::Sync])
                .iter()
                .map(|s| s.name().to_string()),
        );
        assert_eq!(
            syncs,
            (&hash_set(&PREDEFINED_SECTIONS) - &hash_set(&PREDEFINED_ASYNC_SECTIONS))
        );

        let asyncs = s
            .select(&[SectionKind::Async])
            .iter()
            .map(|s| s.name().as_str())
            .collect::<Vec<&str>>();
        assert_eq!(asyncs, PREDEFINED_ASYNC_SECTIONS);

        assert_eq!(s.cache_age(), defaults::SECTIONS_CACHE_AGE);
        assert_eq!(
            s.custom_metrics_cache_age(),
            defaults::CUSTOM_METRICS_CACHE_AGE
        );

        assert_eq!(
            Sections::from_yaml(&create_yaml("_sections:\n"), &Sections::default())
                .unwrap()
                .sections()
                .len(),
            20
        );
        assert_eq!(s.sections.len(), PREDEFINED_SECTIONS.len());
        s.sections.iter().for_each(|s| {
            assert_eq!(
                s.affinity(),
                DEFAULT_AFFINITY_MAP.get(s.name().as_str()).unwrap()
            )
        });
    }

    fn create_sections_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
sections:
_nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }

    fn create_yaml_sections_with_custom() -> Yaml {
        const SOURCE: &str = r#"
custom_metrics:
  - product_price:
      sql: "select 'details:hello' from dual"
  - last_sessions:
      sql: "select 'details:async' from dual"
      is_async: yes

sections:
  - something:
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_sections_with_custom_metrics() {
        let s =
            Sections::from_yaml(&create_yaml_sections_with_custom(), &Sections::default()).unwrap();
        let sections: &Vec<Section> = s.sections();
        assert_eq!(sections.len(), 3);
        assert!(sections[0].item_value().is_none());
        assert_eq!(sections[0].kind(), SectionKind::Sync);

        assert_eq!(sections[1].name().as_str(), names::CUSTOM_METRIC);
        assert_eq!(sections[1].item_value().unwrap().as_str(), "product_price");
        assert_eq!(sections[1].kind(), SectionKind::Sync);
        assert_eq!(sections[1].sep(), defaults::CUSTOM_METRIC_SEPARATOR);
        assert_eq!(sections[1].sql(), Some("select 'details:hello' from dual"));

        assert_eq!(sections[2].name().as_str(), names::CUSTOM_METRIC);
        assert_eq!(sections[2].item_value().unwrap().as_str(), "last_sessions");
        assert_eq!(sections[2].kind(), SectionKind::Async);
        assert_eq!(sections[2].sep(), defaults::CUSTOM_METRIC_SEPARATOR);
    }

    #[test]
    fn test_custom_metric_path_parsed_relative() {
        const SOURCE: &str = r#"
custom_metrics:
  - product_price:
      path: "queries/product_price.sql"
"#;
        let s = Sections::from_yaml(&create_yaml(SOURCE), &Sections::default()).unwrap();
        let custom: Vec<&Section> = s
            .sections()
            .iter()
            .filter(|sec| sec.is_custom_metric())
            .collect();
        assert_eq!(custom.len(), 1);
        assert_eq!(
            custom[0].path(),
            Some(Path::new("queries/product_price.sql"))
        );
        assert!(custom[0].path().is_some_and(|p| p.is_relative()));
        assert_eq!(custom[0].sql(), None);
        assert_eq!(custom[0].item_value().unwrap().as_str(), "product_price");
    }

    #[test]
    fn test_custom_metric_path_parsed_absolute() {
        #[cfg(not(windows))]
        let sql_path = "/test/checkmk/sql/heavy_query.sql";
        #[cfg(windows)]
        let sql_path = r"C:\test\checkmk\sql\heavy_query.sql";
        let source = format!(
            r#"
custom_metrics:
  - heavy_query:
      path: '{}'
"#,
            sql_path
        );
        let s = Sections::from_yaml(&create_yaml(source), &Sections::default()).unwrap();
        let custom: Vec<&Section> = s
            .sections()
            .iter()
            .filter(|sec| sec.is_custom_metric())
            .collect();
        assert_eq!(custom.len(), 1);
        assert_eq!(custom[0].path(), Some(Path::new(sql_path)));
        assert!(custom[0].path().is_some_and(|p| p.is_absolute()));
    }

    #[test]
    fn test_custom_metric_sql_and_path_both_parsed() {
        const SOURCE: &str = r#"
custom_metrics:
  - mixed:
      path: "queries/mixed.sql"
      sql: "select 'details:fallback' from dual"
"#;
        let s = Sections::from_yaml(&create_yaml(SOURCE), &Sections::default()).unwrap();
        let custom: Vec<&Section> = s
            .sections()
            .iter()
            .filter(|sec| sec.is_custom_metric())
            .collect();
        assert_eq!(custom.len(), 1);
        assert_eq!(custom[0].path(), Some(Path::new("queries/mixed.sql")));
        assert_eq!(custom[0].sql(), Some("select 'details:fallback' from dual"));
    }

    #[test]
    fn test_predefined_section_path_parsed() {
        const SOURCE: &str = r#"
sections:
  - instance:
      path: "/opt/checkmk/sql/instance.sql"
  - sessions:
      path: "queries/sessions"
"#;
        let s = Sections::from_yaml(&create_yaml(SOURCE), &Sections::default()).unwrap();
        let find_path = |name: &str| -> Option<&Path> {
            s.sections()
                .iter()
                .find(|sec| sec.name().as_str() == name)
                .and_then(|sec| sec.path())
        };
        assert_eq!(
            find_path("instance"),
            Some(Path::new("/opt/checkmk/sql/instance.sql"))
        );
        assert_eq!(find_path("sessions"), Some(Path::new("queries/sessions")));
    }

    #[test]
    fn test_section_builder_path_setter() {
        let section = SectionBuilder::new("foo").path("queries/foo.sql").build();
        assert_eq!(section.path(), Some(Path::new("queries/foo.sql")));
    }

    #[test]
    fn test_pdbs_parsed_from_yaml() {
        const SOURCE: &str = r#"
custom_metrics:
  - product_price:
      sql: "select 'details:hello' from dual"
      pdbs: ["PDB1", ".*PDB"]
"#;
        let s = Sections::from_yaml(&create_yaml(SOURCE), &Sections::default()).unwrap();
        let custom: Vec<&Section> = s
            .sections()
            .iter()
            .filter(|sec| sec.is_custom_metric())
            .collect();
        assert_eq!(custom[0].pdb_patterns(), &["PDB1", ".*PDB"]);
    }

    fn parse_custom_metrics(source: &str) -> Vec<Section> {
        Sections::from_yaml(&create_yaml(source), &Sections::default())
            .unwrap()
            .sections()
            .iter()
            .filter(|sec| sec.is_custom_metric())
            .cloned()
            .collect()
    }

    #[test]
    fn test_sql_params_parsed_from_yaml() {
        const SOURCE: &str = r#"
custom_metrics:
  - test:
      sql: "SELECT ${parameter_1} FROM dual"
      sql_params:
        parameter_1: "value_1"
        parameter_2: 42
"#;
        let custom = parse_custom_metrics(SOURCE);
        assert_eq!(
            custom[0].sql_params(),
            &[
                ("parameter_1".to_string(), "value_1".to_string()),
                ("parameter_2".to_string(), "42".to_string()),
            ]
        );
    }

    #[test]
    fn test_sql_params_empty_when_absent() {
        const SOURCE: &str = r#"
custom_metrics:
  - test:
      sql: "SELECT 1 FROM dual"
"#;
        let custom = parse_custom_metrics(SOURCE);
        assert!(custom[0].sql_params().is_empty());
    }

    #[test]
    fn test_sql_params_env_var_resolved() {
        unsafe { std::env::set_var("_MK_TEST_SQL_PARAM", "from_env") };
        const SOURCE: &str = r#"
custom_metrics:
  - test:
      sql: "SELECT ${parameter_1} FROM dual"
      sql_params:
        parameter_1: "${_MK_TEST_SQL_PARAM}"
"#;
        let custom = parse_custom_metrics(SOURCE);
        assert_eq!(
            custom[0].sql_params(),
            &[("parameter_1".to_string(), "from_env".to_string())]
        );
        unsafe { std::env::remove_var("_MK_TEST_SQL_PARAM") };
    }

    #[test]
    fn test_sql_params_unset_env_var_skips_parameter() {
        const SOURCE: &str = r#"
custom_metrics:
  - test:
      sql: "SELECT ${parameter_1} FROM dual"
      sql_params:
        parameter_1: "${_MK_TEST_UNDEFINED_VAR_12345}"
        parameter_2: "kept"
"#;
        let custom = parse_custom_metrics(SOURCE);
        assert_eq!(
            custom[0].sql_params(),
            &[("parameter_2".to_string(), "kept".to_string())]
        );
    }

    #[test]
    fn test_sql_params_non_scalar_value_skipped() {
        const SOURCE: &str = r#"
custom_metrics:
  - test:
      sql: "SELECT 1 FROM dual"
      sql_params:
        parameter_1: [a, b]
        parameter_2: "ok"
"#;
        let custom = parse_custom_metrics(SOURCE);
        assert_eq!(
            custom[0].sql_params(),
            &[("parameter_2".to_string(), "ok".to_string())]
        );
    }

    #[test]
    fn test_pdbs_empty_when_absent() {
        const SOURCE: &str = r#"
custom_metrics:
  - product_price:
      sql: "select 'details:hello' from dual"
"#;
        let s = Sections::from_yaml(&create_yaml(SOURCE), &Sections::default()).unwrap();
        let custom: Vec<&Section> = s
            .sections()
            .iter()
            .filter(|sec| sec.is_custom_metric())
            .collect();
        assert!(custom[0].pdb_patterns().is_empty());
    }
}
