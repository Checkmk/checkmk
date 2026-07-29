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

//! Component tests that need a database: the reference endpoint
//! (CI_ORA2_DB_TEST) and, when set, the secondary one (CI_ORA1_DB_TEST).

#[cfg(feature = "build_system_bazel")]
extern crate common;
#[cfg(not(feature = "build_system_bazel"))]
mod common;

use crate::common::tools::{
    make_endpoint_tns_admin_dir, make_mini_config, make_mini_config_cdb_root,
    make_mini_config_custom_instance, make_mini_config_custom_instance_with_tns_admin,
    make_mini_config_pdb, make_mini_config_pdb_builtin_then_custom,
    make_mini_config_pdb_custom_then_builtin, make_mini_config_with_sid,
    platform::add_runtime_to_path, role_spec, ORA_ENDPOINT_ENV_VAR, ORA_ENDPOINT_ENV_VAR_SECONDARY,
};
use mk_oracle::config::authentication::{AuthType, Authentication, Role, SqlDbEndpoint};
use mk_oracle::config::defines::defaults::SECTION_SEPARATOR;
use mk_oracle::config::ora_sql::Config;
use mk_oracle::ora_sql::backend;
use mk_oracle::ora_sql::instance::generate_data;
use mk_oracle::ora_sql::section;
use mk_oracle::ora_sql::sqls;
use mk_oracle::ora_sql::system;
use mk_oracle::setup::Env;
use mk_oracle::types::SqlQuery;

use mk_oracle::types::{
    ConnectionStringType, Credentials, InstanceName, InstanceNumVersion, InstanceVersion,
    ServiceName, Tenant,
};
use regex::Regex;
use std::collections::HashSet;
use std::sync::LazyLock;

pub fn get_sid(endpoint: &SqlDbEndpoint) -> String {
    endpoint.sid.clone().unwrap()
}

pub fn get_service_name(endpoint: &SqlDbEndpoint) -> String {
    endpoint.service_name.clone().to_uppercase()
}

static ORA_TEST_INSTANCE_DATA: &str = r"
XE|21.3.0.0.0|OPEN|ALLOWED|STOPPED|1496|3073262481|
NOARCHIVELOG|PRIMARY|NO|XE|030220252229|TRUE|2|PDB$SEED
|1566296130|READ ONLY|NO|770703360|ENABLED|1483|8192|oralinux810.myguest.virtualbox.org";

static ORA_TEST_SESSION_PDB_DATA: &str = "XE.XEPDB1|1";

static ORA_TEST_SESSION_CDB_DATA: &str = "XE|61|472|-1";

static ORA_TEST_LOGSWITCHES_DATA: &str = "XE|0";

static ORA_TEST_UNDOSTAT_DATA: &str = "XE|160|1|900|0|0";

static ORA_TEST_PROCESSES_DATA: &str = "XE|52|300";

static ORA_TEST_RECOVERY_STATUS_DATA: &str = r"
XE|XE|PRIMARY|READ WRITE|1|1753809286|1488|ONLINE|NO|YES|14817978|NOT ACTIVE|0";

static ORA_TEST_LONGACTIVESESSIONS_DATA: &str = "XE.CDB$ROOT||||||||";

static ORA_TEST_PERFORMANCE_SYSTIMEMODEL_DATA: &str = "XE.CDB$ROOT|sys_time_model|DB CPU|16";

static ORA_TEST_PERFORMANCE_SYSWAITCLASS_DATA: &str = r"
XE.CDB$ROOT|sys_wait_class|Administrative|103|0|103|0";

static ORA_TEST_PERFORMANCE_BUFFERPOOL_DATA: &str = r"
XE.CDB$ROOT|buffer_pool_statistics|DEFAULT|20121|25027|345233|19206|1592|0|17";

static ORA_TEST_PERFORMANCE_SGAINFO_DATA: &str = "XE.CDB$ROOT|SGA_info|Fixed SGA Size|9691632";

static ORA_TEST_PERFORMANCE_LIBRARYCACHE_DATA: &str = r"
XE.CDB$ROOT|librarycache|SQL AREA|12297|8158|87660|79684|216|351";

static ORA_TEST_PERFORMANCE_PGAINFO_DATA: &str = r"
XE.CDB$ROOT|PGA_info|MGA allocated (under PGA)|0|bytes";

static ORA_TEST_LOCKS_DATA: &str = "XE.CDB$ROOT|||||||||||||||||";

static ORA_TEST_TABLESPACES_DATA: &str = r"
XE|/opt/oracle/oradata/XE/users01.dbf|
USERS|AVAILABLE|YES|640|4194302|512|160|ONLINE|8192|ONLINE|296|PERMANENT|21.0.0.0.0";

static ORA_TEST_JOBS_DATA: &str = r"
XE|CDB$ROOT|ORACLE_OCM|MGMT_STATS_CONFIG_JOB
|SCHEDULED|1|3|TRUE|01-AUG-25 01.01.01.502927 AM +01:00|-|SUCCEEDED";

static ORA_TEST_IOSTAT_DATA: &str = r"
XE.CDB$ROOT|iostat_file|Archive Log|0|0|0|0|0|0|0|0|0|0|0|0";

static ORA_TEST_SYSTEMPARAM_DATA: &str = "XE|lock_name_space||TRUE";

static ORA_TEST_RESUMABLE_DATA: &str = "XE|||||||||";

fn make_base_config(
    credentials: &Credentials,
    auth_type: AuthType,
    role: Option<Role>,
    address: &str,
    port: u16,
    service_name: Option<ServiceName>,
) -> Config {
    let role_string = if let Some(r) = role {
        format!("{}", r)
    } else {
        String::new()
    };
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{}"
       password: "{}"
       type: {}
       role: {}
    connection:
       hostname: {}
       port: {}
       service_name: "{}"
       timeout: 10
    discovery:
       detect: no
"#,
        credentials.user,
        credentials.password,
        auth_type,
        role_string,
        address,
        port,
        service_name.unwrap_or_default()
    );
    Config::from_string(config_str).unwrap().unwrap()
}

fn reference_endpoint() -> SqlDbEndpoint {
    SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR).unwrap()
}

/// The reference endpoint plus, if configured, the secondary endpoint.
fn working_endpoints() -> Vec<SqlDbEndpoint> {
    let mut endpoints = vec![reference_endpoint()];
    if let Ok(secondary) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_SECONDARY) {
        endpoints.push(secondary);
    }
    endpoints
}

static WORKING_ENDPOINTS: LazyLock<Vec<SqlDbEndpoint>> = LazyLock::new(working_endpoints);

static TEST_SQL_INSTANCE: LazyLock<SqlQuery> = LazyLock::new(|| {
    SqlQuery::new(
        r"
    select upper(i.INSTANCE_NAME)
        ||'|'|| 'sys_time_model'
        ||'|'|| S.STAT_NAME
        ||'|'|| Round(s.value/1000000)
    from v$instance i,
        v$sys_time_model s
    where s.stat_name in('DB time', 'DB CPU')
    order by s.stat_name",
        &Vec::new(),
    )
});

/// `version` selects the SQL variant directly, bypassing the live
/// version/tenant detection of `WorkInstances::get_info`. A legacy version
/// forces the pre-CDB queries.
fn connect_and_query(
    endpoint: &SqlDbEndpoint,
    id: sqls::Id,
    version: Option<InstanceNumVersion>,
) -> Vec<String> {
    let config = make_mini_config(endpoint);
    eprintln!("Connecting to {:#?}", endpoint);

    let spot = backend::make_spot(&config.endpoint()).unwrap();
    let conn = spot.connect(None).unwrap();
    let factory_query = sqls::get_factory_query(id, version, Tenant::All, None).unwrap();
    let queries = section::split_into_queries(&factory_query, config.params());

    queries
        .iter()
        .flat_map(|q| {
            conn.query_table(q)
                .format(&SECTION_SEPARATOR.to_string())
                .unwrap()
        })
        .collect()
}

/// Tests that connect but assert nothing CDB/PDB-specific.
mod connect_and_cdb_agnostic {
    use super::*;

    #[test]
    fn test_authentication_from_env_var() {
        use mk_oracle::config::yaml::test_tools::create_yaml;
        pub const AUTHENTICATION_ENV_VAR: &str = r#"
authentication:
  username: "$CI_ORA2_DB_TEST"
  password: "$CI_ORA2_DB_TEST"
    "#;
        let a = Authentication::from_yaml(&create_yaml(AUTHENTICATION_ENV_VAR))
            .unwrap()
            .unwrap();
        assert_ne!(a.username(), "$CI_ORA2_DB_TEST");
        assert!(a.password().is_some());
        assert_ne!(a.password(), Some("$CI_ORA2_DB_TEST"));
    }

    #[cfg(windows)]
    #[test]
    fn test_environment() {
        // it seems we need this flag to properly link openssl on Windows
        let env_value = std::env::var("CFLAGS")
            .map_err(|e| anyhow::anyhow!("{e}"))
            .unwrap();
        assert_eq!(env_value, "-DNDEBUG");
    }

    #[test]
    fn test_connection_with_explicit_sysdba_role() {
        let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_SECONDARY);
        if r.is_err() {
            eprintln!(
                "Skipping test_connection_with_explicit_sysdba_role: {}",
                r.err().unwrap()
            );
            return;
        }
        add_runtime_to_path();
        let endpoint = r.unwrap();
        let instance_name = get_sid(&endpoint);

        for service_name in [None, Some(ServiceName::from(&endpoint.service_name))] {
            let config = make_base_config(
                &Credentials {
                    user: endpoint.user.clone(),
                    password: endpoint.pwd.clone(),
                },
                AuthType::Standard,
                Some(Role::SysDba),
                &endpoint.host,
                endpoint.port,
                service_name.clone(),
            );
            let spot = backend::make_spot(&config.endpoint()).unwrap();
            let conn = spot.connect(None).unwrap();
            let result = conn.query_table(&TEST_SQL_INSTANCE).format("");
            assert!(result.is_ok());
            let rows = result.unwrap();
            eprintln!(
                "Rows: {service_name:?} {:?} {:?}",
                rows,
                conn.target()
                    .make_connection_string(None, ConnectionStringType::Tns)
            );
            assert!(!rows.is_empty());
            assert!(rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &instance_name)));
            assert!(rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &instance_name)));
            assert_eq!(rows.len(), 2);
        }
    }

    #[test]
    fn test_remote_mini_connection() {
        add_runtime_to_path();
        let endpoint = reference_endpoint();
        let config = make_mini_config(&endpoint);

        let spot = backend::make_spot(&config.endpoint()).unwrap();
        println!("Target {:?}", spot.target());
        let conn = spot.connect(None).unwrap();
        let result = conn.query_table(&TEST_SQL_INSTANCE).format("");
        assert!(result.is_ok());
        let rows = result.unwrap();
        assert!(!rows.is_empty());
        let sid_name = &endpoint.sid.clone().unwrap();
        assert!(
            rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &sid_name)),
            "Actual: {}",
            rows[0]
        );
        assert!(
            rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &sid_name)),
            "Actual: {}",
            rows[1]
        );
        assert_eq!(rows.len(), 2);
    }

    #[test]
    fn test_remote_custom_metric_with_sql_params() {
        add_runtime_to_path();
        let endpoint = reference_endpoint();
        let config_str = format!(
            r#"
---
oracle:
  main:
    authentication:
       username: "{}"
       password: "{}"
       type: standard
       role: {}
    connection:
       hostname: {}
       port: {}
       timeout: 10
       service_name: {}
    discovery:
       detect: no
    custom_metrics:
      - params_metric:
          sql: "select 'details:${{greeting}}' from dual; select ${{column}} from dual"
          sql_params:
            greeting: "hello-from-params"
            column: "dummy"
    "#,
            endpoint.user,
            endpoint.pwd,
            role_spec(&endpoint.role),
            endpoint.host,
            endpoint.port,
            endpoint.service_name
        );
        let config = Config::from_string(config_str).unwrap().unwrap();

        let custom = config
            .all_sections()
            .iter()
            .find(|s| s.is_custom_metric())
            .expect("custom metric must be parsed");
        let runtime = section::Section::new(custom, 0, config.options());
        let queries = runtime
            .find_queries_with_search_dirs(InstanceNumVersion::from(0), Tenant::All, &[], &[])
            .expect("custom metric sql must yield queries");
        assert_eq!(queries.len(), 2);
        assert_eq!(
            queries[0].as_str(),
            "select 'details:hello-from-params' from dual"
        );
        assert_eq!(queries[1].as_str(), "select dummy from dual");

        let spot = backend::make_spot(&config.endpoint()).unwrap();
        let conn = spot.connect(None).unwrap();
        let rows = conn
            .query_table(&queries[0])
            .format("")
            .expect("patched literal query must execute");
        assert_eq!(rows, vec!["details:hello-from-params".to_string()]);
        let rows = conn
            .query_table(&queries[1])
            .format("")
            .expect("patched column-name query must execute");
        assert_eq!(rows, vec!["X".to_string()], "dual.dummy always holds 'X'");
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_remote_sid_only_connection() {
        add_runtime_to_path();
        let endpoint = reference_endpoint();
        let sid = endpoint
            .sid
            .clone()
            .or_else(|| endpoint.instance_name.clone())
            .unwrap_or_else(|| endpoint.service_name.clone());
        let config = make_mini_config_with_sid(&endpoint, &sid);

        let env = Env::default();
        let result = generate_data(&config, &env).await;
        assert!(result.is_ok());
        let table = result.unwrap();
        assert_eq!(
            table.len(),
            2,
            "Unexpected table length: {:?}, table: {:?}",
            table.len(),
            table
        );
        assert_eq!(table[0], "<<<oracle_instance>>>");
        let rows: Vec<&str> = table[1].split("\n").collect();
        assert!(!rows.is_empty());
        for r in rows[1..].iter() {
            assert!(r.starts_with(&format!("{}|", sid.to_uppercase())));
        }
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_remote_custom_instance_connection() {
        add_runtime_to_path();
        let endpoint = reference_endpoint();
        let config = make_mini_config_custom_instance(&endpoint, &endpoint.service_name, None);
        let env = Env::default();
        let r = generate_data(&config, &env).await;

        assert!(r.is_ok());
        let table = r.unwrap();
        eprintln!("{:?}", table);
        assert_eq!(table.len(), 2);
        assert_eq!(table[0], "<<<oracle_instance>>>");
        let rows: Vec<&str> = table[1].split("\n").collect();
        eprintln!("{rows:?}");
        assert_eq!(rows[0], "<<<oracle_instance:sep(124)>>>");
        for r in rows[1..].iter() {
            assert!(r.starts_with(endpoint.sid.as_ref().unwrap()));
        }
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_absent_remote_custom_instance_connection() {
        add_runtime_to_path();

        let endpoint = reference_endpoint();
        let config = make_mini_config_custom_instance(&endpoint, "absent", None);
        let env = Env::default();
        let r = generate_data(&config, &env).await;

        assert!(r.is_ok());
        let table = r.unwrap();
        assert_eq!(table[0], "<<<oracle_instance>>>");
        assert_eq!(table[1], "<<<oracle_instance:sep(124)>>>");
        assert!(
            table[2].starts_with("ABSENT|FAILURE|ERROR: ORA-"),
            "Unexpected output: {:?}",
            table
        );
    }

    // TODO: Remove windows tag when TNS_ADMIN is properly supported on non-Windows platforms
    //#[cfg(windows)]
    #[tokio::test(flavor = "multi_thread")]
    async fn test_remote_tns_custom_instance_connection() {
        use mk_oracle::types::InstanceAlias;

        add_runtime_to_path();
        log::warn!(
            "TNS_ADMIN='{}'",
            std::env::var("TNS_ADMIN").unwrap_or_default()
        );
        let endpoint = reference_endpoint();
        // Resolve the alias through a generated tnsnames.ora that points at the
        // reference endpoint itself: the alias mechanics get exercised without
        // pinning the test to one specific reference DB host.
        let tns_admin = make_endpoint_tns_admin_dir(&endpoint, "ora_remote");
        let config = make_mini_config_custom_instance_with_tns_admin(
            &endpoint,
            "FREE",
            Some(InstanceAlias::from("ora_remote".to_string())),
            &tns_admin,
        );
        let env = Env::default();
        let r = generate_data(&config, &env).await;

        assert!(r.is_ok());
        let table = r.unwrap();
        assert_eq!(table.len(), 2, "{:?}", table);
        assert_eq!(table[0], "<<<oracle_instance>>>");
        let rows: Vec<&str> = table[1].split("\n").collect();
        assert_eq!(rows[0], "<<<oracle_instance:sep(124)>>>");
        for r in rows[1..].iter() {
            let expected_sid = get_sid(&endpoint);
            assert!(
                r.starts_with(expected_sid.as_str()),
                "Row does not start with {expected_sid}: {r}"
            );
        }
    }

    // `VERSION_FULL_2` does not exist: the query fails and drives
    // `WorkInstances::new` into its pre-VERSION_FULL fallback path.
    pub const INSTANCE_INFO_SQL_TEXT_FAIL: &str = r"
SELECT
    INSTANCE_NAME,
    i.CON_ID,
    VERSION_FULL_2,
    d.name,
    d.cdb
    FROM v$instance i
    join v$database d
        on i.con_id = d.con_id";

    #[test]
    fn test_remote_mini_connection_version() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            eprintln!("Endpoint: {}", endpoint.host);
            let config = make_mini_config(endpoint);

            let spot = backend::make_spot(&config.endpoint()).unwrap();
            let conn = spot
                .connect(None)
                .expect("Connect failed, check environment variables");

            // get instances using two different scripts, one of them simulates call to the old instance
            // which doesn't report VERSION_FULL
            let instances_new = system::WorkInstances::new(&conn, None);
            let instances_old =
                system::WorkInstances::new(&conn, Some(INSTANCE_INFO_SQL_TEXT_FAIL));
            let r_new = instances_new
                .unwrap()
                .get_full_version(&InstanceName::from(get_sid(endpoint)));
            let r_old = instances_old
                .unwrap()
                .get_full_version(&InstanceName::from(get_sid(endpoint)));
            let version_ok = r_new.unwrap();
            let version_old = r_old.unwrap();
            //check that both methods return the same values
            assert_eq!(version_ok, version_old);
            assert!(
                system::convert_to_num_version(&version_ok).is_some(),
                "not a well-formed version: {version_ok}"
            );

            // check missing db again
            let instances_new = system::WorkInstances::new(&conn, None);
            assert!(instances_new
                .unwrap()
                .get_full_version(&InstanceName::from("no-such-db"))
                .is_none());
        }
    }

    #[test]
    fn test_io_stats_query() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            let rows = connect_and_query(endpoint, sqls::Id::IoStats, None);
            assert!(rows.len() > 10);
            let name_dot = format!("{}.", &endpoint.sid.clone().unwrap());
            for r in &rows {
                let values: Vec<String> = r.split('|').map(|s| s.to_string()).collect();
                assert_eq!(
                    values.len(),
                    ORA_TEST_IOSTAT_DATA.split('|').collect::<Vec<_>>().len(),
                    "Row does not have enough columns: {}",
                    r
                );
                assert!(
                    values[0].starts_with(name_dot.as_str()),
                    "Row does not start with SID name: {}",
                    r
                );
                assert_eq!(values[1], "iostat_file");
                let all_types: HashSet<String> = HashSet::from_iter(
                    vec![
                        "Archive Log",
                        "Archive Log Backup",
                        "Control File",
                        "Data File",
                        "Data File Backup",
                        "Data File Copy",
                        "Data File Incremental Backup",
                        "Data Pump Dump File",
                        "External Table",
                        "Flashback Log",
                        "Log File",
                        "Other",
                        "Temp File",
                    ]
                    .into_iter()
                    .map(|s| s.to_string()),
                );
                let the_type = &values[2];
                assert!(all_types.contains(the_type), "Wrong type: {}", the_type);
                for v in &values[3..] {
                    assert!(v.parse::<u64>().is_ok(), "Value is not digit: {}", v);
                }
            }
        }
    }

    #[test]
    fn test_ts_quotas() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::TsQuotas, None);
            assert!(!rows.is_empty());
            let expected = format!("{}||||", get_service_name(endpoint));
            assert_eq!(rows[0], expected);
        }
    }

    #[test]
    fn test_jobs() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Jobs, None);
            assert!(rows.len() > 10);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_JOBS_DATA.split('|').collect::<Vec<_>>().len(),
                    "Row does not have enough columns: {}",
                    r
                );
                assert_eq!(line[0], get_sid(endpoint).as_str());
                assert!(
                    [1, 2, 3, 4, 6, 7, 8]
                        .iter()
                        .all(|i| { !line[*i].is_empty() }),
                    "Columns 1, 2, 3, 4, 6, 7, 8 should be NOT empty: {:?}",
                    line
                );
            });
        }
    }

    #[test]
    fn test_resumable() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Resumable, None);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_RESUMABLE_DATA.split('|').collect::<Vec<_>>().len(),
                );
            });
            assert_eq!(
                rows[0],
                format!("{}|||||||||", endpoint.sid.clone().unwrap().as_str())
            );
        }
    }

    #[test]
    fn test_undo_stats() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            for version in [None, Some(InstanceNumVersion::from(11_00_00_00))] {
                println!("Testing version: {:?}", version);
                let rows = connect_and_query(endpoint, sqls::Id::UndoStat, version);
                assert_eq!(rows.len(), 1);
                let r = &rows[0];
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_UNDOSTAT_DATA.split('|').collect::<Vec<_>>().len(),
                    "Row does not have enough columns: {}",
                    r,
                );
                assert_eq!(line[0], get_sid(endpoint));
                assert!(
                    [2, 3, 4, 5]
                        .iter()
                        .all(|i| { line[*i].parse::<u32>().is_ok() }),
                    "Columns 2..5 should be numbers: {:?}",
                    line
                );
            }
        }
    }

    #[test]
    fn test_log_switches() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::LogSwitches, None);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_LOGSWITCHES_DATA
                        .split('|')
                        .collect::<Vec<_>>()
                        .len(),
                    "Row does not have enough columns: {}",
                    rows.len()
                );
            });
            assert!(!rows.is_empty());
            // we only check that instance name is correct
            assert!(rows[0].starts_with(format!("{}|", get_sid(endpoint)).as_str()));
        }
    }

    #[test]
    fn test_processes() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Processes, None);
            assert!(!rows.is_empty());
            let array = rows[0].split('|').collect::<Vec<&str>>();
            assert_eq!(
                array.len(),
                ORA_TEST_PROCESSES_DATA.split('|').collect::<Vec<_>>().len(),
                "Row does not have enough columns: {}",
                rows.len()
            );
            assert_eq!(array[0], get_sid(endpoint).as_str());
            assert!(array[1].parse::<u32>().is_ok());
            assert!(array[2].parse::<u32>().is_ok());
        }
    }

    #[test]
    fn test_recovery_status_last() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::RecoveryStatus, None);
            for r in rows {
                let array = r.split('|').collect::<Vec<&str>>();
                assert_eq!(
                    array.len(),
                    ORA_TEST_RECOVERY_STATUS_DATA
                        .split('|')
                        .collect::<Vec<_>>()
                        .len(),
                );
                assert!(array[0].starts_with(get_service_name(endpoint).as_str()));
                // column 1 contains uniq database name which may differ in casing from SID/Instance
                assert_eq!(array[1].to_uppercase(), get_service_name(endpoint).as_str());
                assert!(!array[2].is_empty());
                assert!(!array[3].is_empty());
                assert!(array[4].parse::<u32>().is_ok());
                assert!(array[5].parse::<u32>().is_ok());
                assert!(array[6].parse::<u64>().is_ok());
                assert!(!array[7].is_empty());
                assert!(!array[9].is_empty());
                assert!(array[10].parse::<u32>().is_ok());
            }
        }
    }

    #[test]
    fn test_rman() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Rman, None);
            assert!(rows.is_empty());
        }
    }

    #[test]
    fn test_system_parameter() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::SystemParameter, None);
            assert!(rows.len() > 100);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_SYSTEMPARAM_DATA
                        .split('|')
                        .collect::<Vec<_>>()
                        .len(),
                );
                assert_eq!(line[0], get_sid(endpoint).as_str());
                assert!(!line[1].is_empty());
                assert!(
                    line[3] == "TRUE" || line[3] == "FALSE",
                    "Value is not TRUE or FALSE:  {:?}",
                    line
                );
            });
        }
    }

    #[test]
    fn test_table_spaces() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::TableSpaces, None);
            assert!(rows.len() > 2);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_TABLESPACES_DATA
                        .split('|')
                        .collect::<Vec<_>>()
                        .len(),
                );
                // SID23 or SID23.CDB$ROOT or SID23.PDBXXX
                assert!(
                    line[0].starts_with(get_service_name(endpoint).as_str()),
                    "{}",
                    line[0]
                );
                assert!(
                    line[1].to_uppercase().ends_with(".DBF"),
                    "File name does not end with .DBF: {}",
                    line[1]
                );
                assert!(
                    line[3] == "ONLINE" || line[3] == "AVAILABLE",
                    "3 is not ONLINE or AVAILABLE: {} {}",
                    line[3],
                    r
                );
                for i in [5, 6, 7, 8, 10, 12] {
                    assert!(
                        line[i].parse::<u64>().is_ok(),
                        "Value is not a number: {} line = {}",
                        line[i],
                        r
                    );
                }
                assert!(line[11] == "ONLINE", "11 is not ONLINE: {} {}", line[11], r);
                assert!(
                    line[14].ends_with(".0.0.0.0"),
                    "14 is not version: {} {}",
                    line[14],
                    r
                );
            });
        }
    }

    #[test]
    fn test_data_guard_stats() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::DataGuardStats, None);
            assert!(rows.is_empty());
        }
    }

    #[test]
    fn test_instance() {
        use crate::system::convert_to_num_version;
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Instance, None);
            assert!(rows.len() > 2);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_INSTANCE_DATA.split('|').collect::<Vec<_>>().len(),
                );
                assert_eq!(line[0], get_sid(endpoint).as_str());
                assert!(
                    convert_to_num_version(&InstanceVersion::from(line[1].to_string())).is_some(),
                    "1 is not a valid instance name: {}",
                    line[1]
                );
                assert_eq!(line[2], "OPEN");
                assert_eq!(line[3], "ALLOWED");
                for i in [5, 6, 11, 13, 15, 20, 21] {
                    assert!(
                        line[i].parse::<i64>().is_ok(),
                        "Value is not a number: {} line = {}",
                        line[i],
                        r
                    );
                }
                for i in [7, 8, 9, 10, 13] {
                    assert!(!line[i].is_empty(), "Value is empty: {} line = {}", i, r);
                }
            });
        }
    }

    #[test]
    fn test_instance_full_version() {
        use crate::system::convert_to_num_version;
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Instance,
                Some(InstanceNumVersion::from(18_00_00_00)),
            );
            assert!(!rows.is_empty());
            let line_last: Vec<&str> = rows[0].split("|").collect();
            assert!(
                convert_to_num_version(&InstanceVersion::from(line_last[1].to_string())).is_some(),
                "1 is not a valid instance name: {}",
                line_last[1]
            );
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Instance,
                Some(InstanceNumVersion::from(17_00_00_00)),
            );
            assert!(!rows.is_empty());
            let line_old: Vec<&str> = rows[0].split("|").collect();
            assert!(
                convert_to_num_version(&InstanceVersion::from(line_old[1].to_string())).is_some(),
                "1 is not a valid instance name: {}",
                line_old[1]
            );
            assert_ne!(
                line_last[1], line_old[1],
                "Last and old versions should not be equal"
            );
        }
    }

    #[ignore = "due to lack of ASM instances in test environments"]
    #[test]
    fn test_asm_instance_new() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::AsmInstance, None);
            assert_eq!(rows.len(), 1);
            let r = rows[0].clone();
            let line: Vec<&str> = r.split("|").collect();
            assert_eq!(line.len(), 12);
            assert_eq!(line[0], get_sid(endpoint).as_str());
            assert!(
                !line[1].ends_with(".0.0.0.0"),
                "1 is not a valid instance version: {}",
                line[1]
            );
            assert_eq!(line[2], "OPEN");
            assert_eq!(line[3], "ALLOWED");
            for i in [5, 6] {
                assert!(
                    line[i].parse::<i64>().is_ok(),
                    "Value is not a number: {} line = {}",
                    line[i],
                    r
                );
            }
            assert_eq!(line[8], "ASM");
            for i in [7, 9, 10, 11] {
                assert!(!line[i].is_empty(), "Value is empty: {} line = {}", i, r);
            }

            let old_rows = connect_and_query(
                endpoint,
                sqls::Id::AsmInstance,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            let old_line: Vec<&str> = old_rows[0].split("|").collect();
            assert!(
                old_line[1].ends_with(".0.0.0.0"),
                "1 is not a valid instance version: {}",
                old_line[1]
            );
            assert_eq!(line[0], old_line[0]);
            for i in 8..11 {
                assert_eq!(line[i], old_line[i]);
            }
        }
    }
}

/// Tests forcing the pre-CDB query variant via an explicit version.
mod non_cdb_simulated {
    use super::*;

    #[test]
    fn test_jobs_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Jobs,
                Some(InstanceNumVersion::from(11_00_00_00)),
            );
            assert!(rows.len() > 10);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(line.len(), 10, "Row does not have enough columns: {}", r);
                assert_eq!(line[0], get_service_name(endpoint));
                assert!(
                    [1, 2, 3, 5, 6].iter().all(|i| { !line[*i].is_empty() }),
                    "Columns 1, 2, 3, 5, 6 should be NOT empty: {:?}",
                    line
                );
            });
        }
    }

    #[test]
    fn test_locks_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Locks,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_LOCKS_DATA.split('|').collect::<Vec<_>>().len(),
                    "Row does not have enough columns: {}",
                    rows.len()
                );
            });
            assert!(!rows.is_empty());
            // We may receive here either
            // FREE|206|37328|klapp-0336|pa@klapp-0336 (TNS V1-V3)|12|sergeykipnis|SYSTEM|0|VALID|1|179|64573|klapp-0336|pa@klapp-0336 (TNS V1-V3)|12|sergeykipnis|SYSTEM
            // or
            // FREE|||||||||||||||||
            // Let's QA team checks correctness
            assert!(rows[0].starts_with(format!("{}|", get_sid(endpoint)).as_str()));
        }
    }

    #[test]
    fn test_long_active_sessions_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::LongActiveSessions,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            assert!(!rows.is_empty());
            assert_eq!(rows[0], format!("{}||||||||", get_sid(endpoint)));
        }
    }

    #[test]
    fn test_recovery_status_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::RecoveryStatus,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            assert!(rows.len() > 10);
            for r in rows {
                let array = r.split('|').collect::<Vec<&str>>();
                assert_eq!(array.len(), 11);
                assert_eq!(array[0], get_service_name(endpoint).as_str());
                // column 1 contains uniq database name which may differ in casing from SID/Instance
                assert_eq!(array[1].to_uppercase(), get_service_name(endpoint));
                assert!(!array[2].is_empty());
                assert!(!array[3].is_empty());
                assert!(array[4].parse::<u32>().is_ok());
                assert!(array[5].parse::<u32>().is_ok());
                assert!(array[6].parse::<u64>().is_ok());
                assert!(!array[7].is_empty());
                assert!(!array[9].is_empty());
                assert!(array[10].parse::<u32>().is_ok());
            }
        }
    }

    #[test]
    fn test_rman_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Rman,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            assert!(rows.is_empty());
        }
    }

    #[test]
    fn test_sessions_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Sessions,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            assert_eq!(rows.len(), 1);
            let line: Vec<&str> = rows[0].split("|").collect();
            assert_eq!(line.len(), 4);
            line[1..].iter().for_each(|s| {
                assert!(s.parse::<i32>().is_ok(), "Value is not a number: {}", s);
            });
        }
    }

    #[test]
    fn test_table_spaces_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::TableSpaces,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            assert!(rows.len() > 2);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(line.len(), 15);
                // SID23 or SID23.CDB$ROOT or SID23.PDBXXX or dbtest23
                assert!(line[0].starts_with(get_service_name(endpoint).as_str()));
                assert!(
                    line[1].to_uppercase().ends_with(".DBF"),
                    "File name does not end with .DBF: {}",
                    line[1]
                );
                assert!(
                    line[3] == "ONLINE" || line[3] == "AVAILABLE",
                    "3 is not ONLINE or AVAILABLE: {} {}",
                    line[3],
                    r
                );
                for i in [5, 6, 7, 8, 10, 12] {
                    assert!(
                        line[i].parse::<u64>().is_ok(),
                        "Value is not a number: {} line = {}",
                        line[i],
                        r
                    );
                }
                assert!(line[11] == "ONLINE", "11 is not ONLINE: {} {}", line[11], r);
                assert!(
                    line[14].ends_with(".0.0.0.0"),
                    "14 is not version: {} {}",
                    line[14],
                    r
                );
            });
        }
    }

    #[test]
    fn test_instance_old() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Instance,
                Some(InstanceNumVersion::from(12_00_00_00)),
            );
            assert_eq!(rows.len(), 1);
            let r = rows[0].clone();
            let line: Vec<&str> = r.split("|").collect();
            assert_eq!(line.len(), 13);
            assert_eq!(line[0], get_sid(endpoint).as_str());
            assert!(
                line[1].ends_with(".0.0.0"),
                "1 is not a valid instance version: {}",
                line[1]
            );
            assert_eq!(line[2], "OPEN");
            assert_eq!(line[3], "ALLOWED");
            for i in [5, 6, 11] {
                assert!(
                    line[i].parse::<i64>().is_ok(),
                    "Value is not a number: {} line = {}",
                    line[i],
                    r
                );
            }
            for i in [7, 8, 9, 10, 12] {
                assert!(!line[i].is_empty(), "Value is empty: {} line = {}", i, r);
            }
        }
    }

    #[test]
    fn test_performance_old() {
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(
                endpoint,
                sqls::Id::Performance,
                Some(InstanceNumVersion::from(11_00_00_00)),
            );
            assert!(rows.len() > 30);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert!(line[0].starts_with(get_sid(endpoint).as_str()));
                assert!(
                    [4, 5, 7, 9, 10].contains(&line.len()),
                    "Row has wrong quantities of columns: {} {}",
                    r,
                    line.len()
                );
                assert!(
                    [
                        "SGA_info",
                        "librarycache",
                        "sys_time_model",
                        "sys_wait_class",
                        "buffer_pool_statistics"
                    ]
                    .contains(&line[1]),
                    "Column 2 is wrong: {} {}",
                    r,
                    line[2]
                );
            });
        }
    }
}

/// Tests needing a CDB with at least one PDB.
mod cdb {
    use super::*;

    #[test]
    fn test_locks_last() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Locks, None);
            assert!(rows.len() >= 3);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_LOCKS_DATA.split('|').collect::<Vec<_>>().len(),
                    "Row does not have enough columns: {}",
                    rows.len()
                );
            });
            // We may receive here either
            // ???CDB/???PDB???|206|37328|klapp-0336|pa@klapp-0336 (TNS V1-V3)|12|sergeykipnis|SYSTEM|0|VALID|1|179|64573|klapp-0336|pa@klapp-0336 (TNS V1-V3)|12|sergeykipnis|SYSTEM
            // or
            // FREE|||||||||||||||||
            // Let's QA team checks correctness
            let sid = get_sid(endpoint);
            let sid_name = sid.as_str();
            let cdb_prefix = format!("{}.CDB$ROOT|", sid_name);
            let pdb_prefix = format!("{0}.", sid_name);

            let row_prefixes = [cdb_prefix.as_str(), pdb_prefix.as_str(), sid_name];
            assert!(
                row_prefixes.iter().any(|p| rows[0].starts_with(p)),
                "expected {} to start with one of {:?}",
                rows[0],
                row_prefixes
            );
            assert!(
                row_prefixes.iter().any(|p| rows[1].starts_with(p)),
                "expected {} to start with one of {:?}",
                rows[1],
                row_prefixes
            );
            assert!(
                row_prefixes.iter().any(|p| rows[2].starts_with(p)),
                "expected {} to start with one of {:?}",
                rows[2],
                row_prefixes
            );
        }
    }

    #[test]
    fn test_long_active_sessions_last() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::LongActiveSessions, None);
            assert!(rows.len() >= 3);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_LONGACTIVESESSIONS_DATA
                        .split('|')
                        .collect::<Vec<_>>()
                        .len(),
                    "Row does not have enough columns: {}",
                    rows.len()
                );
            });

            let inst = get_sid(endpoint);
            assert_eq!(rows[0], format!("{}.CDB$ROOT||||||||", inst));
            // may contain something like
            // "SIDD23.PDB23_1||||||||"
            // "SID23.SID23PDB1||||||||"
            // <inst>.<anything>PDB<anything>1||||||||
            let re = Regex::new(&format!(
                r"^{}\..*PDB.*1\|\|\|\|\|\|\|\|$",
                regex::escape(&inst),
            ))
            .unwrap();

            assert!(re.is_match(&rows[1]), "row did not match: {}", rows[1]);
            assert_eq!(rows[2], format!("{}||||||||", inst));
        }
    }

    #[test]
    fn test_sessions_last() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Sessions, None);
            assert_eq!(rows.len(), 3);
            let start = get_sid(endpoint) + ".";
            for n in [0, 1] {
                let r = rows[n].clone();
                assert!(r.starts_with(start.as_str()));

                let line: Vec<&str> = r.split("|").collect();
                assert_eq!(
                    line.len(),
                    ORA_TEST_SESSION_PDB_DATA
                        .split('|')
                        .collect::<Vec<_>>()
                        .len(),
                );
                assert!(
                    line[1].parse::<i32>().is_ok(),
                    "Value is not a number: {}",
                    line[1]
                );
            }

            let line_2: Vec<&str> = rows[2].split("|").collect();
            assert_eq!(
                line_2.len(),
                ORA_TEST_SESSION_CDB_DATA
                    .split('|')
                    .collect::<Vec<_>>()
                    .len(),
            );
            line_2[1..].iter().for_each(|s| {
                assert!(s.parse::<i32>().is_ok(), "Value is not a number: {}", s);
            });
        }
    }

    #[test]
    fn test_performance_new() {
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let rows = connect_and_query(endpoint, sqls::Id::Performance, None);
            assert!(rows.len() > 30);
            rows.iter().for_each(|r| {
                let line: Vec<&str> = r.split("|").collect();
                match line[1] {
                    "PGA_info" => assert_eq!(
                        line.len(),
                        ORA_TEST_PERFORMANCE_PGAINFO_DATA
                            .split('|')
                            .collect::<Vec<_>>()
                            .len()
                    ),
                    "SGA_info" => assert_eq!(
                        line.len(),
                        ORA_TEST_PERFORMANCE_SGAINFO_DATA
                            .split('|')
                            .collect::<Vec<_>>()
                            .len()
                    ),
                    "librarycache" => assert_eq!(
                        line.len(),
                        ORA_TEST_PERFORMANCE_LIBRARYCACHE_DATA
                            .split('|')
                            .collect::<Vec<_>>()
                            .len()
                    ),
                    "sys_time_model" => assert_eq!(
                        line.len(),
                        ORA_TEST_PERFORMANCE_SYSTIMEMODEL_DATA
                            .split('|')
                            .collect::<Vec<_>>()
                            .len()
                    ),
                    "sys_wait_class" => assert_eq!(
                        line.len(),
                        ORA_TEST_PERFORMANCE_SYSWAITCLASS_DATA
                            .split('|')
                            .collect::<Vec<_>>()
                            .len()
                    ),
                    "buffer_pool_statistics" => assert_eq!(
                        line.len(),
                        ORA_TEST_PERFORMANCE_BUFFERPOOL_DATA
                            .split('|')
                            .collect::<Vec<_>>()
                            .len()
                    ),
                    _ => panic!("Unknown category: {} in line {}", line[1], r),
                }
                assert!(line[0].starts_with(format!("{}.", get_sid(endpoint).as_str()).as_str()));
                assert!(
                    [4, 5, 7, 9, 10].contains(&line.len()),
                    "Row has wrong quantities of columns: {} {}",
                    r,
                    line.len()
                );
                assert!(
                    [
                        "PGA_info",
                        "SGA_info",
                        "librarycache",
                        "sys_time_model",
                        "sys_wait_class",
                        "buffer_pool_statistics"
                    ]
                    .contains(&line[1]),
                    "Column 2 is wrong: {} {}",
                    r,
                    line[2]
                );
                assert!(line[0].starts_with(get_sid(endpoint).as_str()));
            });
        }
    }

    #[test]
    fn test_pdbs_discovery() {
        use mk_oracle::ora_sql::pdbs::Pdbs;
        add_runtime_to_path();
        for endpoint in WORKING_ENDPOINTS.iter() {
            println!("endpoint.host = {}", &endpoint.host);
            let config = make_mini_config(endpoint);

            let spot = backend::make_spot(&config.endpoint()).unwrap();
            let conn = spot
                .connect(None)
                .expect("Connect failed, check environment variables");

            let pdbs = Pdbs::discover(&conn).expect("PDB discovery failed");

            // The test database has a single user PDB. We don't care about its
            // name — just that exactly one survives after CDB$ROOT and PDB$SEED
            // have been filtered out.
            assert_eq!(
                pdbs.len(),
                1,
                "Expected exactly one PDB after filtering, got {:?}",
                pdbs.names(),
            );
        }
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_pdb_nonexistent_pattern_produces_no_subsection() {
        add_runtime_to_path();
        let Some(ep) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR).ok() else {
            return;
        };
        let config = make_mini_config_pdb(&ep, &["GHOST_PDB"]);
        let env = Env::default();
        let output = generate_data(&config, &env).await.unwrap().join("\n");
        assert!(
            !output.contains("container_identity"),
            "expected no subsection output: {output}"
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_pdb_wildcard_pattern_targets_all_discovered_pdbs() {
        use mk_oracle::ora_sql::pdbs::Pdbs;
        add_runtime_to_path();
        let Some(endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR).ok() else {
            return;
        };
        let sid = endpoint
            .sid
            .as_deref()
            .unwrap_or(&endpoint.service_name)
            .to_uppercase();

        let config = make_mini_config_pdb(&endpoint, &[".*"]);
        let spot = backend::make_spot(&config.endpoint()).unwrap();
        let conn = spot
            .connect(None)
            .expect("Connect failed, check environment variables");

        let discovered = Pdbs::discover(&conn).expect("PDB discovery failed");
        let env = Env::default();
        let output = generate_data(&config, &env).await.unwrap().join("\n");

        assert!(
            !discovered.is_empty(),
            "test endpoint must expose at least one PDB for this scenario"
        );

        assert_eq!(
            output.matches("|container_identity").count(),
            discovered.len(),
            "expected exactly one subsection per discovered PDB: {output}"
        );

        for pdb in discovered.names() {
            assert!(
                output.contains(&format!("{sid}_{pdb}|container_identity")),
                "expected subsection header for PDB {pdb}: {output}"
            );
        }
    }

    // TC-ORA-144
    #[tokio::test(flavor = "multi_thread")]
    async fn test_pdb_scoped_query_reverts_to_cdb_root_builtin_then_custom() {
        use mk_oracle::ora_sql::pdbs::Pdbs;
        add_runtime_to_path();
        let Some(endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR).ok() else {
            return;
        };
        let sid = endpoint
            .sid
            .as_deref()
            .unwrap_or(&endpoint.service_name)
            .to_uppercase();

        let discovery_config = make_mini_config_pdb(&endpoint, &[".*"]);
        let spot = backend::make_spot(&discovery_config.endpoint()).unwrap();
        let conn = spot
            .connect(None)
            .expect("Connect failed, check environment variables");
        let discovered = Pdbs::discover(&conn).expect("PDB discovery failed");
        let pdb = discovered
            .names()
            .first()
            .expect("test endpoint must expose at least one PDB for this scenario")
            .as_ref()
            .to_string();

        let config = make_mini_config_pdb_builtin_then_custom(&endpoint, &pdb);
        let env = Env::default();
        let output = generate_data(&config, &env).await.unwrap().join("\n");

        let builtin_pos = output
            .find(&format!("[[[{sid}|probe_builtin]]]\nCDB$ROOT"))
            .unwrap_or_else(|| panic!("expected leading probe to see CDB$ROOT: {output}"));
        let pdb_pos = output
            .find(&format!("[[[{sid}_{pdb}|probe_pdb]]]\n{pdb}"))
            .unwrap_or_else(|| panic!("expected PDB-scoped probe to see {pdb}: {output}"));
        let followup_pos = output
            .find(&format!("[[[{sid}|probe_followup]]]\nCDB$ROOT"))
            .unwrap_or_else(|| panic!("expected follow-up probe to see CDB$ROOT again: {output}"));

        assert!(
            builtin_pos < pdb_pos && pdb_pos < followup_pos,
            "expected probes in order builtin -> pdb -> followup; \
             out-of-order output means the PDB switch didn't revert to CDB$ROOT \
             before the follow-up query ran: {output}"
        );
    }

    // TC-ORA-144
    #[tokio::test(flavor = "multi_thread")]
    async fn test_pdb_scoped_query_reverts_to_cdb_root_custom_then_builtin() {
        use mk_oracle::ora_sql::pdbs::Pdbs;
        add_runtime_to_path();
        let Some(endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR).ok() else {
            return;
        };
        let sid = endpoint
            .sid
            .as_deref()
            .unwrap_or(&endpoint.service_name)
            .to_uppercase();

        let discovery_config = make_mini_config_pdb(&endpoint, &[".*"]);
        let spot = backend::make_spot(&discovery_config.endpoint()).unwrap();
        let conn = spot
            .connect(None)
            .expect("Connect failed, check environment variables");
        let discovered = Pdbs::discover(&conn).expect("PDB discovery failed");
        let pdb = discovered
            .names()
            .first()
            .expect("test endpoint must expose at least one PDB for this scenario")
            .as_ref()
            .to_string();

        let config = make_mini_config_pdb_custom_then_builtin(&endpoint, &pdb);
        let env = Env::default();
        let output = generate_data(&config, &env).await.unwrap().join("\n");

        let pdb_pos = output
            .find(&format!("[[[{sid}_{pdb}|probe_pdb]]]\n{pdb}"))
            .unwrap_or_else(|| panic!("expected PDB-scoped probe to see {pdb}: {output}"));
        let followup_pos = output
            .find(&format!("[[[{sid}|probe_followup]]]\nCDB$ROOT"))
            .unwrap_or_else(|| panic!("expected follow-up probe to see CDB$ROOT: {output}"));

        assert!(
            pdb_pos < followup_pos,
            "expected probe_pdb before probe_followup; \
             out-of-order output means the PDB switch didn't revert to CDB$ROOT \
             before the follow-up query ran: {output}"
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_pdb_absent_runs_against_cdb_root() {
        add_runtime_to_path();
        let Some(ep) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR).ok() else {
            return;
        };
        let sid = ep.sid.as_deref().unwrap_or(&ep.service_name).to_uppercase();
        let config = make_mini_config_cdb_root(&ep);
        let env = Env::default();
        let output = generate_data(&config, &env).await.unwrap().join("\n");
        assert!(
            output.contains(&format!("{sid}|container_identity")),
            "expected CDB root subsection: {output}"
        );
        assert!(
            output.contains("CDB$ROOT"),
            "expected CDB$ROOT in output: {output}"
        );
    }
}
