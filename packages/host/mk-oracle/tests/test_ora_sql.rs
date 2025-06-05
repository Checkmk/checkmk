// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(feature = "build_system_bazel")]
extern crate common;
#[cfg(not(feature = "build_system_bazel"))]
mod common;

use mk_oracle::config::ora_sql::{AuthType, Config, EngineTag};
use mk_oracle::ora_sql::backend;

use common::tools::SQL_DB_ENDPOINT;
use mk_oracle::types::{Credentials, InstanceName};

fn make_base_config(
    credentials: &Credentials,
    auth_type: AuthType,
    address: &str,
    port: u16,
    instance_name: InstanceName,
) -> Config {
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
       port: {}
       instance: {}
       timeout: 10
"#,
        credentials.user, credentials.password, auth_type, address, port, instance_name
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
        "localhost",
        1521,
        InstanceName::from("XE"),
    );

    assert_eq!(config.conn().engine_tag(), &EngineTag::Std);
}

#[allow(clippy::const_is_empty)]
#[test]
fn test_local_connection() {
    assert!(!SQL_DB_ENDPOINT.is_empty());
    let config = make_base_config(
        &Credentials {
            user: "sys".to_string(),
            password: "Oracle-dba".to_string(),
        },
        AuthType::Standard,
        "localhost",
        1521,
        InstanceName::from("XE"),
    );

    let mut task = backend::make_task(&config.endpoint()).unwrap();
    assert!(task.connect().is_err());
}
