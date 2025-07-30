// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::ora_sql::backend::Spot;
use crate::types::{InstanceName, Separator, SqlQuery};
use anyhow::Result;
use std::collections::HashMap;

pub fn get_version(connected_spot: &Spot, instance: &InstanceName) -> Result<Option<String>> {
    let hashmap = _get_instances(connected_spot)?;
    Ok(hashmap.get(instance).cloned())
}

pub fn _get_instances(connected_spot: &Spot) -> Result<HashMap<InstanceName, String>> {
    let result = connected_spot.query_table(&SqlQuery::new(
        r"SELECT INSTANCE_NAME, VERSION_FULL FROM v$instance",
        Separator::default(),
    ))?;
    let hashmap: HashMap<InstanceName, String> = result
        .into_iter()
        .map(|x| (InstanceName::from(x[0].as_str()), x[1].clone()))
        .collect();
    Ok(hashmap)
}

pub fn get_instances(connected_spot: &Spot) -> HashMap<InstanceName, String> {
    let hashmap = _get_instances(connected_spot).unwrap_or_else(|e| {
        log::error!("Failed to get instances: {}", e);
        HashMap::<InstanceName, String>::new()
    });
    hashmap
}
