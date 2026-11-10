// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The log file of the controller on Linux, written in addition to stderr.

use crate::constants;
use anyhow::{anyhow, bail, Context, Result as AnyhowResult};
use flexi_logger::writers::{FileLogWriter, LogWriter};
use flexi_logger::{DeferredNow, FileSpec};
use log::{LevelFilter, Record};
use nix::unistd;
use std::fs::OpenOptions;
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::path::Path;
use std::sync::OnceLock;

pub const LEVEL: LevelFilter = LevelFilter::Info;

/// The lines repeat parts of the update state, which other users must not read
/// either.
const MODE: u32 = 0o600;

static FILE: OnceLock<FileLogWriter> = OnceLock::new();

/// The logger's writer, which drops every record until [`open`] has run.
///
/// The logger has to start before the controller switches to the agent user.
/// Only that switch decides where the file lives and who owns it.
pub struct LogFile;

impl LogWriter for LogFile {
    fn write(&self, now: &mut DeferredNow, record: &Record) -> std::io::Result<()> {
        FILE.get().map_or(Ok(()), |file| file.write(now, record))
    }

    fn flush(&self) -> std::io::Result<()> {
        FILE.get().map_or(Ok(()), |file| file.flush())
    }
}

pub fn open(path: &Path) -> AnyhowResult<()> {
    FILE.set(writer(path)?)
        .map_err(|_| anyhow!("The log file is already open"))
}

fn writer(path: &Path) -> AnyhowResult<FileLogWriter> {
    let dir = path.parent().context("The log file has no directory")?;
    let dir_metadata = std::fs::symlink_metadata(dir)?;
    // The owner of the directory could redirect the writes with a symlink. That
    // matters when the daemon runs as root.
    if !dir_metadata.is_dir() || dir_metadata.uid() != unistd::geteuid().as_raw() {
        bail!("{dir:?} is not a directory owned by the current user");
    }
    // The writer cannot give the file a mode, so the file is created here.
    OpenOptions::new()
        .create(true)
        .append(true)
        .mode(MODE)
        .open(path)?;
    Ok(FileLogWriter::builder(FileSpec::try_from(path)?)
        .format(flexi_logger::detailed_format)
        .append()
        .max_level(LEVEL)
        .rotate(
            constants::log::FILE_MAX_SIZE,
            constants::log::FILE_NAMING,
            constants::log::FILE_CLEANUP,
        )
        .try_build()?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;
    use std::path::PathBuf;

    fn write(writer: &FileLogWriter, level: log::Level, message: &str) {
        writer
            .write(
                &mut DeferredNow::new(),
                &Record::builder()
                    .args(format_args!("{message}"))
                    .level(level)
                    .module_path(Some("cmk_agent_ctl::updater"))
                    .file(Some("src/updater.rs"))
                    .line(Some(42))
                    .build(),
            )
            .unwrap();
    }

    fn write_600_kb(writer: &FileLogWriter) {
        let line = "x".repeat(1000);
        for _ in 0..600 {
            write(writer, log::Level::Info, &line);
        }
        writer.flush().unwrap();
    }

    fn file_names(dir: &Path) -> Vec<String> {
        let mut names: Vec<String> = std::fs::read_dir(dir)
            .unwrap()
            .map(|entry| entry.unwrap().file_name().into_string().unwrap())
            .collect();
        names.sort();
        names
    }

    fn log_path(dir: &tempfile::TempDir) -> PathBuf {
        dir.path().join("cmk-agent-ctl.log")
    }

    /// CMK-41736 AC2
    #[test]
    fn test_rotation_keeps_the_current_file_at_its_plain_name() {
        let dir = tempfile::tempdir().unwrap();

        write_600_kb(&writer(&log_path(&dir)).unwrap());

        let names = file_names(dir.path());
        assert_eq!(names.len(), 2, "{names:?}");
        assert_eq!(names[0], "cmk-agent-ctl.log");
        assert!(names[1].starts_with("cmk-agent-ctl_r"), "{names:?}");
    }

    /// CMK-41736 AC1
    #[test]
    fn test_the_file_leaves_out_debug_lines() {
        let dir = tempfile::tempdir().unwrap();
        let writer = writer(&log_path(&dir)).unwrap();

        write(&writer, log::Level::Debug, "a debug line");
        write(&writer, log::Level::Info, "an info line");
        writer.flush().unwrap();

        let log = std::fs::read_to_string(log_path(&dir)).unwrap();
        assert!(log.contains("an info line"), "{log}");
        assert!(!log.contains("a debug line"), "{log}");
    }

    /// CMK-41736 AC9
    #[test]
    fn test_the_lines_carry_timestamp_level_and_source() {
        let dir = tempfile::tempdir().unwrap();
        let writer = writer(&log_path(&dir)).unwrap();

        write(&writer, log::Level::Info, "an info line");
        writer.flush().unwrap();

        let log = std::fs::read_to_string(log_path(&dir)).unwrap();
        assert!(log.starts_with("[2"), "{log}");
        assert!(log.contains(" INFO "), "{log}");
        assert!(log.contains("src/updater.rs:42"), "{log}");
    }

    /// CMK-41736 AC8
    #[test]
    fn test_only_the_owner_can_read_the_file() {
        let dir = tempfile::tempdir().unwrap();

        writer(&log_path(&dir)).unwrap();

        let mode = std::fs::metadata(log_path(&dir))
            .unwrap()
            .permissions()
            .mode();
        assert_eq!(mode & 0o777, 0o600);
    }

    #[test]
    fn test_a_linked_directory_is_refused() {
        let dir = tempfile::tempdir().unwrap();
        let link = dir.path().join("link");
        std::os::unix::fs::symlink(dir.path(), &link).unwrap();

        assert!(writer(&link.join("cmk-agent-ctl.log")).is_err());
        assert!(!log_path(&dir).exists());
    }

    #[test]
    fn test_a_missing_directory_stays_missing() {
        let dir = tempfile::tempdir().unwrap();
        let missing = dir.path().join("controller");

        assert!(writer(&missing.join("cmk-agent-ctl.log")).is_err());
        assert!(!missing.exists());
    }
}
