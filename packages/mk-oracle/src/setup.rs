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
use crate::config::grid::GridInfrastructure;
use crate::config::merge;
use crate::config::options::Options;
use crate::config::system::{Logging, SystemConfig};
use crate::config::OracleConfig;
use crate::constants::{get_user_config_file, RUNTIME_DIR};
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

    /// detect sids on local machine and stop
    detect_sids: bool,

    /// detect runtime and stop
    find_runtime: bool,

    /// the runtime environment is already prepared by the parent process
    runtime_ready: bool,

    /// filtering sections for sync/async, possible values are "sync", "async", "all"
    filter: SectionFilter,

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
            detect_sids: args.detect_sids,
            find_runtime: args.find_runtime,
            runtime_ready: args.runtime_ready,
            filter: args.filter.unwrap_or_default(),
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

    pub fn detect_sids(&self) -> bool {
        self.detect_sids
    }

    pub fn find_runtime(&self) -> bool {
        self.find_runtime
    }

    pub fn runtime_ready(&self) -> bool {
        self.runtime_ready
    }

    pub fn generate_plugins(&self) -> Option<&Path> {
        self.generate_plugins.as_deref()
    }

    pub fn filter(&self) -> SectionFilter {
        self.filter
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
    let main_file = get_config_file(&args);
    let user_file = get_user_config_file(&RUNTIME_DIR);

    let merged_config = merge::merge_configs(&main_file, &user_file);

    let logging_config = merged_config
        .as_ref()
        .ok()
        .and_then(|e| e.config.as_ref())
        .and_then(|doc| SystemConfig::from_yaml(doc).ok())
        .map(|s| s.logging().to_owned());
    let environment = Env::new(&args);
    init_logging(&args, &environment, logging_config)?;

    // Logging is up now: surface a broken bakery file, then the merge notes
    // and the list of values the user file overrode.
    let merged_config = match merged_config {
        Ok(merged_config) => merged_config,
        Err(e) => {
            log::error!("Failed to load config file {:?}: {e}", main_file);
            return Err(e);
        }
    };
    for note in &merged_config.notes {
        log::warn!("{note}");
    }
    for path in &merged_config.overrides {
        log::info!("User config {user_file:?} overrides bakery config at: {path}");
    }

    let Some(config) = merged_config.config else {
        anyhow::bail!(
            "No config file found (neither {:?} nor {:?})",
            main_file,
            user_file
        );
    };
    if user_file.exists() {
        log::info!("Using main config {main_file:?} merged with user config {user_file:?}");
    }
    Ok((OracleConfig::from_yaml(&config)?, environment))
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
    log_info(level, environment, s.is_ok());
    s
}

/// Report the paths and the log level every run starts with: the first thing a
/// support case asks for. Logged at debug, so a default-level log stays clean.
/// Goes to stdout when there is no log to write to.
fn log_info(level: log::Level, environment: &Env, log_available: bool) {
    let info = create_info_text(&level, environment);
    if log_available {
        log::debug!("{}", info);
    } else {
        println!("{}", info);
    }
}

fn create_info_text(level: &log::Level, environment: &Env) -> String {
    format!(
        "\n  - Log level: {}\n  - Log dir: {}\n  - Temp dir: {}\n  - MK_CONFDIR: {}\n  - MK_LIBDIR: {}",
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
        constants::get_env_value(constants::environment::LIB_DIR_ENV_VAR, "undefined"),
    )
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

#[cfg(unix)]
pub const CLIENT_LIB_NAME: &str = "libclntsh.so";
#[cfg(windows)]
pub const CLIENT_LIB_NAME: &str = "oci.dll";

/// The directory contains an Oracle client library: libclntsh.so* on Unix
/// (installations may ship only the versioned file without the unversioned
/// symlink), oci.dll on Windows.
pub fn contains_oracle_client_lib(dir: &Path) -> bool {
    #[cfg(unix)]
    {
        std::fs::read_dir(dir).is_ok_and(|entries| {
            entries
                .flatten()
                .any(|e| e.file_name().to_string_lossy().starts_with(CLIENT_LIB_NAME))
        })
    }
    #[cfg(windows)]
    {
        dir.join(CLIENT_LIB_NAME).is_file()
    }
}

/// Detects Oracle runtime path using local Oracle instances or environment variables
/// Do not obligated to validate permissions
pub fn detect_host_runtime() -> Option<ClientRuntime> {
    match get_local_instances() {
        Err(e) => {
            log::info!("Local Oracle instances detection failed with {} - can't use them to detect runtime path", &e.to_string());
            find_std_env_var_runtime()
        }
        Ok(instances) if instances.is_empty() => {
            log::info!(
                "Local Oracle instances are not detected - can't use them to detect runtime path"
            );
            find_std_env_var_runtime()
        }
        Ok(locals) => {
            for local in &locals {
                log::debug!(
                    "Trying local Oracle instance {}: home={:?}",
                    local.name,
                    local.home
                );
                // shared libraries live in lib on Unix, DLLs in bin on Windows
                let candidate = local.home.join(if cfg!(windows) { "bin" } else { "lib" });
                if !candidate.is_dir() {
                    log::warn!(
                        "Oracle home {:?} is not suitable: {:?} is not a directory",
                        local.home,
                        candidate
                    );
                    continue;
                }
                if !contains_oracle_client_lib(&candidate) {
                    log::warn!(
                        "Oracle home {:?} is not suitable: {:?} has no {}",
                        local.home,
                        candidate,
                        CLIENT_LIB_NAME
                    );
                    continue;
                }
                return Some(ClientRuntime::in_home(local.home.clone()));
            }
            None
        }
    }
}

fn find_std_env_var_runtime() -> Option<ClientRuntime> {
    const CLIENT_ENV_VAR: &str = "ORACLE_INSTANT_CLIENT";
    if let Ok(env_var) = std::env::var(CLIENT_ENV_VAR) {
        let candidate = PathBuf::from(env_var);
        if !candidate.is_dir() {
            log::warn!("{} path {:?} is not a directory", CLIENT_ENV_VAR, candidate);
            return None;
        }
        if !contains_oracle_client_lib(&candidate) {
            log::warn!(
                "{} path {:?} has no {}",
                CLIENT_ENV_VAR,
                candidate,
                CLIENT_LIB_NAME
            );
            return None;
        }
        return Some(ClientRuntime::instant_client(candidate));
    };

    const ENV_VAR: &str = "ORACLE_HOME";
    if find_env_var_lib_runtime(ENV_VAR).is_some() {
        std::env::var(ENV_VAR)
            .ok()
            .map(PathBuf::from)
            .map(ClientRuntime::in_home)
    } else {
        log::info!("Failed to find local Oracle instances using {ENV_VAR}");
        None
    }
}

pub fn find_env_var_lib_runtime(env_var: &str) -> Option<PathBuf> {
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
        return None;
    }
    if !contains_oracle_client_lib(&candidate) {
        log::warn!(
            "{} path {:?} has no {}",
            env_var,
            candidate,
            CLIENT_LIB_NAME
        );
        return None;
    }
    log::info!("Using {} {:?} for runtime", env_var, candidate);
    Some(candidate)
}

/// The Oracle client shipped with the agent, below the agent's library
/// directory at plugins/packages/mk-oracle. `lib_dir` is what MK_LIBDIR names.
pub fn detect_factory_runtime(lib_dir: &Path) -> Option<PathBuf> {
    let runtime_path = lib_dir.join("plugins/packages/mk-oracle");
    let runtime_path = if cfg!(windows) && runtime_path.join("runtime").is_dir() {
        runtime_path.join("runtime")
    } else {
        runtime_path
    };
    if !runtime_path.is_dir() {
        log::error!("{:?} is not a directory", runtime_path);
        return None;
    }
    if !contains_oracle_client_lib(&runtime_path) {
        log::warn!(
            "{:?} exists but has no {}: not a valid runtime",
            runtime_path,
            CLIENT_LIB_NAME
        );
        return None;
    }
    Some(runtime_path)
}

/// The Oracle client the monitoring process will load, together with the
/// installation it belongs to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClientRuntime {
    /// prepended to LD_LIBRARY_PATH (PATH on Windows)
    pub dir: PathBuf,
    /// ORACLE_HOME: None for an Instant Client, which carries its own message and timezone data
    pub home: Option<PathBuf>,
}

impl ClientRuntime {
    fn instant_client(dir: PathBuf) -> Self {
        Self { dir, home: None }
    }

    /// The client of a full Oracle home, whose location the caller already knows.
    fn in_home(home: PathBuf) -> Self {
        Self {
            dir: home.join(if cfg!(windows) { "bin" } else { "lib" }),
            home: Some(home),
        }
    }
}

/// Searches for the Oracle client to load.
/// The Grid home is a last resort, and only where the configuration leaves the
/// choice open.
pub fn detect_runtime(
    use_host_client: &UseHostClient,
    lib_dir: Option<&Path>,
    grid: Option<&GridInfrastructure>,
) -> Option<ClientRuntime> {
    log::info!("Oracle client selection mode: {use_host_client:?}");
    let factory_runtime = || {
        lib_dir
            .and_then(detect_factory_runtime)
            .map(ClientRuntime::instant_client)
    };
    match use_host_client {
        UseHostClient::Always => detect_host_runtime().or_else(|| grid_runtime(grid)),
        UseHostClient::Never => factory_runtime(),
        UseHostClient::Auto => factory_runtime()
            .or_else(|| {
                log::info!("No client bundled with the agent");
                detect_host_runtime()
            })
            .or_else(|| grid_runtime(grid)),
        // an operator-supplied path is the one case where nothing knows what
        // was pointed at, so it has to be inspected
        UseHostClient::Path(p) => {
            let dir = PathBuf::from(p);
            let home = derive_home_from_runtime_dir(&dir);
            Some(ClientRuntime { dir, home })
        }
    }
    .and_then(validate_runtime)
}

fn validate_runtime(candidate: ClientRuntime) -> Option<ClientRuntime> {
    if !candidate.dir.is_dir() {
        log::error!(
            "Runtime path {:?} is not a directory or missing",
            candidate.dir
        );
        return None;
    }
    if !contains_oracle_client_lib(&candidate.dir) {
        log::error!(
            "Runtime path {:?} has no {}",
            candidate.dir,
            CLIENT_LIB_NAME
        );
        return None;
    }
    match &candidate.home {
        Some(home) => log::info!(
            "Oracle client at {:?}, belonging to the Oracle home {:?}",
            candidate.dir,
            home
        ),
        None => log::info!(
            "Oracle client at {:?}, an Instant Client that needs no {ORACLE_HOME_ENV_VAR}",
            candidate.dir
        ),
    }
    Some(candidate)
}

/// The client of the Grid home named by the Oracle Local Registry. Grid
/// Infrastructure stops maintaining oratab from 12.2 on, so on such a node this
/// can be the only Oracle client present.
fn grid_runtime(grid: Option<&GridInfrastructure>) -> Option<ClientRuntime> {
    let crs_home = grid?.crs_home();
    log::debug!("Trying the Grid home {crs_home:?}");
    Some(ClientRuntime::in_home(crs_home.to_path_buf()))
}

#[cfg(windows)]
pub const RUNTIME_PATH_ENV_VAR: &str = "PATH";
#[cfg(unix)]
pub const RUNTIME_PATH_ENV_VAR: &str = "LD_LIBRARY_PATH";

static DEFAULT_ENV_VAR: LazyLock<EnvVarName> =
    LazyLock::new(|| EnvVarName::from(RUNTIME_PATH_ENV_VAR.to_string()));

#[cfg(windows)]
const ENV_VAR_SEP: &str = ";";
#[cfg(unix)]
const ENV_VAR_SEP: &str = ":";

pub const ORACLE_HOME_ENV_VAR: &str = "ORACLE_HOME";

/// The environment the monitoring process is spawned with: computed by
/// detect_runtime_env, exported by apply_runtime_env and rendered for
/// --find-runtime by format_runtime_env.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RuntimeEnv {
    /// directory to prepend to LD_LIBRARY_PATH (PATH on Windows)
    pub runtime_dir: Option<PathBuf>,
    /// effective ORACLE_HOME of the spawned process, if any
    pub oracle_home: Option<PathBuf>,
}

/// Why no Oracle client runtime could be prepared.
#[derive(Debug, PartialEq)]
pub enum RuntimeError {
    NoConfig,
    NotFound,
    Rejected { dir: PathBuf },
}

impl std::fmt::Display for RuntimeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::NoConfig => write!(f, "No Config"),
            Self::NotFound => write!(f, "No Oracle client runtime found"),
            Self::Rejected { dir } => write!(
                f,
                "{dir:?} - Execution is blocked because you try to load an unsafe Oracle client \
                 library as a privileged user. Please, disable write access to the files by \
                 non-privileged users."
            ),
        }
    }
}

impl std::error::Error for RuntimeError {}

/// Detect the oracle client and the ORACLE_HOME that comes with it.
/// ORACLE_HOME can be overridden by an inherited env var, while the client
/// is always set based on the config and the search.
pub fn detect_runtime_env(config: &OracleConfig) -> Result<RuntimeEnv, RuntimeError> {
    const LIB_DIR: &str = constants::environment::LIB_DIR_ENV_VAR;
    let lib_dir = std::env::var(LIB_DIR)
        .inspect_err(|_| log::warn!("{LIB_DIR} is not set"))
        .ok()
        .map(PathBuf::from);
    let inherited = std::env::var(ORACLE_HOME_ENV_VAR)
        .ok()
        .filter(|v| !v.is_empty());
    let ora_sql = config.ora_sql().ok_or(RuntimeError::NoConfig)?;
    let client = detect_runtime(
        ora_sql.options().use_host_client(),
        lib_dir.as_deref(),
        ora_sql.conn().grid(),
    )
    .ok_or(RuntimeError::NotFound)?;
    if !runtime_permissions_ok(&client, ora_sql.options()) {
        return Err(RuntimeError::Rejected { dir: client.dir });
    }
    Ok(RuntimeEnv {
        oracle_home: effective_oracle_home(Some(&client), inherited),
        runtime_dir: Some(client.dir),
    })
}

fn runtime_permissions_ok(runtime: &ClientRuntime, options: &Options) -> bool {
    if validate_permissions(
        &runtime.dir,
        options.permissions_check(),
        options.permissions_safe_entries(),
    ) {
        return true;
    }
    log::error!("Runtime path {:?} has wrong permissions", runtime.dir);
    false
}

pub fn effective_oracle_home(
    client: Option<&ClientRuntime>,
    inherited: Option<String>,
) -> Option<PathBuf> {
    if let Some(current) = inherited {
        log::info!("{ORACLE_HOME_ENV_VAR} is already set to {current}, keeping it");
        return Some(PathBuf::from(current));
    }
    if cfg!(windows) {
        return None;
    }
    client?.home.clone()
}

/// A full Oracle home (server or full client) ships the client library in
/// <home>/lib and its message/timezone data in <home>/oracore; OCI resolves
/// the latter only via ORACLE_HOME (else ORA-01804). Instant Client bundles
/// that data, needs no ORACLE_HOME and has no oracore sibling of its lib dir.
fn derive_home_from_runtime_dir(runtime_dir: &Path) -> Option<PathBuf> {
    if runtime_dir.file_name() != Some(std::ffi::OsStr::new("lib")) {
        log::debug!("{runtime_dir:?} is not the lib dir of an Oracle home");
        return None;
    }
    let home = runtime_dir.parent()?;
    if !home.join("oracore").is_dir() {
        log::debug!("{home:?} has no oracore: not a full Oracle home");
        return None;
    }
    Some(home.to_path_buf())
}

/// Exports the runtime environment to the process environment: prepends the
/// runtime directory to LD_LIBRARY_PATH (PATH on Windows) and sets ORACLE_HOME.
/// Re-exporting an inherited ORACLE_HOME writes the value it already has.
/// Returns the old content of the modified path variable so that reset_env
/// can restore it after the spawn; None if there is no runtime.
pub fn apply_runtime_env(
    runtime_env: &RuntimeEnv,
    path_var: Option<EnvVarName>,
    home_var: Option<EnvVarName>,
) -> Option<PathBuf> {
    let runtime_dir = runtime_env.runtime_dir.as_ref()?;
    let path_var = path_var.unwrap_or(DEFAULT_ENV_VAR.clone());
    let old_content = std::env::var(path_var.to_str()).ok().unwrap_or_default();
    log::debug!("Current {path_var}={old_content}");
    let mut new_content = runtime_dir.clone().into_os_string();
    if !old_content.is_empty() {
        new_content.push(ENV_VAR_SEP);
        new_content.push(&old_content);
    }
    unsafe {
        std::env::set_var(path_var.to_str(), &new_content);
    }

    if let Some(home) = &runtime_env.oracle_home {
        let home_var =
            home_var.unwrap_or_else(|| EnvVarName::from(ORACLE_HOME_ENV_VAR.to_string()));
        log::info!("Exporting {home_var}={:?}", home);
        unsafe {
            std::env::set_var(home_var.to_str(), home);
        }
    }
    Some(PathBuf::from(old_content))
}

/// Renders the runtime environment for --find-runtime as shell-sourceable
/// KEY=VALUE lines; current is the present content of LD_LIBRARY_PATH (PATH
/// on Windows). Variables without a value are omitted.
pub fn format_runtime_env(runtime_env: &RuntimeEnv, current: &str) -> String {
    let mut output = String::new();
    if let Some(runtime_dir) = &runtime_env.runtime_dir {
        output.push_str(&format!("{RUNTIME_PATH_ENV_VAR}={}", runtime_dir.display()));
        if !current.is_empty() {
            output.push_str(&format!("{ENV_VAR_SEP}{current}"));
        }
        output.push('\n');
    }
    if let Some(home) = &runtime_env.oracle_home {
        output.push_str(&format!("{ORACLE_HOME_ENV_VAR}={}\n", home.display()));
    }
    output
}

pub fn reset_env(old_path: &Path, mut_env: Option<String>) {
    let mutable_var = mut_env.unwrap_or(DEFAULT_ENV_VAR.to_string());
    unsafe {
        std::env::set_var(mutable_var, old_path);
    }
}

/// Validate permissions of the given path before we load an Oracle client
/// library from it. Dispatches to the platform-specific implementation.
///
/// On Unix the path, its direct entries and its parent directories must only be
/// writable by root, by the conventional Oracle owner `oracle:oinstall`, or by a
/// user or group listed in `safe_entries`, whenever the plugin runs as root. On
/// Windows the path's DACL must grant write access only to privileged SIDs
/// (SYSTEM, built-in Administrators, Domain Admins, Enterprise Admins) or to a
/// listed safe entry, whenever the plugin runs elevated. In both cases a
/// non-privileged caller always passes, and `check` turns the validation off
/// entirely.
pub fn validate_permissions(p: &Path, check: bool, safe_entries: &[String]) -> bool {
    #[cfg(unix)]
    {
        crate::permissions_linux::validate(p, check, safe_entries)
    }
    #[cfg(windows)]
    {
        crate::permissions_windows::validate(p, check, safe_entries)
    }
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

& $env:MK_PLUGINSDIR\packages\mk-oracle\mk-oracle.exe -c $env:MK_CONFDIR/mk-oracle.yml "#,
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

"${{MK_LIBDIR}}/plugins/packages/mk-oracle/mk-oracle" -c "${{MK_CONFDIR}}/mk-oracle.yml" "#,
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

pub fn create_plugin(name: &str, dir: &Path, cache_age: Option<u32>, cmd_line: &str) -> bool {
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

fn build_plugin_list(
    cache_age: u32,
    custom_metrics_cache_age: u32,
) -> Vec<(String, Option<u32>, &'static str)> {
    let ext = if cfg!(windows) { ".ps1" } else { "" };
    let mut plugins = vec![
        ("oracle_unified_sync", None, "--filter sync"),
        ("oracle_unified_async", Some(cache_age), "--filter async"),
    ];
    if cache_age != custom_metrics_cache_age {
        plugins.push((
            "oracle_unified_async_custom_metrics",
            Some(custom_metrics_cache_age),
            "--filter async-custom-metrics",
        ));
    }
    plugins
        .into_iter()
        .map(|(base, age, filter)| (format!("{base}{ext}"), age, filter))
        .collect()
}

pub fn create_plugins(p: &Path, cache_age: u32, custom_metrics_cache_age: u32) -> i32 {
    log::info!("PLUGINS GENERATED for path {p:?}");
    if !p.is_dir() {
        return 1;
    }
    log::info!("PLUGINS DIR={}", p.display());

    for (name, age, filter) in build_plugin_list(cache_age, custom_metrics_cache_age) {
        setup::create_plugin(&name, p, age, filter);
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

    #[test]
    fn test_build_plugin_list_same_cache_age() {
        let plugins = build_plugin_list(600, 600);
        assert_eq!(plugins.len(), 2);
        assert_eq!(plugins[0].2, "--filter sync");
        assert_eq!(plugins[1].2, "--filter async");
        assert_eq!(plugins[1].1, Some(600));
    }

    #[test]
    fn test_build_plugin_list_different_cache_age() {
        let plugins = build_plugin_list(600, 900);
        assert_eq!(plugins.len(), 3);
        assert_eq!(plugins[2].2, "--filter async-custom-metrics");
        assert_eq!(plugins[2].1, Some(900));
    }

    #[cfg(unix)]
    #[test]
    fn test_build_plugin_list_names_unix() {
        let plugins = build_plugin_list(100, 200);
        assert_eq!(plugins[0].0, "oracle_unified_sync");
        assert_eq!(plugins[1].0, "oracle_unified_async");
        assert_eq!(plugins[2].0, "oracle_unified_async_custom_metrics");
    }

    #[test]
    fn test_format_runtime_env_full() {
        let runtime_env = RuntimeEnv {
            runtime_dir: Some(PathBuf::from("/runtime/lib")),
            oracle_home: Some(PathBuf::from("/oracle/home")),
        };
        assert_eq!(
            format_runtime_env(&runtime_env, "/existing/path"),
            format!(
                "{RUNTIME_PATH_ENV_VAR}=/runtime/lib{ENV_VAR_SEP}/existing/path\nORACLE_HOME=/oracle/home\n"
            )
        );
    }

    #[test]
    fn test_format_runtime_env_empty_current_has_no_separator() {
        let runtime_env = RuntimeEnv {
            runtime_dir: Some(PathBuf::from("/runtime/lib")),
            oracle_home: None,
        };
        assert_eq!(
            format_runtime_env(&runtime_env, ""),
            format!("{RUNTIME_PATH_ENV_VAR}=/runtime/lib\n")
        );
    }

    #[test]
    fn test_format_runtime_env_inherited_home() {
        let runtime_env = RuntimeEnv {
            runtime_dir: Some(PathBuf::from("/runtime/lib")),
            oracle_home: Some(PathBuf::from("/inherited/home")),
        };
        assert_eq!(
            format_runtime_env(&runtime_env, ""),
            format!("{RUNTIME_PATH_ENV_VAR}=/runtime/lib\nORACLE_HOME=/inherited/home\n")
        );
    }

    #[test]
    fn test_format_runtime_env_nothing_detected() {
        assert_eq!(format_runtime_env(&RuntimeEnv::default(), "/some/path"), "");
    }
}
