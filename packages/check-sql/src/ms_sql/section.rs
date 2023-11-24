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
pub const TABLE_SPACES_SECTION_NAME: &str = "tablespaces";
pub const BACKUP_SECTION_NAME: &str = "backup";
pub const TRANSACTION_LOG_SECTION_NAME: &str = "transactionlogs";
pub const DATAFILES_SECTION_NAME: &str = "datafiles";
pub const DATABASES_SECTION_NAME: &str = "databases";
pub const CLUSTERS_SECTION_NAME: &str = "clusters";
pub const CONNECTIONS_SECTION_NAME: &str = "connections";

// query based section
pub const JOBS_SECTION_NAME: &str = "jobs";
pub const MIRRORING_SECTION_NAME: &str = "mirroring";
pub const AVAILABILITY_GROUPS_SECTION_NAME: &str = "availability_groups";

pub struct Section {
    name: String,
    sep: Option<char>,
}

impl Section {
    pub fn new(name: impl ToString) -> Self {
        let name = name.to_string();
        let sep = get_section_separator(&name);
        Self { name, sep }
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
            Err(anyhow::anyhow!("No output from query"))
        }
    }
}

pub fn get_work_sections(ms_sql: &config::ms_sql::Config) -> Vec<Section> {
    let sections = ms_sql.sections();
    let mut base: Vec<Section> = sections
        .get_filtered_always()
        .iter()
        .map(Section::new)
        .collect();
    base.extend(sections.get_filtered_cached().iter().map(Section::new));
    base
}

fn get_section_separator(name: &str) -> Option<char> {
    match name {
        "instance" | "databases" | "counters" | "blocked_sessions" | "transactionlogs"
        | "datafiles" | "clusters" | "backup" => Some('|'),
        "jobs" | "mirroring" | "availability_groups" => Some('\t'),
        "tablespaces" | "connections" => None,
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ms_sql::Config;

    #[tokio::test(flavor = "multi_thread")]
    async fn test_work_sections() {
        let config = Config::default();
        assert_eq!(get_work_sections(&config).len(), 13);
    }
}
