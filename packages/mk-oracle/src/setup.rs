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
use crate::config::merge;
use crate::config::system::{Logging, SystemConfig};
use crate::config::OracleConfig;
use crate::constants::{get_user_config_file, RUNTIME_DIR};
use crate::platform::{get_local_instances, registry};
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
pub fn detect_host_runtime() -> Option<PathBuf> {
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
                log::info!(
                    "Try to find runtime using local Oracle instance: name={}, home={:?}, base={:?}",
                    local.name,
                    local.home,
                    local.base
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
                return Some(candidate);
            }
            None
        }
    }
}

fn find_std_env_var_runtime() -> Option<PathBuf> {
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
        return Some(candidate);
    };

    const ENV_VAR: &str = "ORACLE_HOME";
    if let Some(runtime) = find_env_var_lib_runtime(ENV_VAR) {
        Some(runtime)
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

/// Finds runtime dir using MK_LIBDIR or custom env var
/// usually at: MK_LIBDIR/plugins/packages/mk-oracle
/// Returns None if env var is not set or path is not a directory
pub fn detect_factory_runtime(env_var: Option<String>) -> Option<PathBuf> {
    let env_var = env_var.unwrap_or_else(|| constants::environment::LIB_DIR_ENV_VAR.to_string());
    let lib_dir = match std::env::var(&env_var) {
        Ok(v) => v,
        Err(_) => {
            log::warn!("{:?} is not set", &env_var);
            return None;
        }
    };
    let runtime_path = if env_var == constants::environment::LIB_DIR_ENV_VAR {
        RUNTIME_DIR.to_path_buf()
    } else {
        Path::new(&lib_dir).join("plugins/packages/mk-oracle")
    };

    let runtime_path = if cfg!(windows) && runtime_path.join("runtime").is_dir() {
        runtime_path.join("runtime")
    } else {
        runtime_path
    };
    if !runtime_path.is_dir() {
        log::error!(
            "{:?} is set but {:?} is not a directory",
            &env_var,
            runtime_path
        );
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

/// Detects Oracle runtime path using local Oracle instances or environment variables
pub fn detect_runtime(use_host_client: &UseHostClient, env_var: Option<String>) -> Option<PathBuf> {
    match use_host_client {
        UseHostClient::Always => detect_host_runtime(),
        UseHostClient::Never => detect_factory_runtime(env_var),
        UseHostClient::Auto => detect_factory_runtime(env_var).or_else(|| {
            log::info!("Factory setup not found");
            detect_host_runtime()
        }),
        UseHostClient::Path(p) => Some(PathBuf::from(p)),
    }
    .and_then(|p| {
        if !p.is_dir() {
            log::error!("Runtime path {:?} is not a directory or missing", p);
            return None;
        }
        if !contains_oracle_client_lib(&p) {
            log::error!("Runtime path {:?} has no {}", p, CLIENT_LIB_NAME);
            return None;
        }
        log::info!("Runtime detected at {:?}", p);
        Some(p)
    })
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

/// The ORACLE_HOME the spawned monitoring process will see: either inherited
/// from the current environment or derived from the local instances (oratab).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OracleHome {
    Inherited(PathBuf),
    Derived(PathBuf),
}

impl OracleHome {
    pub fn path(&self) -> &Path {
        match self {
            OracleHome::Inherited(path) | OracleHome::Derived(path) => path,
        }
    }
}

/// The environment the monitoring process is spawned with: computed by
/// detect_runtime_env, exported by apply_runtime_env and rendered for
/// --find-runtime by format_runtime_env.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct RuntimeEnv {
    /// directory to prepend to LD_LIBRARY_PATH (PATH on Windows)
    pub runtime_dir: Option<PathBuf>,
    /// effective ORACLE_HOME of the spawned process, if any
    pub oracle_home: Option<OracleHome>,
}

/// Computes the runtime environment without touching the process environment.
/// Must run before apply_runtime_env: runtime detection reads the current
/// ORACLE_HOME/ORACLE_INSTANT_CLIENT values.
pub fn detect_runtime_env(config: &OracleConfig) -> RuntimeEnv {
    let runtime_dir = detect_runtime_dir(config, None, true);
    let oracle_home = detect_oracle_home(config, None, None, runtime_dir.as_deref());
    RuntimeEnv {
        runtime_dir,
        oracle_home,
    }
}

/// Detects the directory with the Oracle client runtime to be prepended to
/// LD_LIBRARY_PATH (PATH on Windows) using config and, by default, MK_LIBDIR.
/// May validate permissions of the detected path: returns None if they are
/// not correct.
pub fn detect_runtime_dir(
    config: &OracleConfig,
    mk_lib_dir: Option<String>,
    check_permissions: bool,
) -> Option<PathBuf> {
    let use_host_client: UseHostClient = config.ora_sql()?.options().use_host_client().clone();
    log::info!("Use host client {:?}", use_host_client);
    let runtime = detect_runtime(&use_host_client, mk_lib_dir)?;
    if !check_permissions {
        log::info!("Skip permissions check for runtime path {:?}", runtime);
        return Some(runtime);
    }
    let options = if cfg!(windows) {
        config
            .ora_sql()
            .map(|c| c.options().clone())
            .unwrap_or_default()
    } else {
        crate::config::options::Options::default()
    };
    if !validate_permissions(
        &runtime,
        options.permissions_check(),
        options.permissions_safe_entries(),
    ) {
        log::error!("Runtime path {:?} has wrong permissions", runtime);
        return None;
    }
    Some(runtime)
}

/// A full Oracle home (server or full client) ships the client library in
/// <home>/lib and its message/timezone data in <home>/oracore; OCI resolves
/// the latter only via ORACLE_HOME (else ORA-01804). Instant Client bundles
/// that data, needs no ORACLE_HOME and has no oracore sibling of its lib dir.
fn derive_home_from_runtime_dir(runtime_dir: &Path) -> Option<PathBuf> {
    if runtime_dir.file_name() != Some(std::ffi::OsStr::new("lib")) {
        log::info!(
            "Runtime dir {:?} is not a lib dir of an Oracle home: treating as Instant Client, {ORACLE_HOME_ENV_VAR} stays unset",
            runtime_dir
        );
        return None;
    }
    let home = runtime_dir.parent()?;
    if !home.join("oracore").is_dir() {
        log::info!(
            "Runtime dir {:?} has no oracore next to it: treating as Instant Client, {ORACLE_HOME_ENV_VAR} stays unset",
            runtime_dir
        );
        return None;
    }
    log::info!(
        "Deriving {ORACLE_HOME_ENV_VAR} {:?} from configured client runtime dir {:?}",
        home,
        runtime_dir
    );
    Some(home.to_path_buf())
}

/// Determines the ORACLE_HOME the spawned monitoring process will see: the
/// value already set in the environment wins; otherwise (on Unix) it is
/// derived - for an explicit use_host_client path from the parent of the
/// runtime dir when that is the lib dir of a full Oracle home, for auto or
/// always from the home of the first local instance (as listed in oratab)
/// which exists and has a lib dir. Windows never derives: OCI is served by
/// the registry there.
pub fn detect_oracle_home(
    config: &OracleConfig,
    custom_path: Option<String>,
    home_var: Option<EnvVarName>,
    runtime_dir: Option<&Path>,
) -> Option<OracleHome> {
    let env_var = home_var.unwrap_or_else(|| EnvVarName::from(ORACLE_HOME_ENV_VAR.to_string()));
    let current = std::env::var(env_var.to_str()).unwrap_or_default();
    if !current.is_empty() {
        log::info!("{env_var} is already set to {current}, keeping it");
        return Some(OracleHome::Inherited(PathBuf::from(current)));
    }

    if cfg!(windows) {
        log::debug!("{ORACLE_HOME_ENV_VAR} based setup is not supported on Windows");
        return None;
    }

    let use_host_client: UseHostClient = config.ora_sql()?.options().use_host_client().clone();
    match use_host_client {
        UseHostClient::Always | UseHostClient::Auto => {}
        UseHostClient::Path(_) => {
            return derive_home_from_runtime_dir(runtime_dir?).map(OracleHome::Derived);
        }
        UseHostClient::Never => {
            log::info!("Use host client is Never: skipping {ORACLE_HOME_ENV_VAR} based setup");
            return None;
        }
    }

    let locals = match registry::get_instances(custom_path) {
        Ok(locals) if !locals.is_empty() => locals,
        Ok(_) => {
            log::info!("Local Oracle instances are not detected - can't use them to set {env_var}");
            return None;
        }
        Err(e) => {
            log::info!(
                "Local Oracle instances detection failed with {e} - can't use them to set {env_var}"
            );
            return None;
        }
    };

    let home = locals.into_iter().find_map(|local| {
        log::info!(
            "Checking Oracle home {:?} of local instance {}",
            local.home,
            local.name
        );
        if !local.home.is_dir() {
            log::warn!("Oracle home {:?} doesn't exist", local.home);
            return None;
        }
        let lib_dir = local.home.join("lib");
        if lib_dir.is_dir() {
            Some(local.home)
        } else {
            log::warn!("Oracle home {:?} has no lib dir", local.home);
            None
        }
    });

    if home.is_none() {
        log::info!("No suitable Oracle home found to set {env_var}");
    }
    home.map(OracleHome::Derived)
}

/// Exports the runtime environment to the process environment: prepends the
/// runtime directory to LD_LIBRARY_PATH (PATH on Windows) and sets a derived
/// ORACLE_HOME (an inherited one is already in the environment and left untouched).
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
    log::info!("Current {path_var}={old_content}");
    let mut new_content = runtime_dir.clone().into_os_string();
    new_content.push(ENV_VAR_SEP);
    new_content.push(&old_content);
    unsafe {
        std::env::set_var(path_var.to_str(), &new_content);
    }

    if let Some(OracleHome::Derived(home)) = &runtime_env.oracle_home {
        let home_var =
            home_var.unwrap_or_else(|| EnvVarName::from(ORACLE_HOME_ENV_VAR.to_string()));
        log::info!("Setting {home_var} to {:?}", home);
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
        output.push_str(&format!(
            "{ORACLE_HOME_ENV_VAR}={}\n",
            home.path().display()
        ));
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
/// On Linux the path and, if it is a directory, its subtree must be
/// only-root-modifiable whenever the plugin runs as root. On Windows the
/// path's DACL must grant write access only to privileged SIDs (SYSTEM,
/// built-in Administrators, Domain Admins, Enterprise Admins) whenever the
/// plugin runs elevated. In both cases a non-privileged caller always
/// passes.
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
            oracle_home: Some(OracleHome::Derived(PathBuf::from("/oracle/home"))),
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
            oracle_home: Some(OracleHome::Inherited(PathBuf::from("/inherited/home"))),
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
