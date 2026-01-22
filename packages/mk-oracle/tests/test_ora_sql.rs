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
    make_mini_config, make_mini_config_custom_instance, make_wallet_config,
    platform::add_runtime_to_path, ORA_ENDPOINT_ENV_VAR_EXT, ORA_ENDPOINT_ENV_VAR_LOCAL,
};
use mk_oracle::config::authentication::{AuthType, Authentication, Role, SqlDbEndpoint};
use mk_oracle::config::defines::defaults::SECTION_SEPARATOR;
use mk_oracle::config::ora_sql::Config;
use mk_oracle::config::OracleConfig;
use mk_oracle::ora_sql::backend;
use mk_oracle::ora_sql::instance::generate_data;
use mk_oracle::ora_sql::sqls;
use mk_oracle::ora_sql::system;
use mk_oracle::platform::registry::get_instances;
use mk_oracle::setup::{create_plugin, detect_host_runtime, detect_runtime, Env};
use mk_oracle::types::{EnvVarName, SqlQuery};

use mk_oracle::config::connection::setup_wallet_environment;
#[cfg(windows)]
use mk_oracle::types::InstanceAlias;
use mk_oracle::types::{
    Credentials, InstanceName, InstanceNumVersion, InstanceVersion, ServiceName, Tenant,
    UseHostClient,
};
use std::collections::HashSet;
use std::path::PathBuf;
use std::str::FromStr;
use std::sync::LazyLock;

pub static ORA_TEST_ENDPOINTS: &str = include_str!("files/endpoints.txt");

pub fn get_instance(endpoint: &SqlDbEndpoint) -> String {
    endpoint.instance_name.clone().unwrap()
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
    instance_name: Option<InstanceName>,
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
       service_name: {}
       timeout: 10
"#,
        credentials.user,
        credentials.password,
        auth_type,
        role_string,
        address,
        port,
        instance_name.unwrap_or_default()
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
    assert!(!s.is_empty());
    assert_eq!(s[0], r);
    for e in &s[..] {
        if e.host == "localhost" {
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
    let instance_name = get_instance(&endpoint);

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
            conn.target().make_connection_string(None)
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
    let instance_name = &endpoint.instance_name.clone().unwrap();
    assert!(rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &instance_name)));
    assert!(rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &instance_name)));
    assert_eq!(rows.len(), 2);
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
        assert!(r.starts_with(endpoint.instance_name.as_ref().unwrap()));
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
    assert_eq!(r.unwrap()[0], "<<<oracle_instance>>>");
}

// TODO: Remove this test when TNS_ADMIN is properly supported on non-Windows platforms
#[cfg(windows)]
#[tokio::test(flavor = "multi_thread")]
async fn test_remote_tns_custom_instance_connection() {
    let logger = flexi_logger::Logger::try_with_str("info").unwrap();
    logger.log_to_stderr().start().unwrap();
    add_runtime_to_path();
    log::warn!(
        "TNS_ADMIN='{}'",
        std::env::var("TNS_ADMIN").unwrap_or_default()
    );
    let endpoint = remote_reference_endpoint();
    let config = make_mini_config_custom_instance(
        &endpoint,
        "FREE",
        Some(InstanceAlias::from("ora_remote".to_string())),
    );
    let env = Env::default();
    let r = generate_data(&config, &env).await;

    assert!(r.is_ok());
    let table = r.unwrap();
    assert_eq!(table.len(), 2);
    assert_eq!(table[0], "<<<oracle_instance>>>");
    let rows: Vec<&str> = table[1].split("\n").collect();
    assert_eq!(rows[0], "<<<oracle_instance:sep(124)>>>");
    for r in rows[1..].iter() {
        assert!(r.starts_with("FREE"));
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
        let r_new = instances_new.get_full_version(&InstanceName::from(get_instance(endpoint)));
        let r_old = instances_old.get_full_version(&InstanceName::from(get_instance(endpoint)));
        let version_ok = r_new.unwrap();
        let version_old = r_old.unwrap();
        //check that both methods return the same values
        assert_eq!(version_ok, version_old);
        assert!(String::from(version_ok).starts_with("2"));
        assert!(instances_new
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
        let name_dot = format!("{}.", &endpoint.instance_name.clone().unwrap());
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
                "Row does not start with instance name: {}",
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

    let spot = backend::make_spot(&config.endpoint()).unwrap();
    let conn = spot.connect(None).unwrap();
    let queries = sqls::get_factory_query(id, version, Tenant::All, None)
        .unwrap()
        .split(';')
        .filter_map(|q| {
            let trimmed = q.trim();
            if !trimmed.is_empty() {
                Some(SqlQuery::new(trimmed, config.params()))
            } else {
                None
            }
        })
        .collect::<Vec<_>>();

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
        let expected = format!("{}||||", get_instance(endpoint));
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
            assert_eq!(line[0], get_instance(endpoint).as_str());
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
            assert_eq!(line[0], get_instance(endpoint).as_str());
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
            format!(
                "{}|||||||||",
                endpoint.instance_name.clone().unwrap().as_str()
            )
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
            assert_eq!(line[0], get_instance(endpoint));
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
        // ???CDB/PDB???|206|37328|klapp-0336|pa@klapp-0336 (TNS V1-V3)|12|sergeykipnis|SYSTEM|0|VALID|1|179|64573|klapp-0336|pa@klapp-0336 (TNS V1-V3)|12|sergeykipnis|SYSTEM
        // or
        // FREE|||||||||||||||||
        // Let's QA team checks correctness
        assert!(rows[0].starts_with(format!("{}.CDB$ROOT|", get_instance(endpoint)).as_str()));
        assert!(rows[1].starts_with(format!("{0}.{0}PDB1|", get_instance(endpoint)).as_str()));
        assert!(rows[2].starts_with(format!("{}|", get_instance(endpoint)).as_str()));
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
        assert!(rows[0].starts_with(format!("{}|", get_instance(endpoint)).as_str()));
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
        assert!(rows[0].starts_with(format!("{}|", get_instance(endpoint)).as_str()));
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
        assert_eq!(
            rows[0],
            format!("{}.CDB$ROOT||||||||", get_instance(endpoint))
        );
        assert_eq!(
            rows[1],
            format!("{0}.{0}PDB1||||||||", get_instance(endpoint))
        );
        assert_eq!(rows[2], format!("{}||||||||", get_instance(endpoint)));
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
        assert_eq!(rows[0], format!("{}||||||||", get_instance(endpoint)));
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
        assert_eq!(array[0], get_instance(endpoint).as_str());
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
            assert!(array[0].starts_with(get_instance(endpoint).as_str()));
            assert_eq!(array[1], get_instance(endpoint).as_str());
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
            assert_eq!(array[0], get_instance(endpoint).as_str());
            assert_eq!(array[1], get_instance(endpoint).as_str());
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
        let start = get_instance(endpoint) + ".";
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
            assert_eq!(line[0], get_instance(endpoint).as_str());
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
            assert_eq!(line[0], get_instance(endpoint).as_str());
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
            assert_eq!(line[0], get_instance(endpoint).as_str());
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
            assert_eq!(line[0], get_instance(endpoint).as_str());
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
        assert_eq!(line[0], get_instance(endpoint).as_str());
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
        assert_eq!(line[0], get_instance(endpoint).as_str());
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
            assert!(line[0].starts_with(format!("{}.", get_instance(endpoint).as_str()).as_str()));
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
            assert!(line[0].starts_with(get_instance(endpoint).as_str()));
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
            assert!(line[0].starts_with(get_instance(endpoint).as_str()));
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
        assert!(i.name == InstanceName::from("XE") || i.name == InstanceName::from("FREE"));
        assert!(std::path::PathBuf::from(&i.home).is_dir());
        assert!(std::path::PathBuf::from(&i.home).exists());
        assert!(std::path::PathBuf::from(&i.base).is_dir());
        assert!(std::path::PathBuf::from(&i.base).exists());
    }
}

#[test]
fn test_detect_host_runtime() {
    let local_exists = if std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok() {
        SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
    } else {
        std::env::var("ORACLE_HOME").is_ok_and(|v| !v.is_empty())
    };
    if local_exists {
        assert!(detect_host_runtime().is_some());
    } else {
        assert!(detect_host_runtime().is_none());
    }
}

fn base_dir() -> std::path::PathBuf {
    std::path::PathBuf::from(std::env::var("MK_CONFDIR").unwrap_or_else(|_| {
        let this_file: PathBuf = PathBuf::from(file!());
        this_file
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .to_owned()
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
        std::env::var("ORACLE_HOME").is_ok_and(|v| !v.is_empty())
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
    let local_exists = if std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok() {
        SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
    } else {
        std::env::var("ORACLE_HOME").is_ok_and(|v| !v.is_empty())
    };

    // Never
    assert!(detect_runtime(&UseHostClient::Never, lib_dir_var.clone()).is_none());

    // Auto and Always are the same if no runtimes
    // If local exists -> expected path to local client otherwise nothing
    for mode in [UseHostClient::Auto, UseHostClient::Always] {
        let path = to_string(detect_runtime(&mode, lib_dir_var.clone()));
        if local_exists {
            assert!(path.clone().unwrap().ends_with("bin") || path.unwrap().ends_with("lib"));
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
    connection: # optional
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
        add_runtime_path_to_env(cfg, Some(mk_lib.to_owned()), Some(mut_env_var.clone()))
    }
    let mk_lib_dir_env_var = "MK_LIB_DIR_TEST_VAR_XXX".to_string();
    let mut_env_var = EnvVarName::from("SOME_PATH_TEST_VAR_XXX".to_string());
    let good_path = base_dir().join("runtimes");
    let local_db_exists = if std::env::var(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
        && SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL).is_ok()
    {
        println!("ORA_DB_ENDPOINT_LOCAL is set");
        true
    } else if std::env::var("ORACLE_HOME").is_ok_and(|v| !v.is_empty()) {
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
    assert!(std::env::var(mut_env_var.to_str())
        .unwrap()
        .starts_with(good_path_str.as_str()));

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
    let ret = create_plugin("a", plugin_dir, None);
    assert!(plugin_dir.join("a").is_file());
    validate_permissions(&plugin_dir.join("a"), 0o755);
    let content = std::fs::read_to_string(plugin_dir.join("a")).unwrap();
    assert!(content.ends_with(" --filter sync\n"));
    assert!(ret);
}

#[cfg(unix)]
#[test]
fn test_create_plugin_async() {
    let lib_dir = tempfile::tempdir().unwrap();
    let plugin_dir = lib_dir.path().join("plugins").to_owned();
    let ret = create_plugin("a", &plugin_dir, Some(100));
    assert!(!ret); // no plugins, no creation
    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100));
    assert!(ret);

    let async_plugin_dir_100 = plugin_dir.join("100");
    let plugin_100_path = async_plugin_dir_100.join("a");
    assert!(plugin_100_path.is_file());
    let content = std::fs::read_to_string(async_plugin_dir_100.join("a")).unwrap();
    assert!(content.ends_with(" --filter async\n"));
    validate_permissions(&plugin_100_path, 0o755);

    let ret = create_plugin("a", &plugin_dir, Some(200));
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
    let ret = create_plugin("a", &plugin_dir, Some(100));
    assert!(!ret); // no plugins dir no success

    std::fs::create_dir_all(&plugin_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100));
    assert!(!ret); // no bakery dir no success

    let bakery_dir = lib_dir.path().join("bakery").to_owned();
    std::fs::create_dir_all(&bakery_dir).unwrap();
    let ret = create_plugin("a", &plugin_dir, Some(100));
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
    use mk_oracle::setup::find_default_instance_runtime;
    assert!(find_default_instance_runtime("HURZ-burz").is_none());
    assert!(find_default_instance_runtime("PATH").is_none());
    let db_location = tempfile::tempdir().unwrap();
    let temp_var = "ORACLE_HOME_TEST_VAR";
    unsafe {
        std::env::set_var(temp_var, db_location.path());
    }
    assert!(find_default_instance_runtime(temp_var).is_none());
    let lib_path = db_location.path().join("lib");
    std::fs::create_dir_all(&lib_path).unwrap();
    assert_eq!(
        find_default_instance_runtime(temp_var).unwrap(),
        db_location.path().join("lib")
    );
}

#[ignore = "requires Oracle Wallet files"]
#[tokio::test(flavor = "multi_thread")]
async fn test_wallet_authentication_connection() {
    // This test requires:
    // MK_CONFDIR env var pointing to a directory with oracle_wallet containing valid wallet files
    // OR a pre-configured sqlnet.ora with wallet location

    let base_dir = base_dir();

    // Set MK_CONFDIR based on where oracle_wallet exists
    let mk_confdir = if base_dir.join("oracle_wallet").exists() {
        base_dir.clone()
    } else {
        base_dir.join("tests").join("files")
    };

    unsafe {
        std::env::set_var("MK_CONFDIR", &mk_confdir);
    }
    eprintln!("MK_CONFDIR set to: {:?}", mk_confdir);

    add_runtime_to_path();
    let endpoint = remote_reference_endpoint();
    let config = make_wallet_config(&endpoint);
    let env = Env::default();
    let r = generate_data(&config, &env).await;

    assert!(r.is_ok(), "Wallet authentication failed: {:?}", r.err());
    let table = r.unwrap();
    eprintln!("Wallet auth result: {:?}", table);
    assert_eq!(table.len(), 2);
    assert_eq!(table[0], "<<<oracle_instance>>>");
    let rows: Vec<&str> = table[1].split("\n").collect();
    assert_eq!(rows[0], "<<<oracle_instance:sep(124)>>>");
    for row in rows[1..].iter() {
        if !row.is_empty() {
            assert!(
                row.starts_with(endpoint.instance_name.as_ref().unwrap()),
                "Row should start with instance name '{}': {}",
                endpoint.instance_name.as_ref().unwrap(),
                row
            );
        }
    }
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
