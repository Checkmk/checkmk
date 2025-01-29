// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::mailslot_transport::{send_to_mailslot, service_mailslot_name, DataType};
use flexi_logger::writers::LogWriter;
use flexi_logger::DeferredNow;
use log::Record;

pub fn send_log_to_service_mailslot(log_text: &str) {
    send_to_mailslot(&service_mailslot_name(), DataType::Log, log_text.as_bytes());
}

#[derive(Debug)]
pub struct MailSlotLogWriter {
    max_log_level: log::LevelFilter,
}

impl MailSlotLogWriter {
    fn new(max_log_level: log::LevelFilter) -> MailSlotLogWriter {
        MailSlotLogWriter { max_log_level }
    }
}

impl LogWriter for MailSlotLogWriter {
    #[inline]
    fn write(&self, _now: &mut DeferredNow, record: &Record) -> std::io::Result<()> {
        let log_line = format!(
            "[{}][{}] {}",
            record.target(),
            record.level(),
            record.args(),
        );
        send_log_to_service_mailslot(&log_line);
        Ok(())
    }

    #[inline]
    fn flush(&self) -> std::io::Result<()> {
        Ok(())
    }

    #[inline]
    fn max_log_level(&self) -> log::LevelFilter {
        self.max_log_level
    }
}

pub fn to_log_level(level: &str) -> log::LevelFilter {
    let result = flexi_logger::LogSpecification::env_or_parse(level);
    match result {
        Ok(spec) => spec
            .module_filters()
            .iter()
            .map(|d| d.level_filter)
            .max()
            .unwrap_or(log::LevelFilter::Trace),
        Err(_) => log::LevelFilter::Trace,
    }
}

pub fn make_mailslot_logger(level: &str) -> Box<MailSlotLogWriter> {
    Box::new(MailSlotLogWriter::new(to_log_level(level)))
}

#[cfg(test)]
#[cfg(windows)]
mod tests {
    use super::*;

    #[test]
    fn test_log_levels() {
        let tests = [
            ("warn", log::LevelFilter::Warn),
            ("debug", log::LevelFilter::Debug),
            ("info", log::LevelFilter::Info),
            ("bad", log::LevelFilter::Trace),
        ];
        for &(s, expected) in &tests {
            assert_eq!(to_log_level(s), expected);
        }
    }
}
