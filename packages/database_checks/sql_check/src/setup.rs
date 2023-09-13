// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::constants;
use flexi_logger::{self, FileSpec};
use std::path::Path;

pub enum SendTo {
    Null,
    Stderr,
    Stdout,
}

pub fn init_logging(
    level: &str,
    log_dir: Option<&Path>,
    send_to: SendTo,
) -> Result<flexi_logger::LoggerHandle, flexi_logger::FlexiLoggerError> {
    let mut logger = flexi_logger::Logger::try_with_env_or_str(level)?;

    if let Some(dir) = log_dir {
        logger = logger
            .log_to_file(make_log_file_spec(dir))
            .rotate(
                constants::log::FILE_MAX_SIZE,
                constants::log::FILE_NAMING,
                constants::log::FILE_CLEANUP,
            )
            .append();
    }
    logger = match send_to {
        SendTo::Null => logger,
        SendTo::Stderr => logger.log_to_stderr(),
        SendTo::Stdout => logger.log_to_stdout(),
    };

    logger.format(flexi_logger::detailed_format).start()
}

fn make_log_file_spec(log_dir: &Path) -> FileSpec {
    FileSpec::default()
        .directory(log_dir.to_owned())
        .suppress_timestamp()
        .basename("sql_check")
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
            PathBuf::from("_").join("sql_check.log")
        );
    }
}
