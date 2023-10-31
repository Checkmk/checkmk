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
use std::path::Path;

pub enum SendTo {
    Null,
    Stderr,
    Stdout,
}

pub fn init(args: ArgsOs) -> Result<CheckConfig> {
    let args = Args::parse_from(args);
    init_logging_from_args(&args)?;
    get_check_config(&args)
}

fn init_logging_from_args(args: &Args) -> Result<()> {
    let level = &args.logging_level();
    let log_dir = args.log_dir.as_deref();
    let send_to = if args.display_log {
        SendTo::Stderr
    } else {
        SendTo::Null
    };

    init_logging(level, log_dir, send_to)?;
    Ok(())
}

fn get_check_config(args: &Args) -> Result<CheckConfig> {
    let file = match args.config_file {
        Some(ref config_file) => config_file,
        None => &constants::DEFAULT_CONFIG_FILE,
    };

    CheckConfig::load_file(file)
}

fn init_logging(
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
}
