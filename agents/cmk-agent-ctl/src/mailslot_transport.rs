// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use mail_slot::{MailslotClient, MailslotName};
use serde::{Deserialize, Serialize};
use std::convert::From;

// data must be in sync with windows agent
const PROVIDER_NAME_LENGTH: usize = 32;
pub enum DataType {
    Log,
    Segment,
    Yaml,
    Command,
}

impl From<DataType> for u64 {
    fn from(v: DataType) -> Self {
        match v {
            DataType::Log => 0u64,
            DataType::Segment => 1u64,
            DataType::Yaml => 2u64,
            DataType::Command => 3u64,
        }
    }
}

const AGENT_SERVICE_MAILSLOT_NAME: &str = "Global\\WinAgent_0";

pub fn service_mailslot_name() -> String {
    AGENT_SERVICE_MAILSLOT_NAME.to_string()
}

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

pub fn send_to_mailslot(mailslot_name: &str, data_type: DataType, data: &[u8]) {
    let name = MailslotName::local(mailslot_name);
    match &mut MailslotClient::new(&name) {
        Ok(client) => {
            let header = MailSlotHeader {
                provider: provider_name(),
                data_id: 0,
                type_id: data_type.into(),
                info: 0,
                reserved: [0; 16],
                length: data.len() as u64,
            };
            let mut bytes = bincode::serialize(&header).unwrap();
            let payload = bincode::serialize(&data).unwrap();
            // remove encoded length of the log_text:
            let offset = payload.len() - data.len();
            bytes.extend_from_slice(&payload[offset..]);
            client.send_message(&bytes).unwrap();
        }
        Err(_) => {
            // happens if we have not enough user rights
            // todo(sk): Add some reasonable error processing
        }
    }
}

#[cfg(test)]
#[cfg(windows)]
mod tests {
    use super::*;
    use mail_slot::{MailslotName, MailslotServer};
    use std::convert::From;

    const TEXT_TO_SEND: &str = "message to log";

    #[test]
    fn test_from() {
        assert_eq!(u64::from(DataType::Log), 0u64);
        assert_eq!(u64::from(DataType::Segment), 1u64);
        assert_eq!(u64::from(DataType::Yaml), 2u64);
        assert_eq!(u64::from(DataType::Command), 3u64);
    }

    fn parse_message(msg: &[u8]) -> (MailSlotHeader, Vec<u8>) {
        let hdr_end = std::mem::size_of::<MailSlotHeader>();
        let hdr: MailSlotHeader = bincode::deserialize(&msg[..hdr_end]).unwrap();
        (hdr, msg[hdr_end..].to_vec())
    }

    #[test]
    fn test_mailslot_log() {
        let mail_slot_name = format!("mail_slot_{}", std::process::id());
        let mut server = MailslotServer::new(&MailslotName::local(&mail_slot_name)).unwrap();
        send_to_mailslot(&mail_slot_name, DataType::Log, TEXT_TO_SEND.as_bytes());
        let msg = server.get_next_unread().unwrap().take().expect("Empty!");
        let (hdr, payload) = parse_message(&msg);
        assert_eq!(&payload, TEXT_TO_SEND.as_bytes());
        assert_eq!(hdr.data_id, 0u64);
        assert_eq!(hdr.type_id, 0);
        assert_eq!(hdr.provider, provider_name());
        assert_eq!(hdr.length, TEXT_TO_SEND.len() as u64);
    }
}
