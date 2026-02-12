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

use crate::args::Args;
use crate::config::system::{Logging, SystemConfig};
use crate::config::OracleConfig;
use crate::platform::get_local_instances;
use crate::types::{EnvVarName, SectionFilter, UseHostClient};
use crate::version::VERSION;
use crate::{constants, setup};
use anyhow::Result;
use clap::Parser;
use flexi_logger::{self, Cleanup, Criterion, DeferredNow, FileSpec, LogSpecification, Record};
use std::env::ArgsOs;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::LazyLock;

#[derive(Default, Clone, Debug)]
pub struct Env {
    /// guaranteed to contain dir or None
    temp_dir: Option<PathBuf>,

    /// guaranteed to contain dir or None
    log_dir: Option<PathBuf>,

    /// guaranteed to contain dir or None
    state_dir: Option<PathBuf>,

    /// disable caching
    disable_caching: bool,

    /// detect instances and stop
    detect_only: bool,

    /// detect sids on local machine and stop
    detect_sids: bool,

    /// detect runtime and stop
    find_runtime: bool,

    /// detect instances and stop
    execution: SectionFilter,

    /// generate plugins and stop
    generate_plugins: Option<PathBuf>,
}

impl Env {
    pub fn new(args: &Args) -> Self {
        let log_dir = Env::make_dir(&args.log_dir, &constants::ENV_LOG_DIR.as_deref());
        let temp_dir = Env::build_dir(&args.temp_dir, &constants::ENV_TEMP_DIR.as_deref());
        #[cfg(windows)]
        let state_dir = Env::build_dir(&args.state_dir, &constants::ENV_STATE_DIR.as_deref());
        #[cfg(unix)]
        let state_dir = Env::build_dir(&args.state_dir, &constants::ENV_VAR_DIR.as_deref());
        Self {
            temp_dir,
            log_dir,
            state_dir,
            disable_caching: args.no_spool,
            detect_only: args.detect_only,
            detect_sids: args.detect_sids,
            find_runtime: args.find_runtime,
            execution: args.filter.clone().unwrap_or_default(),
            generate_plugins: args.generate_plugins.clone(),
        }
    }

    pub fn temp_dir(&self) -> Option<&Path> {
        self.temp_dir.as_deref()
    }

    pub fn log_dir(&self) -> Option<&Path> {
        self.log_dir.as_deref()
    }

    pub fn state_dir(&self) -> Option<&Path> {
        self.state_dir.as_deref()
    }

    pub fn disable_caching(&self) -> bool {
        self.disable_caching
    }

    pub fn detect_only(&self) -> bool {
        self.detect_only
    }

    pub fn detect_sids(&self) -> bool {
        self.detect_sids
    }

    pub fn find_runtime(&self) -> bool {
        self.find_runtime
    }

    pub fn generate_plugins(&self) -> Option<&Path> {
        self.generate_plugins.as_deref()
    }

    pub fn execution(&self) -> SectionFilter {
        self.execution.clone()
    }

    fn build_dir(dir: &Option<PathBuf>, fallback: &Option<&Path>) -> Option<PathBuf> {
        if dir.is_some() {
            dir.as_deref()
        } else {
            fallback.as_deref()
        }
        .map(PathBuf::from)
        .filter(|p| Path::is_dir(p))
    }

    fn make_dir(dir: &Option<PathBuf>, fallback: &Option<&Path>) -> Option<PathBuf> {
        let path = dir.as_deref().or(fallback.as_deref())?;

        if !path.exists() {
            std::fs::create_dir_all(path).ok()?;
        }

        path.is_dir().then(|| path.to_path_buf())
    }
}

pub enum SendTo {
    Null,
    Stderr,
    Stdout,
}

pub fn init(args: ArgsOs) -> Result<(OracleConfig, Env)> {
    let args = Args::parse_from(args);
    let config_file = get_config_file(&args);

    let logging_config = get_system_config(&config_file)
        .map(|x| Some(x.logging().to_owned()))
        .unwrap_or(None);
    let environment = Env::new(&args);
    init_logging(&args, &environment, logging_config)?;
    if !config_file.exists() {
        anyhow::bail!("The config file {:?} doesn't exist", config_file);
    }
    Ok((get_check_config(&config_file)?, environment))
}

fn init_logging(args: &Args, environment: &Env, logging: Option<Logging>) -> Result<()> {
    let l = logging.unwrap_or_default();
    let level = args.logging_level().unwrap_or_else(|| l.level());
    let send_to = if args.display_log {
        SendTo::Stderr
    } else {
        SendTo::Null
    };

    let s = apply_logging_parameters(level, environment.log_dir(), send_to, l).map(|_| ());
    log_info_optional(args, level, environment, s.is_ok());
    s
}

fn log_info_optional(args: &Args, level: log::Level, environment: &Env, log_available: bool) {
    if args.print_info {
        let info = create_info_text(&level, environment);
        if log_available {
            log::info!("{}", info);
        } else {
            println!("{}", info);
        }
    }
}
fn create_info_text(level: &log::Level, environment: &Env) -> String {
    format!(
        "\n  - Log level: {}\n  - Log dir: {}\n  - Temp dir: {}\n  - MK_CONFDIR: {}",
        level,
        environment
            .log_dir()
            .unwrap_or_else(|| Path::new(""))
            .display(),
        environment
            .temp_dir()
            .unwrap_or_else(|| Path::new("."))
            .display(),
        constants::get_env_value(constants::environment::CONFIG_DIR_ENV_VAR, "undefined"),
    )
}

fn get_check_config(file: &Path) -> Result<OracleConfig> {
    log::info!("Using config file: {}", file.display());

    OracleConfig::load_file(file)
}

fn get_system_config(file: &Path) -> Result<SystemConfig> {
    SystemConfig::load_file(file)
}

fn get_config_file(args: &Args) -> PathBuf {
    match args.config_file {
        Some(ref config_file) => config_file,
        None => &constants::DEFAULT_CONFIG_FILE,
    }
    .to_owned()
}

fn custom_format(
    w: &mut dyn std::io::Write,
    now: &mut DeferredNow,
    record: &Record,
) -> Result<(), std::io::Error> {
    write!(
        w,
        "{} [{}] [{}]: {}",
        now.format("%Y-%m-%d %H:%M:%S%.3f %:z"),
        record.level(),
        record.module_path().unwrap_or("<unnamed>"),
        &record.args()
    )
}

fn apply_logging_parameters(
    level: log::Level,
    log_dir: Option<&Path>,
    send_to: SendTo,
    logging: Logging,
) -> Result<flexi_logger::LoggerHandle> {
    let spec = LogSpecification::parse(level.as_str().to_lowercase())?;
    let mut logger = flexi_logger::Logger::with(spec);

    logger = if let Some(dir) = log_dir {
        logger
            .log_to_file(make_log_file_spec(dir))
            .rotate(
                Criterion::Size(logging.max_size()),
                constants::log::FILE_NAMING,
                Cleanup::KeepLogFiles(logging.max_count()),
            )
            .append()
    } else {
        logger.do_not_log()
    };

    logger = match send_to {
        SendTo::Null => logger
            .duplicate_to_stderr(flexi_logger::Duplicate::None)
            .duplicate_to_stdout(flexi_logger::Duplicate::None),
        SendTo::Stderr => logger.log_to_stderr(),
        SendTo::Stdout => logger.log_to_stdout(),
    };

    log::info!("Log level: {}", level.as_str());
    Ok(logger.format(custom_format).start()?)
}

fn make_log_file_spec(log_dir: &Path) -> FileSpec {
    FileSpec::default()
        .directory(log_dir.to_owned())
        .suppress_timestamp()
        .basename("mk-oracle")
}

pub const RUNTIME_SUB_DIR: &str = "mk-oracle";

pub fn detect_host_runtime() -> Option<PathBuf> {
    match get_local_instances() {
        Err(e) => {
            log::info!("Local Oracle instances detection failed with {} - can't use them to detect runtime path", &e.to_string());
            try_find_instance_runtime()
        }
        Ok(instances) if instances.is_empty() => {
            log::info!(
                "Local Oracle instances are not detected - can't use them to detect runtime path"
            );
            try_find_instance_runtime()
        }
        Ok(instances) => {
            for instance in &instances {
                log::info!(
                    "Try to find runtime using local Oracle instance: name={}, home={:?}, base={:?}",
                    instance.name,
                    instance.home,
                    instance.base
                );
                let candidate = instance.home.join("bin");
                if candidate.is_dir() && validate_permissions(&candidate) {
                    return Some(instance.home.join("bin"));
                } else {
                    log::warn!("Oracle home {:?} is not suitable", instance.home);
                }
            }
            None
        }
    }
}

fn try_find_instance_runtime() -> Option<PathBuf> {
    const CLIENT_ENV_VAR: &str = "ORACLE_INSTANT_CLIENT";
    if let Ok(env_var) = std::env::var(CLIENT_ENV_VAR) {
        let candidate = PathBuf::from(env_var);
        return if candidate.is_dir() && validate_permissions(&candidate) {
            Some(candidate)
        } else {
            log::warn!(
                "{} path {:?} is not a directory or has wrong permissions",
                CLIENT_ENV_VAR,
                candidate
            );
            None
        };
    };

    const ENV_VAR: &str = "ORACLE_HOME";
    if let Some(runtime) =
        find_default_instance_runtime(ENV_VAR).filter(|r| validate_permissions(r))
    {
        Some(runtime)
    } else {
        log::info!("Failed to find local Oracle instances using {ENV_VAR}");
        None
    }
}

pub fn find_default_instance_runtime(env_var: &str) -> Option<PathBuf> {
    let oracle_home = match std::env::var(env_var) {
        Ok(path) => path,
        Err(_) => {
            log::warn!("{} is not set", env_var);
            return None;
        }
    };

    let candidate = PathBuf::from(oracle_home).join("lib");

    if !candidate.is_dir() {
        log::warn!("{} path {:?} is not a directory", env_var, candidate);
        None
    } else if !validate_permissions(&candidate) {
        log::warn!("{env_var} path {:?} has wrong permissions", candidate);
        None
    } else {
        log::info!("Using {} {:?} for runtime", env_var, candidate);
        Some(candidate)
    }
}
/// Finds runtime dir using MK_LIBDIR or custom env var
/// usually at: MK_LIBDIR/plugins/packages/mk-oracle
/// Returns None if env var is not set or path is not a directory
pub fn detect_factory_runtime(env_var: Option<String>) -> Option<PathBuf> {
    let env_var = env_var.unwrap_or_else(|| "MK_LIBDIR".to_string());
    if let Ok(lib_path) = std::env::var(&env_var) {
        let runtime_path = PathBuf::from(lib_path)
            .join("plugins")
            .join("packages")
            .join(RUNTIME_SUB_DIR);

        let runtime_path = if cfg!(windows) && runtime_path.join("runtime").is_dir() {
            runtime_path.join("runtime")
        } else {
            runtime_path
        };
        if runtime_path.is_dir() {
            Some(runtime_path)
        } else {
            log::error!(
                "{:?} is set but {:?} is not a directory",
                &env_var,
                runtime_path
            );
            None
        }
    } else {
        log::warn!("{:?} is not set", &env_var);
        None
    }
}

pub fn detect_runtime(use_host_client: &UseHostClient, env_var: Option<String>) -> Option<PathBuf> {
    match use_host_client {
        UseHostClient::Always => detect_host_runtime(),
        UseHostClient::Never => detect_factory_runtime(env_var),
        UseHostClient::Auto => detect_factory_runtime(env_var).or_else(detect_host_runtime),
        UseHostClient::Path(p) => Some(PathBuf::from(p)),
    }
    .and_then(|p| {
        if p.is_dir() {
            log::info!("Runtime detected at {:?}", p);
            Some(p)
        } else {
            log::error!("Runtime path {:?} is not a directory or missing", p);
            None
        }
    })
}

#[cfg(windows)]
const _DEFAULT_ENV_VAR: &str = "PATH";
#[cfg(unix)]
const _DEFAULT_ENV_VAR: &str = "LD_LIBRARY_PATH";

static DEFAULT_ENV_VAR: LazyLock<EnvVarName> =
    LazyLock::new(|| EnvVarName::from(_DEFAULT_ENV_VAR.to_string()));

#[cfg(windows)]
const ENV_VAR_SEP: &str = ";";
#[cfg(unix)]
const ENV_VAR_SEP: &str = ":";

/// On Unix we modify LD_LIBRARY_PATH using config and, by default, MK_LIBDIR
/// On Windows we modify PATH using config and, by default, MK_LIBDIR
pub fn add_runtime_path_to_env(
    config: &OracleConfig,
    mk_lib_dir: Option<String>,
    mut_env: Option<EnvVarName>,
) -> Option<PathBuf> {
    log::info!("Runtime to be added");
    let mutable_var_name = mut_env.unwrap_or(DEFAULT_ENV_VAR.clone());
    let mutable_var_content = std::env::var(mutable_var_name.to_str())
        .ok()
        .unwrap_or_default();
    log::info!("Current {mutable_var_name}={mutable_var_content}");
    let use_host_client: UseHostClient = config.ora_sql()?.options().use_host_client().clone();
    log::info!("Use host client {:?}", use_host_client);
    let runtime = detect_runtime(&use_host_client, mk_lib_dir)?.into_os_string();
    log::info!("Runtime found at {:?}", runtime);
    let mut additional_path = runtime.clone();
    additional_path.push(ENV_VAR_SEP);
    additional_path.push(&mutable_var_content);
    unsafe {
        std::env::set_var(mutable_var_name.to_str(), additional_path);
    }
    Some(PathBuf::from(mutable_var_content))
}

pub fn reset_env(old_path: &Path, mut_env: Option<String>) {
    let mutable_var = mut_env.unwrap_or(DEFAULT_ENV_VAR.to_string());
    unsafe {
        std::env::set_var(mutable_var, old_path);
    }
}

/// Validate permissions of the given path(see mk-oracle)
pub fn validate_permissions(p: &Path) -> bool {
    // TODO. Implement permission checks for Oracle home/bin
    // If executable is elevated,
    // then permissions for directory and all required binaries should be admin only.
    log::warn!("CHECK PERMISSIONS is not implemented yet, {p:?} is allowed to be used");
    true
}

#[cfg(windows)]
static PLUGIN_TEMPLATE_TEXT: LazyLock<String> = LazyLock::new(|| {
    format!(
        r#"# Copyright (C) 2025 Checkmk GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

$CMK_VERSION = "{}"

& $env:MK_PLUGINSDIR\packages\mk-oracle\mk-oracle.exe -c $env:MK_CONFDIR/oracle.yml "#,
        VERSION
    )
});

const BAKERY_TEXT: &str = r#" Created by mk-oracle plugin.
# This file is managed via mk-oracle plugin, do not edit manually or you
# lose your changes next time when you update the agent.
global:
  enabled: true
  install: true
plugins:
  enabled: true
  execution:
  - pattern: $CUSTOM_PLUGINS_PATH$\"#;

#[cfg(not(windows))]
static PLUGIN_TEMPLATE_TEXT: LazyLock<String> = LazyLock::new(|| {
    format!(
        r#"!/bin/bash
# Copyright (C) 2025 Checkmk GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

CMK_VERSION="{}"

"${{MK_LIBDIR}}/plugins/packages/mk-oracle/mk-oracle" -c "${{MK_CONFDIR}}/oracle.yml" "#,
        VERSION
    )
});

fn delete_file_in_sub_dirs(folder: &Path, name: &str) -> std::io::Result<()> {
    for entry in std::fs::read_dir(folder)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            let file_path = path.join(name);
            if file_path.is_file() {
                std::fs::remove_file(file_path).unwrap_or_else(|e| {
                    log::error!("Failed to delete old plugin file: {e}");
                });
            }
        }
    }
    Ok(())
}

fn add_yml_config_async_entry(lib_dir: &Path, name: &str, cache_age: u32) -> bool {
    if !lib_dir.is_dir() {
        log::error!("Lib dir {:?} doesn't exist", lib_dir);
        return false;
    }
    let bakery_dir = lib_dir.join("bakery");
    if !bakery_dir.is_dir() {
        log::error!("Bakery dir absent/inaccessible {:?}", &bakery_dir);
        return false;
    }
    let bakery_file = bakery_dir.join("check_mk.bakery.yml");
    if !&bakery_file.exists()
        || !fs::read_to_string(&bakery_file)
            .unwrap_or_default()
            .contains("# Created by Check_MK Agent Bakery.")
    {
        let content =
            BAKERY_TEXT.to_string() + name + "\n" + "    cache: " + &cache_age.to_string() + "\n";
        fs::write(&bakery_file, content)
            .map(|_| true)
            .unwrap_or_else(|e| {
                log::error!("Failed to create config file {:?}: {}", &bakery_file, &e);
                false
            })
    } else {
        log::error!("File {bakery_file:?} exists and it's managed by bakery");
        false
    }
}

#[cfg(unix)]
fn set_file_permissions(path: &Path, mode: u32) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt;

    let perms = fs::Permissions::from_mode(mode);
    fs::set_permissions(path, perms)
}

#[cfg(windows)]
fn set_file_permissions(_path: &Path, _mode: u32) -> std::io::Result<()> {
    // Windows doesn't support Unix-like permissions
    Ok(())
}

pub fn create_plugin(name: &str, dir: &Path, cache_age: Option<u32>) -> bool {
    if !dir.is_dir() {
        log::info!("Plugin dir {:?} doesn't exist", dir);
        return false;
    }
    if let Some(parent) = dir.parent() {
        if !parent.is_dir() {
            log::info!("Parent directory of plugin dir {:?} doesn't exist", dir);
            return false;
        }
        if let Some(cache_age) = cache_age {
            if cfg!(windows) {
                if add_yml_config_async_entry(parent, name, cache_age) {
                    Some(dir.to_owned())
                } else {
                    log::error!("Config is not updated/created");
                    None
                }
            } else {
                delete_file_in_sub_dirs(dir, name)
                    .map(|_| make_cached_subdir(dir, cache_age))
                    .unwrap_or_else(|e| {
                        log::error!("Failed to delete old plugin files: {e}");
                        None
                    })
            }
        } else {
            Some(dir.to_owned())
        }
        .map(|plugin_dir| {
            let cmd_line = if cache_age.is_some() {
                "--filter async"
            } else {
                "--filter sync"
            };
            let the_file = plugin_dir.join(name);
            fs::write(
                &the_file,
                PLUGIN_TEMPLATE_TEXT.to_string() + cmd_line + "\n",
            )
            .map(|_| set_file_permissions(&the_file, 0o755))
            .map(|_| true)
            .unwrap_or_else(|e| {
                log::error!("Failed to create plugin file: {e}");
                false
            })
        })
        .unwrap_or_default()
    } else {
        log::error!("Plugin dir {:?} has no parent dir", dir);
        false
    }
}

fn make_cached_subdir(dir: &Path, cache_age: u32) -> Option<PathBuf> {
    let joined_path = dir.join(cache_age.to_string());
    fs::create_dir_all(&joined_path)
        .map(|_| Some(joined_path))
        .unwrap_or_else(|e| {
            log::error!("Failed to create parent directory of plugin dir: {e}");
            None
        })
}

pub fn create_plugins(p: &Path, cache_age: u32) -> i32 {
    log::info!("PLUGINS GENERATED for path {p:?}");
    if !p.is_dir() {
        return 1;
    }
    log::info!("PLUGINS DIR={}", p.display());

    if cfg!(windows) {
        setup::create_plugin("oracle_unified_sync.ps1", p, None);
        setup::create_plugin("oracle_unified_async.ps1", p, Some(cache_age));
    } else {
        setup::create_plugin("oracle_unified_sync", p, None);
        setup::create_plugin("oracle_unified_async", p, Some(cache_age));
    }

    0
}

pub fn display_and_log(e: impl std::fmt::Display) {
    log::error!("{e}",);
    eprintln!("Stop on error: `{e}`",);
}

pub fn spawn_new_process(args: Vec<String>, old_path: std::path::PathBuf) -> i32 {
    let mut new_args = args.clone();
    new_args.push("--runtime-ready".to_string());
    let exe = std::env::current_exe().expect("Failed to get current exe");
    let status = std::process::Command::new(exe)
        .args(&new_args[1..]) // skip the old program name
        .status()
        .unwrap_or_else(|e| {
            display_and_log(e);
            setup::reset_env(&old_path, None);
            std::process::exit(1);
        });
    setup::reset_env(&old_path, None);
    status.code().unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_spec() {
        let spec = make_log_file_spec(&PathBuf::from("_"));
        assert_eq!(
            spec.as_pathbuf(None),
            PathBuf::from("_").join("mk-oracle.log")
        );
    }
    #[test]
    fn test_env_dir_exist() {
        let args = Args {
            log_dir: Some(PathBuf::from(".")),
            temp_dir: Some(PathBuf::from(".")),
            state_dir: Some(PathBuf::from(".")),
            ..Default::default()
        };
        let e = Env::new(&args);
        assert_eq!(e.log_dir(), Some(Path::new(".")));
        assert_eq!(e.temp_dir(), Some(Path::new(".")));
    }
    #[test]
    fn test_temp_dir_absent() {
        let args = Args {
            temp_dir: Some(PathBuf::from("burr-dir")),
            ..Default::default()
        };
        let e = Env::new(&args);
        assert!(e.temp_dir().is_none());
    }
    #[test]
    fn test_log_dir_exists() {
        // we do not want to create dirs during tests, so we use "."
        let args = Args {
            log_dir: Some(PathBuf::from(".")),
            ..Default::default()
        };
        let e = Env::new(&args);
        assert!(e.log_dir().is_some());
    }
    #[test]
    fn test_create_info_text() {
        assert!(
            create_info_text(&log::Level::Debug, &Env::new(&Args::default())).starts_with(
                r#"
  - Log level: DEBUG
  - Log dir: 
  - Temp dir: .
  - MK_CONFDIR: "#
            )
        );
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
    fn test_detect_factory_runtime() {
        unsafe {
            std::env::remove_var("MK_LIBDIR");
        }
        assert!(detect_factory_runtime(None).is_none());
        unsafe {
            std::env::set_var("MK_LIBDIR", base_dir().join("runtimes"));
        }
        assert!(detect_factory_runtime(None).is_some());

        unsafe {
            std::env::set_var("MK_MY_VAR", base_dir().join("runtimes"));
        }
        assert!(detect_factory_runtime(Some("MK_MY_VAR".to_string())).is_some());
    }
}
