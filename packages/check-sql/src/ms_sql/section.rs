// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self};
use crate::emit::header;
use crate::ms_sql::queries;
use anyhow::Result;

use tiberius::Row;

// section hand-made
pub const INSTANCE_SECTION_NAME: &str = "instance";
pub const COUNTERS_SECTION_NAME: &str = "counters";
pub const BLOCKED_SESSIONS_SECTION_NAME: &str = "blocked_sessions";
pub const BACKUP_SECTION_NAME: &str = "backup";
pub const TRANSACTION_LOG_SECTION_NAME: &str = "transactionlogs";
pub const DATAFILES_SECTION_NAME: &str = "datafiles";
pub const DATABASES_SECTION_NAME: &str = "databases";
pub const CLUSTERS_SECTION_NAME: &str = "clusters";

pub const TABLE_SPACES_SECTION_NAME: &str = "tablespaces";
pub const CONNECTIONS_SECTION_NAME: &str = "connections";

// query based section
pub const JOBS_SECTION_NAME: &str = "jobs";
pub const MIRRORING_SECTION_NAME: &str = "mirroring";
pub const AVAILABILITY_GROUPS_SECTION_NAME: &str = "availability_groups";

const PIPE_SEP_SECTIONS: [&str; 8] = [
    INSTANCE_SECTION_NAME,
    COUNTERS_SECTION_NAME,
    BLOCKED_SESSIONS_SECTION_NAME,
    BACKUP_SECTION_NAME,
    TRANSACTION_LOG_SECTION_NAME,
    DATAFILES_SECTION_NAME,
    DATABASES_SECTION_NAME,
    CLUSTERS_SECTION_NAME,
];

const SPACE_SEP_SECTIONS: [&str; 2] = [TABLE_SPACES_SECTION_NAME, CONNECTIONS_SECTION_NAME];

const QUERY_BASED_SECTIONS: [&str; 3] = [
    JOBS_SECTION_NAME,
    MIRRORING_SECTION_NAME,
    AVAILABILITY_GROUPS_SECTION_NAME,
];

#[derive(Debug, PartialEq)]
pub enum SectionKind {
    Sync,
    Async,
}

pub struct Section {
    name: String,
    sep: Option<char>,
    cache_age: Option<u32>,
}

impl Section {
    pub fn new(name: impl ToString, cache_age: Option<u32>) -> Self {
        let name = name.to_string();
        let sep = get_section_separator(&name);
        Self {
            name,
            sep,
            cache_age,
        }
    }

    pub fn to_header(&self) -> String {
        header(&self.name, self.sep)
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn sep(&self) -> char {
        self.sep.unwrap_or(' ')
    }

    pub fn kind(&self) -> &SectionKind {
        if self.cache_age.is_some() {
            &SectionKind::Async
        } else {
            &SectionKind::Sync
        }
    }

    pub fn cache_age(&self) -> u32 {
        if let Some(v) = self.cache_age {
            v
        } else {
            0
        }
    }

    pub fn first_line<F>(&self, closure: F) -> String
    where
        F: Fn() -> String,
    {
        match self.name.as_ref() {
            JOBS_SECTION_NAME | MIRRORING_SECTION_NAME => closure(),
            _ => "".to_string(),
        }
    }

    pub fn query_selector<'a>(&'a self, custom_query: Option<&'a str>) -> Option<&str> {
        if custom_query.is_some() {
            custom_query
        } else {
            match self.name.as_ref() {
                JOBS_SECTION_NAME => Some(queries::QUERY_JOBS),
                MIRRORING_SECTION_NAME => Some(queries::QUERY_MIRRORING),
                AVAILABILITY_GROUPS_SECTION_NAME => Some(queries::QUERY_AVAILABILITY_GROUP),
                _ => None,
            }
        }
    }

    pub fn main_db(&self) -> Option<String> {
        match self.name.as_ref() {
            JOBS_SECTION_NAME => Some("msdb"),
            MIRRORING_SECTION_NAME => Some("master"),
            _ => None,
        }
        .map(|s| s.to_string())
    }

    pub fn validate_rows(&self, rows: Vec<Vec<Row>>) -> Result<Vec<Vec<Row>>> {
        const ALLOW_TO_HAVE_EMPTY_OUTPUT: [&str; 2] =
            [MIRRORING_SECTION_NAME, AVAILABILITY_GROUPS_SECTION_NAME];
        if (!rows.is_empty() && !rows[0].is_empty())
            || (ALLOW_TO_HAVE_EMPTY_OUTPUT.contains(&self.name()))
        {
            Ok(rows)
        } else {
            log::warn!("No output from query");
            Err(anyhow::anyhow!("No output from query"))
        }
    }
}

pub fn get_work_sections(ms_sql: &config::ms_sql::Config) -> Vec<Section> {
    let sections = ms_sql.sections();
    let mut base: Vec<Section> = sections
        .get_filtered_always()
        .iter()
        .map(|n| Section::new(n, None))
        .collect();
    base.extend(
        sections
            .get_filtered_cached()
            .iter()
            .map(|n| Section::new(n, Some(ms_sql.sections().cache_age()))),
    );
    base
}

fn get_section_separator(name: &str) -> Option<char> {
    match name {
        _ if PIPE_SEP_SECTIONS.contains(&name) => Some('|'),
        _ if SPACE_SEP_SECTIONS.contains(&name) => None,
        _ if QUERY_BASED_SECTIONS.contains(&name) => Some('\t'),
        _ => {
            log::warn!("Unknown section: {}", name);
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ms_sql::Config;

    #[test]
    fn test_work_sections() {
        let config = Config::default();
        assert_eq!(get_work_sections(&config).len(), 13);
    }

    #[test]
    fn test_sections_enabled() {
        const CONFIG: &str = r#"
---
mssql:
  main: # mandatory, to be used if no specific config
    authentication: # mandatory
      username: "f" # mandatory
    sections:
      always: 
      - "instance"
      - "backup"
      cached:
      - "jobs"
      disabled: 
      - "backup"
"#;
        let sections = get_work_sections(&Config::from_string(CONFIG).unwrap().unwrap());
        assert_eq!(
            sections
                .iter()
                .map(|s| (s.name(), s.kind()))
                .collect::<Vec<(&str, &SectionKind)>>(),
            [
                ("instance", &SectionKind::Sync),
                ("jobs", &SectionKind::Async)
            ]
        );
    }

    #[test]
    fn test_known_sections() {
        assert!(get_section_separator("zu").is_none());
        assert!(get_section_separator("tablespaces").is_none());
        assert!(get_section_separator("connections").is_none());
        assert_eq!(get_section_separator("jobs").unwrap(), '\t');
        assert_eq!(get_section_separator("mirroring").unwrap(), '\t');
        assert_eq!(get_section_separator("availability_groups").unwrap(), '\t');
        assert_eq!(get_section_separator("instance").unwrap(), '|');
    }
}
