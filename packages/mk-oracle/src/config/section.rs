// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::defines::{defaults, keys};
use super::yaml::{Get, Yaml};
use anyhow::Result;
use log;

// "tablespaces", "rman", "jobs", "ts_quotas", "resumable", "locks"
pub mod names {
    pub const INSTANCE: &str = "instance";
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
}

#[derive(Debug, PartialEq, Copy, Clone)]
pub enum SectionKind {
    Sync,
    Async,
    Disabled,
}

const PREDEFINED_SECTIONS: [&str; 18] = [
    names::INSTANCE,
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
];

const PREDEFINED_ASYNC_SECTIONS: [&str; 6] = [
    names::TABLESPACES,
    names::RMAN,
    names::JOBS,
    names::RESUMABLE,
    names::IO_STATS,
    names::ASM_DISK_GROUP,
];

#[allow(dead_code)]
const ASM_SECTIONS: [&str; 3] = [names::INSTANCE, names::PROCESSES, names::ASM_DISK_GROUP];

#[derive(PartialEq, Debug, Clone)]
pub enum SectionAffinity {
    All,
    Db,
    Asm,
}

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
    affinity: SectionAffinity,
}

impl SectionBuilder {
    pub fn new<S: Into<String>>(name: S) -> Self {
        let name = name.into();
        let is_async = PREDEFINED_ASYNC_SECTIONS.contains(&name.as_str());
        Self {
            name,
            sep: defaults::DEFAULT_SEP,
            is_async,
            is_disabled: false,
            sql: None,
            affinity: SectionAffinity::Db,
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
            affinity: self.affinity,
        }
    }
}

#[derive(PartialEq, Debug, Clone)]
pub struct Section {
    name: String,
    sep: char,
    kind: SectionKind,
    sql: Option<String>,
    affinity: SectionAffinity,
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

    pub fn affinity(&self) -> &SectionAffinity {
        &self.affinity
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

        let affinity = yaml
            .get_string(keys::AFFINITY)
            .map(SectionAffinity::from_text)
            .unwrap_or(SectionAffinity::Db);

        if yaml.get_optional_bool(keys::DISABLED) == Some(true) {
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::test_tools::create_yaml;
    use std::collections::HashSet;

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
                .map(|s| (s.name(), s.sep()))
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
            .map(|s| s.name())
            .collect::<Vec<&str>>();
        assert_eq!(asyncs, PREDEFINED_ASYNC_SECTIONS);

        assert_eq!(s.cache_age(), defaults::SECTIONS_CACHE_AGE);

        assert_eq!(
            Sections::from_yaml(&create_yaml("_sections:\n"), &Sections::default())
                .unwrap()
                .sections()
                .len(),
            18
        );
    }

    fn create_sections_yaml_default() -> Yaml {
        const SOURCE: &str = r#"
sections:
_nothing: "nothing"
"#;
        create_yaml(SOURCE)
    }
}
