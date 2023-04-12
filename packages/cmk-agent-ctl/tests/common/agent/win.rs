// Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Error as AnyhowError;
use anyhow::Result as AnyhowResult;
use cmk_agent_ctl::mailslot_transport::MailSlotBackend;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpStream;

/// creates mailslot port simulating agent
pub async fn make_agent_response_peer() -> AnyhowResult<MailSlotBackend> {
    use cmk_agent_ctl::mailslot_transport;
    let own_mailslot = mailslot_transport::build_own_mailslot_name() + "_agent_peer";
    MailSlotBackend::new(&own_mailslot).map_err(anyhow::Error::from)
}

/// awaits on mailslot connection from controller
pub async fn run_agent_response_loop(
    mut _backend: MailSlotBackend,
    _output: String,
) -> AnyhowResult<()> {
    Ok(())
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
