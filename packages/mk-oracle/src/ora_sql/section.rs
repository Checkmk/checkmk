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

use crate::config::{self, section, section::names};
use crate::emit::{header, signaling_header};
use crate::ora_sql::sqls;
use crate::types::{InstanceName, InstanceNumVersion, ItemValue, SectionName, Tenant};
use crate::types::{SectionAffinity, SqlBindParam, SqlQuery};
use crate::{constants, utils};
use anyhow::Result;
use std::collections::HashMap;
use std::fs::read_to_string;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

#[derive(Debug, PartialEq)]
pub enum SectionKind {
    Sync,
    Async,
}

#[derive(Debug, Clone)]
pub struct Section {
    name: SectionName,
    sep: char,
    cache_age: Option<u32>,
    header_name: String,
    section_affinity: SectionAffinity,
    item_value: Option<ItemValue>,
    inline_sql: Option<String>,
}

impl Section {
    pub fn make_instance_section() -> Self {
        let config_section = config::section::SectionBuilder::new(section::names::INSTANCE).build();
        Self::new(&config_section, 0)
    }

    pub fn new(section: &config::section::Section, global_cache_age: u32) -> Self {
        let cache_age = if section.kind() == config::section::SectionKind::Async {
            Some(global_cache_age)
        } else {
            None
        };
        Self {
            name: section.name().clone(),
            sep: section.sep(),
            cache_age,
            header_name: section.name().clone().into(),
            section_affinity: section.affinity().clone(),
            item_value: section.item_value().cloned(),
            inline_sql: section.sql().map(str::to_owned),
        }
    }

    pub fn to_signaling_header(&self) -> Option<String> {
        if self.header_name.as_str() == section::names::ASM_INSTANCE {
            return None;
        }
        Some(signaling_header(&self.header_name))
    }

    pub fn to_work_header(&self) -> String {
        let real_name = match self.header_name.as_str() {
            names::IO_STATS => names::PERFORMANCE, // IO_STATS is a performance section
            names::ASM_INSTANCE => names::INSTANCE, // ASM_INSTANCE is an instance section
            _ => &self.header_name,
        };
        // For custom-metric sections the cached marker lives on the subsection
        // header (see to_work_header_for); the section header stays plain so
        // the existing oracle_sql server-side parser continues to work.
        let suffix = if self.item_value.is_some() {
            String::new()
        } else {
            self.cached_header()
        };
        header(&(real_name.to_string() + &suffix), self.sep)
    }

    /// Build the instance-aware emit header for this section.
    /// For predefined sections this is just the section header
    /// (`<<<oracle_xxx:sep(N)>>>`). For custom-metric sections it additionally
    /// emits the subsection header `[[[<ORACLE_ID>|<item>]]]`, with `|cached(...)`
    /// appended when the metric is async.
    pub fn to_work_header_for(&self, instance: &InstanceName) -> String {
        let section_header = self.to_work_header();
        match self.item_value.as_ref() {
            None => section_header,
            Some(item) => {
                let cached = self.cached_subsection_suffix();
                format!("{}\n[[[{}|{}{}]]]", section_header, instance, item, cached)
            }
        }
    }

    fn cached_header(&self) -> String {
        self.cache_age
            .map(|age| {
                format!(
                    ":cached({},{})",
                    utils::get_utc_now().unwrap_or_default(),
                    age
                )
            })
            .unwrap_or_default()
    }

    fn cached_subsection_suffix(&self) -> String {
        self.cache_age
            .map(|age| {
                format!(
                    "|cached({},{})",
                    utils::get_utc_now().unwrap_or_default(),
                    age
                )
            })
            .unwrap_or_default()
    }

    pub fn item_value(&self) -> Option<&ItemValue> {
        self.item_value.as_ref()
    }

    pub fn inline_sql(&self) -> Option<&str> {
        self.inline_sql.as_deref()
    }

    pub fn name(&self) -> &SectionName {
        &self.name
    }

    pub fn header_name(&self) -> &str {
        &self.header_name
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
        self.cache_age.unwrap_or_default()
    }

    pub fn affinity(&self) -> &SectionAffinity {
        &self.section_affinity
    }

    pub fn find_queries(
        &self,
        sql_dir: Option<PathBuf>,
        instance_version: InstanceNumVersion,
        tenant: Tenant,
        params: &[SqlBindParam],
    ) -> Option<Vec<SqlQuery>> {
        Some(
            self.inline_sql
                .clone()
                .or_else(|| self.find_custom_query(sql_dir, instance_version))
                .or_else(|| {
                    get_sql_id(&self.header_name)
                        .and_then(|s| Self::find_known_query(s, instance_version, tenant))
                        .map(|s| s.to_owned())
                })?
                .split(';')
                .filter_map(|q| {
                    let trimmed = q.trim();
                    if !trimmed.is_empty() {
                        Some(SqlQuery::new(trimmed, params))
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>(),
        )
    }

    pub fn find_custom_query(
        &self,
        sql_dir: Option<PathBuf>,
        instance_version: InstanceNumVersion,
    ) -> Option<String> {
        let dir = sql_dir?;
        let versioned_files = find_sql_files(&dir, &self.header_name).ok()?;
        versioned_files
            .into_iter()
            .find(|(min_version, _)| instance_version >= InstanceNumVersion::from(*min_version))
            .and_then(|(_, sql_file)| {
                read_to_string(&sql_file)
                    .inspect_err(|e| {
                        log::error!("Can't read file {:?} {}", &sql_file, &e);
                    })
                    .ok()
            })
    }

    fn find_known_query(
        id: sqls::Id,
        version: InstanceNumVersion,
        tenant: Tenant,
    ) -> Option<String> {
        sqls::get_factory_query(id, Some(version), tenant, None)
            .map_err(|e| {
                log::error!("Can't find query {id:?} {e}");
                e
            })
            .ok()
    }
}

fn find_sql_files(dir: &Path, section_name: &str) -> Result<Vec<(u32, PathBuf)>> {
    let mut paths: Vec<(u32, PathBuf)> = std::fs::read_dir(dir)?
        .filter_map(|res| res.ok())
        .map(|dir_entry| dir_entry.path())
        .filter_map(|path| {
            if path
                .extension()
                .is_some_and(|ext| ext == constants::SQL_QUERY_EXTENSION)
            {
                Some(path)
            } else {
                None
            }
        })
        .filter_map(|path| get_file_version(&path, section_name).map(|version| (version, path)))
        .collect::<Vec<_>>();
    paths.sort_by_key(|p| p.0);
    paths.reverse();
    Ok(paths)
}

fn get_file_version(path: &Path, section_name: &str) -> Option<u32> {
    if let Some(stem) = path.file_stem().map(|n| n.to_string_lossy().to_string()) {
        match stem.rsplitn(2, '@').collect::<Vec<&str>>().as_slice() {
            [min_version, name] => {
                if name.to_lowercase() == section_name.to_lowercase() {
                    return Some(min_version.parse::<u32>().unwrap_or(0));
                }
            }
            [stem] => {
                if stem.to_lowercase() == section_name.to_lowercase() {
                    return Some(0);
                }
            }
            _ => {}
        }
    }
    None
}

static SECTION_MAP: LazyLock<HashMap<&'static str, sqls::Id>> = LazyLock::new(|| {
    HashMap::from([
        (names::IO_STATS, sqls::Id::IoStats),
        (names::TS_QUOTAS, sqls::Id::TsQuotas),
        (names::JOBS, sqls::Id::Jobs),
        (names::RESUMABLE, sqls::Id::Resumable),
        (names::UNDO_STAT, sqls::Id::UndoStat),
        (names::RECOVERY_AREA, sqls::Id::RecoveryArea),
        (names::ASM_DISK_GROUP, sqls::Id::AsmDiskGroup),
        (names::LOCKS, sqls::Id::Locks),
        (names::LOG_SWITCHES, sqls::Id::LogSwitches),
        (names::LONG_ACTIVE_SESSIONS, sqls::Id::LongActiveSessions),
        (names::PROCESSES, sqls::Id::Processes),
        (names::RECOVERY_STATUS, sqls::Id::RecoveryStatus),
        (names::RMAN, sqls::Id::Rman),
        (names::SESSIONS, sqls::Id::Sessions),
        (names::SYSTEM_PARAMETER, sqls::Id::SystemParameter),
        (names::TABLESPACES, sqls::Id::TableSpaces),
        (names::DATAGUARD_STATS, sqls::Id::DataGuardStats),
        (names::INSTANCE, sqls::Id::Instance),
        (names::ASM_INSTANCE, sqls::Id::AsmInstance),
        (names::PERFORMANCE, sqls::Id::Performance),
    ])
});

pub fn get_sql_id<T: AsRef<str>>(section_name: T) -> Option<sqls::Id> {
    SECTION_MAP.get(section_name.as_ref()).copied()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::section;

    #[test]
    fn test_section_header() {
        let section = Section::make_instance_section();
        assert_eq!(
            section.to_signaling_header().unwrap(),
            "<<<oracle_instance>>>"
        );
        assert_eq!(section.to_work_header(), "<<<oracle_instance:sep(124)>>>");

        let section = Section::new(
            &section::SectionBuilder::new("backup")
                .set_async(true)
                .build(),
            100,
        );
        assert_eq!(
            section.to_signaling_header().unwrap(),
            "<<<oracle_backup>>>"
        );
        assert!(section
            .to_work_header()
            .starts_with("<<<oracle_backup:cached("));
        assert!(section.to_work_header().ends_with("100):sep(124)>>>"));

        let section = Section::new(&section::SectionBuilder::new("jobs").build(), 100);
        assert!(section
            .to_work_header()
            .starts_with("<<<oracle_jobs:cached("));
        let section = Section::new(
            &section::SectionBuilder::new("jobs")
                .set_async(false)
                .build(),
            100,
        );
        assert_eq!(section.to_work_header(), "<<<oracle_jobs:sep(124)>>>");
    }

    /// We test only few parameters
    #[test]
    fn test_get_ids() {
        assert_eq!(get_sql_id(names::IO_STATS).unwrap(), sqls::Id::IoStats);
        // TODO: add all..
        assert!(get_sql_id("").is_none());
    }

    fn make_custom_metric_section(name: &str, async_: bool, cache_age: u32) -> Section {
        let item = ItemValue::from(name.to_string());
        let mut builder = section::SectionBuilder::new(name)
            .sql("select 'details:hi' from dual")
            .set_item_value(item);
        if async_ {
            builder = builder.set_async(true);
        }
        Section::new(&builder.build(), cache_age)
    }

    #[test]
    fn test_custom_metric_section_header_uses_sep_58() {
        let sync = make_custom_metric_section("product_price", false, 600);
        assert_eq!(sync.to_work_header(), "<<<oracle_sql:sep(58)>>>");

        // Even for an async metric, the section header stays plain — the
        // cached(...) marker lives on the subsection header per tech design.
        let async_ = make_custom_metric_section("last_sessions", true, 600);
        assert_eq!(async_.to_work_header(), "<<<oracle_sql:sep(58)>>>");
    }

    #[test]
    fn test_custom_metric_work_header_for_includes_subsection() {
        let sync = make_custom_metric_section("product_price", false, 600);
        let header = sync.to_work_header_for(&InstanceName::from("ORCL"));
        assert_eq!(header, "<<<oracle_sql:sep(58)>>>\n[[[ORCL|product_price]]]");
    }

    #[test]
    fn test_async_cached_marker_lives_on_subsection_header() {
        let async_ = make_custom_metric_section("last_sessions", true, 600);
        let header = async_.to_work_header_for(&InstanceName::from("ORCL"));
        // section header must not carry cached(...)
        assert!(header.starts_with("<<<oracle_sql:sep(58)>>>\n"));
        // subsection header must carry cached(...,600)]]] suffix
        assert!(
            header.contains("[[[ORCL|last_sessions|cached("),
            "subsection header missing cached marker: {header}"
        );
        assert!(header.ends_with(",600)]]]"), "unexpected tail: {header}");
    }

    #[test]
    fn test_inline_sql_takes_precedence_over_file_lookup() {
        let cfg_section = section::SectionBuilder::new("product_price")
            .sql("select 'details:inline' from dual")
            .set_item_value(ItemValue::from("product_price".to_string()))
            .build();
        let runtime = Section::new(&cfg_section, 0);
        let queries = runtime
            .find_queries(
                None, // no sql_dir -> file lookup is a no-op
                InstanceNumVersion::from(0),
                Tenant::All,
                &[],
            )
            .expect("inline sql should yield queries");
        assert_eq!(queries.len(), 1);
        assert_eq!(queries[0].as_str(), "select 'details:inline' from dual");
    }
}
