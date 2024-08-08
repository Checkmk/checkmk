// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use std::collections::HashSet;

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use anyhow::Result;

pub mod names {
    pub const INSTANCE: &str = "instance";
    pub const COUNTERS: &str = "counters";
    pub const BLOCKED_SESSIONS: &str = "blocked_sessions";
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
    names::BLOCKED_SESSIONS,
    names::BACKUP,
    names::TRANSACTION_LOG,
    names::DATAFILES,
    names::DATABASES,
    names::CLUSTERS,
];

const SPACE_SEP_SECTIONS: [&str; 2] = [names::TABLE_SPACES, names::CONNECTIONS];

const QUERY_BASED_SECTIONS: [&str; 3] = [names::JOBS, names::MIRRORING, names::AVAILABILITY_GROUPS];
const PREDEFINED_SECTIONS: [&str; 13] = [
    names::INSTANCE,
    names::DATABASES,
    names::COUNTERS,
    names::BLOCKED_SESSIONS,
    names::TRANSACTION_LOG,
    names::CLUSTERS,
    names::MIRRORING,
    names::AVAILABILITY_GROUPS,
    names::CONNECTIONS,
    names::TABLE_SPACES,
    names::DATAFILES,
    names::BACKUP,
    names::JOBS,
];

const ASYNC_SECTIONS: [&str; 4] = [
    names::TABLE_SPACES,
    names::DATAFILES,
    names::BACKUP,
    names::JOBS,
];

const PER_DATABASE_SECTIONS: [&str; 5] = [
    names::DATABASES,
    names::TRANSACTION_LOG,
    names::TABLE_SPACES,
    names::DATAFILES,
    names::CLUSTERS,
];

const FIRST_LINE_SECTIONS: [&str; 2] = [names::MIRRORING, names::JOBS];
#[derive(Debug, PartialEq, Copy, Clone)]
pub enum SectionKind {
    Sync,
    Async,
    Disabled,
}

pub struct SectionBuilder {
    name: String,
    sep: char,
    is_async: bool,
    is_disabled: bool,
    sql: Option<String>,
}

impl SectionBuilder {
    pub fn new<S: Into<String>>(name: S) -> Self {
        let name = name.into();
        let sep = get_default_separator(&name);
        let is_async = ASYNC_SECTIONS.contains(&name.as_str());
        Self {
            name,
            sep,
            is_async,
            is_disabled: false,
            sql: None,
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
            sep: self.sep,
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
            sections: get_predefined_sections(),
            cache_age: defaults::SECTIONS_CACHE_AGE,
        }
    }
}

fn get_predefined_sections() -> Vec<Section> {
    PREDEFINED_SECTIONS
        .iter()
        .map(|&s| Section::new(s))
        .collect()
}

pub fn get_per_database_sections() -> Vec<String> {
    PER_DATABASE_SECTIONS
        .iter()
        .map(|&s| s.to_string())
        .collect()
}

fn get_predefined_section_names() -> Vec<String> {
    get_predefined_sections()
        .iter()
        .map(|s| s.name().to_owned())
        .collect()
}

fn get_decorated_section_names() -> Vec<String> {
    FIRST_LINE_SECTIONS.iter().map(|&s| s.to_owned()).collect()
}

pub fn get_plain_section_names() -> HashSet<String> {
    let all = hash_set(&get_predefined_section_names());
    let decorated = hash_set(&get_decorated_section_names());
    (&all - &decorated).into_iter().collect()
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
        let builder = SectionBuilder::new(name).sep(c);

        if yaml.get_optional_bool(keys::DISABLED) == Some(true) {
            builder.set_disabled()
        } else if let Some(v) = yaml.get_optional_bool(keys::IS_ASYNC) {
            builder.set_async(v)
        } else {
            builder
        }
        .build()
    }
}

impl Sections {
    pub fn from_yaml(yaml: &Yaml, default: &Sections) -> Result<Self> {
        let cache_age = yaml.get_int::<u32>(keys::CACHE_AGE).unwrap_or_else(|| {
            log::debug!("Using default cache age");
            default.cache_age()
        });
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

fn get_default_separator(name: &str) -> char {
    if PIPE_SEP_SECTIONS.contains(&name) {
        '|'
    } else if SPACE_SEP_SECTIONS.contains(&name) {
        ' '
    } else if QUERY_BASED_SECTIONS.contains(&name) {
        '\t'
    } else {
        log::warn!("Unknown section: {}", name);
        ' '
    }
}

fn hash_set<T: AsRef<str>>(v: &[T]) -> HashSet<String> {
    HashSet::from_iter(v.iter().map(|s| s.as_ref().to_string()))
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
        let s = Sections::from_yaml(&create_yaml(SECTIONS_FULL), &Sections::default()).unwrap();
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
        let s = Sections::from_yaml(&create_sections_yaml_default(), &Sections::default()).unwrap();
        assert_eq!(
            HashSet::from_iter(
                s.select(&[SectionKind::Sync])
                    .iter()
                    .map(|s| s.name().to_string())
            ),
            (&hash_set(&PREDEFINED_SECTIONS) - &hash_set(&ASYNC_SECTIONS))
        );
        assert_eq!(
            s.select(&[SectionKind::Async])
                .iter()
                .map(|s| s.name())
                .collect::<Vec<&str>>(),
            ASYNC_SECTIONS
        );
        assert_eq!(s.cache_age(), defaults::SECTIONS_CACHE_AGE);
        assert_eq!(
            Sections::from_yaml(&create_yaml("_sections:\n"), &Sections::default())
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
        assert_eq!(get_default_separator("zu"), ' ');
        assert_eq!(get_default_separator("tablespaces"), ' ');
        assert_eq!(get_default_separator("connections"), ' ');
        assert_eq!(get_default_separator("jobs"), '\t');
        assert_eq!(get_default_separator("mirroring"), '\t');
        assert_eq!(get_default_separator("availability_groups"), '\t');
        assert_eq!(get_default_separator("instance"), '|');
    }
    #[test]
    fn test_get_no_first_line() {
        assert_eq!(
            get_plain_section_names(),
            (&hash_set(&get_predefined_section_names())
                - &hash_set(&get_decorated_section_names()))
        );
    }
}
