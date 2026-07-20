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
use crate::ora_sql::custom;
use crate::ora_sql::sqls;
use crate::setup::validate_permissions;
use crate::types::{InstanceName, InstanceNumVersion, ItemValue, PdbName, SectionName, Tenant};
use crate::types::{SectionAffinity, SqlBindParam, SqlQuery};
use crate::{constants, utils};
use anyhow::Result;
use regex::Regex;
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
    sql_params: Vec<(String, String)>,
    path: Option<PathBuf>,
    pdb_patterns: Vec<Regex>,
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
            sql_params: section.sql_params().to_vec(),
            path: section.path().map(Path::to_path_buf),
            pdb_patterns: section
                .pdb_patterns()
                .iter()
                .filter_map(|p| match Regex::new(&format!("(?i)^{p}$")) {
                    Ok(r) => Some(r),
                    Err(e) => {
                        log::warn!("Invalid PDB pattern {p:?}: {e}");
                        None
                    }
                })
                .collect(),
        }
    }

    pub fn to_signaling_header(&self) -> Option<String> {
        if self.header_name.as_str() == section::names::ASM_INSTANCE {
            return None;
        }
        Some(signaling_header(&self.header_name))
    }

    pub fn pdb_patterns(&self) -> &[Regex] {
        &self.pdb_patterns
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

    pub fn to_work_header_for_pdb(&self, instance: &InstanceName, pdb: &PdbName) -> String {
        let section_header = self.to_work_header();
        match self.item_value.as_ref() {
            None => section_header,
            Some(item) => {
                let cached = self.cached_subsection_suffix();
                format!(
                    "{}\n[[[{}_{}|{}{}]]]",
                    section_header, instance, pdb, item, cached
                )
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

    pub fn path(&self) -> Option<&Path> {
        self.path.as_deref()
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
        instance_version: InstanceNumVersion,
        tenant: Tenant,
        params: &[SqlBindParam],
    ) -> Option<Vec<SqlQuery>> {
        self.find_queries_with_search_dirs(
            instance_version,
            tenant,
            params,
            &custom::get_sql_search_dirs(),
        )
    }

    /// Same as [`Section::find_queries`], but with explicit search roots for
    /// relative `path:` resolution instead of the environment-derived
    /// [`custom::get_sql_search_dirs`].
    ///
    /// This is the seam used by the component tests: they inject fixture
    /// directories directly, so the `path:` resolver can be exercised without
    /// mutating `MK_CONFDIR` / `MK_LIBDIR` (and the `LazyLock`-backed globals
    /// derived from them).
    pub fn find_queries_with_search_dirs(
        &self,
        instance_version: InstanceNumVersion,
        tenant: Tenant,
        params: &[SqlBindParam],
        search_dirs: &[PathBuf],
    ) -> Option<Vec<SqlQuery>> {
        let body = self
            .resolve_path_query(instance_version, search_dirs)
            .or_else(|| self.inline_sql.clone())
            .or_else(|| {
                get_sql_id(&self.header_name)
                    .and_then(|s| Self::find_known_query(s, instance_version, tenant))
                    .map(|s| s.to_owned())
            })?;
        Some(split_into_queries(
            &apply_sql_params(body, &self.sql_params),
            params,
        ))
    }

    /// Resolve the SQL body when the section has a user-supplied `path:`.
    ///
    /// * Absolute paths use the path as the only search root.
    /// * Relative paths are joined under each entry of `search_dirs` (in
    ///   production: runtime directory first, config directory second), so the
    ///   first matching root wins on collisions.
    /// * If path is not set, we set path to "" and treat it as a relative path,
    ///   so the search roots are still used.
    ///
    /// Each candidate may be either a file or a directory;
    /// in the directory case the lookup stem is the custom-metric item name
    /// (or the section header name for predefined sections). Version variants
    /// follow the `<name>@<min_version>.sql` convention.
    fn resolve_path_query(
        &self,
        instance_version: InstanceNumVersion,
        search_dirs: &[PathBuf],
    ) -> Option<String> {
        let path = self.path.as_deref().unwrap_or(Path::new(""));
        let candidates: Vec<PathBuf> = if path.is_absolute() {
            vec![path.to_path_buf()]
        } else {
            search_dirs.iter().map(|root| root.join(path)).collect()
        };

        match candidates
            .iter()
            .find_map(|candidate| self.resolve_candidate(candidate, instance_version))
        {
            Some((sql_file, contents)) => {
                log::info!(
                    "Resolved `path:` {:?} for section '{}' to SQL file {:?}",
                    path,
                    self.item_value
                        .as_ref()
                        .map(|iv| iv.as_str())
                        .unwrap_or(&self.header_name),
                    &sql_file
                );
                Some(contents)
            }
            None => {
                log::info!(
                    "Could not find a SQL file for section '{}' at the provided `path:` \
                    {:?}; tried candidates {:?}",
                    self.item_value
                        .as_ref()
                        .map(|iv| iv.as_str())
                        .unwrap_or(&self.header_name),
                    path,
                    &candidates
                );
                None
            }
        }
    }

    fn resolve_candidate(
        &self,
        candidate: &Path,
        instance_version: InstanceNumVersion,
    ) -> Option<(PathBuf, String)> {
        let (dir, stem): (PathBuf, String) = if candidate.is_dir() {
            (
                candidate.to_path_buf(),
                self.directory_lookup_stem().to_owned(),
            )
        } else {
            let parent = candidate.parent()?.to_path_buf();
            let stem = candidate.file_stem()?.to_str()?.to_owned();
            (parent, stem)
        };
        read_versioned_query(&dir, &stem, instance_version)
    }

    /// Stem used when `path:` resolves to a directory: the custom-metric item
    /// name for custom metrics, the section header name otherwise.
    fn directory_lookup_stem(&self) -> &str {
        self.item_value
            .as_ref()
            .map(|iv| iv.as_str())
            .unwrap_or(&self.header_name)
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

/// Substitute the `${name}` placeholders of the section's `sql_params` in the
/// SQL body.
fn apply_sql_params(sql: String, sql_params: &[(String, String)]) -> String {
    sql_params.iter().fold(sql, |body, (name, value)| {
        body.replace(&format!("${{{name}}}"), value)
    })
}

/// Look up a SQL file in `dir` whose name matches `stem` (optionally with a
/// `@<min_version>` suffix) and return the highest-version contents that fit
/// `instance_version`.
fn read_versioned_query(
    dir: &Path,
    stem: &str,
    instance_version: InstanceNumVersion,
) -> Option<(PathBuf, String)> {
    let versioned_files = find_sql_files(dir, stem).ok()?;
    versioned_files
        .into_iter()
        .find(|(min_version, _)| instance_version >= InstanceNumVersion::from(*min_version))
        .and_then(|(_, sql_file)| {
            if !validate_permissions(&sql_file) {
                log::warn!("SQL file {:?} rejected: wrong permissions", &sql_file);
                return None;
            }
            read_to_string(&sql_file)
                .inspect_err(|e| {
                    log::error!("Can't read file {:?} {}", &sql_file, &e);
                })
                .ok()
                .map(|contents| (sql_file, contents))
        })
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

/// Split a SQL script into statements on top-level `;` terminators.
///
/// A `;` ends a statement only in ordinary SQL text — not inside a
/// single-quoted string literal, a `"..."` quoted identifier, a `--` line
/// comment, or a `/* ... */` block comment. This keeps statements such as
/// `SELECT 'a;b' FROM dual` and `SELECT 1 AS "a;b" FROM dual` intact.
fn split_sql_statements(sql: &str) -> Vec<&str> {
    enum State {
        Normal,
        InString,
        InQuotedIdentifier,
        InLineComment,
        InBlockComment,
    }

    let mut statements: Vec<&str> = Vec::new();
    let mut state = State::Normal;
    let mut start = 0usize;
    let mut chars = sql.char_indices().peekable();

    while let Some((i, c)) = chars.next() {
        match state {
            State::Normal => match c {
                '\'' => state = State::InString,
                '"' => state = State::InQuotedIdentifier,
                ';' => {
                    statements.push(&sql[start..i]);
                    start = i + 1; // `;` is a single ASCII byte
                }
                '-' if matches!(chars.peek(), Some((_, '-'))) => {
                    chars.next(); // consume the second `-`
                    state = State::InLineComment;
                }
                '/' if matches!(chars.peek(), Some((_, '*'))) => {
                    chars.next(); // consume the `*`
                    state = State::InBlockComment;
                }
                _ => {}
            },
            State::InString => {
                if c == '\'' {
                    // A doubled `''` is an escaped quote: stay in the string.
                    if matches!(chars.peek(), Some((_, '\''))) {
                        chars.next();
                    } else {
                        state = State::Normal;
                    }
                }
            }
            State::InQuotedIdentifier => {
                // Oracle quoted identifiers cannot themselves contain a `"`, so
                // the next `"` always ends the identifier.
                if c == '"' {
                    state = State::Normal;
                }
            }
            State::InLineComment => {
                if c == '\n' {
                    state = State::Normal;
                }
            }
            State::InBlockComment => {
                if c == '*' && matches!(chars.peek(), Some((_, '/'))) {
                    chars.next(); // consume the `/`
                    state = State::Normal;
                }
            }
        }
    }

    // Trailing remainder after the last `;` (or the whole input if there is
    // none), mirroring the final segment `str::split(';')` always yields.
    statements.push(&sql[start..]);
    statements
}

/// Split a SQL script into the non-empty [`SqlQuery`] statements it contains,
/// binding `params` into each.
pub fn split_into_queries(sql: &str, params: &[SqlBindParam]) -> Vec<SqlQuery> {
    split_sql_statements(sql)
        .into_iter()
        .filter_map(|q| {
            let trimmed = q.trim();
            if !trimmed.is_empty() {
                Some(SqlQuery::new(trimmed, params))
            } else {
                None
            }
        })
        .collect()
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

    // TC-ORA-101 (Param: plain <<<oracle_sql:sep(58)>>> header, sync and async)
    #[test]
    fn test_custom_metric_section_header_uses_sep_58() {
        let sync = make_custom_metric_section("product_price", false, 600);
        assert_eq!(sync.to_work_header(), "<<<oracle_sql:sep(58)>>>");

        // Even for an async metric, the section header stays plain — the
        // cached(...) marker lives on the subsection header per tech design.
        let async_ = make_custom_metric_section("last_sessions", true, 600);
        assert_eq!(async_.to_work_header(), "<<<oracle_sql:sep(58)>>>");
    }

    // TC-ORA-101 (Param: subsection header carries the item_name -> [[[<SID>|<item>]]])
    #[test]
    fn test_custom_metric_work_header_for_includes_subsection() {
        let sync = make_custom_metric_section("product_price", false, 600);
        let header = sync.to_work_header_for(&InstanceName::from("ORCL"));
        assert_eq!(header, "<<<oracle_sql:sep(58)>>>\n[[[ORCL|product_price]]]");
    }

    // TC-ORA-101 (Param: PDB instance type -> [[[<SID>_<PDB>|<item>]]])
    #[test]
    fn test_work_header_for_pdb_includes_pdb_in_subsection() {
        let section = make_custom_metric_section("product_price", false, 0);
        let header =
            section.to_work_header_for_pdb(&InstanceName::from("ORCL"), &PdbName::from("MYPDB"));
        assert_eq!(
            header,
            "<<<oracle_sql:sep(58)>>>\n[[[ORCL_MYPDB|product_price]]]"
        );
    }

    // TC-ORA-101 (Param: PDB instance type + async -> cached marker on the PDB subsection)
    #[test]
    fn test_work_header_for_pdb_async_includes_cached_marker() {
        let section = make_custom_metric_section("last_sessions", true, 600);
        let header =
            section.to_work_header_for_pdb(&InstanceName::from("ORCL"), &PdbName::from("MYPDB"));
        assert!(header.starts_with("<<<oracle_sql:sep(58)>>>\n[[[ORCL_MYPDB|last_sessions|cached("));
        assert!(header.ends_with(",600)]]]"));
    }

    // TC-ORA-101 (Param: async -> cached marker on subsection, not section header)
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
        let section_config = section::SectionBuilder::new("product_price")
            .sql("select 'details:inline' from dual")
            .set_item_value(ItemValue::from("product_price".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        let queries = runtime
            .find_queries(InstanceNumVersion::from(0), Tenant::All, &[])
            .expect("inline sql should yield queries");
        assert_eq!(queries.len(), 1);
        assert_eq!(queries[0].as_str(), "select 'details:inline' from dual");
    }

    // TC-ORA-150
    #[test]
    fn test_yaml_inline_sql_overrides_builtin_instance_query() {
        // Start from the YAML a user would actually write, so the whole chain
        // config parsing -> runtime section -> query resolution is covered.
        let config = config::ora_sql::Config::from_string(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          sql: "select 'details:overridden-instance' from dual"
"#,
        )
        .expect("yaml parses")
        .expect("oracle config present");
        let section_config = config
            .all_sections()
            .iter()
            .find(|s| s.name().as_str() == names::INSTANCE)
            .expect("instance section parsed from yaml");
        let overridden = Section::new(section_config, 0);
        // Empty search dirs: nothing on disk may shadow the inline `sql:`.
        let queries = overridden
            .find_queries_with_search_dirs(InstanceNumVersion::from(0), Tenant::All, &[], &[])
            .expect("sql: override should yield queries");
        assert_eq!(queries.len(), 1);
        assert_eq!(
            queries[0].as_str(),
            "select 'details:overridden-instance' from dual"
        );
        // Header stays the built-in's, not redirected to the custom-metric
        // `oracle_sql:sep(58)` header used for `custom_metrics:`.
        assert_eq!(
            overridden.to_work_header(),
            "<<<oracle_instance:sep(124)>>>"
        );
        assert!(
            overridden.pdb_patterns().is_empty(),
            "override runs against CDB only (no PDB targeting)"
        );
    }

    #[test]
    fn test_sql_params_patched_into_inline_sql() {
        let section_config = section::SectionBuilder::new("test")
            .sql("SELECT ${parameter_1} FROM dual; SELECT ${parameter_2} FROM dual")
            .sql_params(vec![
                ("parameter_1".to_string(), "value_1".to_string()),
                ("parameter_2".to_string(), "value_2".to_string()),
            ])
            .set_item_value(ItemValue::from("test".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        let queries = runtime
            .find_queries(InstanceNumVersion::from(0), Tenant::All, &[])
            .expect("inline sql should yield queries");
        assert_eq!(queries.len(), 2);
        assert_eq!(queries[0].as_str(), "SELECT value_1 FROM dual");
        assert_eq!(queries[1].as_str(), "SELECT value_2 FROM dual");
    }

    #[test]
    fn test_sql_params_unknown_placeholder_left_untouched() {
        let section_config = section::SectionBuilder::new("test")
            .sql("SELECT ${parameter_1}, ${no_such_param} FROM dual")
            .sql_params(vec![("parameter_1".to_string(), "value_1".to_string())])
            .set_item_value(ItemValue::from("test".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        let queries = runtime
            .find_queries(InstanceNumVersion::from(0), Tenant::All, &[])
            .expect("inline sql should yield queries");
        assert_eq!(
            queries[0].as_str(),
            "SELECT value_1, ${no_such_param} FROM dual"
        );
    }

    #[test]
    fn test_sql_params_repeated_placeholder_replaced_everywhere() {
        let section_config = section::SectionBuilder::new("test")
            .sql("SELECT ${p} FROM t WHERE c = ${p}")
            .sql_params(vec![("p".to_string(), "42".to_string())])
            .set_item_value(ItemValue::from("test".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        let queries = runtime
            .find_queries(InstanceNumVersion::from(0), Tenant::All, &[])
            .expect("inline sql should yield queries");
        assert_eq!(queries[0].as_str(), "SELECT 42 FROM t WHERE c = 42");
    }

    // end-to-end: yaml -> config section -> runtime section -> patched queries
    #[test]
    fn test_yaml_sql_params_patch_custom_metric_queries() {
        let config = config::ora_sql::Config::from_string(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - test:
          sql: "SELECT ${parameter_1} FROM dual; SELECT ${parameter_2} FROM dual"
          sql_params:
            parameter_1: "value_1"
            parameter_2: "value_2"
"#,
        )
        .expect("yaml parses")
        .expect("oracle config present");
        let section_config = config
            .all_sections()
            .iter()
            .find(|s| s.is_custom_metric())
            .expect("custom metric parsed from yaml");
        let runtime = Section::new(section_config, 0);
        let queries = runtime
            .find_queries_with_search_dirs(InstanceNumVersion::from(0), Tenant::All, &[], &[])
            .expect("custom metric sql should yield queries");
        assert_eq!(queries.len(), 2);
        assert_eq!(queries[0].as_str(), "SELECT value_1 FROM dual");
        assert_eq!(queries[1].as_str(), "SELECT value_2 FROM dual");
    }

    #[test]
    fn test_custom_metric_path_propagated_to_runtime_section() {
        let section_config = section::SectionBuilder::new("product_price")
            .path("queries/product_price.sql")
            .set_item_value(ItemValue::from("product_price".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        assert_eq!(runtime.path(), Some(Path::new("queries/product_price.sql")));
        assert!(runtime.path().is_some_and(|p| p.is_relative()));
        assert!(runtime.inline_sql().is_none());
    }

    #[test]
    fn test_predefined_section_path_propagated_to_runtime_section() {
        let section_config = section::SectionBuilder::new("instance")
            .path("/opt/checkmk/sql/instance.sql")
            .build();
        let runtime = Section::new(&section_config, 0);
        assert_eq!(
            runtime.path(),
            Some(Path::new("/opt/checkmk/sql/instance.sql"))
        );
    }

    #[test]
    fn test_section_path_and_inline_sql_both_propagated() {
        let section_config = section::SectionBuilder::new("mixed")
            .path("queries/mixed.sql")
            .sql("select 'details:fallback' from dual")
            .set_item_value(ItemValue::from("mixed".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        assert_eq!(runtime.path(), Some(Path::new("queries/mixed.sql")));
        assert_eq!(
            runtime.inline_sql(),
            Some("select 'details:fallback' from dual")
        );
    }

    fn section_with_pdb_patterns(patterns: &[&str]) -> Section {
        let config = section::SectionBuilder::new("test")
            .set_pdb_patterns(patterns.iter().map(|s| s.to_string()).collect())
            .build();
        Section::new(&config, 0)
    }

    #[test]
    fn test_pdb_patterns_compiled_anchored() {
        let pats = section_with_pdb_patterns(&["PDB1"]).pdb_patterns().to_vec();
        assert!(pats[0].is_match("PDB1"));
        assert!(!pats[0].is_match("PDB10")); // anchored: no partial match
    }

    #[test]
    fn test_pdb_patterns_compiled_case_insensitive() {
        let pats = section_with_pdb_patterns(&["freepdb1"])
            .pdb_patterns()
            .to_vec();
        assert!(pats[0].is_match("FREEPDB1"));
        assert!(pats[0].is_match("freepdb1"));
    }

    #[test]
    fn test_invalid_pdb_pattern_filtered_out() {
        // "[invalid" is not a valid regex; only the valid pattern should survive
        let section = section_with_pdb_patterns(&["[invalid", "PDB1"]);
        assert_eq!(section.pdb_patterns().len(), 1);
        assert!(section.pdb_patterns()[0].is_match("PDB1"));
    }

    #[test]
    fn test_pdb_patterns_suffix_wildcard() {
        let pats = section_with_pdb_patterns(&["FREE.*"])
            .pdb_patterns()
            .to_vec();
        assert!(pats[0].is_match("FREEPDB1"));
        assert!(pats[0].is_match("FREEPDB2"));
        assert!(!pats[0].is_match("TESTPDB"));
    }

    #[test]
    fn test_pdb_patterns_prefix_wildcard() {
        let pats = section_with_pdb_patterns(&[".*PDB"])
            .pdb_patterns()
            .to_vec();
        assert!(pats[0].is_match("TESTPDB"));
        assert!(!pats[0].is_match("FREEPDB1")); // ends in digit, not PDB
    }

    #[test]
    fn test_pdb_patterns_grouped_alternation() {
        // Users must group alternations: "(A|B)" not "A|B"
        let pats = section_with_pdb_patterns(&["(FREEPDB1|XEPDB1)"])
            .pdb_patterns()
            .to_vec();
        assert!(pats[0].is_match("FREEPDB1"));
        assert!(pats[0].is_match("XEPDB1"));
        assert!(!pats[0].is_match("TESTPDB"));
    }

    #[test]
    fn test_pdb_patterns_character_class() {
        let pats = section_with_pdb_patterns(&["PDB[123]"])
            .pdb_patterns()
            .to_vec();
        assert!(pats[0].is_match("PDB1"));
        assert!(pats[0].is_match("PDB2"));
        assert!(pats[0].is_match("PDB3"));
        assert!(!pats[0].is_match("PDB4"));
    }

    fn split_trimmed(sql: &str) -> Vec<&str> {
        split_sql_statements(sql)
            .into_iter()
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .collect()
    }

    #[test]
    fn test_split_sql_statements_plain() {
        assert_eq!(split_trimmed("a;b;c"), vec!["a", "b", "c"]);
    }

    #[test]
    fn test_split_sql_statements_semicolon_in_string_literal() {
        assert_eq!(
            split_trimmed("SELECT 'a;b' FROM dual"),
            vec!["SELECT 'a;b' FROM dual"]
        );
    }

    #[test]
    fn test_split_sql_statements_escaped_quote_in_string() {
        assert_eq!(
            split_trimmed("SELECT 'it''s;ok' FROM dual; SELECT 2 FROM dual"),
            vec!["SELECT 'it''s;ok' FROM dual", "SELECT 2 FROM dual"]
        );
    }

    #[test]
    fn test_split_sql_statements_semicolon_in_quoted_identifier() {
        assert_eq!(
            split_trimmed("SELECT 1 AS \"a;b\" FROM dual; SELECT 2 FROM dual"),
            vec!["SELECT 1 AS \"a;b\" FROM dual", "SELECT 2 FROM dual"]
        );
    }

    #[test]
    fn test_split_sql_statements_semicolon_in_line_comment() {
        // The `;` in the `-- c;d` comment must not split; the one after `dual` does.
        assert_eq!(
            split_trimmed("SELECT 1 -- c;d\nFROM dual; SELECT 2 FROM dual"),
            vec!["SELECT 1 -- c;d\nFROM dual", "SELECT 2 FROM dual"]
        );
    }

    #[test]
    fn test_split_sql_statements_semicolon_in_block_comment() {
        // The `;` inside the /* ... */ block comment must not split.
        assert_eq!(
            split_trimmed("SELECT /* x;y */ 1 FROM dual; SELECT 2 FROM dual"),
            vec!["SELECT /* x;y */ 1 FROM dual", "SELECT 2 FROM dual"]
        );
    }

    #[test]
    fn test_split_sql_statements_trailing_and_empty_segments() {
        assert_eq!(
            split_trimmed("SELECT 1 FROM dual;;  ;"),
            vec!["SELECT 1 FROM dual"]
        );
    }

    // TC-ORA-101 (Param: SQL containing CHR(59) is not a statement terminator)
    #[test]
    fn test_split_sql_statements_chr59_passes_through() {
        assert_eq!(
            split_trimmed("SELECT CHR(59) FROM dual"),
            vec!["SELECT CHR(59) FROM dual"]
        );
    }

    // TC-ORA-101 (Param: embedded semicolons in a SQL string literal preserved)
    #[test]
    fn test_find_queries_keeps_semicolon_in_string_literal() {
        let section_config = section::SectionBuilder::new("product_price")
            .sql("SELECT 'a;b' FROM dual")
            .set_item_value(ItemValue::from("product_price".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        let queries = runtime
            .find_queries(InstanceNumVersion::from(0), Tenant::All, &[])
            .expect("inline sql should yield queries");
        assert_eq!(queries.len(), 1);
        assert_eq!(queries[0].as_str(), "SELECT 'a;b' FROM dual");
    }

    #[test]
    fn test_find_queries_splits_real_statement_terminators() {
        let section_config = section::SectionBuilder::new("product_price")
            .sql("SELECT 1 FROM dual; SELECT 2 FROM dual")
            .set_item_value(ItemValue::from("product_price".to_string()))
            .build();
        let runtime = Section::new(&section_config, 0);
        let queries = runtime
            .find_queries(InstanceNumVersion::from(0), Tenant::All, &[])
            .expect("inline sql should yield queries");
        assert_eq!(queries.len(), 2);
        assert_eq!(queries[0].as_str(), "SELECT 1 FROM dual");
        assert_eq!(queries[1].as_str(), "SELECT 2 FROM dual");
    }
}
