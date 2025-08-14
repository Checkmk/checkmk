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
    Jobs,
    Resumable,
    UndoStat,
    RecoveryArea,
    AsmDiskGroup,
    Locks,
    LogSwitches,
    LongActiveSessions,
    Processes,
    RecoveryStatus,
    Rman, // Backup and Recovery Manager
    Sessions,
    SystemParameter,
    TableSpaces,
    DataGuardStats,
    Instance,
    AsmInstance,
    Performance,
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
    pub const JOBS_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/jobs.12010000.all.sql"),
            min_version: 12010000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/jobs.10020000.all.sql"),
            min_version: 10020000,
            tenant: Tenant::All,
        },
    ];
    pub const RESUMABLE_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/resumable.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const UNDOSTAT_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/undostat.12010000.all.sql"),
            min_version: 12010000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/undostat.10020000.all.sql"),
            min_version: 10020000,
            tenant: Tenant::All,
        },
    ];
    pub const RECOVERY_AREA_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/recovery_area.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const ASM_DISKGROUP_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/asm_diskgroup.12010000.all.sql"),
            min_version: 12010000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/asm_diskgroup.10020000.all.sql"),
            min_version: 10020000,
            tenant: Tenant::All,
        },
    ];
    pub const ASM_INSTANCE_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/asm_instance.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const DATAGUARD_STATS_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/dataguard_stats.10020000.all.sql"),
        min_version: 10020000,
        tenant: Tenant::All,
    }];
    pub const INSTANCE_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/instance.12010002.all.sql"),
            min_version: 1201_0002,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/instance.0.all.sql"),
            min_version: 0,
            tenant: Tenant::All,
        },
    ];
    pub const LOCKS_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/locks.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/locks.10020000.all.sql"),
            min_version: 1002_0000,
            tenant: Tenant::All,
        },
    ];
    pub const LOGSWITCHES_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/logswitches.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const LONGACTIVESESSIONS_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/longactivesessions.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/longactivesessions.10010000.all.sql"),
            min_version: 1001_0000,
            tenant: Tenant::All,
        },
    ];
    pub const PERFORMANCE_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/performance.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/performance.10010000.all.sql"),
            min_version: 1001_0000,
            tenant: Tenant::All,
        },
    ];
    pub const PROCESSES_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/processes.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const SYSTEM_PARAMETER_META: &[RawMetadata] = &[RawMetadata {
        sql: include_str!("../../sqls/systemparameter.0.all.sql"),
        min_version: 0,
        tenant: Tenant::All,
    }];
    pub const RECOVERY_STATUS_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/recovery_status.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/recovery_status.10010000.all.sql"),
            min_version: 1001_0000,
            tenant: Tenant::All,
        },
    ];
    pub const RMAN_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/rman.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/rman.10020000.all.sql"),
            min_version: 1002_0000,
            tenant: Tenant::All,
        },
    ];
    pub const SESSIONS_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/sessions.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/sessions.0.all.sql"),
            min_version: 0,
            tenant: Tenant::All,
        },
    ];
    pub const TABLESPACES_META: &[RawMetadata] = &[
        RawMetadata {
            sql: include_str!("../../sqls/tablespaces.12010000.all.sql"),
            min_version: 1201_0000,
            tenant: Tenant::All,
        },
        RawMetadata {
            sql: include_str!("../../sqls/tablespaces.10020000.all.sql"),
            min_version: 1002_0000,
            tenant: Tenant::All,
        },
    ];

    pub mod internal {
        pub const INSTANCE_INFO_SQL_TEXT_NEW: &str = r"
SELECT
    INSTANCE_NAME,
    i.CON_ID,
    VERSION_FULL,
    d.name,
    d.cdb
    FROM v$instance i
    join v$database d
        on i.con_id = d.con_id";
        pub const INSTANCE_INFO_SQL_TEXT_OLD: &str = r"
SELECT
    INSTANCE_NAME,
    i.CON_ID,
    VERSION,
    d.name,
    d.cdb
    FROM v$instance i
    join v$database d
        on i.con_id = d.con_id";
        pub const INSTANCE_APPROXIMATE_VERSION: &str =
            r"SELECT BANNER_FULL FROM v$version WHERE banner LIKE 'Oracle%'";
    }
}

static QUERY_MAP: LazyLock<HashMap<Id, Vec<query::Metadata>>> = LazyLock::new(|| {
    HashMap::from([
        query::build_query_metadata(Id::TsQuotas, query::TS_QUOTAS_META),
        query::build_query_metadata(Id::IoStats, query::IO_STATS_META),
        query::build_query_metadata(Id::Jobs, query::JOBS_META),
        query::build_query_metadata(Id::Resumable, query::RESUMABLE_META),
        query::build_query_metadata(Id::UndoStat, query::UNDOSTAT_META),
        query::build_query_metadata(Id::RecoveryArea, query::RECOVERY_AREA_META),
        query::build_query_metadata(Id::AsmDiskGroup, query::ASM_DISKGROUP_META),
        query::build_query_metadata(Id::Locks, query::LOCKS_META),
        query::build_query_metadata(Id::LogSwitches, query::LOGSWITCHES_META),
        query::build_query_metadata(Id::LongActiveSessions, query::LONGACTIVESESSIONS_META),
        query::build_query_metadata(Id::Processes, query::PROCESSES_META),
        query::build_query_metadata(Id::RecoveryStatus, query::RECOVERY_STATUS_META),
        query::build_query_metadata(Id::Rman, query::RMAN_META),
        query::build_query_metadata(Id::Sessions, query::SESSIONS_META),
        query::build_query_metadata(Id::SystemParameter, query::SYSTEM_PARAMETER_META),
        query::build_query_metadata(Id::TableSpaces, query::TABLESPACES_META),
        query::build_query_metadata(Id::DataGuardStats, query::DATAGUARD_STATS_META),
        query::build_query_metadata(Id::Instance, query::INSTANCE_META),
        query::build_query_metadata(Id::AsmInstance, query::ASM_INSTANCE_META),
        query::build_query_metadata(Id::Performance, query::PERFORMANCE_META),
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
        .map(|q| {
            q.sql.clone().replace(
                "${version_column}",
                get_version_column_patch(version).as_str(),
            )
        })
        .ok_or(anyhow::anyhow!(
            "Query for {:?} not found",
            query_id.borrow()
        ))
}

fn get_version_column_patch(version: Option<InstanceNumVersion>) -> String {
    match version {
        Some(v) if v >= InstanceNumVersion::from(18_00_00_00) => String::from("version_full"),
        None => String::from("version_full"),
        _ => String::from("version"),
    }
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

    fn find_helper(id: Id, v: u32, t: Tenant) -> Result<String> {
        get_factory_query(
            id,
            if v == 0 {
                None
            } else {
                Some(InstanceNumVersion::from(v))
            },
            t,
            None,
        )
    }
    #[test]
    fn test_find_jobs() {
        let id = Id::Jobs;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }
    #[test]
    fn test_find_resumable() {
        let id = Id::Resumable;

        let query_new = find_helper(id, 23010000, Tenant::Cdb).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_last.is_empty());
        assert_eq!(query_new, query_last);
    }
    #[test]
    fn test_find_undostat() {
        let id = Id::UndoStat;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }
    #[test]
    fn test_find_recovery_area() {
        let id = Id::RecoveryArea;

        let query_new = find_helper(id, 23010000, Tenant::Cdb).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_last.is_empty());
        assert_eq!(query_new, query_last);
    }

    #[test]
    fn test_find_asm_diskgroup() {
        let id = Id::AsmDiskGroup;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }
    #[test]
    fn test_find_locks() {
        let id = Id::Locks;

        let query_new = find_helper(id, 12010000, Tenant::NoCdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_find_logswitches() {
        let id = Id::LogSwitches;

        let query_new = find_helper(id, 12010000, Tenant::NoCdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_obsolete = find_helper(id, 10000000, Tenant::Cdb).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert_eq!(query_old, query_new);
        assert_eq!(query_last, query_new);
        assert_eq!(query_obsolete, query_new);
    }

    #[test]
    fn test_find_processes() {
        let id = Id::Processes;

        let query_new = find_helper(id, 12010000, Tenant::NoCdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_obsolete = find_helper(id, 10000000, Tenant::Cdb).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert_eq!(query_old, query_new);
        assert_eq!(query_last, query_new);
        assert_eq!(query_obsolete, query_new);
    }

    #[test]
    fn test_long_active_sessions() {
        let id = Id::LongActiveSessions;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_recovery_status() {
        let id = Id::RecoveryStatus;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_find_rman() {
        let id = Id::Rman;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_find_sessions() {
        let id = Id::Sessions;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_find_system_parameter() {
        let id = Id::SystemParameter;

        let query_new = find_helper(id, 12010000, Tenant::NoCdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::Cdb).unwrap();
        let query_obsolete = find_helper(id, 10000000, Tenant::Cdb).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert_eq!(query_old, query_new);
        assert_eq!(query_last, query_new);
        assert_eq!(query_obsolete, query_new);
    }

    #[test]
    fn test_find_table_spaces() {
        let id = Id::TableSpaces;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_find_data_guard_stats() {
        let id = Id::DataGuardStats;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert_eq!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }

    #[test]
    fn test_find_instance() {
        let id = Id::Instance;

        let query_full_version = find_helper(id, 18000001, Tenant::Cdb).unwrap();
        let query_version = find_helper(id, 12010000, Tenant::All).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_full_version.is_empty());
        assert!(query_full_version.contains("i.version_full"));
        assert!(!query_version.contains("i.version_full"));
        assert_eq!(query_last, query_full_version);
    }
    #[test]
    fn test_find_asm_instance() {
        let id = Id::AsmInstance;

        let query_full_version = find_helper(id, 18000001, Tenant::Cdb).unwrap();
        let query_version = find_helper(id, 12010000, Tenant::All).unwrap();
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_full_version.is_empty());
        assert!(query_full_version.contains("i.version_full"));
        assert!(!query_version.contains("i.version_full"));
        assert_eq!(query_last, query_full_version);
    }

    #[test]
    fn test_find_performance() {
        let id = Id::Performance;

        let query_new = find_helper(id, 12010000, Tenant::Cdb).unwrap();
        let query_old = find_helper(id, 10200000, Tenant::All).unwrap();
        let query_nothing = find_helper(id, 10000000, Tenant::Cdb);
        let query_last = find_helper(id, 0, Tenant::Cdb).unwrap(); // simulates 0
        assert!(!query_new.is_empty());
        assert!(!query_old.is_empty());
        assert!(query_nothing.is_err());
        assert_ne!(query_old, query_new);
        assert_eq!(query_last, query_new);
    }
}
