// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use anyhow::Result;

pub mod names {
    pub const INSTANCE: &str = "instance";
    pub const COUNTERS: &str = "counters";
    pub const BLOCKED: &str = "blocked_sessions";
    pub const BACKUP: &str = "backup";
    pub const TRANSACTION_LOG: &str = "transactionlogs";
    pub const DATAFILES: &str = "datafiles";
    pub const DATABASES: &str = "databases";
    pub const CLUSTERS: &str = "clusters";

    pub const TABLE_SPACES: &str = "tablespaces";
    pub const CONNECTIONS: &str = "connections";

    // query based section
    pub const JOBS: &str = "jobs";
    pub const MIRRORING: &str = "mirroring";
    pub const AVAILABILITY_GROUPS: &str = "availability_groups";
}

/// TODO(sk): convert into HashSet
const PIPE_SEP_SECTIONS: [&str; 8] = [
    names::INSTANCE,
    names::COUNTERS,
    names::BLOCKED,
    names::BACKUP,
    names::TRANSACTION_LOG,
    names::DATAFILES,
    names::DATABASES,
    names::CLUSTERS,
];

const SPACE_SEP_SECTIONS: [&str; 2] = [names::TABLE_SPACES, names::CONNECTIONS];

const QUERY_BASED_SECTIONS: [&str; 3] = [names::JOBS, names::MIRRORING, names::AVAILABILITY_GROUPS];
const DEFAULT_SYNC_SECTIONS: [&str; 9] = [
    names::INSTANCE,
    names::DATABASES,
    names::COUNTERS,
    names::BLOCKED,
    names::TRANSACTION_LOG,
    names::CLUSTERS,
    names::MIRRORING,
    names::AVAILABILITY_GROUPS,
    names::CONNECTIONS,
];

const DEFAULT_ASYNC_SECTIONS: [&str; 4] = [
    names::TABLE_SPACES,
    names::DATAFILES,
    names::BACKUP,
    names::JOBS,
];

#[derive(Debug, PartialEq, Copy, Clone)]
pub enum SectionKind {
    Sync,
    Async,
    Disabled,
}

pub struct SectionBuilder {
    name: String,
    sep: Option<char>,
    is_async: bool,
    is_disabled: bool,
    sql: Option<String>,
}

impl SectionBuilder {
    pub fn new<S: Into<String>>(name: S) -> Self {
        let name = name.into();
        let sep = get_default_separator(&name);
        Self {
            name,
            sep,
            is_async: false,
            is_disabled: false,
            sql: None,
        }
    }
    pub fn sep(mut self, sep: Option<char>) -> Self {
        self.sep = sep;
        self
    }
    pub fn set_async(mut self) -> Self {
        self.is_async = true;
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

    pub fn build(self) -> Section {
        Section {
            name: self.name,
            sep: self.sep.unwrap_or(defaults::DEFAULT_SEP),
            kind: if self.is_disabled {
                SectionKind::Disabled
            } else if self.is_async {
                SectionKind::Async
            } else {
                SectionKind::Sync
            },
            sql: self.sql,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Section {
    name: String,
    sep: char,
    kind: SectionKind,
    sql: Option<String>,
}

impl Section {
    pub fn new<S: Into<String>>(name: S) -> Self {
        SectionBuilder::new(name.into()).build()
    }

    pub fn name(&self) -> &str {
        &self.name
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
}

#[derive(PartialEq, Debug, Clone)]
pub struct Sections {
    sections: Vec<Section>,
    cache_age: u32,
}

impl Default for Sections {
    fn default() -> Self {
        Self {
            sections: get_default_sections(),
            cache_age: defaults::SECTIONS_CACHE_AGE,
        }
    }
}

fn get_default_sections() -> Vec<Section> {
    let sync_sections: Vec<Section> = DEFAULT_SYNC_SECTIONS
        .iter()
        .map(|&s| Section::new(s))
        .collect();
    let async_sections: Vec<Section> = DEFAULT_ASYNC_SECTIONS
        .iter()
        .map(|&s| SectionBuilder::new(s).set_async().build())
        .collect();
    [sync_sections, async_sections].concat()
}

impl Section {
    /// Converts entry to Section
    /// - databases:     # name
    ///   is_async: true    # option
    ///   disabled: true # option
    /// Note: yaml_rust represents such entry as a LinkedHashMap
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
        let builder = SectionBuilder::new(name).sep(c);

        if yaml.get_bool(keys::DISABLED, false) {
            builder.set_disabled()
        } else if yaml.get_bool(keys::IS_ASYNC, false) {
            builder.set_async()
        } else {
            builder
        }
        .build()
    }
}

impl Sections {
    pub fn from_yaml(yaml: &Yaml, default: Sections) -> Result<Self> {
        let cache_age = yaml.get_int::<u32>(keys::CACHE_AGE, default.cache_age());
        let sections = Sections::get_sections(yaml.get(keys::SECTIONS));
        Ok(Self {
            sections: sections.unwrap_or(default.sections().clone()),
            cache_age,
        })
    }

    fn get_sections(yaml: &Yaml) -> Option<Vec<Section>> {
        if yaml.is_badvalue() {
            return None;
        }
        if let Some(sections) = yaml.as_vec() {
            let l: Vec<Section> = sections.iter().flat_map(Section::from_yaml).collect();
            Some(l)
        } else {
            None
        }
    }
    pub fn sections(&self) -> &Vec<Section> {
        &self.sections
    }

    pub fn cache_age(&self) -> u32 {
        self.cache_age
    }

    pub fn select(&self, kinds: &[SectionKind]) -> Vec<&Section> {
        self.sections()
            .iter()
            .filter(|s| kinds.contains(&s.kind()))
            .collect()
    }
}

pub fn get_default_separator(name: &str) -> Option<char> {
    if PIPE_SEP_SECTIONS.contains(&name) {
        Some('|')
    } else if SPACE_SEP_SECTIONS.contains(&name) {
        None
    } else if QUERY_BASED_SECTIONS.contains(&name) {
        Some('\t')
    } else {
        log::warn!("Unknown section: {}", name);
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::test_tools::create_yaml;

    pub const SECTIONS_FULL: &str = r#"
sections:
- aaa:
    sep: '|'
- bbb:
    sep: "|ss"
- ccc:
    is_async: yes
    sep: |
- ddd:
    is_async: yes
- "eee":
    sep: "|ss"
    disabled: yes
"#;

    #[test]
    fn test_sections_from_yaml_full() {
        let s = Sections::from_yaml(&create_yaml(SECTIONS_FULL), Sections::default()).unwrap();
        assert_eq!(
            s.select(&[SectionKind::Sync])
                .iter()
                .map(|s| (s.name(), s.sep()))
                .collect::<Vec<(&str, char)>>(),
            [("aaa", '|'), ("bbb", '|')]
        );
        assert_eq!(
            s.select(&[SectionKind::Async])
                .iter()
                .map(|s| s.name())
                .collect::<Vec<&str>>(),
            ["ccc", "ddd"]
        );
        assert_eq!(
            s.select(&[SectionKind::Disabled])
                .iter()
                .map(|s| (s.name(), s.sep()))
                .collect::<Vec<(&str, char)>>(),
            [("eee", '|')]
        );
    }

    #[test]
    fn test_sections_from_yaml_default() {
        let s = Sections::from_yaml(&create_sections_yaml_default(), Sections::default()).unwrap();
        assert_eq!(
            s.select(&[SectionKind::Sync])
                .iter()
                .map(|s| s.name())
                .collect::<Vec<&str>>(),
            DEFAULT_SYNC_SECTIONS
        );
        assert_eq!(
            s.select(&[SectionKind::Async])
                .iter()
                .map(|s| s.name())
                .collect::<Vec<&str>>(),
            DEFAULT_ASYNC_SECTIONS
        );
        assert_eq!(s.cache_age(), defaults::SECTIONS_CACHE_AGE);
        assert_eq!(
            Sections::from_yaml(&create_yaml("_sections:\n"), Sections::default())
                .unwrap()
                .sections()
                .len(),
            13
        );
    }

    fn create_sections_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
sections:
_nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_known_sections() {
        assert!(get_default_separator("zu").is_none());
        assert!(get_default_separator("tablespaces").is_none());
        assert!(get_default_separator("connections").is_none());
        assert_eq!(get_default_separator("jobs").unwrap(), '\t');
        assert_eq!(get_default_separator("mirroring").unwrap(), '\t');
        assert_eq!(get_default_separator("availability_groups").unwrap(), '\t');
        assert_eq!(get_default_separator("instance").unwrap(), '|');
    }
}
