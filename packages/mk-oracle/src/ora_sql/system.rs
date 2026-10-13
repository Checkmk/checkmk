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

use crate::ora_sql::backend::OpenedSpot;
use crate::ora_sql::pdbs::Pdbs;
use crate::ora_sql::sqls;
use crate::types::{InstanceName, InstanceNumVersion, InstanceVersion, SqlQuery, Tenant};
use anyhow::Result;
use std::collections::HashMap;

type _InstanceEntries = HashMap<InstanceName, (InstanceVersion, Tenant)>;
#[derive(Debug)]
pub struct WorkInstances {
    instances: _InstanceEntries,
    /// PDBs of the connected CDB. A single connection sees one set of PDBs
    /// shared by every instance entry above (relevant for RAC). Empty until
    /// `discover_pdbs` is called.
    pdbs: Pdbs,
}

impl WorkInstances {
    pub fn new(spot: &OpenedSpot, custom_query: Option<&str>) -> Result<Self> {
        let instances = _get_instances(spot, custom_query)?;
        Ok(WorkInstances {
            instances,
            pdbs: Pdbs::default(),
        })
    }

    /// Run PDB discovery on the open connection and store the result.
    /// On failure, the existing PDB list is left unchanged and the error is
    /// returned for the caller to log.
    pub fn discover_pdbs(&mut self, spot: &OpenedSpot) -> Result<()> {
        self.pdbs = Pdbs::discover(spot)?;
        Ok(())
    }

    pub fn pdbs(&self) -> &Pdbs {
        &self.pdbs
    }

    pub fn get_full_version(&self, instance: &InstanceName) -> Option<InstanceVersion> {
        self.instances
            .get(instance)
            .cloned()
            .map(|(version, _)| version)
    }

    /// Returns the version of the given instance as a number.
    /// For example, version "19.1.1.1" will return 19010101.
    /// If the version cannot be parsed, it returns `None`.
    ///
    /// If the instance is not found, it returns `None`.
    pub fn get_info(&self, instance: &InstanceName) -> Option<(InstanceNumVersion, Tenant)> {
        self.instances
            .get(instance)
            .map(|(v, c)| (convert_to_num_version(v).unwrap_or_default(), *c))
    }

    pub fn all(&self) -> &_InstanceEntries {
        &self.instances
    }
}

/// The only error that means "this release lacks the column"; anything else is
/// a real failure and must not be retried away.
fn is_unknown_column_error(e: &anyhow::Error) -> bool {
    e.to_string().contains("ORA-00904")
}

/// Oracle changed the versioning information with release 18c, introducing
/// `VERSION_FULL`. Where that is unavailable, `VERSION` carries the full
/// versioning information instead.
#[derive(Debug)]
enum DetectedVersion {
    Since18c(InstanceVersion),
    Before18c(InstanceVersion),
}

impl DetectedVersion {
    fn version(&self) -> &InstanceVersion {
        match self {
            Self::Since18c(v) | Self::Before18c(v) => v,
        }
    }
}

impl std::fmt::Display for DetectedVersion {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Since18c(v) => write!(f, "{v} (18c or newer)"),
            Self::Before18c(v) => write!(f, "{v} (before 18c)"),
        }
    }
}

fn _detect_version(spot: &OpenedSpot) -> Result<DetectedVersion> {
    let ask = |sql: &str| -> Result<InstanceVersion> {
        let rows = spot.query_table(&SqlQuery::new(sql, &Vec::new())).0?;
        _extract_version(rows.into_iter().map(|row| row.join("")).collect())
            .map(InstanceVersion::from)
            .ok_or_else(|| anyhow::anyhow!("No usable version in v$instance"))
    };
    match ask(sqls::query::internal::INSTANCE_VERSION_FULL) {
        Ok(version) => Ok(DetectedVersion::Since18c(version)),
        Err(e) if is_unknown_column_error(&e) => {
            log::info!("No VERSION_FULL in v$instance ({e}), asking for VERSION instead");
            ask(sqls::query::internal::INSTANCE_VERSION).map(DetectedVersion::Before18c)
        }
        Err(e) => Err(e),
    }
}

fn _get_instances(spot: &OpenedSpot, custom_query: Option<&str>) -> Result<_InstanceEntries> {
    if let Some(query) = custom_query {
        // Replaces the probe entirely; the caller owns the column set.
        return _to_instance_entries(spot.query_table(&SqlQuery::new(query, &Vec::new())).0?);
    }

    let detected = _detect_version(spot)?;
    log::info!("Instance reports version {detected}");

    let sql = match (spot.target().is_asm(), &detected) {
        (true, DetectedVersion::Since18c(_)) => {
            sqls::query::internal::ASM_INSTANCE_INFO_SQL_TEXT_NEW
        }
        (true, DetectedVersion::Before18c(_)) => {
            sqls::query::internal::ASM_INSTANCE_INFO_SQL_TEXT_OLD
        }
        (false, DetectedVersion::Since18c(_)) => sqls::query::internal::INSTANCE_INFO_SQL_TEXT_NEW,
        (false, DetectedVersion::Before18c(_)) => sqls::query::internal::INSTANCE_INFO_SQL_TEXT_OLD,
    };

    let mut result = spot.query_table(&SqlQuery::new(sql, &Vec::new())).0?;
    for r in result.iter_mut() {
        if let Some(version_column) = r.get_mut(2) {
            *version_column = detected.version().clone().into();
        }
    }
    _to_instance_entries(result)
}

fn _extract_version(result: Vec<String>) -> Option<String> {
    if result.is_empty() {
        log::warn!("No version information found in v$instance");
        return None;
    }
    result
        .iter()
        .flat_map(|line| line.split_whitespace())
        .find(|token| convert_to_num_version(&InstanceVersion::from((*token).to_owned())).is_some())
        .map(str::to_string)
}

/// Consumes columns 0, 2 and 4. Instance info we cannot interpret fails the
/// endpoint, which surfaces as a FAILURE row, rather than guessing a tenancy
/// that would silently reshape every section.
fn _to_instance_entries(result: Vec<Vec<String>>) -> Result<_InstanceEntries> {
    result
        .into_iter()
        .map(|row| {
            let (Some(name), Some(version), Some(tenant)) = (row.first(), row.get(2), row.get(4))
            else {
                anyhow::bail!(
                    "Unexpected result from v$instance: expected at least 5 columns, got {}",
                    row.len()
                );
            };
            let tenant = Tenant::from_cdb_column(tenant).ok_or_else(|| {
                anyhow::anyhow!("Unexpected v$database.cdb value '{tenant}' for instance {name}")
            })?;
            Ok((
                InstanceName::from(name.as_str()),
                (InstanceVersion::from(version.clone()), tenant),
            ))
        })
        .collect()
}
pub fn convert_to_num_version(version: &InstanceVersion) -> Option<InstanceNumVersion> {
    let tops = String::from(version.clone())
        .splitn(5, '.')
        .take(4)
        .filter_map(|s| s.parse::<u32>().ok())
        .collect::<Vec<u32>>();
    if tops.len() < 4 {
        log::warn!("Bad version format: '{version}'");
        None
    } else {
        const BASE: u32 = 100;
        let result = tops.iter().fold(0, |acc, &x| acc * BASE + x);
        Some(InstanceNumVersion::from(result))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ora_sql::Endpoint;
    use crate::ora_sql::backend::test_support::{instance_row, MiniOra};
    use crate::ora_sql::backend::SpotBuilder;

    /// Returns the derived (version, tenant) plus every query the run issued.
    fn discover_at(version: &str, cdb: &str) -> (InstanceNumVersion, Tenant, Vec<String>) {
        let db = MiniOra::at_version("ORCL", version, cdb);
        let asked = std::sync::Arc::clone(&db.asked);
        let spot = SpotBuilder::new()
            .endpoint_target(&Endpoint::default())
            .custom_engine(Box::new(db))
            .build()
            .unwrap()
            .connect(None)
            .unwrap();
        let works = WorkInstances::new(&spot, None).expect("instance must be discovered");
        let (v, t) = works
            .get_info(&InstanceName::from("ORCL"))
            .expect("ORCL must be present");
        let queries = asked.lock().unwrap().clone();
        (v, t, queries)
    }

    #[test]
    fn test_18c_and_later_use_the_precise_version_and_ask_for_cdb() {
        let (version, tenant, asked) = discover_at("19.28.0.0.0", "YES");
        assert_eq!(version, InstanceNumVersion::from(19_28_00_00));
        assert_eq!(tenant, Tenant::Cdb);
        assert!(
            asked.iter().any(|q| q.contains("VERSION_FULL")),
            "{asked:?}"
        );
        assert!(asked.iter().any(|q| q.contains("d.cdb")), "{asked:?}");
    }

    #[test]
    fn test_12c_falls_back_to_version_but_still_asks_for_cdb() {
        // No VERSION_FULL, but CON_ID and CDB are there: the probe degrades
        // while the instance query still reads the real tenancy.
        let (version, tenant, asked) = discover_at("12.2.0.1.0", "YES");
        assert_eq!(version, InstanceNumVersion::from(12_02_00_01));
        assert_eq!(tenant, Tenant::Cdb);
        assert!(
            asked
                .iter()
                .any(|q| q.trim() == "SELECT VERSION FROM v$instance"),
            "the probe must fall back to VERSION: {asked:?}"
        );
        assert!(asked.iter().any(|q| q.contains("d.cdb")), "{asked:?}");
    }

    /// The supported floor is 12.1.0.2, so a release without `V$DATABASE.CDB`
    /// fails rather than being accommodated. Its version reaches the log first,
    /// which is what tells an operator why.
    #[test]
    fn test_before_12c_fails_on_the_absent_cdb_column() {
        let db = MiniOra::at_version("ORCL", "11.2.0.4.0", "irrelevant");
        let spot = SpotBuilder::new()
            .endpoint_target(&Endpoint::default())
            .custom_engine(Box::new(db))
            .build()
            .unwrap()
            .connect(None)
            .unwrap();
        let err = WorkInstances::new(&spot, None).expect_err("must not be accommodated");
        assert!(err.to_string().contains("ORA-00904"), "{err}");
    }

    #[test]
    fn test_a_real_error_is_not_treated_as_a_missing_column() {
        // Anything but ORA-00904 must surface, or a permissions problem reads
        // as an ancient Oracle.
        let spot = SpotBuilder::new()
            .endpoint_target(&Endpoint::default())
            .custom_engine(Box::new(MiniOra {
                absent_columns: vec!["v$instance".to_string()],
                ..Default::default()
            }))
            .build()
            .unwrap()
            .connect(None)
            .unwrap();
        let err = WorkInstances::new(&spot, None).expect_err("must not be swallowed");
        assert!(err.to_string().contains("ORA-00904"), "{err}");
    }

    #[test]
    fn test_extract_version_is_not_positional() {
        assert_eq!(
            _extract_version(vec!["23.26.0.24.03".to_string()]).as_deref(),
            Some("23.26.0.24.03")
        );
        assert_eq!(
            _extract_version(vec![
                "Oracle Database 12c Enterprise Edition Release 12.1.0.2.0 - 64bit Production"
                    .to_string()
            ])
            .as_deref(),
            Some("12.1.0.2.0")
        );
        assert_eq!(_extract_version(vec![]), None);
        assert_eq!(_extract_version(vec!["no version here".to_string()]), None);
    }

    #[test]
    fn test_get_version() {
        let simulated_spot = SpotBuilder::new()
            .endpoint_target(&Endpoint::default())
            .custom_engine(Box::new(MiniOra::at_version("free", "22.1.1.6.0", "YES")))
            .build()
            .unwrap();
        let conn = simulated_spot.connect(None).unwrap();
        assert_eq!(
            &WorkInstances::new(&conn, None)
                .unwrap()
                .get_full_version(&InstanceName::from("fREe"))
                .unwrap(),
            &InstanceVersion::from("22.1.1.6.0".to_string())
        );
        assert!(&WorkInstances::new(&conn, None)
            .unwrap()
            .get_full_version(&InstanceName::from("HURZ"))
            .is_none());
    }

    #[test]
    fn test_instance_entries_tenant_from_cdb_column() {
        for (cdb, expected) in [("NO", Tenant::NoCdb), ("YES", Tenant::Cdb)] {
            let entries =
                _to_instance_entries(vec![instance_row("ORCL", "19.28.0.0.0", cdb)]).unwrap();
            assert_eq!(
                entries.get(&InstanceName::from("ORCL")).unwrap().1,
                expected
            );
        }
    }

    #[test]
    fn test_instance_entries_short_row_is_skipped_not_panic() {
        for row in [vec!["ORCL".to_string()], vec!["ORCL".into(), "0".into()]] {
            assert!(_to_instance_entries(vec![row]).is_err());
        }
    }

    #[test]
    fn test_instance_entries_unknown_cdb_value_fails() {
        assert!(_to_instance_entries(vec![instance_row("ORCL", "19.28.0.0.0", "MAYBE")]).is_err());
    }

    #[test]
    fn test_convert_to_num_version() {
        assert_eq!(
            convert_to_num_version(&InstanceVersion::from("19.1.2.3.4".to_string())),
            Some(InstanceNumVersion::from(19010203))
        );
        assert_eq!(
            convert_to_num_version(&InstanceVersion::from("19.1.2.3".to_string())),
            Some(InstanceNumVersion::from(19010203))
        );
        assert!(convert_to_num_version(&InstanceVersion::from("19.1.0".to_string())).is_none());
        assert!(convert_to_num_version(&InstanceVersion::from("21.2".to_string())).is_none());
        assert!(convert_to_num_version(&InstanceVersion::from("".to_string())).is_none());
        assert!(convert_to_num_version(&InstanceVersion::from("a.".to_string())).is_none());
    }
}
