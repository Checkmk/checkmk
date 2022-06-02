// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use flexi_logger::writers::LogWriter;
use flexi_logger::DeferredNow;
use log::Record;

use mail_slot::{MailslotClient, MailslotName};
use serde::{Deserialize, Serialize};

// data must be in sync with windows agent
const PROVIDER_NAME_LENGTH: usize = 32;
pub const DATA_TYPE_LOG: u64 = 0;
const AGENT_SERVICE_MAILSLOT_NAME: &str = "Global\\WinAgent_0";

// struct must be in sync with windows agent
#[derive(Serialize, Deserialize)]
pub struct MailSlotHeader {
    pub provider: [u8; PROVIDER_NAME_LENGTH],
    pub data_id: u64,
    pub type_id: u64,
    info: u64,
    reserved: [u32; 16],
    pub length: u64,
}

pub fn provider_name() -> [u8; PROVIDER_NAME_LENGTH] {
    let name = format!("ctl:{}", std::process::id());
    let pad = vec![0u8; PROVIDER_NAME_LENGTH - name.len()];
    [name.as_bytes(), &pad].concat().try_into().expect("FAIL!")
}

pub fn send_log_to_mailslot(log_text: &str, mailslot_name: &str) {
    let name = MailslotName::local(mailslot_name);
    match &mut MailslotClient::new(&name) {
        Ok(client) => {
            let log_string = String::from(log_text);
            let lp = MailSlotHeader {
                provider: provider_name(),
                data_id: 0,
                type_id: DATA_TYPE_LOG,
                info: 0,
                reserved: [0; 16],
                length: log_string.len() as u64,
            };
            let mut bytes = bincode::serialize(&lp).unwrap();
            let data = bincode::serialize(&log_text).unwrap();
            // remove encoded length of the log_text:
            bytes.extend_from_slice(&data[(data.len() - log_text.len())..]);
            client.send_message(&bytes).unwrap();
        }
        Err(_) => {
            // happens if we have not enough user rights
            // todo(sk): Add some reasonable error processing
        }
    }
}

pub fn send_log_to_service_mailslot(log_text: &str) {
    send_log_to_mailslot(log_text, &AGENT_SERVICE_MAILSLOT_NAME);
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
    use mail_slot::{MailslotName, MailslotServer};

    const TEXT_TO_SEND: &str = "message to log";

    fn parse_message(msg: &[u8]) -> (MailSlotHeader, Vec<u8>) {
        let hdr_end = std::mem::size_of::<MailSlotHeader>();
        let hdr: MailSlotHeader = bincode::deserialize(&msg[..hdr_end]).unwrap();
        (hdr, msg[hdr_end..].to_vec())
    }

    #[test]
    fn test_mailslot_log() {
        let mail_slot_name = format!("mail_slot_{}", std::process::id());
        let mut server = MailslotServer::new(&MailslotName::local(&mail_slot_name)).unwrap();
        send_log_to_mailslot(&TEXT_TO_SEND, &mail_slot_name);
        let msg = server.get_next_unread().unwrap().take().expect("Empty!");
        let (hdr, payload) = parse_message(&msg);
        assert_eq!(&payload, TEXT_TO_SEND.as_bytes());
        assert_eq!(hdr.data_id, 0u64);
        assert_eq!(hdr.type_id, DATA_TYPE_LOG);
        assert_eq!(hdr.provider, provider_name());
        assert_eq!(hdr.length, TEXT_TO_SEND.len() as u64);
    }

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
