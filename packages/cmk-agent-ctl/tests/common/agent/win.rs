// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Error as AnyhowError;
use anyhow::Result as AnyhowResult;
use cmk_agent_ctl::mailslot_transport::MailSlotBackend;
use mail_slot::{MailslotClient, MailslotName};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;

/// creates mailslot port simulating agent
pub fn make_agent_response_peer() -> AnyhowResult<MailSlotBackend> {
    use cmk_agent_ctl::mailslot_transport;
    let own_mailslot = mailslot_transport::build_own_mailslot_name() + "_agent_peer";
    MailSlotBackend::new(&own_mailslot)
}

/// awaits on mailslot connection from controller
pub async fn run_agent_response_loop(
    mut backend: MailSlotBackend,
    output: String,
) -> AnyhowResult<()> {
    loop {
        let value: Vec<u8> =
            tokio::time::timeout(std::time::Duration::from_secs(180), backend.tx.recv())
                .await
                .unwrap_or_else(|_| {
                    Some(vec![]) // we return empty string on timeout
                })
                .unwrap_or_default();
        let command = String::from_utf8_lossy(&value);
        if command.is_empty() {
            break;
        }
        let name = MailslotName::local(&extract_mailslot_name_from_yaml_text(&command));
        let result = MailslotClient::new(&name);
        let mut client = result.unwrap_or_else(|_| {
            panic!(
                "Name of the slot {}\\{} is probably incorrect",
                name.domain, name.path
            )
        });
        if client.send_message(output.as_bytes()).is_err() {
            break;
        }
    }

    Ok(())
}

/// simplest possible extraction of the channel, we don't care about yaml
fn extract_mailslot_name_from_yaml_text(command: &str) -> String {
    let words: Vec<&str> = command.split(' ').collect();
    words[4].trim().to_owned()
}

pub async fn agent_response(
    mut stream: TcpStream,
    output: String,
    expected_input: Option<&str>,
) -> AnyhowResult<()> {
    let (mut reader, mut writer) = stream.split();
    let mut buf = vec![];
    tokio::time::timeout(tokio::time::Duration::from_secs(1), async {
        loop {
            reader.read_buf(&mut buf).await?;
            tokio::time::sleep(tokio::time::Duration::from_millis(20)).await;
            if !buf.is_empty() {
                return Ok::<(), AnyhowError>(());
            }
        }
    })
    .await
    .unwrap_or(Ok(()))?;

    if let Some(input) = expected_input {
        assert_eq!(String::from_utf8(buf)?, input);
    }

    writer.write_all(output.as_bytes()).await?;
    writer.flush().await?;
    let _ = writer.shutdown().await; // ignore error: not our problem
    Ok(())
}

pub fn is_elevation_required() -> bool {
    !is_elevated::is_elevated()
}

pub fn is_port_available(port: u16) -> bool {
    std::net::TcpListener::bind(("127.0.0.1", port)).is_ok()
}
