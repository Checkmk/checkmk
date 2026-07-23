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

use mk_oracle::config::authentication::{AuthType, Role, SqlDbEndpoint};
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
        let base_root = std::env::current_dir().unwrap();
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

    pub fn clean_path() -> String {
        let path = std::env::var("PATH").unwrap_or_default();
        let cleaned: Vec<&str> = path
            .split(';')
            .filter(|p| {
                let lower = p.to_ascii_lowercase();
                !lower.contains("mk-oracle") && !lower.contains(r"xe\bin")
            })
            .collect();
        cleaned.join(";")
    }

    fn _patch_path() {
        let path = RUNTIME_PATH
            .get_or_init(_init_runtime_path)
            .clone()
            .into_os_string();
        let oci_path = path.to_str().unwrap();
        let cleaned_path = clean_path();
        unsafe {
            std::env::set_var("PATH", format!("{oci_path};{cleaned_path}"));
        }
    }
}

#[cfg(unix)]
pub mod platform {
    pub fn add_runtime_to_path() {
        // script is responsible for setting up the environment
    }
}

/// The role to put into a generated config: an explicit endpoint role wins
/// (e.g. the local endpoint authenticates as sys/sysdba even when addressed
/// by hostname). Otherwise the localhost (Docker) database is accessed as
/// sys, which Oracle refuses without SYSDBA (ORA-28009,
/// https://docs.oracle.com/en/error-help/db/ora-28009).
pub fn role_spec(role: &Option<Role>, address: &str) -> String {
    if let Some(r) = role {
        r.to_string()
    } else if address == "localhost" {
        "sysdba".to_string()
    } else {
        String::new()
    }
}

fn _make_mini_config(
    credentials: &Credentials,
    auth_type: AuthType,
    address: &str,
    port: u16,
    service_name: &String,
    instance_name: &Option<String>,
    role: &Option<Role>,
) -> Config {
    let config_str = format!(
        r#"
---
oracle:
  main:
    discovery:
       detect: no
    authentication:
       username: "{}"
       password: "{}"
       type: {}
       role: {}
    connection:
       hostname: {}
       port: {}
       timeout: 10
       service_name: {}
       {}
"#,
        credentials.user,
        credentials.password,
        auth_type,
        role_spec(role, address),
        address,
        port,
        service_name,
        instance_name
            .as_ref()
            .map(|s| format!("instance_name: {}", s))
            .as_deref()
            .unwrap_or(""),
    );
    Config::from_string(config_str).unwrap().unwrap()
}

#[allow(clippy::too_many_arguments)]
fn _make_mini_config_custom_instance(
    credentials: &Credentials,
    auth_type: AuthType,
    address: &str,
    port: u16,
    include: &str,
    alias: Option<InstanceAlias>,
    tns_admin: &str,
    role: &Option<Role>,
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
       tns_admin: '{8}'
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
          port: {7}
        authentication: # mandatory
          username: "{0}"
          password: "{1}"
          type: standard
          role: {3} # it may be not enabled by Oracle DBA
"#,
        credentials.user,
        credentials.password,
        auth_type,
        role_spec(role, address),
        address,
        include,
        alias_raw(&alias),
        port,
        tns_admin
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
        endpoint.port,
        include,
        alias,
        "./tests/files/tns",
        &endpoint.role,
    )
}

/// Writes a tnsnames.ora resolving `alias` to `endpoint` into a
/// process-private directory and returns that directory, suitable as
/// tns_admin. Keeps alias-based tests independent of which reference DB
/// the endpoint env vars point at.
pub fn make_endpoint_tns_admin_dir(endpoint: &SqlDbEndpoint, alias: &str) -> std::path::PathBuf {
    let dir =
        std::env::temp_dir().join(format!("mk-oracle-test-tns-{}-{alias}", std::process::id()));
    std::fs::create_dir_all(&dir).expect("failed to create TNS_ADMIN dir");
    let content = format!(
        r"{alias} =
  (DESCRIPTION =
  (ADDRESS_LIST =
  (ADDRESS = (PROTOCOL = TCP)(HOST = {host})(PORT = {port}))
  )
  (CONNECT_DATA =
  (SID = {sid})
  (SERVER = DEDICATED)
  )
  )
",
        host = endpoint.host,
        port = endpoint.port,
        sid = endpoint
            .sid
            .as_deref()
            .expect("endpoint must provide a SID"),
    );
    std::fs::write(dir.join("tnsnames.ora"), content).expect("failed to write tnsnames.ora");
    dir
}

pub fn make_mini_config_custom_instance_with_tns_admin(
    endpoint: &SqlDbEndpoint,
    include: &str,
    alias: Option<InstanceAlias>,
    tns_admin: &std::path::Path,
) -> Config {
    _make_mini_config_custom_instance(
        &Credentials {
            user: endpoint.user.clone(),
            password: endpoint.pwd.clone(),
        },
        AuthType::Standard,
        &endpoint.host,
        endpoint.port,
        include,
        alias,
        tns_admin.to_str().expect("tns_admin path must be UTF-8"),
        &endpoint.role,
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
        endpoint.port,
        &endpoint.service_name,
        &endpoint.instance_name,
        &endpoint.role,
    )
}

fn _make_mini_config_with_sid(
    credentials: &Credentials,
    auth_type: AuthType,
    address: &str,
    port: &u16,
    sid: &str,
    role: &Option<Role>,
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
       port: {}
       timeout: 10
    discovery:
       detect: no
    sections:
       - instance:
    instances:
       - sid: {}
"#,
        credentials.user,
        credentials.password,
        auth_type,
        role_spec(role, address),
        address,
        port,
        sid,
    );
    Config::from_string(config_str).unwrap().unwrap()
}

pub fn make_mini_config_with_sid(endpoint: &SqlDbEndpoint, sid: &str) -> Config {
    _make_mini_config_with_sid(
        &Credentials {
            user: endpoint.user.clone(),
            password: endpoint.pwd.clone(),
        },
        AuthType::Standard,
        &endpoint.host,
        &endpoint.port,
        sid,
        &endpoint.role,
    )
}

pub fn make_mini_config_pdb(endpoint: &SqlDbEndpoint, pdbs: &[&str]) -> Config {
    let pdbs_yaml = pdbs
        .iter()
        .map(|p| format!("\"{p}\""))
        .collect::<Vec<_>>()
        .join(", ");
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{user}"
       password: "{pwd}"
       type: standard
       role: "{role}"
    connection:
       hostname: {host}
       port: {port}
       timeout: 15
       service_name: {service}
    discovery:
       detect: no
    custom_metrics:
      - container_identity:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
          pdbs: [{pdbs}]
"#,
        user = endpoint.user,
        pwd = endpoint.pwd,
        role = role_spec(&endpoint.role, &endpoint.host),
        host = endpoint.host,
        port = endpoint.port,
        service = endpoint.service_name,
        pdbs = pdbs_yaml,
    );
    Config::from_string(config_str).unwrap().unwrap()
}

pub fn make_mini_config_cdb_root(endpoint: &SqlDbEndpoint) -> Config {
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{user}"
       password: "{pwd}"
       type: standard
       role: "{role}"
    connection:
       hostname: {host}
       port: {port}
       timeout: 15
       service_name: {service}
    discovery:
       detect: no
    custom_metrics:
      - container_identity:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
"#,
        user = endpoint.user,
        pwd = endpoint.pwd,
        role = role_spec(&endpoint.role, &endpoint.host),
        host = endpoint.host,
        port = endpoint.port,
        service = endpoint.service_name,
    );
    Config::from_string(config_str).unwrap().unwrap()
}

/// Probe order: CDB-root, PDB-scoped, CDB-root (TC-ORA-144).
pub fn make_mini_config_pdb_builtin_then_custom(endpoint: &SqlDbEndpoint, pdb: &str) -> Config {
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{user}"
       password: "{pwd}"
       type: standard
       role: "{role}"
    connection:
       hostname: {host}
       port: {port}
       timeout: 15
       service_name: {service}
    discovery:
       detect: no
    custom_metrics:
      - probe_builtin:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
      - probe_pdb:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
          pdbs: ["{pdb}"]
      - probe_followup:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
"#,
        user = endpoint.user,
        pwd = endpoint.pwd,
        role = role_spec(&endpoint.role, &endpoint.host),
        host = endpoint.host,
        port = endpoint.port,
        service = endpoint.service_name,
        pdb = pdb,
    );
    Config::from_string(config_str).unwrap().unwrap()
}

/// Probe order: PDB-scoped, CDB-root (TC-ORA-144).
pub fn make_mini_config_pdb_custom_then_builtin(endpoint: &SqlDbEndpoint, pdb: &str) -> Config {
    let config_str = format!(
        r#"
---
oracle:
  main:
    authentication:
       username: "{user}"
       password: "{pwd}"
       type: standard
       role: "{role}"
    connection:
       hostname: {host}
       port: {port}
       timeout: 15
       service_name: {service}
    discovery:
       detect: no
    custom_metrics:
      - probe_pdb:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
          pdbs: ["{pdb}"]
      - probe_followup:
          sql: "SELECT SYS_CONTEXT('USERENV', 'CON_NAME') FROM DUAL"
"#,
        user = endpoint.user,
        pwd = endpoint.pwd,
        role = role_spec(&endpoint.role, &endpoint.host),
        host = endpoint.host,
        port = endpoint.port,
        service = endpoint.service_name,
        pdb = pdb,
    );
    Config::from_string(config_str).unwrap().unwrap()
}
