// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::args::Args;
use crate::config::CheckConfig;
use crate::constants;
use anyhow::Result;
use clap::Parser;
use flexi_logger::{self, FileSpec, LogSpecification};
use std::env::ArgsOs;
use std::path::{Path, PathBuf};

#[derive(Default, Clone, Debug)]
pub struct Env {
    /// guaranteed to contain dir or None
    temp_dir: Option<PathBuf>,
    /// guaranteed to contain dir or None
    log_dir: Option<PathBuf>,
}

impl Env {
    pub fn new(args: &Args) -> Self {
        let log_dir = Env::build_dir(&args.log_dir, &constants::ENV_LOG_DIR.as_deref());
        let temp_dir = Env::build_dir(&args.temp_dir, &constants::ENV_TEMP_DIR.as_deref());
        Self { temp_dir, log_dir }
    }

    /// guaranteed to return temp dir or None
    pub fn temp_dir(&self) -> Option<&Path> {
        self.temp_dir.as_deref()
    }

    /// guaranteed to return log dir or None
    pub fn log_dir(&self) -> Option<&Path> {
        self.log_dir.as_deref()
    }

    /// guaranteed to return cache dir or None
    pub fn cache_dir(&self) -> Option<PathBuf> {
        self.temp_dir().map(|temp_dir| temp_dir.join("cache"))
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

    pub fn calc_cache_sub_dir(&self, sub: &str) -> Option<PathBuf> {
        self.cache_dir().map(|d| d.join(sub))
    }

    pub fn obtain_cache_sub_dir(&self, sub: &str) -> Option<PathBuf> {
        if let Some(cache_dir) = self.calc_cache_sub_dir(sub) {
            if cache_dir.is_dir() {
                log::info!("Cache dir exists");
                Some(cache_dir)
            } else if cache_dir.exists() {
                log::error!("Cache dir exists but isn't usable(not a directory)");
                None
            } else {
                log::info!("Cache dir to be created");
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
    let environment = Env::new(&args);
    init_logging(&args, &environment)?;
    Ok((get_check_config(&args)?, environment))
}

fn init_logging(args: &Args, environment: &Env) -> Result<()> {
    let level = &args.logging_level();
    let send_to = if args.display_log {
        SendTo::Stderr
    } else {
        SendTo::Null
    };

    apply_logging_parameters(level, environment.log_dir(), send_to)?;
    Ok(())
}

fn get_check_config(args: &Args) -> Result<CheckConfig> {
    let file = match args.config_file {
        Some(ref config_file) => config_file,
        None => &constants::DEFAULT_CONFIG_FILE,
    };
    log::info!("Using config file: {}", file.display());
    CheckConfig::load_file(file)
}

fn apply_logging_parameters(
    level: &str,
    log_dir: Option<&Path>,
    send_to: SendTo,
) -> Result<flexi_logger::LoggerHandle> {
    let spec = LogSpecification::parse(level)?;
    let mut logger = flexi_logger::Logger::with(spec);

    logger = if let Some(dir) = log_dir {
        logger
            .log_to_file(make_log_file_spec(dir))
            .rotate(
                constants::log::FILE_MAX_SIZE,
                constants::log::FILE_NAMING,
                constants::log::FILE_CLEANUP,
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

    Ok(logger.format(flexi_logger::detailed_format).start()?)
}

fn make_log_file_spec(log_dir: &Path) -> FileSpec {
    FileSpec::default()
        .directory(log_dir.to_owned())
        .suppress_timestamp()
        .basename("check-sql")
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
            PathBuf::from("_").join("check-sql.log")
        );
    }
    #[test]
    fn test_env_dir_exist() {
        let args = Args {
            log_dir: Some(PathBuf::from(".")),
            temp_dir: Some(PathBuf::from(".")),
            ..Default::default()
        };
        let e = Env::new(&args);
        assert_eq!(e.log_dir(), Some(Path::new(".")));
        assert_eq!(e.temp_dir(), Some(Path::new(".")));
        assert_eq!(e.cache_dir(), Some(PathBuf::from(".").join("cache")));
        assert_eq!(
            e.calc_cache_sub_dir("aa"),
            Some(PathBuf::from(".").join("cache").join("aa"))
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
        assert!(e.cache_dir().is_none());
        assert!(e.calc_cache_sub_dir("aa").is_none());
        assert!(e.obtain_cache_sub_dir("a").is_none());
    }
}
