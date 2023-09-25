// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::args::Args;
use crate::config::CheckConfig;
use crate::constants;
use clap::Parser;
use flexi_logger::{self, FileSpec, LogSpecification};
use std::env::ArgsOs;
use std::path::Path;

pub enum SendTo {
    Null,
    Stderr,
    Stdout,
}

pub fn init(args: ArgsOs) -> anyhow::Result<()> {
    let args = Args::parse_from(args);

    init_logging(
        &args.logging_level(),
        args.log_dir.as_deref(),
        if args.display_log {
            SendTo::Stderr
        } else {
            SendTo::Null
        },
    )?;

    if let Some(config_file) = args.config_file {
        let _ = CheckConfig::load_file(&config_file)?;
    }

    Ok(())
}

fn init_logging(
    level: &str,
    log_dir: Option<&Path>,
    send_to: SendTo,
) -> Result<flexi_logger::LoggerHandle, flexi_logger::FlexiLoggerError> {
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

    logger.format(flexi_logger::detailed_format).start()
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
