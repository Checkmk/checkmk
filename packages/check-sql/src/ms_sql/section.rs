// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, section};
use crate::emit::header;
use crate::ms_sql::sqls;
use crate::utils;
use anyhow::Result;

use tiberius::Row;

#[derive(Debug, PartialEq)]
pub enum SectionKind {
    Sync,
    Async,
}

#[derive(Debug, Clone)]
pub struct Section {
    name: String,
    sep: Option<char>,
    cache_age: Option<u32>,
}

impl Section {
    pub fn make_instance_section() -> Self {
        let name = section::names::INSTANCE.to_string();
        let sep = section::get_default_separator(&name);
        Self {
            name,
            sep,
            cache_age: None,
        }
    }

    pub fn new(section: &config::section::Section, cache_age: u32) -> Self {
        let cache_age = if section.kind() == config::section::SectionKind::Async {
            Some(cache_age)
        } else {
            None
        };
        Self {
            name: section.name().into(),
            sep: section.sep().into(),
            cache_age,
        }
    }

    pub fn to_plain_header(&self) -> String {
        header(&self.name, self.sep)
    }

    pub fn to_work_header(&self) -> String {
        header(&(self.name.clone() + &self.cached_header()), self.sep)
    }

    fn cached_header(&self) -> String {
        self.cache_age
            .map(|age| {
                format!(
                    ":cached({}:{})",
                    utils::get_utc_now().unwrap_or_default(),
                    age
                )
            })
            .unwrap_or_default()
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
            section::names::JOBS | section::names::MIRRORING => closure(),
            _ => "".to_string(),
        }
    }

    pub fn query_selector<'a>(&'a self, custom_query: Option<&'a str>) -> Option<&str> {
        if custom_query.is_some() {
            custom_query
        } else {
            match self.name.as_ref() {
                section::names::JOBS => Some(sqls::QUERY_JOBS),
                section::names::MIRRORING => Some(sqls::QUERY_MIRRORING),
                section::names::AVAILABILITY_GROUPS => Some(sqls::QUERY_AVAILABILITY_GROUP),
                _ => None,
            }
        }
    }

    pub fn main_db(&self) -> Option<String> {
        match self.name.as_ref() {
            section::names::JOBS => Some("msdb"),
            section::names::MIRRORING => Some("master"),
            _ => None,
        }
        .map(|s| s.to_string())
    }

    pub fn validate_rows(&self, rows: Vec<Vec<Row>>) -> Result<Vec<Vec<Row>>> {
        const ALLOW_TO_HAVE_EMPTY_OUTPUT: [&str; 2] = [
            section::names::MIRRORING,
            section::names::AVAILABILITY_GROUPS,
        ];
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ms_sql::Config;
    use crate::config::section;

    #[test]
    fn test_section_header() {
        let section = Section::make_instance_section();
        assert_eq!(section.to_plain_header(), "<<<mssql_instance:sep(124)>>>\n");
        assert_eq!(section.to_work_header(), "<<<mssql_instance:sep(124)>>>\n");

        let section = Section::new(
            &section::SectionBuilder::new("backup").set_async().build(),
            100,
        );
        assert_eq!(section.to_plain_header(), "<<<mssql_backup:sep(124)>>>\n");
        assert!(section
            .to_work_header()
            .starts_with("<<<mssql_backup:cached("));
        assert!(section.to_work_header().ends_with("100):sep(124)>>>\n"));
    }

    #[test]
    fn test_work_sections() {
        let config = Config::default();
        assert_eq!(config.all_sections().len(), 13);
    }
}
