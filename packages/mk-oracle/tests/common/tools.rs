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

use mk_oracle::config::authentication::{AuthType, SqlDbEndpoint};
use mk_oracle::config::ora_sql::Config;
use mk_oracle::types::{Credentials, InstanceAlias};

pub const ORA_ENDPOINT_ENV_VAR_LOCAL: &str = "CI_ORA1_DB_TEST";
pub const ORA_ENDPOINT_ENV_VAR_EXT: &str = "CI_ORA2_DB_TEST";

#[cfg(windows)]
pub mod platform {
    use mk_oracle::setup::RUNTIME_SUB_DIR;
    use std::path::PathBuf;
    use std::sync::OnceLock;

    static RUNTIME_PATH: OnceLock<PathBuf> = OnceLock::new();
    static PATCHED_PATH: OnceLock<()> = OnceLock::new();
    pub fn add_runtime_to_path() {
        PATCHED_PATH.get_or_init(_patch_path);
    }

    fn _init_runtime_path() -> PathBuf {
        let this_file: PathBuf = PathBuf::from(file!());
        let base_root = this_file
            .parent()
            .unwrap()
            .parent()
            .unwrap()
            .parent()
            .unwrap();
        std::env::set_var(
            "TNS_ADMIN",
            base_root.join("tests").join("files").join("tns"),
        );

        std::env::var("MK_LIBDIR")
            .map(PathBuf::from)
            .unwrap_or_else(|_| base_root.join("runtimes"))
            .join("plugins")
            .join("packages")
            .join(RUNTIME_SUB_DIR)
            .join("runtime")
    }

    fn _patch_path() {
        let path = RUNTIME_PATH
            .get_or_init(_init_runtime_path)
            .clone()
            .into_os_string();
        let cwd = path.to_str().unwrap();
        unsafe {
            std::env::set_var("PATH", format!("{cwd};") + &std::env::var("PATH").unwrap());
        }
        std::env::set_current_dir(cwd).unwrap();
        eprintln!("PATH={}", std::env::var("PATH").unwrap());
    }
}

#[cfg(unix)]
pub mod platform {
    pub fn add_runtime_to_path() {
        // script is responsible for setting up the environment
    }
}

fn _make_mini_config(
    credentials: &Credentials,
    auth_type: AuthType,
    address: &str,
    service_name: &String,
    instance_name: &Option<String>,
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
       role: {}
    connection:
       hostname: {}
       timeout: 10
       service_name: {}
       {}
"#,
        credentials.user,
        credentials.password,
        auth_type,
        if address == "localhost" { "sysdba" } else { "" },
        address,
        service_name,
        instance_name
            .as_ref()
            .map(|s| format!("instance_name: {}", s))
            .as_deref()
            .unwrap_or(""),
    );
    Config::from_string(config_str).unwrap().unwrap()
}

fn _make_mini_config_custom_instance(
    credentials: &Credentials,
    auth_type: AuthType,
    address: &str,
    include: &str,
    alias: Option<InstanceAlias>,
) -> Config {
    fn alias_raw(alias: &Option<InstanceAlias>) -> String {
        if let Some(a) = alias {
            format!("alias: {a}")
        } else {
            String::new()
        }
    }
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{0}"
       password: "{1}"
       type: {2}
       role: {3}
    connection:
       hostname: absent.{4}
       timeout: 5
       tns_admin: ./tests/files/tns
    sections: # optional, if absent will use default as defined below
      - instance: # special section
    discovery: # optional, defines instances to be monitored
      detect: no # optional
      include: [{5}] # optional
      exclude: [] # optional
    instances: # optional
      - service_name: {5}
        {6}
        connection: # mandatory
          hostname: {4}
        authentication: # mandatory
          username: "{0}"
          password: "{1}"
          type: standard
          role: {3} # it may be not enabled by Oracle DBA
"#,
        credentials.user,
        credentials.password,
        auth_type,
        if address == "localhost" { "sysdba" } else { "" },
        address,
        include,
        alias_raw(&alias)
    );
    Config::from_string(config_str).unwrap().unwrap()
}

pub fn make_mini_config_custom_instance(
    endpoint: &SqlDbEndpoint,
    include: &str,
    alias: Option<InstanceAlias>,
) -> Config {
    _make_mini_config_custom_instance(
        &Credentials {
            user: endpoint.user.clone(),
            password: endpoint.pwd.clone(),
        },
        AuthType::Standard,
        &endpoint.host,
        include,
        alias,
    )
}

pub fn make_mini_config(endpoint: &SqlDbEndpoint) -> Config {
    _make_mini_config(
        &Credentials {
            user: endpoint.user.clone(),
            password: endpoint.pwd.clone(),
        },
        AuthType::Standard,
        &endpoint.host,
        &endpoint.service_name,
        &endpoint.instance_name,
    )
}
