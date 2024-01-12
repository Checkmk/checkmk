// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{self, section, section::names};
use crate::emit::header;
use crate::ms_sql::sqls;
use crate::utils;
use anyhow::Result;
use std::collections::HashMap;

use tiberius::Row;

#[derive(Debug, PartialEq)]
pub enum SectionKind {
    Sync,
    Async,
}

#[derive(Debug, Clone)]
pub struct Section {
    name: String,
    sep: char,
    cache_age: Option<u32>,
}

impl Section {
    pub fn make_instance_section() -> Self {
        let config_section = config::section::SectionBuilder::new(section::names::INSTANCE).build();
        Self {
            name: config_section.name().to_string(),
            sep: config_section.sep(),
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
            sep: section.sep(),
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
        self.sep
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

    pub fn select_query(&self) -> Option<&str> {
        match self.name.as_ref() {
            section::names::JOBS
            | section::names::MIRRORING
            | section::names::AVAILABILITY_GROUPS => get_sql_ids(&self.name)
                .unwrap_or_default()
                .first()
                .and_then(Self::get_query),
            _ => None,
        }
    }

    fn get_query(id: &sqls::Id) -> Option<&str> {
        sqls::get_query(id)
            .map_err(|e| {
                log::error!("{e}");
                e
            })
            .ok()
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

lazy_static::lazy_static! {
    static ref SECTION_MAP: HashMap<&'static str, &'static[sqls::Id]> = HashMap::from([
        (names::INSTANCE, [sqls::Id::InstanceProperties].as_slice()),
        (names::COUNTERS, [sqls::Id::Counters].as_slice()),
        (names::BACKUP, [sqls::Id::Backup].as_slice()),
        (names::BLOCKED_SESSIONS, [sqls::Id::BlockingSessions].as_slice()),
        (names::DATABASES, [sqls::Id::Databases].as_slice()),
        (names::CONNECTIONS, [sqls::Id::Connections].as_slice()),

        (names::TRANSACTION_LOG, [sqls::Id::TransactionLogs].as_slice()),
        (names::DATAFILES, [sqls::Id::Datafiles].as_slice()),
        (names::TABLE_SPACES, [sqls::Id::SpaceUsed].as_slice()),
        (names::CLUSTERS, [sqls::Id::ClusterActiveNodes, sqls::Id::ClusterNodes].as_slice()),

        (names::JOBS, [sqls::Id::Jobs].as_slice()),
        (names::MIRRORING, [sqls::Id::Mirroring].as_slice()),
        (names::AVAILABILITY_GROUPS, [sqls::Id::AvailabilityGroups].as_slice()),
    ]);
}

pub fn get_sql_ids<T: AsRef<str>>(section_name: T) -> Result<&'static [sqls::Id]> {
    SECTION_MAP
        .get(section_name.as_ref())
        .copied()
        .ok_or(anyhow::anyhow!(
            "Query for {:?} not found",
            section_name.as_ref()
        ))
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
    fn test_section_select_query() {
        let mk_section =
            |name: &str| Section::new(&config::section::SectionBuilder::new(name).build(), 100);
        let test_set: &[(&str, Option<&str>)] = &[
            (names::INSTANCE, None),
            (names::DATABASES, None),
            (names::COUNTERS, None),
            (names::BLOCKED_SESSIONS, None),
            (names::TRANSACTION_LOG, None),
            (names::CLUSTERS, None),
            (
                names::MIRRORING,
                Some(sqls::get_query(&sqls::Id::Mirroring).unwrap()),
            ),
            (
                names::AVAILABILITY_GROUPS,
                Some(sqls::get_query(&sqls::Id::AvailabilityGroups).unwrap()),
            ),
            (names::CONNECTIONS, None),
            (names::TABLE_SPACES, None),
            (names::DATAFILES, None),
            (names::BACKUP, None),
            (names::JOBS, Some(sqls::get_query(&sqls::Id::Jobs).unwrap())),
        ];
        for (name, ids) in test_set {
            assert_eq!(mk_section(name).select_query(), *ids);
        }
    }

    #[test]
    fn test_work_sections() {
        let config = Config::default();
        assert_eq!(config.all_sections().len(), 13);
    }

    /// We test only few parameters
    #[test]
    fn test_get_ids() {
        assert_eq!(get_sql_ids(names::JOBS).unwrap(), [sqls::Id::Jobs]);
        assert_eq!(
            get_sql_ids(section::names::MIRRORING).unwrap(),
            [sqls::Id::Mirroring]
        );
        assert_eq!(
            get_sql_ids(names::AVAILABILITY_GROUPS).unwrap(),
            [sqls::Id::AvailabilityGroups]
        );
        assert_eq!(get_sql_ids(names::COUNTERS).unwrap(), [sqls::Id::Counters]);
        assert_eq!(
            get_sql_ids(names::CONNECTIONS).unwrap(),
            [sqls::Id::Connections]
        );
        assert!(get_sql_ids("").is_err());
    }
}
