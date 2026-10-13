// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::{bail, Result as AnyhowResult};
use is_elevated::is_elevated;
use log::warn;
use mail_slot::{MailslotClient, MailslotName, MailslotServer};
use std::convert::From;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread::{sleep, JoinHandle};
use std::time::Duration;
use tokio::sync::mpsc::{
    unbounded_channel as channel, UnboundedReceiver as Receiver, UnboundedSender as Sender,
};
use winapi;

pub const SERVER_CREATION_TIMEOUT: Duration = Duration::from_secs(5);
pub const MAX_SIMULTANEOUS_CONNECTION_PER_THREAD: i32 = 12;

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

// Struct and wire format must be in sync with the windows agent:
// `CarrierDataHeader` in agents/wnx/include/wnx/carrier.h reads these
// bytes as a packed little-endian struct, fields in declaration order.
pub struct MailSlotHeader {
    pub provider: [u8; PROVIDER_NAME_LENGTH],
    pub data_id: u64,
    pub type_id: u64,
    info: u64,
    reserved: [u32; 16],
    pub length: u64,
}

impl MailSlotHeader {
    pub const WIRE_SIZE: usize = PROVIDER_NAME_LENGTH + 3 * 8 + 16 * 4 + 8;

    fn to_le_bytes(&self) -> [u8; Self::WIRE_SIZE] {
        let mut bytes = Vec::with_capacity(Self::WIRE_SIZE);
        bytes.extend_from_slice(&self.provider);
        bytes.extend_from_slice(&self.data_id.to_le_bytes());
        bytes.extend_from_slice(&self.type_id.to_le_bytes());
        bytes.extend_from_slice(&self.info.to_le_bytes());
        for r in &self.reserved {
            bytes.extend_from_slice(&r.to_le_bytes());
        }
        bytes.extend_from_slice(&self.length.to_le_bytes());
        bytes.try_into().expect("field sizes sum to WIRE_SIZE")
    }

    #[cfg(test)]
    fn from_le_bytes(mut bytes: &[u8]) -> Self {
        fn take<const N: usize>(bytes: &mut &[u8]) -> [u8; N] {
            let (head, tail) = bytes.split_at(N);
            *bytes = tail;
            head.try_into().expect("split_at returned N bytes")
        }
        let provider = take::<PROVIDER_NAME_LENGTH>(&mut bytes);
        let data_id = u64::from_le_bytes(take(&mut bytes));
        let type_id = u64::from_le_bytes(take(&mut bytes));
        let info = u64::from_le_bytes(take(&mut bytes));
        let mut reserved = [0u32; 16];
        for r in &mut reserved {
            *r = u32::from_le_bytes(take(&mut bytes));
        }
        let length = u64::from_le_bytes(take(&mut bytes));
        Self {
            provider,
            data_id,
            type_id,
            info,
            reserved,
            length,
        }
    }
}

pub fn provider_name() -> [u8; PROVIDER_NAME_LENGTH] {
    let name = format!("ctl:{}", std::process::id());
    let pad = vec![0u8; PROVIDER_NAME_LENGTH - name.len()];
    [name.as_bytes(), &pad].concat().try_into().expect("FAIL!")
}

/// NOTE: this function is used for logging too
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
            let mut bytes = header.to_le_bytes().to_vec();
            bytes.extend_from_slice(data);
            client.send_message(&bytes).unwrap_or_default(); // we can't log in the function
        }
        Err(_) => {
            // happens if we have not enough user rights
            // todo(sk): Add some reasonable error processing
        }
    }
}

#[inline]
fn get_thread_id() -> usize {
    unsafe { winapi::um::processthreadsapi::GetCurrentThreadId() as usize }
}

pub fn build_own_mailslot_name() -> String {
    format!(
        "{}WinAgentCtl_{}_{}",
        if is_elevated() {
            "Global\\"
        } else {
            "user_mode_"
        },
        std::process::id(),
        get_thread_id()
    )
}

pub struct MailSlotBackend {
    srv: Option<JoinHandle<()>>, // option is need to call join(self) in drop
    stop_flag: Arc<AtomicBool>,
    pub tx: Receiver<Vec<u8>>,
    name: String,
}

impl MailSlotBackend {
    pub fn new(name: &str) -> AnyhowResult<Self> {
        let (rx, tx) = channel::<Vec<u8>>();
        let stop = Arc::new(AtomicBool::new(false));
        let result = Self::start_mailslot_server_thread(name, rx, Arc::clone(&stop));
        let Ok((handle, mailslot_name)) = result else {
            bail!(result.unwrap_err());
        };
        Ok(MailSlotBackend {
            srv: Some(handle),
            stop_flag: Arc::clone(&stop),
            tx,
            name: mailslot_name,
        })
    }

    /// Always returns correct string even if input is not valid utf8 sequence
    /// This is done to prevent crash/panic for the case if peer sends malformed data
    /// DEPRECATED, will be cleaned upon fix confirmed
    #[allow(dead_code)]
    fn try_as_utf8(msg: Vec<u8>) -> String {
        let decoded = String::from_utf8_lossy(&msg).into_owned();
        if decoded.contains(std::char::REPLACEMENT_CHARACTER) {
            warn!("Mailslot receives non utf-8 symbols in output from the agent.");
        };
        decoded
    }

    fn send_notify(cv_pair: &(Mutex<Option<String>>, Condvar), name: &str) {
        let (lock, cond_var) = cv_pair;
        *lock.lock().unwrap() = Some(name.to_owned());
        cond_var.notify_one();
    }

    pub fn used_name(&self) -> &str {
        &self.name
    }

    fn make_mailslot_server(name: &str) -> Result<MailslotServer, mail_slot::Error> {
        let full_name = MailslotName::local(name);
        MailslotServer::new(&full_name)
    }

    fn mailslot_server_thread(
        base_name: String,
        rx: Sender<Vec<u8>>,
        cv_pair: &Arc<(Mutex<Option<String>>, Condvar)>,
        stop: &AtomicBool,
    ) {
        for attempt in 0..MAX_SIMULTANEOUS_CONNECTION_PER_THREAD {
            let name = base_name.clone() + "_" + &attempt.to_string();
            match Self::make_mailslot_server(&name) {
                Ok(mut server) => {
                    Self::send_notify(cv_pair, &name); // caller waits(must!) for signal
                    loop {
                        match server.get_next_unread() {
                            Ok(None) | Err(_) => sleep(Duration::from_millis(20)),
                            Ok(Some(msg)) => rx.send(msg).unwrap_or_default(),
                        }
                        if stop.load(Ordering::Relaxed) {
                            break;
                        }
                    }
                    return;
                }
                Err(mail_slot::Error::Io(ref e))
                    if e.kind() == std::io::ErrorKind::AlreadyExists =>
                {
                    warn!("Error server mailslot name {} is in use, retry...", name,);
                    continue;
                }
                Err(e) => {
                    warn!("Error '{}' creating mailslot server with name:{}", e, name,);
                    break;
                }
            }
        }
        Self::send_notify(cv_pair, ""); // caller waits(must!) for signal
    }

    fn start_mailslot_server_thread(
        base_name: &str,
        rx: Sender<Vec<u8>>,
        stop: Arc<AtomicBool>,
    ) -> AnyhowResult<(JoinHandle<()>, String)> {
        let cv_pair = Arc::new((Mutex::new(None), Condvar::new()));
        let cv_pair_for_thread = Arc::clone(&cv_pair);
        let n = base_name.to_string();
        let server_thread = std::thread::spawn(move || {
            Self::mailslot_server_thread(n, rx, &cv_pair_for_thread, &stop)
        });

        let (lock, cond_var) = &*cv_pair;
        let (mailslot_name, result) = cond_var
            .wait_timeout_while(
                lock.lock().unwrap(), // mutex guard
                SERVER_CREATION_TIMEOUT,
                |name| name.is_none(), // predicate: for wait(opposite to C++)
            )
            .unwrap();
        if result.timed_out() {
            bail!("server creation timeout");
        }
        Ok((
            server_thread,
            mailslot_name.to_owned().unwrap_or_else(|| "".to_owned()),
        ))
    }
}

impl Drop for MailSlotBackend {
    fn drop(&mut self) {
        self.stop_flag.store(true, Ordering::Relaxed);
        if let Some(thread) = self.srv.take() {
            thread.join().expect("Panic"); // panic here is a real disaster
        }
    }
}

#[cfg(test)]
#[cfg(windows)]
mod tests {
    use super::*;
    use mail_slot::{MailslotName, MailslotServer};
    use std::convert::From;
    use std::io::Result as IoResult;

    const TEXT_TO_SEND: &str = "message to log";
    const MESSAGE_COUNT: i32 = 100;

    fn send_messages_to_mailslot(base_name: &str, count: i32) {
        match MailslotClient::new(&MailslotName::local(base_name)) {
            Ok(mut client) => {
                for i in 0..count {
                    client
                        .send_message(i.to_string().as_bytes())
                        .unwrap_or_else(|e| println!("Failed to send {:?}", e));
                }
            }
            Err(e) => panic!("Can't create client '{}'", e),
        }
    }

    async fn receive_expected_messages_from_mailslot(
        tx: &mut Receiver<Vec<u8>>,
        count: i32,
    ) -> bool {
        for i in 0..count {
            let value = tokio::time::timeout(Duration::from_secs(1), tx.recv())
                .await
                .unwrap_or_default() // in tests we ignore elapsed
                .unwrap_or_default(); // in tests we ignore errors
            if i.to_string().as_bytes() != value {
                return false;
            }
        }
        true
    }

    const BAD_UTF8: [u8; 7] = [0x20, 0xF0, 0x28, 0x8C, 0xBC, 0x20, 0x20];
    const GOOD_UTF8: [u8; 4] = [0xF0, 0x9F, 0x92, 0x96];
    #[test]
    /// This test doesn't check logging here despite it is important, because
    /// it is a bit complicated. We need to reconsider this in the future.
    fn test_try_as_utf8() {
        assert_eq!(MailSlotBackend::try_as_utf8(BAD_UTF8.to_vec()), " �(��  ");
        assert_eq!(MailSlotBackend::try_as_utf8(GOOD_UTF8.to_vec()), "💖");
    }

    #[test]
    fn test_mailslot_names() {
        {
            let m1 = MailSlotBackend::new("x").expect("FAILURE!");
            let m2 = MailSlotBackend::new("x").expect("FAILURE!");
            assert_eq!(m1.used_name(), "x_0");
            assert_eq!(m2.used_name(), "x_1");
        }
        let m = MailSlotBackend::new("x").expect("FAILURE!");
        assert_eq!(m.used_name(), "x_0");
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_mailslot_backend() {
        let base_name = build_own_mailslot_name() + "_test";
        let mut backend = MailSlotBackend::new(&base_name).expect("Server is failed");
        send_messages_to_mailslot(backend.used_name(), MESSAGE_COUNT);
        assert!(receive_expected_messages_from_mailslot(&mut backend.tx, MESSAGE_COUNT).await);
    }

    async fn async_collect_from_mailslot(duration: Duration) -> IoResult<Vec<u8>> {
        let base_name = build_own_mailslot_name() + "_test_async";
        let mut backend = MailSlotBackend::new(&base_name).expect("Server is failed");
        send_messages_to_mailslot(backend.used_name(), 1);
        let value = tokio::time::timeout(duration, backend.tx.recv())
            .await
            .unwrap_or_default() // in tests we ignore elapsed
            .unwrap_or_default(); // in tests we ignore errors
        Ok(value)
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn test_mailslot_backend_async() -> AnyhowResult<()> {
        let res = async_collect_from_mailslot(Duration::from_secs(1)).await?;
        assert_eq!(res, "0".as_bytes());
        Ok(())
    }

    #[test]
    fn test_from() {
        assert_eq!(u64::from(DataType::Log), 0u64);
        assert_eq!(u64::from(DataType::Segment), 1u64);
        assert_eq!(u64::from(DataType::Yaml), 2u64);
        assert_eq!(u64::from(DataType::Command), 3u64);
    }

    fn parse_message(msg: &[u8]) -> (MailSlotHeader, Vec<u8>) {
        let (hdr, payload) = msg.split_at(MailSlotHeader::WIRE_SIZE);
        (MailSlotHeader::from_le_bytes(hdr), payload.to_vec())
    }

    #[test]
    fn test_header_to_le_bytes_pins_wire_format() {
        let mut provider = [0u8; PROVIDER_NAME_LENGTH];
        provider[..10].copy_from_slice(b"ctl:golden");
        let mut reserved = [0u32; 16];
        reserved[0] = 0xAABB_CCDD;
        reserved[15] = 0x1122_3344;
        let header = MailSlotHeader {
            provider,
            data_id: 0x0102_0304_0506_0708,
            type_id: DataType::Yaml.into(),
            info: 0xA1A2_A3A4_A5A6_A7A8,
            reserved,
            length: 0xDEAD_BEEF,
        };
        // The packed little-endian layout `CarrierDataHeader` in the
        // windows agent (agents/wnx/include/wnx/carrier.h) reads.
        #[rustfmt::skip]
        let expected: [u8; MailSlotHeader::WIRE_SIZE] = [
            0x63, 0x74, 0x6C, 0x3A, 0x67, 0x6F, 0x6C, 0x64, // provider[0..8]
            0x65, 0x6E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // provider[8..16]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // provider[16..24]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // provider[24..32]
            0x08, 0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, // data_id
            0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // type_id
            0xA8, 0xA7, 0xA6, 0xA5, 0xA4, 0xA3, 0xA2, 0xA1, // info
            0xDD, 0xCC, 0xBB, 0xAA, 0x00, 0x00, 0x00, 0x00, // reserved[0..2]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved[2..4]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved[4..6]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved[6..8]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved[8..10]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved[10..12]
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // reserved[12..14]
            0x00, 0x00, 0x00, 0x00, 0x44, 0x33, 0x22, 0x11, // reserved[14..16]
            0xEF, 0xBE, 0xAD, 0xDE, 0x00, 0x00, 0x00, 0x00, // length
        ];
        assert_eq!(header.to_le_bytes(), expected);
        assert_eq!(
            MailSlotHeader::from_le_bytes(&expected).to_le_bytes(),
            expected
        );
    }

    #[test]
    fn test_mailslot_log() {
        let mail_slot_name = format!("mail_slot_{}", std::process::id());
        let mut server = MailslotServer::new(&MailslotName::local(&mail_slot_name)).unwrap();
        send_to_mailslot(&mail_slot_name, DataType::Log, TEXT_TO_SEND.as_bytes());
        let msg = server.get_next_unread().unwrap().unwrap();
        let (hdr, payload) = parse_message(&msg);
        assert_eq!(&payload, TEXT_TO_SEND.as_bytes());
        assert_eq!(hdr.data_id, 0u64);
        assert_eq!(hdr.type_id, 0);
        assert_eq!(hdr.provider, provider_name());
        assert_eq!(hdr.length, TEXT_TO_SEND.len() as u64);
    }
}
