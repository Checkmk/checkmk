// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(feature = "build_system_bazel")]
extern crate common;
#[cfg(not(feature = "build_system_bazel"))]
mod common;

use crate::common::tools::{
    platform::add_runtime_to_path, ORA_ENDPOINT_ENV_VAR_EXT, ORA_ENDPOINT_ENV_VAR_LOCAL,
};
use mk_oracle::config::authentication::{AuthType, Authentication, Role, SqlDbEndpoint};
use mk_oracle::config::ora_sql::Config;
use mk_oracle::ora_sql::backend;
use mk_oracle::ora_sql::sqls;
use mk_oracle::ora_sql::system;
use mk_oracle::types::{Credentials, InstanceName, InstanceNumVersion, InstanceVersion, Tenant};
use mk_oracle::types::{Separator, SqlQuery};
use std::collections::HashSet;
use std::str::FromStr;
use std::sync::LazyLock;

pub static ORA_TEST_ENDPOINTS: &str = include_str!("files/endpoints.txt");

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
       instance: {}
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

fn _make_mini_config(credentials: &Credentials, auth_type: AuthType, address: &str) -> Config {
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
       timeout: 10
"#,
        credentials.user,
        credentials.password,
        auth_type,
        if address == "localhost" { "sysdba" } else { "" },
        address,
    );
    Config::from_string(config_str).unwrap().unwrap()
}

fn make_mini_config(endpoint: &SqlDbEndpoint) -> Config {
    _make_mini_config(
        &Credentials {
            user: endpoint.user.clone(),
            password: endpoint.pwd.clone(),
        },
        AuthType::Standard,
        &endpoint.host,
    )
}

fn load_endpoints() -> Vec<SqlDbEndpoint> {
    let mut r = reference_endpoint();
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
            if let Some(env_var) = s.strip_prefix("$") {
                r = SqlDbEndpoint::from_env(env_var).unwrap();
                None
            } else {
                Some(s.replacen(":::", &format!(":{}:{}:", r.user, r.pwd), 1))
            }
        })
        .map(|s| SqlDbEndpoint::from_str(s.as_str()).unwrap())
        .collect::<Vec<SqlDbEndpoint>>();
    if let Ok(local_endpoint) = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_LOCAL) {
        endpoints.push(local_endpoint);
    } else {
        eprintln!("No local endpoint found, skipping test_local_connection");
    };
    endpoints
}

fn reference_endpoint() -> SqlDbEndpoint {
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
        Separator::No,
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

    for i in [None, Some(&InstanceName::from(&endpoint.instance))] {
        let spot = backend::make_spot(&config.endpoint()).unwrap();
        let conn = spot.connect(i).unwrap();
        let result = conn.query(&TEST_SQL_INSTANCE, "");
        assert!(result.is_ok());
        let rows = result.unwrap();
        eprintln!(
            "Rows: {i:?} {:?} {:?}",
            rows,
            conn.target().make_connection_string(i)
        );
        assert!(!rows.is_empty());
        assert!(rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &endpoint.instance)));
        assert!(rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &endpoint.instance)));
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
    let result = conn.query(&TEST_SQL_INSTANCE, "");
    assert!(result.is_ok());
    let rows = result.unwrap();
    assert!(!rows.is_empty());
    assert!(rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &endpoint.instance)));
    assert!(rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &endpoint.instance)));
    assert_eq!(rows.len(), 2);
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
        let r_new = instances_new.get_full_version(&InstanceName::from(&endpoint.instance));
        let r_old = instances_old.get_full_version(&InstanceName::from(&endpoint.instance));
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
        let name_dot = format!("{}.", &endpoint.instance);
        for r in &rows {
            let values: Vec<String> = r.split('|').map(|s| s.to_string()).collect();
            assert_eq!(values.len(), 15, "Row does not have enough columns: {}", r);
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
    let q = SqlQuery::new(
        sqls::get_factory_query(id, version, Tenant::All, None).unwrap(),
        Separator::default(),
        config.params(),
    );
    conn.query(&q, "").unwrap()
}

#[test]
fn test_ts_quotas() {
    add_runtime_to_path();
    for endpoint in WORKING_ENDPOINTS.iter() {
        println!("endpoint.host = {}", &endpoint.host);
        let rows = connect_and_query(endpoint, sqls::Id::TsQuotas, None);
        assert!(!rows.is_empty());
        let expected = format!("{}|||", &endpoint.instance);
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
            assert_eq!(line.len(), 11, "Row does not have enough columns: {}", r);
            assert_eq!(line[0], endpoint.instance.as_str());
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
            assert_eq!(line[0], endpoint.instance.as_str());
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
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0], format!("{}|||||||||", &endpoint.instance));
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
            assert_eq!(line.len(), 6, "Row does not have enough columns: {}", r);
            assert_eq!(line[0], endpoint.instance.as_str());
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
        assert_eq!(
            rows[0],
            format!("{}.CDB$ROOT|||||||||||||||||", &endpoint.instance)
        );
        assert_eq!(
            rows[1],
            format!("{0}.{0}PDB1|||||||||||||||||", &endpoint.instance)
        );
        assert_eq!(rows[2], format!("{}|||||||||||||||||", &endpoint.instance));
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
        assert!(!rows.is_empty());
        assert_eq!(rows[0], format!("{}|||||||||||||||||", &endpoint.instance));
    }
}

#[test]
fn test_log_switches() {
    add_runtime_to_path();
    for endpoint in WORKING_ENDPOINTS.iter() {
        println!("endpoint.host = {}", &endpoint.host);
        let rows = connect_and_query(endpoint, sqls::Id::LogSwitches, None);
        assert!(!rows.is_empty());
        assert_eq!(rows[0], format!("{}|0", &endpoint.instance));
    }
}

#[test]
fn test_long_active_sessions_last() {
    add_runtime_to_path();
    for endpoint in WORKING_ENDPOINTS.iter() {
        println!("endpoint.host = {}", &endpoint.host);
        let rows = connect_and_query(endpoint, sqls::Id::LongActiveSessions, None);
        assert!(rows.len() >= 3);
        assert_eq!(rows[0], format!("{}.CDB$ROOT||||||||", &endpoint.instance));
        assert_eq!(rows[1], format!("{0}.{0}PDB1||||||||", &endpoint.instance));
        assert_eq!(rows[2], format!("{}||||||||", &endpoint.instance));
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
        assert_eq!(rows[0], format!("{}||||||||", &endpoint.instance));
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
        assert_eq!(array[0], endpoint.instance.as_str());
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
            assert_eq!(array.len(), 13);
            assert!(array[0].starts_with(endpoint.instance.as_str()));
            assert_eq!(array[1], endpoint.instance.as_str());
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
            assert_eq!(array[0], endpoint.instance.as_str());
            assert_eq!(array[1], endpoint.instance.as_str());
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
        let start = endpoint.instance.as_str().to_string() + ".";
        for n in [0, 1] {
            let r = rows[n].clone();
            assert!(r.starts_with(start.as_str()));

            let line: Vec<&str> = r.split("|").collect();
            assert_eq!(line.len(), 2);
            assert!(
                line[1].parse::<i32>().is_ok(),
                "Value is not a number: {}",
                line[1]
            );
        }

        let line_2: Vec<&str> = rows[2].split("|").collect();
        assert_eq!(line_2.len(), 4);
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
            assert_eq!(line.len(), 4);
            assert_eq!(line[0], endpoint.instance.as_str());
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
            assert_eq!(line.len(), 15);
            assert_eq!(line[0], endpoint.instance.as_str());
            assert!(
                line[1].ends_with(".DBF"),
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
            assert_eq!(line[0], endpoint.instance.as_str());
            assert!(
                line[1].ends_with(".DBF"),
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
            assert_eq!(line.len(), 23);
            assert_eq!(line[0], endpoint.instance.as_str());
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
        assert_eq!(line[0], endpoint.instance.as_str());
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
fn test_asm_instance_new() {
    add_runtime_to_path();
    for endpoint in WORKING_ENDPOINTS.iter() {
        println!("endpoint.host = {}", &endpoint.host);
        let rows = connect_and_query(endpoint, sqls::Id::AsmInstance, None);
        assert_eq!(rows.len(), 1);
        let r = rows[0].clone();
        let line: Vec<&str> = r.split("|").collect();
        assert_eq!(line.len(), 12);
        assert_eq!(line[0], endpoint.instance.as_str());
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
            assert!(line[0].starts_with(format!("{}.", endpoint.instance.as_str()).as_str()));
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
            assert!(line[0].starts_with(endpoint.instance.as_str()));
        });
    }
}

#[test]
fn test_performance_old() {
    add_runtime_to_path();
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
            assert!(line[0].starts_with(endpoint.instance.as_str()));
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
