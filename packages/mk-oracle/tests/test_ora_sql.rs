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

#[cfg(feature = "build_system_bazel")]
extern crate common;
#[cfg(not(feature = "build_system_bazel"))]
mod common;

use crate::common::tools::{
    make_endpoint_tns_admin_dir, make_mini_config, make_mini_config_cdb_root,
    make_mini_config_custom_instance, make_mini_config_custom_instance_with_tns_admin,
    make_mini_config_pdb, make_mini_config_pdb_builtin_then_custom,
    make_mini_config_pdb_custom_then_builtin, make_mini_config_with_sid,
    platform::add_runtime_to_path, role_spec, ORA_ENDPOINT_ENV_VAR_EXT, ORA_ENDPOINT_ENV_VAR_LOCAL,
};
use mk_oracle::config::authentication::{AuthType, Authentication, Role, SqlDbEndpoint};
use mk_oracle::config::defines::defaults::SECTION_SEPARATOR;
use mk_oracle::config::ora_sql::Config;
use mk_oracle::config::OracleConfig;
use mk_oracle::ora_sql::backend;
use mk_oracle::ora_sql::instance::generate_data;
use mk_oracle::ora_sql::section;
use mk_oracle::ora_sql::sqls;
use mk_oracle::ora_sql::system;
use mk_oracle::platform::registry::get_instances;
use mk_oracle::setup::{create_plugin, detect_host_runtime, detect_runtime, Env};
use mk_oracle::types::{EnvVarName, SqlQuery};

use mk_oracle::config::connection::setup_wallet_environment;
use mk_oracle::types::{
    ConnectionStringType, Credentials, InstanceName, InstanceNumVersion, InstanceVersion,
    ServiceName, Tenant, UseHostClient,
};
use regex::Regex;
use std::collections::HashSet;
use std::str::FromStr;
use std::sync::LazyLock;

pub static ORA_TEST_ENDPOINTS: &str = include_str!("files/endpoints.txt");

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

fn load_endpoints() -> Vec<SqlDbEndpoint> {
    let mut reference: Option<SqlDbEndpoint> = None;
    let content = ORA_TEST_ENDPOINTS.to_owned();
    let mut endpoints = content
        .split("\n")
        .filter_map(|s| {
            let cleaned = s.split('#').next().unwrap_or("").trim();
            if cleaned.is_empty() {
                None
            } else {
                Some(cleaned)
            }
        })
        .filter_map(|s| {
            if let Some(credentials_env_var) = s.strip_prefix("CREDENTIALS_ONLY:$") {
                reference = Some(SqlDbEndpoint::from_env(credentials_env_var).unwrap());
                return None;
            };

            let mut connection_string = if let Some(env_var) = s.strip_prefix("$") {
                std::env::var(env_var).unwrap()
            } else {
                s.to_string()
            };

            if connection_string.contains(":::") {
                let existing_reference = reference
                    .as_ref()
                    .expect("Specify at least one endpoint with credentials as reference");
                connection_string = connection_string.replacen(
                    ":::",
                    &format!(":{}:{}:", existing_reference.user, existing_reference.pwd,),
                    1,
                );
            }

            let new_connection = SqlDbEndpoint::from_str(&connection_string).unwrap();
            reference = Some(new_connection.clone());

            Some(new_connection)
        })
        .collect::<Vec<SqlDbEndpoint>>();

    if let Ok(local_endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL) {
        endpoints.push(local_endpoint);
    } else {
        eprintln!("No local endpoint found, skipping test_local_connection");
    };

    endpoints
}

fn remote_reference_endpoint() -> SqlDbEndpoint {
    SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).unwrap()
}

static WORKING_ENDPOINTS: LazyLock<Vec<SqlDbEndpoint>> = LazyLock::new(load_endpoints);
#[test]
fn test_endpoints_file() {
    let s = &WORKING_ENDPOINTS;
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).unwrap();
    let local = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).ok();
    assert!(!s.is_empty());
    assert_eq!(s[0], r);
    for e in &s[..] {
        if e.host == "localhost" || Some(e) == local.as_ref() {
            continue; // skip local endpoint, it may have strange credentials
        }
        assert_eq!(e.user, r.user);
        assert_eq!(e.pwd, r.pwd);
    }
}

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

#[cfg(windows)]
#[test]
fn test_environment() {
    // it seems we need this flag to properly link openssl on Windows
    let env_value = std::env::var("CFLAGS")
        .map_err(|e| anyhow::anyhow!("{e}"))
        .unwrap();
    assert_eq!(env_value, "-DNDEBUG");
}

#[allow(clippy::const_is_empty)]
#[test]
fn test_local_connection() {
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL);
    if r.is_err() {
        eprintln!("Skipping test_local_connection: {}", r.err().unwrap());
        return;
    }
    add_runtime_to_path();
    let endpoint = r.unwrap();
    let instance_name = get_sid(&endpoint);

    let config = make_base_config(
        &Credentials {
            user: endpoint.user,
            password: endpoint.pwd,
        },
        AuthType::Standard,
        Some(Role::SysDba),
        &endpoint.host,
        endpoint.port,
        None,
    );

    for i in [None, Some(&ServiceName::from(&endpoint.service_name))] {
        let spot = backend::make_spot(&config.endpoint()).unwrap();
        let conn = spot.connect(None).unwrap();
        let result = conn.query_table(&TEST_SQL_INSTANCE).format("");
        assert!(result.is_ok());
        let rows = result.unwrap();
        eprintln!(
            "Rows: {i:?} {:?} {:?}",
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
    let endpoint = remote_reference_endpoint();
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
    let endpoint = remote_reference_endpoint();
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
        role_spec(&endpoint.role, &endpoint.host),
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
    let runtime = section::Section::new(custom, 0);
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
    let endpoint = remote_reference_endpoint();
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
    let endpoint = remote_reference_endpoint();
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

    let endpoint = remote_reference_endpoint();
    let config = make_mini_config_custom_instance(&endpoint, "absent", None);
    let env = Env::default();
    let r = generate_data(&config, &env).await;

    assert!(r.is_ok());
    let table = r.unwrap();
    assert_eq!(table[0], "<<<oracle_instance>>>");
    assert_eq!(table[1], "<<<oracle_instance:sep(124)>>>");
    assert!(
        table[2].starts_with("REMOTE_INSTANCE_ABSENT|FAILURE|ERROR: ORA-"),
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
    let endpoint = remote_reference_endpoint();
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
        let instances_old = system::WorkInstances::new(&conn, Some(INSTANCE_INFO_SQL_TEXT_FAIL));
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
        assert!(String::from(version_ok).starts_with("2"));

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
fn test_rman() {
    add_runtime_to_path();
    for endpoint in WORKING_ENDPOINTS.iter() {
        println!("endpoint.host = {}", &endpoint.host);
        let rows = connect_and_query(endpoint, sqls::Id::Rman, None);
        assert!(rows.is_empty());
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
    let Some(ep) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).ok() else {
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
    let Some(endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).ok() else {
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
    let Some(endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).ok() else {
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
    let Some(endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).ok() else {
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
    let Some(ep) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).ok() else {
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

#[test]
fn test_detection_registry() {
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL);
    if r.is_err() {
        eprintln!("Skipping test_detection_registry: {}", r.err().unwrap());
        return;
    }
    let instances = get_instances(None).unwrap();
    eprintln!("Instances = {:?}", instances);
    assert!(!instances.is_empty());
    for i in instances {
        // Instance names are deployment-specific: XE / FREE on the reference
        // hosts, ORCL* on the ORACLE-WIN-CI VM (e.g. ORCL19 alongside 23ai Free).
        let name = i.name.to_string();
        assert!(
            i.name == InstanceName::from("XE")
                || i.name == InstanceName::from("FREE")
                || name.starts_with("ORCL"),
            "unexpected instance name: {name}"
        );
        assert!(std::path::PathBuf::from(&i.home).is_dir());
        assert!(std::path::PathBuf::from(&i.home).exists());
        let base = i.base.unwrap();
        assert!(std::path::PathBuf::from(&base).is_dir());
        assert!(std::path::PathBuf::from(&base).exists());
    }
}

#[test]
fn test_detect_host_runtime() {
    let local_exists = if std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok() {
        SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
    } else {
        std::env::var("ORACLE_HOME")
            .is_ok_and(|v| !v.is_empty() && std::path::Path::new(&v).join("lib").is_dir())
    };
    if local_exists {
        assert!(
            detect_host_runtime().is_some(),
            "{:?}",
            SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL)
        );
    } else {
        assert!(detect_host_runtime().is_none());
    }
}

fn base_dir() -> std::path::PathBuf {
    std::path::PathBuf::from(std::env::var("MK_CONFDIR").unwrap_or_else(|_| {
        std::env::current_dir()
            .unwrap()
            .into_os_string()
            .into_string()
            .unwrap()
    }))
}

#[test]
fn test_detect_runtime_with_runtime() {
    // MK_LIBDIR is set so that runtimes exist
    let good_path = base_dir().join("runtimes");
    const LIBDIR_VAR: &str = "MK_LIBDIR_TEST1";
    unsafe {
        std::env::set_var(LIBDIR_VAR, &good_path);
    }
    let lib_dir_var: Option<String> = Some(LIBDIR_VAR.to_string());
    let local_exists = if std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok() {
        SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
    } else {
        std::env::var("ORACLE_HOME")
            .is_ok_and(|v| !v.is_empty() && std::path::Path::new(&v).join("lib").is_dir())
    };

    // Never
    assert!(detect_runtime(&UseHostClient::Never, Some("Hurz".to_string())).is_none()); // env var does not exist
    eprintln!("good_path = {:?}", lib_dir_var.clone());
    assert!(detect_runtime(&UseHostClient::Never, lib_dir_var.clone()).is_some()); // detected

    // Always
    assert_eq!(
        detect_runtime(&UseHostClient::Always, lib_dir_var.clone()).is_some(),
        local_exists
    ); // detected only if local exists(skip factory)
    if local_exists {
        assert!(!detect_runtime(&UseHostClient::Always, lib_dir_var.clone())
            .unwrap()
            .into_os_string()
            .into_string()
            .unwrap()
            .contains("mk-oracle")); // path is to host
    }

    // Auto
    let path = detect_runtime(&UseHostClient::Auto, lib_dir_var.clone())
        .unwrap()
        .into_os_string()
        .into_string()
        .unwrap();
    assert!(path.contains("mk-oracle")); // detected factory

    // Path:
    // path is correct -> expected correct path
    let correct_path = base_dir()
        .join("runtimes")
        .into_os_string()
        .into_string()
        .unwrap();
    let path = to_string(detect_runtime(
        &UseHostClient::Path(correct_path.clone()),
        lib_dir_var.clone(),
    ))
    .unwrap();
    assert_eq!(path, correct_path);

    // path is wrong -> expected nothing
    let wrong_path = correct_path + "something-missing";
    let path = detect_runtime(&UseHostClient::Path(wrong_path), lib_dir_var.clone());
    assert!(path.is_none());
}

fn to_string(p: Option<std::path::PathBuf>) -> Option<String> {
    p.map(|pb| pb.into_os_string().into_string().unwrap())
}

#[test]
fn test_detect_runtime_without_runtime() {
    // MK_LIBDIR is set so that runtimes is missing
    let bad_path = base_dir().join("runtimes-wrong");
    const LIBDIR_VAR: &str = "MK_LIBDIR_TEST2";
    unsafe {
        std::env::set_var(LIBDIR_VAR, &bad_path);
    }
    let lib_dir_var: Option<String> = Some(LIBDIR_VAR.to_string());
    let local_installation = std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
        && SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok();
    let oracle_home_set = std::env::var("ORACLE_HOME")
        .is_ok_and(|v| !v.is_empty() && std::path::Path::new(&v).join("lib").is_dir());

    // Never
    assert!(detect_runtime(&UseHostClient::Never, lib_dir_var.clone()).is_none());

    // Auto and Always are the same if no runtimes
    // If local exists -> expected path to local client otherwise nothing
    for mode in [UseHostClient::Auto, UseHostClient::Always] {
        let path = to_string(detect_runtime(&mode, lib_dir_var.clone()));
        if local_installation || oracle_home_set {
            eprintln!(
                "Local installation path = {:?} {} {}",
                path, local_installation, oracle_home_set
            );
            #[cfg(unix)]
            assert!(path.clone().unwrap().ends_with("bin") || path.unwrap().ends_with("lib"));
            #[cfg(windows)]
            eprintln!("DISABLED! On Windows ");
        } else {
            assert!(path.is_none());
        }
    }

    // Path:
    // path is correct -> expected correct path
    let correct_path = base_dir()
        .join("runtimes")
        .into_os_string()
        .into_string()
        .unwrap();
    let path = to_string(detect_runtime(
        &UseHostClient::Path(correct_path.clone()),
        lib_dir_var.clone(),
    ))
    .unwrap();
    assert_eq!(path, correct_path);

    // path is wrong -> expected nothing
    let wrong_path = correct_path + "something-missing";
    let path = detect_runtime(&UseHostClient::Path(wrong_path), lib_dir_var.clone());
    assert!(path.is_none());
}

fn make_config_with_use_host(use_host: &str) -> String {
    format!(
        r#"
---
oracle:
  main: # mandatory, defines main SQL check to be executed
    options: # optional
      use_host_client: {} # optional, default: auto, values: auto, never, always, "path-to-oci-lib"
    authentication: # mandatory
      username: "foo" # mandatory if not using wallet, examples: "mydbuser", "c##multitenantuser"
      password: "bar" # optional
    discovery:
       detect: no
    connection: # optional
      service_name: "will not be used"
      hostname: "localhost" # optional, default: "localhost"    "#,
        use_host
    )
}

/// NOT ALL CONDITIONS TESTED
#[test]
fn test_add_runtime_to_path() {
    use mk_oracle::platform::get_local_instances;
    use mk_oracle::setup::add_runtime_path_to_env;

    fn exec_add_runtime_to_path(
        cfg: &OracleConfig,
        mk_lib: &str,
        mut_env_var: &EnvVarName,
    ) -> Option<std::path::PathBuf> {
        unsafe {
            std::env::set_var(mut_env_var.to_str(), "xxx");
        }
        add_runtime_path_to_env(
            cfg,
            Some(mk_lib.to_owned()),
            Some(mut_env_var.clone()),
            false,
        )
    }
    let mk_lib_dir_env_var = "MK_LIB_DIR_TEST_VAR_XXX".to_string();
    let mut_env_var = EnvVarName::from("SOME_PATH_TEST_VAR_XXX".to_string());
    let good_path = base_dir().join("runtimes");
    let local_db_exists = if std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
        && SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
    {
        println!("ORA_DB_ENDPOINT_LOCAL is set");
        true
    } else if std::env::var("ORACLE_HOME")
        .is_ok_and(|v| !v.is_empty() && std::path::Path::new(&v).join("lib").is_dir())
    {
        println!("ORACLE_HOME is set");
        true
    } else if !get_local_instances().unwrap_or_default().is_empty() {
        println!("Local instances detected");
        true
    } else {
        println!("No local Oracle client detected");
        false
    };
    let good_path_str = good_path.clone().into_os_string().into_string().unwrap();

    // *** AUTO ***
    let cfg = OracleConfig::load_str(&make_config_with_use_host("auto")).unwrap();
    // MK_LIBDIR ABSENT
    unsafe {
        std::env::remove_var(&mk_lib_dir_env_var);
    }
    // depends on local SQL endpoint, if exist -> found otherwise not
    let result = exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    assert_eq!(result.is_some(), local_db_exists);
    // MK_LIBDIR is good_path
    unsafe {
        std::env::set_var(&mk_lib_dir_env_var, good_path_str.as_str());
    }
    exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    let var_value = std::env::var(mut_env_var.to_str()).unwrap();
    assert!(var_value.starts_with(good_path_str.as_str()));

    // *** NEVER ***
    let cfg = OracleConfig::load_str(&make_config_with_use_host("never")).unwrap();
    // MK_LIBDIR ABSENT
    unsafe {
        std::env::remove_var(&mk_lib_dir_env_var);
    }
    assert!(exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var).is_none());
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with("xxx"));

    // MK_LIBDIR is good_path
    unsafe {
        std::env::set_var(&mk_lib_dir_env_var, good_path_str.as_str());
    }
    exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(good_path_str.as_str()));

    // *** ALWAYS ***
    let cfg = OracleConfig::load_str(&make_config_with_use_host("always")).unwrap();
    unsafe {
        std::env::remove_var(&mk_lib_dir_env_var);
    }

    // depends on local SQL endpoint, if exist -> found otherwise not
    let result = exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    assert_eq!(result.is_some(), local_db_exists);
    assert_eq!(
        std::env::var(mut_env_var.to_str())
            .unwrap()
            .starts_with("xxx"),
        !local_db_exists
    );
    unsafe {
        std::env::set_var(&mk_lib_dir_env_var, good_path_str.as_str());
    }
    exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    // depends on local SQL endpoint, if exist -> found otherwise not
    assert_eq!(
        exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var).is_some(),
        local_db_exists
    );

    // SOME PATH
    let some_path = base_dir().into_os_string().into_string().unwrap();
    let cfg = OracleConfig::load_str(&make_config_with_use_host(some_path.as_str())).unwrap();
    unsafe {
        std::env::remove_var(&mk_lib_dir_env_var);
    }
    // depends on local SQL endpoint, if exist -> found otherwise not
    exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(some_path.as_str()));
    unsafe {
        std::env::set_var(&mk_lib_dir_env_var, good_path_str.as_str());
    }
    exec_add_runtime_to_path(&cfg, &mk_lib_dir_env_var, &mut_env_var);
    // depends on local SQL endpoint, if exist -> found otherwise not
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(some_path.as_str()));
}

#[cfg(unix)]
fn validate_permissions(file: &std::path::Path, mode: u32) {
    use std::os::unix::fs::PermissionsExt;
    let permissions = std::fs::metadata(file).unwrap().permissions();
    assert_eq!(permissions.mode() & 0o777, mode); // is executable
}

#[cfg(windows)]
fn validate_permissions(_file: &std::path::Path, _mode: u32) {}

#[test]
fn test_create_plugin_sync() {
    let plugin = tempfile::tempdir().unwrap();
    let plugin_dir = plugin.path();
    let ret = create_plugin("a", plugin_dir, None, "--filter sync");
    assert!(plugin_dir.join("a").is_file());
    validate_permissions(&plugin_dir.join("a"), 0o755);
    let content = std::fs::read_to_string(plugin_dir.join("a")).unwrap();
    assert!(content.ends_with(" --filter sync\n"));
    assert!(ret);
}

#[cfg(unix)]
#[test]
fn test_create_plugin_async_custom_metrics() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(300), "--filter async-custom-metrics");
    assert!(ret);
    let content = std::fs::read_to_string(plugin_dir.join("300").join("a")).unwrap();
    assert!(content.ends_with(" --filter async-custom-metrics\n"));
}

#[cfg(unix)]
#[test]
fn test_create_plugin_async() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(!ret); // no plugins, no creation
    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(ret);

    let async_plugin_dir_100 = plugin_dir.join("100");
    let plugin_100_path = async_plugin_dir_100.join("a");
    assert!(plugin_100_path.is_file());
    let content = std::fs::read_to_string(async_plugin_dir_100.join("a")).unwrap();
    assert!(content.ends_with(" --filter async\n"));
    validate_permissions(&plugin_100_path, 0o755);

    let ret = create_plugin("a", &plugin_dir, Some(200), "--filter async");
    assert!(ret);

    let async_plugin_dir_200 = plugin_dir.join("200");
    assert!(async_plugin_dir_200.join("a").is_file());
    let content = std::fs::read_to_string(async_plugin_dir_200.join("a")).unwrap();
    assert!(content.ends_with(" --filter async\n"));
    assert!(!async_plugin_dir_100.join("a").exists()); // file must be deleted
}

#[cfg(windows)]
#[test]
fn test_create_plugin_async() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(!ret); // no plugins dir no success

    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(!ret); // no bakery dir no success

    let bakery_dir = lib_dir.path().join("bakery").to_owned();
    std::fs::create_dir_all(&bakery_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100), "--filter async");
    assert!(ret);

    assert!(plugin_dir.join("a").is_file());
    let plugin_content = std::fs::read_to_string(plugin_dir.join("a")).unwrap();
    assert!(plugin_content.ends_with(" --filter async\n"));

    let bakery_content = std::fs::read_to_string(bakery_dir.join("check_mk.bakery.yml")).unwrap();
    assert!(bakery_content.contains("    cache: 100"));
    assert!(bakery_content.contains("  - pattern: $CUSTOM_PLUGINS_PATH$\\a"));
}

#[test]
fn test_find_current_instance_runtime() {
    use mk_oracle::setup::find_env_var_lib_runtime;
    assert!(find_env_var_lib_runtime("HURZ-burz").is_none());
    assert!(find_env_var_lib_runtime("PATH").is_none());
    let db_location = tempfile::tempdir().unwrap();
    let temp_var = "ORACLE_HOME_TEST_VAR";
    unsafe {
        std::env::set_var(temp_var, db_location.path());
    }
    assert!(find_env_var_lib_runtime(temp_var).is_none());
    let lib_path = db_location.path().join("lib");
    std::fs::create_dir_all(&lib_path).unwrap();
    assert_eq!(
        find_env_var_lib_runtime(temp_var).unwrap(),
        db_location.path().join("lib")
    );
}

#[test]
fn test_sqlnet_ora_file_creation() {
    use std::env;
    use std::fs;

    let random_var = format!("MK_CONFDIR_TEST_{}", std::process::id());
    let tmp_dir = tempfile::tempdir().expect("create temp dir");
    let tmp_dir_path = tmp_dir.path().to_path_buf();

    unsafe {
        env::set_var(&random_var, &tmp_dir_path);
    }

    setup_wallet_environment(Some(random_var.clone())).unwrap();

    let sqlnet_path = tmp_dir_path.join("sqlnet.ora");
    let content = fs::read_to_string(&sqlnet_path).expect("read sqlnet.ora");

    let expected = format!(
        r#"# Auto-generated by mk-oracle for wallet authentication
NAMES.DIRECTORY_PATH = (TNSNAMES, EZCONNECT)
WALLET_LOCATION = (SOURCE = (METHOD = FILE) (METHOD_DATA = (DIRECTORY = {})))
SQLNET.WALLET_OVERRIDE = TRUE
"#,
        tmp_dir_path.join("oracle_wallet").display()
    );

    assert_eq!(content, expected);
}

mod find_sids {
    use mk_oracle::platform::registry::find_oratab_file;
    use std::io::Write;

    #[cfg(unix)]
    #[test]
    fn test_find_sids() {
        use mk_oracle::ora_sql::detect::find_sids_by_processes;

        if std::env::var("TEST_WORKSPACE").is_ok() {
            eprintln!("Skipping test_find_sids if TEST_WORKSPACE is set(Bazel sandboxing)");
            return;
        }
        const TEST_MASK: &str = r"^(/usr/lib/systemd/systemd)(.*)$";
        let sids = find_sids_by_processes(Some(TEST_MASK)).unwrap();
        assert!(sids.len() > 2);
        assert!(sids.contains("-logind"));
    }

    #[test]
    fn test_find_oratab_file_not_found() {
        let result = find_oratab_file(Some(&["/nonexistent/path/oratab"]));
        assert!(result.is_err());
        if cfg!(windows) {
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("oratab is not supported on Windows"));
        } else {
            assert!(result.unwrap_err().to_string().contains("oratab not found"));
        }
    }

    #[test]
    fn test_find_oratab_file_found() {
        let tmp_dir = tempfile::tempdir().expect("create temp dir");
        let oratab_path = tmp_dir.path().join("oratab");
        let mut file = std::fs::File::create(&oratab_path).expect("create oratab file");
        writeln!(file, "XE:/opt/oracle/product/21c/dbhomeXE:N # xxx").expect("write to oratab");

        let oratab_str = oratab_path.to_str().unwrap();
        let result = find_oratab_file(Some(&["/nonexistent/path/oratab", oratab_str]));
        if cfg!(windows) {
            assert!(result
                .unwrap_err()
                .to_string()
                .contains("oratab is not supported on Windows"));
        } else {
            assert!(result.is_ok());
            assert_eq!(result.unwrap(), oratab_path);
        }
    }

    #[cfg(unix)]
    #[test]
    fn test_find_oracle_home_from_oratab_sid_found() {
        use mk_oracle::ora_sql::detect::find_oracle_home;
        use mk_oracle::types::Sid;

        let tmp_dir = tempfile::tempdir().expect("create temp dir");
        let oratab_path = tmp_dir.path().join("oratab");
        let mut file = std::fs::File::create(&oratab_path).expect("create oratab file");
        writeln!(file, " # Comment line").expect("write comment");
        writeln!(file, "INVALID_LINE_NO_COLON").expect("write invalid line");
        writeln!(file, "XE:/opt/oracle/product/21c/dbhomeXE:N # some comment")
            .expect("write XE entry");
        writeln!(file, "ORCL:/opt/oracle/product/19c/dbhome1:Y # nothing")
            .expect("write ORCL entry");

        let oratab_str = oratab_path.to_str().unwrap().to_string();
        let sid = Sid::from("xE");
        let result = find_oracle_home(&sid, Some(oratab_str));
        assert!(result.is_ok());
        assert_eq!(
            result.unwrap(),
            Some(std::path::PathBuf::from("/opt/oracle/product/21c/dbhomeXE"))
        );

        let oratab_str = oratab_path.to_str().unwrap();
        let result = find_oracle_home(&Sid::from("NONEXISTENT"), Some(oratab_str.to_string()));
        assert!(result.unwrap().is_none());
    }
}

#[cfg(unix)]
#[test]
fn test_add_oracle_home_to_env() {
    use mk_oracle::setup::try_add_oracle_home_to_env;
    use mk_oracle::types::EnvVarName;

    let make_env_var = |name: &str| Some(EnvVarName::from(name.to_string()));

    // oratab with two instances: the home of the first doesn't exist,
    // the home of the second does and contains a lib dir
    let tmp_dir = tempfile::tempdir().expect("create temp dir");
    let home = tmp_dir.path().join("dbhome");
    std::fs::create_dir_all(home.join("lib")).expect("create home/lib");
    let oratab_path = tmp_dir.path().join("oratab");
    std::fs::write(
        &oratab_path,
        format!("BAD:/nonexistent/oracle/home:N\nXE:{}:Y\n", home.display()),
    )
    .expect("write oratab");
    let oratab = oratab_path.to_str().unwrap().to_string();

    let config_auto = OracleConfig::load_str(&make_config_with_use_host("auto")).unwrap();
    let config_never = OracleConfig::load_str(&make_config_with_use_host("never")).unwrap();

    // use_host_client "never" -> gated out, variable stays unset
    let env_var = "_MK_TEST_ORACLE_HOME_GATED";
    let result =
        try_add_oracle_home_to_env(&config_never, Some(oratab.clone()), make_env_var(env_var));
    assert!(result.is_none());
    assert!(std::env::var(env_var).is_err());

    // variable already set -> untouched, fall back to runtime detection
    let env_var = "_MK_TEST_ORACLE_HOME_PRESET";
    unsafe {
        std::env::set_var(env_var, "/already/set");
    }
    let result =
        try_add_oracle_home_to_env(&config_auto, Some(oratab.clone()), make_env_var(env_var));
    assert!(result.is_none());
    assert_eq!(std::env::var(env_var).unwrap(), "/already/set");

    // "auto" -> the first suitable home is set: BAD doesn't exist, XE wins
    let env_var = "_MK_TEST_ORACLE_HOME_SET";
    let result = try_add_oracle_home_to_env(&config_auto, Some(oratab), make_env_var(env_var));
    assert!(result.is_some());
    assert_eq!(std::env::var(env_var).unwrap(), home.to_str().unwrap());

    // no suitable home at all -> nothing set
    let bad_oratab_path = tmp_dir.path().join("oratab_bad");
    std::fs::write(&bad_oratab_path, "BAD:/nonexistent/oracle/home:N\n").expect("write oratab");
    let env_var = "_MK_TEST_ORACLE_HOME_NO_HOME";
    let result = try_add_oracle_home_to_env(
        &config_auto,
        Some(bad_oratab_path.to_str().unwrap().to_string()),
        make_env_var(env_var),
    );
    assert!(result.is_none());
    assert!(std::env::var(env_var).is_err());
}

// NOTE: Test mutates a process-wide environment variable. The unique prefix
// `_MK_TEST_OCI_DIR` is to minimise collision risk with other parallel tests.
#[test]
fn test_options_use_host_client_with_env_var() {
    #[cfg(not(windows))]
    let (env_val, sep) = ("/opt/oracle/product/19c", "/");
    #[cfg(windows)]
    let (env_val, sep) = (r"C:\oracle\product\19c", r"\");

    let env_var = "_MK_TEST_OCI_DIR";
    unsafe {
        std::env::set_var(env_var, env_val);
    }

    // $VAR/lib — starts with '$' so guard passes; expands to an absolute path
    let cfg =
        OracleConfig::load_str(&make_config_with_use_host(&format!("${env_var}{sep}lib"))).unwrap();
    let options = cfg.ora_sql().unwrap().options();
    assert_eq!(
        options.use_host_client(),
        &UseHostClient::Path(format!("{env_val}{sep}lib"))
    );

    // ${VAR}/lib — brace form, also starts with '$'
    let cfg = OracleConfig::load_str(&make_config_with_use_host(&format!(
        "${{{env_var}}}{sep}lib"
    )))
    .unwrap();
    let options = cfg.ora_sql().unwrap().options();
    assert_eq!(
        options.use_host_client(),
        &UseHostClient::Path(format!("{env_val}{sep}lib"))
    );

    unsafe {
        std::env::remove_var(env_var);
    }
}

#[cfg(unix)]
mod permissions {
    use mk_oracle::permissions_linux::{is_tree_only_root_modifiable, only_root_can_modify};
    use std::fs;
    use std::os::unix::fs::PermissionsExt;
    use std::path::Path;

    fn set_mode(path: &Path, mode: u32) {
        fs::set_permissions(path, fs::Permissions::from_mode(mode)).unwrap();
    }

    #[test]
    fn test_only_root_can_modify_rejects_world_writable_file() {
        let tmp = tempfile::tempdir().expect("create temp dir");
        let p = tmp.path().join("f");
        fs::write(&p, b"").unwrap();
        set_mode(&p, 0o666);
        assert!(!only_root_can_modify(&p));
    }

    #[test]
    fn test_is_tree_only_root_modifiable_rejects_world_writable_entry() {
        let tmp = tempfile::tempdir().expect("create temp dir");
        let sub = tmp.path().join("child");
        fs::create_dir(&sub).unwrap();
        let file = sub.join("lib.so");
        fs::write(&file, b"").unwrap();
        set_mode(tmp.path(), 0o755);
        set_mode(&sub, 0o755);
        set_mode(&file, 0o666);
        assert!(!is_tree_only_root_modifiable(tmp.path()));
    }
}

/// Component tests for the `path:` key of section / custom-metric YAML config.
/// Tests for resolving a custom-metric's SQL from the YAML `path:` key.
///
/// `path:` can point at an absolute file, an absolute directory, or a path
/// relative to a set of search roots. These tests pin down exactly which file
/// gets read in each case, including version-variant selection and the
/// precedence between `path:` and an inline `sql:`.
///
/// # Fixture files (tests/files/, embedded via `include_str!`)
///
/// Each `.sql` file contains a single trivial query whose payload encodes its
/// own origin, e.g. `select 'details:abs' from dual`, so a test can assert
/// which file was resolved purely from the returned query text.
mod custom_path_tests {
    use mk_oracle::config::ora_sql::Config;
    use mk_oracle::ora_sql::section::Section;
    use mk_oracle::types::{InstanceNumVersion, Tenant};
    use std::path::{Path, PathBuf};
    use tempfile::TempDir;

    // SQL fixture bodies committed under tests/files/, embedded at compile time,
    // the `'details:...'` payload identifies which file was resolved.
    const ABS_SQL: &str = include_str!("files/orasql_abs/abs.sql");
    const DIR_METRIC_SQL: &str = include_str!("files/orasql_abs/dir_metric.sql");
    const WINNER_SQL: &str = include_str!("files/orasql_abs/winner.sql");
    const VER_V0_SQL: &str = include_str!("files/orasql_abs/ver_metric.sql");
    const VER_V12_SQL: &str = include_str!("files/orasql_abs/ver_metric@12010000.sql");
    const VER_V19_SQL: &str = include_str!("files/orasql_abs/ver_metric@19000000.sql");
    const RUNTIME_BOTH_SQL: &str = include_str!("files/orasql_runtime/both.sql");
    const RUNTIME_JOBS_SQL: &str = include_str!("files/orasql_runtime/jobs.sql");
    const CONFIG_BOTH_SQL: &str = include_str!("files/orasql_config/both.sql");
    const CONFIG_MAIN_ONLY_SQL: &str = include_str!("files/orasql_config/main_only.sql");

    struct Fixtures {
        _root: TempDir,
        abs_dir: PathBuf,
        /// Injected relative-`path:` search roots: runtime first (so it wins on
        /// collisions), config second — mirroring production order.
        search_dirs: Vec<PathBuf>,
    }

    fn write(dir: &Path, name: &str, body: &str) {
        std::fs::write(dir.join(name), body).expect("write fixture");
    }

    /// Materialise the embedded fixtures into a temp dir:
    /// `orasql_abs/` for absolute-path tests, plus
    /// `orasql_runtime/` and `orasql_config/` as the two relative search roots
    /// (note `both.sql` lives in both, to exercise collision precedence).
    fn fixtures() -> Fixtures {
        let root = tempfile::tempdir().expect("tempdir");
        let abs_dir = root.path().join("orasql_abs");
        let runtime_dir = root.path().join("orasql_runtime");
        let config_dir = root.path().join("orasql_config");
        for d in [&abs_dir, &runtime_dir, &config_dir] {
            std::fs::create_dir_all(d).expect("create fixture dir");
        }

        // Absolute-path test files.
        write(&abs_dir, "abs.sql", ABS_SQL);
        write(&abs_dir, "dir_metric.sql", DIR_METRIC_SQL);
        write(&abs_dir, "winner.sql", WINNER_SQL);
        // Version-variant set: bare stem + two @<version> variants.
        write(&abs_dir, "ver_metric.sql", VER_V0_SQL);
        write(&abs_dir, "ver_metric@12010000.sql", VER_V12_SQL);
        write(&abs_dir, "ver_metric@19000000.sql", VER_V19_SQL);

        // Relative-path search roots. `both.sql` is intentionally present in
        // both roots so a test can prove the runtime root shadows the config one.
        write(&runtime_dir, "both.sql", RUNTIME_BOTH_SQL);
        // Named after the builtin `jobs` section: overrides its factory query.
        write(&runtime_dir, "jobs.sql", RUNTIME_JOBS_SQL);
        write(&config_dir, "both.sql", CONFIG_BOTH_SQL);
        write(&config_dir, "main_only.sql", CONFIG_MAIN_ONLY_SQL);

        Fixtures {
            _root: root,
            abs_dir,
            search_dirs: vec![runtime_dir, config_dir],
        }
    }

    fn section_from_yaml(yaml: &str, item_or_name: &str) -> Section {
        let config = Config::from_string(yaml)
            .expect("config parses")
            .expect("config present");
        let cfg = config
            .all_sections()
            .iter()
            .find(|s| {
                s.item_value()
                    .map(|iv| iv.as_str() == item_or_name)
                    .unwrap_or(false)
                    || s.name().as_str() == item_or_name
            })
            .expect("section not found in config");
        Section::new(cfg, 0)
    }

    /// First resolved query body for `section` at `version`, using `search_dirs`
    /// as the relative-`path:` search roots (irrelevant for absolute paths).
    fn first_query(section: &Section, version: u32, search_dirs: &[PathBuf]) -> Option<String> {
        section
            .find_queries_with_search_dirs(
                InstanceNumVersion::from(version),
                Tenant::All,
                &[],
                search_dirs,
            )
            .map(|queries| queries[0].as_str().to_owned())
    }

    #[test]
    fn test_path_absolute_file_reads_file_contents() {
        // `path:` points straight at orasql_abs/abs.sql. An absolute *file* path
        // is read; the item name ("whatever_name") is ignored. Expect
        // the body of abs.sql -> 'details:abs'.
        let fx = fixtures();
        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - whatever_name:
          path: '{}'
"#,
            fx.abs_dir.join("abs.sql").display()
        );
        let section = section_from_yaml(&yaml, "whatever_name");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:abs' from dual")
        );
    }

    #[test]
    fn test_path_absolute_directory_uses_item_name_as_stem() {
        // `path:` points at the orasql_abs/ *directory*, not a file. The file
        // stem is then derived from the custom-metric item name, so item
        // "dir_metric" resolves to orasql_abs/dir_metric.sql -> 'details:dir'.
        let fx = fixtures();
        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - dir_metric:
          path: '{}'
"#,
            fx.abs_dir.display()
        );
        let section = section_from_yaml(&yaml, "dir_metric");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:dir' from dual")
        );
    }

    #[test]
    fn test_path_version_variant_selected_by_instance_version() {
        // Item "ver_metric" against the orasql_abs/ directory, which holds three
        // variants for the same stem:
        //   ver_metric.sql           -> 'details:v0'  (bare, no version floor)
        //   ver_metric@12010000.sql  -> 'details:v12' (applies for version >= 12.1)
        //   ver_metric@19000000.sql  -> 'details:v19' (applies for version >= 19)
        // The highest @<version> floor that the instance version satisfies wins,
        // falling back to the bare stem below the lowest floor. Asserted below
        // for instance versions 10.0, 14.0 and 23.0.
        let fx = fixtures();
        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - ver_metric:
          path: '{}'
"#,
            fx.abs_dir.display()
        );
        let section = section_from_yaml(&yaml, "ver_metric");
        assert_eq!(
            first_query(&section, 10_00_00_00, &[]).as_deref(),
            Some("select 'details:v0' from dual"),
            "below the lowest @-variant falls back to the bare stem"
        );
        assert_eq!(
            first_query(&section, 14_00_00_00, &[]).as_deref(),
            Some("select 'details:v12' from dual"),
            "between the 12.1 and 19 variants selects the 12.1 one"
        );
        assert_eq!(
            first_query(&section, 23_00_00_00, &[]).as_deref(),
            Some("select 'details:v19' from dual"),
            "at/above the 19 variant selects it"
        );
    }

    #[test]
    fn test_path_relative_resolved_via_injected_search_dirs() {
        // A *relative* `path:` is looked up against the injected search roots, in
        // order: orasql_runtime/ first, then orasql_config/. Covers two cases:
        // a collision (file in both roots) and a file present only in the second.
        let fx = fixtures();
        let dirs = &fx.search_dirs;

        // `both.sql` exists in *both* roots (runtime -> 'details:runtime',
        // config -> 'details:config'); the first (runtime) root must win.
        let collision_yaml = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - both_metric:
          path: "both.sql"
"#;
        let section = section_from_yaml(collision_yaml, "both_metric");
        assert_eq!(
            first_query(&section, 0, dirs).as_deref(),
            Some("select 'details:runtime' from dual"),
            "runtime search dir must win over config on collision"
        );

        // `main_only.sql` exists only in the second (config) root, so lookup must
        // fall through past orasql_runtime/ to orasql_config/ -> 'details:config-only'.
        let config_only_yaml = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - config_metric:
          path: "main_only.sql"
"#;
        let section = section_from_yaml(config_only_yaml, "config_metric");
        assert_eq!(
            first_query(&section, 0, dirs).as_deref(),
            Some("select 'details:config-only' from dual"),
            "must fall through to the config search dir"
        );
    }

    #[test]
    fn test_builtin_section_overridden_by_search_dir_file_without_path() {
        // A builtin section with *no* `path:` key still using the search
        // roots: the unset path defaults to "" (a relative path), so each root
        // itself becomes a candidate directory and the lookup stem is the
        // section name. A `jobs.sql` in the runtime root must therefore
        // override the factory query of the builtin `jobs` section.
        let fx = fixtures();
        let yaml = r#"
oracle:
  main:
    authentication:
      username: u
      password: p
"#;
        let section = section_from_yaml(yaml, "jobs");
        assert!(section.path().is_none(), "no path: configured for jobs");

        assert_eq!(
            first_query(&section, 19_00_00_00, &fx.search_dirs).as_deref(),
            Some("select 'details:builtin-override' from dual"),
            "jobs.sql in a search dir must override the builtin query"
        );
        // Sanity check: without the search dirs the factory query is used.
        let factory = first_query(&section, 19_00_00_00, &[]);
        assert!(factory.is_some(), "builtin jobs query must resolve");
        assert_ne!(
            factory.as_deref(),
            Some("select 'details:builtin-override' from dual"),
            "without search dirs the factory query must be returned"
        );
    }

    #[test]
    fn test_path_wins_over_inline_sql_but_falls_back_when_missing() {
        // A custom metric may carry both `path:` and an inline `sql:`. This test
        // pins the precedence: a resolvable `path:` wins, a missing one falls
        // back to the inline `sql:`.
        let fx = fixtures();
        // File resolves (orasql_abs/winner.sql -> 'details:file'), so `path:`
        // takes precedence over the inline `sql:` ('details:inline').
        let present_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - winner:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("winner.sql").display()
        );
        let section = section_from_yaml(&present_yaml, "winner");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:file' from dual"),
            "resolved path: must win over inline sql:"
        );

        // File is missing (does_not_exist.sql), so resolution falls back to the
        // inline `sql:` -> 'details:inline'.
        let missing_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    custom_metrics:
      - fallback:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("does_not_exist.sql").display()
        );
        let section = section_from_yaml(&missing_yaml, "fallback");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:inline' from dual"),
            "missing path: must fall back to inline sql:"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_path_override() {
        let fx = fixtures();

        // External `path:` file replaces the built-in instance query.
        let path_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
"#,
            fx.abs_dir.join("abs.sql").display()
        );
        let section = section_from_yaml(&path_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:abs' from dual"),
            "path: file must replace the built-in instance query"
        );
        assert_eq!(section.to_work_header(), "<<<oracle_instance:sep(124)>>>");
        assert!(
            section.pdb_patterns().is_empty(),
            "override runs against CDB only (no PDB targeting)"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_missing_path_falls_back_to_builtin_query() {
        let fx = fixtures();

        // Baseline: the shipped built-in `instance` query.
        let builtin_sql = first_query(
            &section_from_yaml(
                r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
"#,
                "instance",
            ),
            0,
            &[],
        );
        assert!(
            builtin_sql.is_some(),
            "sanity: the built-in instance section ships a query"
        );

        // `path:` points to a nonexistent file and there is no inline `sql:`
        // either, so the section must keep running the built-in query.
        let missing_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
"#,
            fx.abs_dir.join("does_not_exist.sql").display()
        );
        let section = section_from_yaml(&missing_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]),
            builtin_sql,
            "a missing path: file must fall back to the built-in query"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_path_override_does_not_validate_sql() {
        // The plugin must not alter or judge user-provided SQL: the file body
        // is only split on `;` and handed to the server verbatim. Whether the
        // SQL is valid is the DB's call. Its complaint is dealt with on the
        // in the Check plugins, not on Agent side.
        let fx = fixtures();
        write(&fx.abs_dir, "not_sql.sql", "this is not valid sql");

        let yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
"#,
            fx.abs_dir.join("not_sql.sql").display()
        );
        let section = section_from_yaml(&yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("this is not valid sql"),
            "the file body must be passed through unvalidated"
        );
    }

    // TC-ORA-150
    #[test]
    fn test_builtin_section_path_wins_over_inline_sql() {
        // A built-in section override may carry both `path:` and an inline
        // `sql:`. Precedence is the same as for custom metrics: a resolvable
        // `path:` wins, a missing one falls back to the inline `sql:` (and
        // only without either does the built-in query run).
        let fx = fixtures();
        // File resolves (orasql_abs/winner.sql -> 'details:file'), so `path:`
        // takes precedence over the inline `sql:` ('details:inline').
        let present_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("winner.sql").display()
        );
        let section = section_from_yaml(&present_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:file' from dual"),
            "resolved path: must win over inline sql:"
        );

        // File is missing (does_not_exist.sql), so resolution falls back to
        // the inline `sql:` -> 'details:inline', not to the built-in query.
        let missing_yaml = format!(
            r#"
oracle:
  main:
    authentication:
      username: u
      password: p
    sections:
      - instance:
          path: '{}'
          sql: "select 'details:inline' from dual"
"#,
            fx.abs_dir.join("does_not_exist.sql").display()
        );
        let section = section_from_yaml(&missing_yaml, "instance");
        assert_eq!(
            first_query(&section, 0, &[]).as_deref(),
            Some("select 'details:inline' from dual"),
            "missing path: must fall back to inline sql:, not the built-in query"
        );
    }
}
