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
use crate::ora_sql::sqls;
use crate::types::{InstanceName, InstanceNumVersion, InstanceVersion, SqlQuery, Tenant};
use anyhow::Result;
use std::collections::HashMap;

type _InstanceEntries = HashMap<InstanceName, (InstanceVersion, Tenant)>;
#[derive(Debug)]
pub struct WorkInstances(_InstanceEntries);

impl WorkInstances {
    pub fn new(spot: &OpenedSpot, custom_query: Option<&str>) -> Self {
        let hashmap = _get_instances(spot, custom_query).unwrap_or_else(|e| {
            log::error!("Failed to get instances: {}", e);
            _InstanceEntries::new()
        });
        WorkInstances(hashmap)
    }
    pub fn get_full_version(&self, instance: &InstanceName) -> Option<InstanceVersion> {
        self.0.get(instance).cloned().map(|(version, _)| version)
    }

    /// Returns the version of the given instance as a number.
    /// For example, version "19.1.1.1" will return 19010101.
    /// If the version cannot be parsed, it returns `None`.
    ///
    /// If the instance is not found, it returns `None`.
    pub fn get_info(&self, instance: &InstanceName) -> Option<(InstanceNumVersion, Tenant)> {
        self.0
            .get(instance)
            .map(|(v, c)| (convert_to_num_version(v).unwrap_or_default(), *c))
    }

    pub fn all(&self) -> &_InstanceEntries {
        &self.0
    }
}

fn _get_instances(spot: &OpenedSpot, custom_query: Option<&str>) -> Result<_InstanceEntries> {
    if let Ok(result) = spot
        .query_table(&SqlQuery::new(
            custom_query.unwrap_or(sqls::query::internal::INSTANCE_INFO_SQL_TEXT_NEW),
            &Vec::new(),
        ))
        .0
    {
        Ok(_to_instance_entries(result))
    } else {
        let mut result = spot
            .query_table(&SqlQuery::new(
                sqls::query::internal::INSTANCE_INFO_SQL_TEXT_OLD,
                &Vec::new(),
            ))
            .0?;
        let result_with_version = spot
            .query_table(&SqlQuery::new(
                sqls::query::internal::INSTANCE_APPROXIMATE_VERSION,
                &Vec::new(),
            ))
            .format("")?;
        if let Some(version) = _extract_version(result_with_version) {
            log::info!("Extracted version: {version}");
            for r in result.iter_mut() {
                r[2] = version.clone(); // Update the version column
            }
        }
        Ok(_to_instance_entries(result))
    }
}

fn _extract_version(result: Vec<String>) -> Option<String> {
    if result.is_empty() {
        log::warn!("No version information found in v$instance");
        return None;
    }
    result[0].split(' ').next_back().and_then(|s| {
        convert_to_num_version(&InstanceVersion::from(s.to_owned())).map(|_| s.to_string())
    })
}

fn _to_instance_entries(result: Vec<Vec<String>>) -> _InstanceEntries {
    let hashmap: _InstanceEntries = result
        .into_iter()
        .filter_map(|x| {
            if x.len() < 2 {
                log::error!(
                    "Unexpected result from v$instance: expected at least 2 columns, got {}",
                    x.len()
                );
                None
            } else {
                Some((
                    InstanceName::from(x[0].as_str()),
                    (InstanceVersion::from(x[2].clone()), Tenant::new(&x[4])),
                ))
            }
        })
        .collect();
    hashmap
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
    use crate::ora_sql::backend::SpotBuilder;
    use crate::ora_sql::backend::{OraDbEngine, QueryResult};
    use crate::ora_sql::sqls::query;
    use crate::ora_sql::types::Target;

    struct TestOra;
    impl OraDbEngine for TestOra {
        fn connect(&mut self, _target: &Target, _instance: Option<&InstanceName>) -> Result<()> {
            Ok(())
        }

        fn close(&mut self) -> Result<()> {
            Ok(())
        }

        fn query_table(&self, query: &SqlQuery) -> QueryResult {
            let result = if query.as_str() == query::internal::INSTANCE_INFO_SQL_TEXT_NEW {
                Ok(vec![vec![
                    "free".to_string(),       // instance name
                    "0".to_string(),          // CON_ID
                    "22.1.1.6.0".to_string(), // VERSION_FULL
                    "FREE".to_string(),       // database name
                    "YES".to_string(),        // cdb
                ]])
            } else {
                Err(anyhow::anyhow!("Query not recognized"))
            };
            QueryResult(result)
        }

        fn clone_box(&self) -> Box<dyn OraDbEngine + Send + Sync> {
            Box::new(TestOra)
        }
    }
    #[test]
    fn test_get_version() {
        let simulated_spot = SpotBuilder::new()
            .endpoint_target(&Endpoint::default())
            .custom_engine(Box::new(TestOra))
            .build()
            .unwrap();
        let conn = simulated_spot.connect(None).unwrap();
        assert_eq!(
            &WorkInstances::new(&conn, None)
                .get_full_version(&InstanceName::from("fREe"))
                .unwrap(),
            &InstanceVersion::from("22.1.1.6.0".to_string())
        );
        assert!(&WorkInstances::new(&conn, None)
            .get_full_version(&InstanceName::from("HURZ"))
            .is_none());
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
