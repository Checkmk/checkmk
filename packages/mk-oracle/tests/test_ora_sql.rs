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
use mk_oracle::types::{Credentials, InstanceName};
use mk_oracle::types::{Separator, SqlQuery};
use std::collections::HashSet;
use std::str::FromStr;

pub static ORA_TEST_ENDPOINTS: &str = include_str!("files/endpoints.txt");

fn make_base_config(
    credentials: &Credentials,
    auth_type: AuthType,
    role: Option<Role>,
    address: &str,
    port: u16,
    instance_name: InstanceName,
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
        instance_name
    );
    Config::from_string(config_str).unwrap().unwrap()
}

fn make_mini_config(credentials: &Credentials, auth_type: AuthType, address: &str) -> Config {
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{}"
       password: "{}"
       type: {}
    connection:
       hostname: {}
       timeout: 10
"#,
        credentials.user, credentials.password, auth_type, address,
    );
    Config::from_string(config_str).unwrap().unwrap()
}

fn load_endpoints() -> Vec<SqlDbEndpoint> {
    let mut r = reference_endpoint();
    let content = ORA_TEST_ENDPOINTS.to_owned();
    content
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
        .collect::<Vec<SqlDbEndpoint>>()
}

fn reference_endpoint() -> SqlDbEndpoint {
    SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).unwrap()
}

lazy_static::lazy_static! {
    static ref WORKING_ENDPOINTS: Vec<SqlDbEndpoint> = load_endpoints();
}
#[test]
fn test_endpoints_file() {
    let s = &WORKING_ENDPOINTS;
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT).unwrap();
    assert!(!s.is_empty());
    assert_eq!(s[0], r);
    for e in &s[1..] {
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

lazy_static::lazy_static! {
    static ref REFERENCE_ENDPOINT: SqlDbEndpoint = reference_endpoint();
    static ref TEST_SQL_INSTANCE:SqlQuery = SqlQuery::new(
            r"
    select upper(i.INSTANCE_NAME)
        ||'|'|| 'sys_time_model'
        ||'|'|| S.STAT_NAME
        ||'|'|| Round(s.value/1000000)
    from v$instance i,
        v$sys_time_model s
    where s.stat_name in('DB time', 'DB CPU')
    order by s.stat_name",
            Separator::No
        );
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
        InstanceName::from(&endpoint.instance),
    );

    let mut task = backend::make_task(&config.endpoint()).unwrap();
    let r = task.connect();
    assert!(r.is_ok());
    let result = task.query(&TEST_SQL_INSTANCE, "");
    assert!(result.is_ok());
    let rows = result.unwrap();
    eprintln!("Rows: {:?}", rows);
    assert!(!rows.is_empty());
    assert!(rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &endpoint.instance)));
    assert!(rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &endpoint.instance)));
    assert_eq!(rows.len(), 2);
}

#[test]
fn test_remote_mini_connection() {
    add_runtime_to_path();
    let endpoint = reference_endpoint();

    let config = make_mini_config(
        &Credentials {
            user: endpoint.user,
            password: endpoint.pwd,
        },
        AuthType::Standard,
        &endpoint.host,
    );

    let mut task = backend::make_task(&config.endpoint()).unwrap();
    let r = task.connect();
    println!("{:?}", r);
    println!("{:?}", std::env::var("LD_LIBRARY_PATH"));
    assert!(r.is_ok());
    let result = task.query(
        &SqlQuery::new(
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
        ),
        "",
    );
    assert!(result.is_ok());
    let rows = result.unwrap();
    eprintln!("Rows: {:?}", rows);
    assert!(!rows.is_empty());
    assert!(rows[0].starts_with(&format!("{}|sys_time_model|DB CPU|", &endpoint.instance)));
    assert!(rows[1].starts_with(&format!("{}|sys_time_model|DB time|", &endpoint.instance)));
    assert_eq!(rows.len(), 2);
}

#[test]
fn test_remote_mini_connection_version() {
    add_runtime_to_path();
    for endpoint in WORKING_ENDPOINTS.iter() {
        eprintln!("Testing endpoint: {}", endpoint.host);

        let config = make_mini_config(
            &Credentials {
                user: endpoint.user.clone(),
                password: endpoint.pwd.clone(),
            },
            AuthType::Standard,
            &endpoint.host,
        );

        let mut task = backend::make_task(&config.endpoint()).unwrap();
        task.connect()
            .expect("Connect failed, check environment variables");

        let version = system::get_version(&task, &InstanceName::from(&endpoint.instance))
            .unwrap()
            .unwrap();
        assert!(version.starts_with("2"));
        assert!(
            system::get_version(&task, &InstanceName::from("no-such-db"))
                .unwrap()
                .is_none()
        );
    }
}

#[test]
fn test_io_stats_query() {
    add_runtime_to_path();
    let endpoint = reference_endpoint();

    let config = make_mini_config(
        &Credentials {
            user: endpoint.user,
            password: endpoint.pwd,
        },
        AuthType::Standard,
        &endpoint.host,
    );

    let mut task = backend::make_task(&config.endpoint()).unwrap();
    let r = task.connect();
    assert!(r.is_ok());
    let q = SqlQuery::new(
        sqls::find_known_query(sqls::Id::IoStats).unwrap(),
        Separator::default(),
    );
    let result = task.query(&q, "");
    assert!(result.is_ok());
    let rows = result.unwrap();
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
