// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::args::Args;
use crate::config::system::{Logging, SystemConfig};
use crate::config::CheckConfig;
use crate::constants;
use anyhow::Result;
use clap::Parser;
use flexi_logger::{self, Cleanup, Criterion, DeferredNow, FileSpec, LogSpecification, Record};
use std::env::ArgsOs;
use std::path::{Path, PathBuf};

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
}

impl Env {
    pub fn new(args: &Args) -> Self {
        let log_dir = Env::build_dir(&args.log_dir, &constants::ENV_LOG_DIR.as_deref());
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
        }
    }

    /// guaranteed to return temp dir or None
    pub fn temp_dir(&self) -> Option<&Path> {
        self.temp_dir.as_deref()
    }

    /// guaranteed to return log dir or None
    pub fn log_dir(&self) -> Option<&Path> {
        self.log_dir.as_deref()
    }

    /// guaranteed to return log dir or None
    pub fn state_dir(&self) -> Option<&Path> {
        self.state_dir.as_deref()
    }

    pub fn disable_caching(&self) -> bool {
        self.disable_caching
    }

    pub fn detect_only(&self) -> bool {
        self.detect_only
    }

    /// guaranteed to return cache dir or None
    pub fn base_cache_dir(&self) -> Option<PathBuf> {
        self.state_dir()
            .map(|state_dir| state_dir.join("mk-sql-cache"))
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

    pub fn calc_cache_sub_dir(&self, sub_dir: &str) -> Option<PathBuf> {
        self.base_cache_dir().map(|d| d.join(sub_dir))
    }

    pub fn obtain_cache_sub_dir(&self, sub_dir: &str) -> Option<PathBuf> {
        if let Some(cache_dir) = self.calc_cache_sub_dir(sub_dir) {
            if cache_dir.is_dir() {
                log::info!("Cache dir exists {:?}", cache_dir);
                Some(cache_dir)
            } else if cache_dir.exists() {
                log::error!("Cache dir exists but isn't usable(not a directory)");
                None
            } else {
                log::info!("Cache dir {:?} to be created", cache_dir);
                std::fs::create_dir_all(&cache_dir).unwrap_or_else(|e| {
                    log::error!("Failed to create root cache dir: {e}");
                });
                cache_dir.is_dir().then_some(cache_dir)
            }
        } else {
            log::error!("Cache dir exists but is not usable");
            None
        }
    }
}

pub enum SendTo {
    Null,
    Stderr,
    Stdout,
}

pub fn init(args: ArgsOs) -> Result<(CheckConfig, Env)> {
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

fn get_check_config(file: &Path) -> Result<CheckConfig> {
    log::info!("Using config file: {}", file.display());

    CheckConfig::load_file(file)
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

fn dec_level(level: log::Level) -> log::Level {
    match level {
        log::Level::Error => log::Level::Error,
        log::Level::Warn => log::Level::Error,
        log::Level::Info => log::Level::Warn,
        log::Level::Debug => log::Level::Info,
        log::Level::Trace => log::Level::Debug,
    }
}

fn apply_logging_parameters(
    level: log::Level,
    log_dir: Option<&Path>,
    send_to: SendTo,
    logging: Logging,
) -> Result<flexi_logger::LoggerHandle> {
    let spec = LogSpecification::parse(format!(
        "{}, tiberius={}, odbc={}",
        level.as_str().to_lowercase(),
        dec_level(level).as_str().to_lowercase(),
        dec_level(dec_level(level)).as_str().to_lowercase(),
    ))?;
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
        .basename("mk-sql")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn test_spec() {
        let spec = make_log_file_spec(&PathBuf::from("_"));
        assert_eq!(spec.as_pathbuf(None), PathBuf::from("_").join("mk-sql.log"));
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
        assert_eq!(
            e.base_cache_dir(),
            Some(PathBuf::from(".").join("mk-sql-cache"))
        );
        assert_eq!(
            e.calc_cache_sub_dir("aa"),
            Some(PathBuf::from(".").join("mk-sql-cache").join("aa"))
        );
    }
    #[test]
    fn test_env_dir_absent() {
        let args = Args {
            log_dir: Some(PathBuf::from("weird-dir")),
            temp_dir: Some(PathBuf::from("burr-dir")),
            ..Default::default()
        };
        let e = Env::new(&args);
        assert!(e.log_dir().is_none());
        assert!(e.temp_dir().is_none());
        assert!(e.base_cache_dir().is_none());
        assert!(e.calc_cache_sub_dir("aa").is_none());
        assert!(e.obtain_cache_sub_dir("a").is_none());
    }
    #[test]
    fn test_create_info_text() {
        assert_eq!(
            create_info_text(&log::Level::Debug, &Env::new(&Args::default())),
            r#"
  - Log level: DEBUG
  - Log dir: 
  - Temp dir: .
  - MK_CONFDIR: undefined"#
        );
    }
}
