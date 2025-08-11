// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{InstanceNumVersion, Tenant};
use anyhow::Result;
use std::borrow::Borrow;
use std::collections::HashMap;
use std::sync::LazyLock;

pub const UTC_DATE_FIELD: &str = "utc_date";

#[derive(Hash, PartialEq, Eq, Debug, Copy, Clone)]
pub enum Id {
    IoStats,
    TsQuotas,
}

pub mod query {
    use crate::types::Tenant;
    use std::cmp::Reverse;
    pub struct RawMetadata {
        pub sql: &'static str,
        pub min_version: u32,
        pub tenant: Tenant,
    }
    pub struct Metadata {
        pub sql: String,
        pub min_version: u32,
        pub tenant: Tenant,
    }

    pub fn build_query_metadata(
        id: super::Id,
        metas: &'static [RawMetadata],
    ) -> (super::Id, Vec<Metadata>) {
        let mut ret: Vec<Metadata> = metas
            .iter()
            .map(|meta| Metadata {
                sql: meta.sql.to_string(),
                min_version: meta.min_version,
                tenant: meta.tenant,
            })
            .collect();
        ret.sort_by_key(|m: &Metadata| Reverse(m.min_version));
        (id, ret)
    }

    pub const IO_STATS_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/io_stats.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const TS_QUOTAS_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/ts_quotas.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];

    pub mod internal {
        pub const INSTANCE_INFO_SQL_TEXT: &str = r"
SELECT
    INSTANCE_NAME,
    i.CON_ID,
    VERSION_FULL,
    d.name,
    d.cdb
    FROM v$instance i
    join v$database d
        on i.con_id = d.con_id";
    }
}

static QUERY_MAP: LazyLock<HashMap<Id, Vec<query::Metadata>>> = LazyLock::new(|| {
    HashMap::from([
        query::build_query_metadata(Id::TsQuotas, query::TS_QUOTAS_META),
        query::build_query_metadata(Id::IoStats, query::IO_STATS_META),
    ])
});

pub fn get_factory_query<T: Borrow<Id>>(
    query_id: T,
    version: Option<InstanceNumVersion>,
    tenant: Tenant,
    data: Option<&HashMap<Id, Vec<query::Metadata>>>,
) -> Result<String> {
    data.unwrap_or(&QUERY_MAP)
        .get(query_id.borrow())
        .and_then(|metas| {
            metas
                .iter()
                .filter(|q| q.tenant == Tenant::All || q.tenant == tenant)
                .find(|q| {
                    version.is_none()
                        || InstanceNumVersion::from(q.min_version) <= version.unwrap_or_default()
                })
        })
        .map(|q| q.sql.clone())
        .ok_or(anyhow::anyhow!(
            "Query for {:?} not found",
            query_id.borrow()
        ))
}

/// Returns the SQL query for the given query ID, latest Version using the default tenant (CDB).
pub fn get_modern_factory_query<T: Borrow<Id>>(query_id: T) -> Result<String> {
    get_factory_query(query_id, None, Tenant::Cdb, None)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ora_sql::sqls::query::RawMetadata;
    use crate::types::{InstanceNumVersion, Separator, SqlQuery};

    static TEST_QUERY_MAP: LazyLock<HashMap<Id, Vec<query::Metadata>>> = LazyLock::new(|| {
        HashMap::from([query::build_query_metadata(
            Id::TsQuotas,
            &[
                RawMetadata {
                    sql: "v0-all",
                    min_version: 0,
                    tenant: Tenant::All,
                },
                RawMetadata {
                    sql: "v23080025-cdb",
                    min_version: 23_08_00_25,
                    tenant: Tenant::Cdb,
                },
                RawMetadata {
                    sql: "v23080025-nocdb",
                    min_version: 23_08_00_25,
                    tenant: Tenant::NoCdb,
                },
                RawMetadata {
                    sql: "v10000000-nocdb",
                    min_version: 10_00_00_00,
                    tenant: Tenant::NoCdb,
                },
            ],
        )])
    });
    #[test]
    fn test_find_test() {
        fn find_helper(v: u32, t: Tenant) -> String {
            get_factory_query(
                Id::TsQuotas,
                Some(InstanceNumVersion::from(v)),
                t,
                Some(&TEST_QUERY_MAP),
            )
            .unwrap()
        }
        assert_eq!(find_helper(24080025, Tenant::Cdb), "v23080025-cdb"); // Latest version for CDB
        assert_eq!(find_helper(24080025, Tenant::NoCdb), "v23080025-nocdb"); // Latest version for NoCDB
        assert_eq!(find_helper(23080024, Tenant::Cdb), "v0-all"); // mid version for CDB
        assert_eq!(find_helper(20080025, Tenant::Cdb), "v0-all"); // Old version for CDB
        assert_eq!(find_helper(20080025, Tenant::NoCdb), "v10000000-nocdb"); // Old version for NoCDB
    }
    static TEST_QUERY_MAP_SHORT: LazyLock<HashMap<Id, Vec<query::Metadata>>> =
        LazyLock::new(|| {
            HashMap::from([query::build_query_metadata(
                Id::TsQuotas,
                &[RawMetadata {
                    sql: "v10000000-all",
                    min_version: 10_00_00_00,
                    tenant: Tenant::All,
                }],
            )])
        });

    #[test]
    fn test_find_test_short() {
        fn find_helper(v: u32, t: Tenant) -> Result<String> {
            get_factory_query(
                Id::TsQuotas,
                Some(InstanceNumVersion::from(v)),
                t,
                Some(&TEST_QUERY_MAP_SHORT),
            )
        }
        assert_eq!(
            find_helper(24080025, Tenant::Cdb).unwrap(),
            "v10000000-all".to_string()
        );
        assert_eq!(
            find_helper(24080025, Tenant::NoCdb).unwrap(),
            "v10000000-all".to_string()
        );
        assert!(find_helper(9999999, Tenant::Cdb).is_err());
        assert!(find_helper(9999999, Tenant::NoCdb).is_err());
    }
    #[test]
    fn test_find_io_stats() {
        let q = SqlQuery::new(
            get_factory_query(Id::IoStats, None, Tenant::All, None).unwrap(),
            Separator::default(),
            &Vec::new(),
        );
        assert!(!q.as_str().is_empty());
    }
    #[test]
    fn test_find_ts_quotas() {
        let q = SqlQuery::new(
            get_factory_query(
                Id::TsQuotas,
                Some(InstanceNumVersion::from(23080025)),
                Tenant::Cdb,
                None,
            )
            .unwrap(),
            Separator::default(),
            &Vec::new(),
        );
        assert!(!q.as_str().is_empty());
    }
}
