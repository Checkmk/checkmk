// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(feature = "build_system_bazel")]
extern crate common;
#[cfg(not(feature = "build_system_bazel"))]
mod common;

use mk_oracle::config::ora_sql::{AuthType, Config, EngineTag, Role};
use mk_oracle::ora_sql::backend;
use std::path::PathBuf;
use std::sync::OnceLock;

use crate::common::tools::{SqlDbEndpoint, ORA_ENDPOINT_ENV_VAR_BASE};
use mk_oracle::types::{Credentials, InstanceName};

static RUNTIME_PATH: OnceLock<PathBuf> = OnceLock::new();

fn _init_runtime_path() -> PathBuf {
    let _this_file: PathBuf = PathBuf::from(file!());
    _this_file
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("runtimes")
        .join("oci_light_win_x86_zip")
}

fn change_cwd_to_runtime_path() {
    let runtime_location = RUNTIME_PATH.get_or_init(_init_runtime_path).clone();
    std::env::set_current_dir(runtime_location).unwrap();
}
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

#[test]
fn test_config_to_remove() {
    let config = make_base_config(
        &Credentials {
            user: "sys".to_string(),
            password: "Oracle-dba".to_string(),
        },
        AuthType::Standard,
        None,
        "localhost",
        1521,
        InstanceName::from("XE"),
    );

    assert_eq!(config.conn().engine_tag(), &EngineTag::Std);
}

#[test]
#[allow(clippy::const_is_empty)]
fn test_endpoint() {
    assert!(!ORA_ENDPOINT_ENV_VAR_BASE.is_empty());
}
#[allow(clippy::const_is_empty)]
#[test]
fn test_local_connection() {
    let r = SqlDbEndpoint::from_env(ORA_ENDPOINT_ENV_VAR_BASE);
    if r.is_err() {
        println!("Skipping test_local_connection: {}", r.err().unwrap());
        return;
    }
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
        InstanceName::from(endpoint.point),
    );

    change_cwd_to_runtime_path();

    let mut task = backend::make_task(&config.endpoint()).unwrap();
    let r = task.connect();
    assert!(r.is_ok());
}
