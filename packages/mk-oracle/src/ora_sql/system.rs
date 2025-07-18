// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::ora_sql::backend::Task;
use crate::types::{InstanceName, SqlQuery};
use anyhow::Result;
use std::collections::HashMap;

#[allow(dead_code)]
pub fn get_version(connected_task: &Task, instance: &InstanceName) -> Result<Option<String>> {
    let result = connected_task.query_table(&SqlQuery::from(
        r"SELECT INSTANCE_NAME, VERSION_FULL FROM v$instance",
    ))?;
    let hashmap: HashMap<InstanceName, String> = result
        .into_iter()
        .map(|x| (InstanceName::from(x[0].as_str()), x[1].clone())) // Replace `operation(x)` with your specific operation
        .collect();
    Ok(hashmap.get(instance).cloned())
}
