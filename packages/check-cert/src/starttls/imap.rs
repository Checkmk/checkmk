// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::starttls::stream_io::{read_line, write};
use anyhow::{anyhow, Result};
use log::{debug, info, warn};
use std::io::{BufReader, Read, Write};

const CRLF: &str = "\r\n";
const TAG: &str = "A001";

/// Performs the IMAP STARTTLS handshake on the given stream according to RFC 2595 / RFC 3501.
pub fn perform<T: Read + Write>(stream: &mut T) -> Result<()> {
    info!("Starting IMAP STARTTLS handshake");

    let mut reader = BufReader::new(stream);
    read_greeting(&mut reader)?;
    send_starttls(&mut reader)?;

    info!("IMAP STARTTLS handshake completed successfully");
    Ok(())
}

fn read_greeting<T: Read + Write>(reader: &mut BufReader<T>) -> Result<()> {
    debug!("Reading IMAP greeting");
    let line = read_line(reader)?;
    let state = parse_untagged_imap_response(&line)?;
    if state == UntaggedState::Bye {
        return Err(anyhow!("Server rejected connection: {}", line.trim_end()));
    }
    if state == UntaggedState::Preauth {
        warn!(
            "IMAP server sent PREAUTH greeting; STARTTLS may be rejected in this state: {}",
            line.trim_end()
        );
    }
    debug!("IMAP greeting received: state={:?}", state);
    Ok(())
}

fn send_starttls<T: Read + Write>(reader: &mut BufReader<T>) -> Result<()> {
    let cmd = format!("{} STARTTLS{}", TAG, CRLF);
    debug!("Sending IMAP STARTTLS command");
    write(reader.get_mut(), &cmd)?;

    loop {
        let line = read_line(reader)?;
        debug!("Read line: {:?}", line);
        if line.starts_with('*') {
            continue;
        }
        return match parse_tagged_imap_response(TAG, &line)? {
            TaggedStatus::Ok => {
                debug!("IMAP STARTTLS command accepted (OK)");
                Ok(())
            }
            TaggedStatus::No => Err(anyhow!(
                "IMAP server declined STARTTLS: {}",
                line.trim_end()
            )),
            TaggedStatus::Bad => Err(anyhow!(
                "IMAP server rejected STARTTLS command: {}",
                line.trim_end()
            )),
        };
    }
}

#[derive(Debug, PartialEq)]
enum UntaggedState {
    Ok,
    Preauth,
    Bye,
    Other,
}

fn parse_untagged_imap_response(line: &str) -> Result<UntaggedState> {
    if !line.ends_with(CRLF) {
        return Err(anyhow!(
            "IMAP response line not terminated with CRLF: {:?}",
            line
        ));
    }
    let trimmed = line.trim_end();
    if !trimmed.starts_with("* ") {
        return Err(anyhow!(
            "Expected untagged IMAP response ('* ...'), got: {:?}",
            trimmed
        ));
    }
    let rest = &trimmed[2..];
    let keyword = rest
        .split_whitespace()
        .next()
        .unwrap_or("")
        .to_ascii_uppercase();
    let state = match keyword.as_str() {
        "OK" => UntaggedState::Ok,
        "PREAUTH" => UntaggedState::Preauth,
        "BYE" => UntaggedState::Bye,
        _ => UntaggedState::Other,
    };
    Ok(state)
}

#[derive(Debug, PartialEq)]
enum TaggedStatus {
    Ok,
    No,
    Bad,
}

fn parse_tagged_imap_response(expected_tag: &str, line: &str) -> Result<TaggedStatus> {
    if !line.ends_with(CRLF) {
        return Err(anyhow!(
            "IMAP response line not terminated with CRLF: {:?}",
            line
        ));
    }
    let trimmed = line.trim_end();
    let mut parts = trimmed.splitn(3, ' ');
    let tag = parts
        .next()
        .ok_or_else(|| anyhow!("Empty IMAP response line"))?;
    if tag != expected_tag {
        return Err(anyhow!(
            "Unexpected IMAP response tag '{}', expected '{}'",
            tag,
            expected_tag
        ));
    }
    let status_str = parts
        .next()
        .ok_or_else(|| anyhow!("Missing status in IMAP tagged response: {:?}", trimmed))?
        .to_ascii_uppercase();
    let status = match status_str.as_str() {
        "OK" => TaggedStatus::Ok,
        "NO" => TaggedStatus::No,
        "BAD" => TaggedStatus::Bad,
        _ => {
            return Err(anyhow!(
                "Unexpected IMAP tagged status '{}' in: {:?}",
                status_str,
                trimmed
            ))
        }
    };
    Ok(status)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_untagged_parse_ok() {
        let line = "* OK Dovecot ready.\r\n";
        assert_eq!(
            parse_untagged_imap_response(line).unwrap(),
            UntaggedState::Ok
        );
    }

    #[test]
    fn test_untagged_parse_preauth() {
        let line = "* PREAUTH Already authenticated\r\n";
        assert_eq!(
            parse_untagged_imap_response(line).unwrap(),
            UntaggedState::Preauth
        );
    }

    #[test]
    fn test_untagged_parse_bye() {
        let line = "* BYE Too many connections\r\n";
        assert_eq!(
            parse_untagged_imap_response(line).unwrap(),
            UntaggedState::Bye
        );
    }

    #[test]
    fn test_untagged_parse_capability() {
        let line = "* CAPABILITY IMAP4rev1 STARTTLS\r\n";
        assert_eq!(
            parse_untagged_imap_response(line).unwrap(),
            UntaggedState::Other
        );
    }

    #[test]
    fn test_untagged_parse_missing_crlf() {
        assert!(parse_untagged_imap_response("* OK ready").is_err());
    }

    #[test]
    fn test_untagged_parse_not_untagged() {
        assert!(parse_untagged_imap_response("A001 OK done\r\n").is_err());
    }

    #[test]
    fn test_tagged_parse_ok() {
        let line = "A001 OK Begin TLS negotiation\r\n";
        assert_eq!(
            parse_tagged_imap_response("A001", line).unwrap(),
            TaggedStatus::Ok
        );
    }

    #[test]
    fn test_tagged_parse_no() {
        let line = "A001 NO STARTTLS not supported\r\n";
        assert_eq!(
            parse_tagged_imap_response("A001", line).unwrap(),
            TaggedStatus::No
        );
    }

    #[test]
    fn test_tagged_parse_bad() {
        let line = "A001 BAD Unknown command\r\n";
        assert_eq!(
            parse_tagged_imap_response("A001", line).unwrap(),
            TaggedStatus::Bad
        );
    }

    #[test]
    fn test_tagged_parse_missing_crlf() {
        assert!(parse_tagged_imap_response("A001", "A001 OK done").is_err());
    }

    #[test]
    fn test_tagged_parse_unknown_status() {
        assert!(parse_tagged_imap_response("A001", "A001 MAYBE done\r\n").is_err());
    }

    #[test]
    fn test_tagged_parse_wrong_tag() {
        assert!(parse_tagged_imap_response("A001", "B002 OK done\r\n").is_err());
    }
}
