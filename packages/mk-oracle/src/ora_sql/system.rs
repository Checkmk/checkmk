// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::ora_sql::backend::OpenedSpot;
use crate::types::{InstanceName, Separator, SqlQuery};
use anyhow::Result;
use std::collections::HashMap;

type _InstanceEntries = HashMap<InstanceName, String>;
pub struct WorkInstances(_InstanceEntries);

impl WorkInstances {
    pub fn new(spot: &OpenedSpot) -> Self {
        let hashmap = _get_instances(spot).unwrap_or_else(|e| {
            log::error!("Failed to get instances: {}", e);
            HashMap::<InstanceName, String>::new()
        });
        WorkInstances(hashmap)
    }
    pub fn get_full_version(&self, instance: &InstanceName) -> Option<String> {
        self.0.get(instance).cloned()
    }

    /// Returns the version of the given instance as a number in the format `major * 100 + minor`.
    /// For example, version "19.1.0" will return 1901, and "21.2" will return 2102.
    /// If the version cannot be parsed, it returns `None`.
    ///
    /// If the instance is not found, it returns `None`.
    pub fn get_num_version(&self, instance: &InstanceName) -> Result<Option<u32>> {
        Ok(self.0.get(instance).and_then(|v| convert_to_num_version(v)))
    }

    pub fn all(&self) -> &_InstanceEntries {
        &self.0
    }
}

fn _get_instances(spot: &OpenedSpot) -> Result<_InstanceEntries> {
    let result = spot.query_table(&SqlQuery::new(
        r"SELECT INSTANCE_NAME, VERSION_FULL FROM v$instance",
        Separator::default(),
        &Vec::new(),
    ))?;
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
                Some((InstanceName::from(x[0].as_str()), x[1].clone()))
            }
        })
        .collect();
    Ok(hashmap)
}

fn convert_to_num_version(version: &str) -> Option<u32> {
    let tops = version
        .splitn(3, '.')
        .take(2)
        .filter_map(|s| s.parse::<u32>().ok())
        .collect::<Vec<u32>>();
    if tops.len() < 2 {
        log::warn!("Bad version format: '{version}'");
        None
    } else {
        Some(tops[0] * 100 + tops[1])
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ora_sql::Endpoint;
    use crate::ora_sql::backend::OraDbEngine;
    use crate::ora_sql::backend::SpotBuilder;
    use crate::ora_sql::types::Target;

    struct TestOra;
    impl OraDbEngine for TestOra {
        fn connect(&mut self, _target: &Target, _instance: Option<&InstanceName>) -> Result<()> {
            Ok(())
        }

        fn close(&mut self) -> Result<()> {
            Ok(())
        }

        fn query(&self, _query: &SqlQuery, _sep: &str) -> Result<Vec<String>> {
            Ok(vec![])
        }
        fn query_table(&self, query: &SqlQuery) -> Result<Vec<Vec<String>>> {
            if query.as_str() == "SELECT INSTANCE_NAME, VERSION_FULL FROM v$instance" {
                Ok(vec![vec!["INSTANCE1".to_string(), "22.1.1".to_string()]])
            } else {
                Err(anyhow::anyhow!("Query not recognized"))
            }
        }

        fn clone_box(&self) -> Box<dyn OraDbEngine> {
            Box::new(TestOra)
        }
    }
    #[test]
    fn test_get_version() {
        let simulated_spot = SpotBuilder::new()
            .target(&Endpoint::default())
            .custom_engine(Box::new(TestOra))
            .build()
            .unwrap();
        let conn = simulated_spot.connect(None).unwrap();
        assert_eq!(
            &WorkInstances::new(&conn)
                .get_full_version(&InstanceName::from("INSTANCE1"))
                .unwrap(),
            "22.1.1"
        );
        assert!(&WorkInstances::new(&conn)
            .get_full_version(&InstanceName::from("HURZ"))
            .is_none());
    }

    #[test]
    fn test_convert_to_num_version() {
        assert_eq!(convert_to_num_version("19.0.0.dd,d"), Some(1900));
        assert_eq!(convert_to_num_version("19.1.0"), Some(1901));
        assert_eq!(convert_to_num_version("21.2"), Some(2102));
        assert!(convert_to_num_version("").is_none());
        assert!(convert_to_num_version("a.").is_none());
    }
}
