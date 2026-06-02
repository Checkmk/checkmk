// Copyright (C) 2026 Checkmk GmbH
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
use crate::ora_sql::sqls;
use crate::types::{PdbName, SqlQuery};
use anyhow::Result;
use regex::Regex;
use std::collections::HashSet;

const PDB_SEED: &str = "PDB$SEED";
const CDB_ROOT: &str = "CDB$ROOT";

/// Pluggable databases discovered for a single CDB connection.
///
/// PDB$SEED (read-only template) and CDB$ROOT (the container root) are
/// filtered out so that only real, usable PDBs remain.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Pdbs(Vec<PdbName>);

impl Pdbs {
    /// Query the open connection for the list of PDBs and filter out the
    /// container root and the read-only seed template.
    pub fn discover(spot: &OpenedSpot) -> Result<Self> {
        let rows = spot
            .query_table(&SqlQuery::new(
                sqls::query::internal::PDB_DISCOVERY_SQL,
                &Vec::new(),
            ))
            .0?;
        Ok(Self::from_rows(rows))
    }

    fn from_rows(rows: Vec<Vec<String>>) -> Self {
        let pdbs = rows
            .into_iter()
            .filter_map(|mut row| {
                let raw = row.drain(..).next()?;
                let trimmed = raw.trim();
                if trimmed.is_empty() || is_filtered_name(trimmed) {
                    None
                } else {
                    Some(PdbName::from(trimmed))
                }
            })
            .collect();
        Self(pdbs)
    }

    pub fn names(&self) -> &[PdbName] {
        &self.0
    }

    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    pub fn len(&self) -> usize {
        self.0.len()
    }

    #[cfg(test)]
    pub fn from_names(names: &[&str]) -> Self {
        Self(names.iter().map(|n| PdbName::from(*n)).collect())
    }
}

fn is_filtered_name(name: &str) -> bool {
    let upper = name.to_uppercase();
    upper == PDB_SEED || upper == CDB_ROOT
}

/// Match compiled PDB patterns against discovered PDBs.
/// Each PDB name is collected only once.
/// Patterns matching nothing are skipped.
pub fn resolve_pdb_patterns(patterns: &[Regex], discovered: &Pdbs) -> Vec<PdbName> {
    let mut matched = HashSet::new();
    for re in patterns {
        let hits: Vec<_> = discovered
            .names()
            .iter()
            .filter(|pdb| re.is_match(pdb.as_ref()))
            .map(|pdb| pdb.as_ref().to_string())
            .collect();
        if hits.is_empty() {
            log::warn!("PDB pattern {:?} matched no discovered PDBs", re.as_str());
            continue;
        }
        matched.extend(hits);
    }
    matched.into_iter().map(PdbName::from).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ora_sql::Endpoint;
    use crate::ora_sql::backend::{OraDbEngine, QueryResult, SpotBuilder};
    use crate::ora_sql::types::Target;
    use crate::types::InstanceName;

    fn rows(names: &[&str]) -> Vec<Vec<String>> {
        names
            .iter()
            .map(|n| vec![(*n).to_string()])
            .collect::<Vec<_>>()
    }

    #[test]
    fn test_from_rows_filters_seed_and_root_case_insensitive() {
        let pdbs = Pdbs::from_rows(rows(&[
            "CDB$ROOT", "PDB$SEED", "PDB1", "pdb2", "cdb$root", "pdb$seed",
        ]));
        let names: Vec<&str> = pdbs.names().iter().map(|p| p.as_ref()).collect();
        assert_eq!(names, vec!["PDB1", "PDB2"]);
    }

    #[test]
    fn test_from_rows_skips_empty_rows_and_blank_names() {
        let pdbs = Pdbs::from_rows(vec![
            vec![],
            vec!["".to_string()],
            vec!["   ".to_string()],
            vec!["PDB1".to_string()],
        ]);
        let names: Vec<&str> = pdbs.names().iter().map(|p| p.as_ref()).collect();
        assert_eq!(names, vec!["PDB1"]);
    }

    #[test]
    fn test_empty_when_no_pdbs() {
        let pdbs = Pdbs::from_rows(rows(&["CDB$ROOT", "PDB$SEED"]));
        assert!(pdbs.is_empty());
        assert_eq!(pdbs.len(), 0);
    }

    /// Engine that returns a canned PDB discovery result for the PDB query and
    /// errors for anything else.
    struct PdbTestEngine {
        rows: Vec<Vec<String>>,
    }

    impl OraDbEngine for PdbTestEngine {
        fn connect(&mut self, _t: &Target, _i: Option<&InstanceName>) -> Result<()> {
            Ok(())
        }
        fn close(&mut self) -> Result<()> {
            Ok(())
        }
        fn query_table(&self, query: &SqlQuery) -> QueryResult {
            if query.as_str() == sqls::query::internal::PDB_DISCOVERY_SQL {
                QueryResult(Ok(self.rows.clone()))
            } else {
                QueryResult(Err(anyhow::anyhow!("unexpected query")))
            }
        }
        fn clone_box(&self) -> Box<dyn OraDbEngine + Send + Sync> {
            Box::new(PdbTestEngine {
                rows: self.rows.clone(),
            })
        }
    }

    #[test]
    fn test_discover_uses_pdb_query_and_filters() {
        let engine = PdbTestEngine {
            rows: rows(&["CDB$ROOT", "PDB$SEED", "PDB1", "PDB2"]),
        };
        let opened = SpotBuilder::new()
            .endpoint_target(&Endpoint::default())
            .custom_engine(Box::new(engine))
            .build()
            .unwrap()
            .connect(None)
            .unwrap();
        let pdbs = Pdbs::discover(&opened).unwrap();
        let names: Vec<&str> = pdbs.names().iter().map(|p| p.as_ref()).collect();
        assert_eq!(names, vec!["PDB1", "PDB2"]);
    }

    fn exact(name: &str) -> Regex {
        Regex::new(&format!("^{name}$")).unwrap()
    }

    #[test]
    fn test_resolve_returns_all_matched_pdbs() {
        let pdbs = Pdbs::from_names(&["PDB1", "PDB2", "OTHER"]);
        let result = resolve_pdb_patterns(&[exact("PDB1"), exact("PDB2")], &pdbs);

        assert_eq!(result.len(), 2);
        assert!(result.contains(&PdbName::from("PDB1")));
        assert!(result.contains(&PdbName::from("PDB2")));
    }

    #[test]
    fn test_resolve_each_pdb_appears_once() {
        let pdbs = Pdbs::from_names(&["PDB1"]);
        assert_eq!(
            resolve_pdb_patterns(&[exact("PDB1"), exact("PDB1")], &pdbs),
            vec![PdbName::from("PDB1")]
        );
    }

    #[test]
    fn test_resolve_returns_nothing_when_unmatched() {
        let pdbs = Pdbs::from_names(&["PDB1"]);
        assert!(resolve_pdb_patterns(&[exact("MISSING")], &pdbs).is_empty());
    }
}
