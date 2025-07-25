// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(feature = "build_system_bazel")]
extern crate common;
#[cfg(not(feature = "build_system_bazel"))]
mod common;

use mk_oracle::config::authentication::{AuthType, Authentication, Role, SqlDbEndpoint};
use mk_oracle::config::ora_sql::Config;
use mk_oracle::ora_sql::backend;
use mk_oracle::ora_sql::system;
use mk_oracle::types::SqlQuery;

use crate::common::tools::{
    platform::add_runtime_to_path, ORA_ENDPOINT_ENV_VAR_EXT, ORA_ENDPOINT_ENV_VAR_LOCAL,
};
use mk_oracle::types::{Credentials, InstanceName};

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

#[test]
fn test_enpoint() {
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT);
    assert!(r.is_ok());
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
    let result = task.query(
        &SqlQuery::from(
            r"
    select upper(i.INSTANCE_NAME)
        ||'|'|| 'sys_time_model'
        ||'|'|| S.STAT_NAME
        ||'|'|| Round(s.value/1000000)
    from v$instance i,
        v$sys_time_model s
    where s.stat_name in('DB time', 'DB CPU')
    order by s.stat_name",
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
fn test_remote_mini_connection() {
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT);
    assert!(r.is_ok());
    add_runtime_to_path();
    let endpoint = r.unwrap();

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
        &SqlQuery::from(
            r"
    select upper(i.INSTANCE_NAME)
        ||'|'|| 'sys_time_model'
        ||'|'|| S.STAT_NAME
        ||'|'|| Round(s.value/1000000)
    from v$instance i,
        v$sys_time_model s
    where s.stat_name in('DB time', 'DB CPU')
    order by s.stat_name",
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
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_EXT);
    assert!(r.is_ok());
    add_runtime_to_path();
    let endpoint = r.unwrap();

    let config = make_mini_config(
        &Credentials {
            user: endpoint.user,
            password: endpoint.pwd,
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
