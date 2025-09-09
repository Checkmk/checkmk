// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::InstanceName;
use anyhow::Result;
use std::path::PathBuf;

pub struct Block {
    pub headline: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

impl Block {
    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }

    pub fn first(&self) -> Option<&Vec<String>> {
        self.rows.first()
    }
    pub fn last(&self) -> Option<&Vec<String>> {
        self.rows.last()
    }

    pub fn get_value_by_name(&self, row: &[String], idx: &str) -> String {
        if let Some(index) = self.headline.iter().position(|r| r == idx) {
            row.get(index).cloned()
        } else {
            None
        }
        .unwrap_or_default()
    }

    pub fn get_bigint_by_name(&self, row: &[String], idx: &str) -> String {
        self.get_value_by_name(row, idx)
            .parse::<i64>()
            .unwrap_or_default()
            .to_string()
    }

    pub fn get_first_row_column(&self, column: usize) -> Option<String> {
        self.rows.first().and_then(|r| r.get(column)).cloned()
    }
}

pub fn get_row_value_by_idx(row: &[String], idx: usize) -> String {
    row.get(idx).cloned().unwrap_or_default()
}

#[derive(Debug, Clone)]
pub struct InstanceInfo {
    pub name: InstanceName,
    pub home: PathBuf,
    pub base: PathBuf,
}

pub fn get_local_instances() -> Result<Vec<InstanceInfo>> {
    registry::get_instances(None)
}

pub mod registry {
    #[cfg(windows)]
    use winreg::{enums::*, RegKey};

    use super::InstanceInfo;
    #[cfg(windows)]
    use super::InstanceName;
    use anyhow::Result;
    #[cfg(windows)]
    pub fn get_instances(_custom_branch: Option<String>) -> Result<Vec<InstanceInfo>> {
        use std::path::PathBuf;

        // Open the branch, e.g. HKEY_LOCAL_MACHINE\SOFTWARE
        let handle = RegKey::predef(HKEY_LOCAL_MACHINE);
        let oracle = handle.open_subkey("SOFTWARE\\Oracle")?;

        let instances: Vec<InstanceInfo> = oracle
            .enum_keys()
            .filter_map(|k| k.ok())
            .filter_map(|k| {
                if let Ok(candidate) = oracle.open_subkey(k) {
                    let values = ["ORACLE_HOME", "ORACLE_BASE", "ORACLE_SID"]
                        .iter()
                        .map(|&key| candidate.get_value(key).unwrap_or_default())
                        .collect::<Vec<String>>();

                    if values.iter().all(|v| !v.is_empty()) {
                        Some(InstanceInfo {
                            name: InstanceName::from(values[2].as_str()),
                            home: PathBuf::from(values[0].as_str()),
                            base: PathBuf::from(values[1].as_str()),
                        })
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect::<Vec<InstanceInfo>>();
        Ok(instances)
    }

    #[cfg(unix)]
    pub fn get_instances(_custom_branch: Option<String>) -> Result<Vec<InstanceInfo>> {
        Ok(vec![])
    }
}
