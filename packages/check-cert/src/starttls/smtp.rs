// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::starttls::stream_io::read_line;
use crate::starttls::stream_io::write;
use anyhow::{anyhow, Result};
use log::{debug, info};
use std::io::{BufReader, Read, Write};
use std::sync::LazyLock;

const SMTP_REPLY_CODE_LEN: usize = 3;
const CHAR_HYPHEN: char = '-';
const CHAR_SPACE: char = ' ';
const CRLF: &str = "\r\n";
static CANNED_STARTTLS_LINE_HYPHEN: LazyLock<SmtpLine> = LazyLock::new(|| SmtpLine {
    code: ReplyCode::Ok,
    separator: Separator::Hyphen,
    text: TextString::parse("STARTTLS").unwrap(),
});
static CANNED_STARTTLS_LINE_SPACE: LazyLock<SmtpLine> = LazyLock::new(|| SmtpLine {
    code: ReplyCode::Ok,
    separator: Separator::Space,
    text: TextString::parse("STARTTLS").unwrap(),
});

/// Performs the SMTP STARTTLS handshake on the given stream according to RFC 3207.
pub fn perform<T: Read + Write>(stream: &mut T, server: &str) -> Result<()> {
    info!("Starting SMTP STARTTLS handshake for server: {}", server);

    read_greeting(stream)?;

    let ehlo_response = send_ehlo(stream, server)?;
    if !ehlo_response
        .lines
        .iter()
        .any(|line| *line == *CANNED_STARTTLS_LINE_HYPHEN || *line == *CANNED_STARTTLS_LINE_SPACE)
    {
        return Err(anyhow!(
            "Server does not support STARTTLS. EHLO response: {}",
            ehlo_response
        ));
    }
    debug!("Server advertises STARTTLS support");

    send_starttls(stream)?;
    info!("SMTP STARTTLS handshake completed successfully");

    Ok(())
}

fn read_greeting<T: Read + Write>(stream: &mut T) -> Result<()> {
    debug!("Reading SMTP greeting from server");

    let greeting = read_response(stream)?;
    if !greeting.is_ready() {
        return Err(anyhow!("Unexpected SMTP greeting code: {}", greeting.code));
    }
    debug!("SMTP greeting indicates server is ready (code 220)");
    Ok(())
}

/// Send EHLO to the SMTP server and parse the response. Returns the parsed SmtpResponse.
pub fn send_ehlo<T: Read + Write>(stream: &mut T, server: &str) -> Result<SmtpResponse> {
    debug!("Sending EHLO command to server: {}", server);
    write(stream, &format!("EHLO {}\r\n", server))?;

    debug!("Reading EHLO response from server");
    let ehlo_response = read_response(stream)?;
    if !ehlo_response.is_ok() {
        return Err(anyhow!("Unexpected EHLO response code: {}", ehlo_response));
    }
    debug!("EHLO response indicates success (code 250)");

    Ok(ehlo_response)
}

fn send_starttls<T: Read + Write>(stream: &mut T) -> Result<()> {
    debug!("Sending STARTTLS command");
    write(stream, "STARTTLS\r\n")?;

    debug!("Reading STARTTLS response from server");
    let starttls_response = read_response(stream)?;
    if !starttls_response.is_ready() {
        return Err(anyhow!(
            "Unexpected STARTTLS response code: {}",
            starttls_response.code
        ));
    }
    debug!("STARTTLS response indicates server is ready for TLS (code 220)");

    Ok(())
}

/// Reads a complete SMTP response from the stream line by line.
/// Continues reading until a line with a space separator is encountered (indicating the last line).
fn read_response<T: Read>(stream: &mut T) -> Result<SmtpResponse> {
    let mut reader = BufReader::new(stream);
    let mut lines = Vec::new();

    loop {
        let line_str = read_line(&mut reader)?;
        debug!("Read line: {:?}", line_str);

        let line = SmtpLine::parse(&line_str)?;
        let is_last_line = line.separator == Separator::Space;
        lines.push(line);

        if is_last_line {
            break;
        }
    }

    SmtpResponse::parse(lines)
}

pub struct SmtpResponse {
    code: ReplyCode,
    lines: Vec<SmtpLine>,
}

impl SmtpResponse {
    fn parse(lines: Vec<SmtpLine>) -> Result<Self> {
        if lines.is_empty() {
            return Err(anyhow!("Empty SMTP response"));
        }

        let response_code = lines[0].code;
        if lines.iter().any(|line| line.code != response_code) {
            return Err(anyhow!(
                "Inconsistent SMTP reply codes in multi-line response."
            ));
        }

        // Only the last line must have Separator::Space, all previous lines must not
        if lines.last().map(|l| &l.separator) != Some(&Separator::Space) {
            return Err(anyhow!("No valid last line found in SMTP response"));
        }
        if lines.len() > 1
            && lines[..lines.len() - 1]
                .iter()
                .any(|line| line.separator == Separator::Space)
        {
            return Err(anyhow!(
                "Only the last line in SMTP response may have Separator::Space"
            ));
        }

        Ok(SmtpResponse {
            code: response_code,
            lines,
        })
    }

    pub fn is_ok(&self) -> bool {
        self.code == ReplyCode::Ok
    }

    pub fn is_ready(&self) -> bool {
        self.code == ReplyCode::Ready
    }
}

impl std::fmt::Display for SmtpResponse {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        for line in &self.lines {
            write!(f, "{}", line)?;
        }
        Ok(())
    }
}

#[derive(PartialEq, Eq, Debug)]
struct SmtpLine {
    code: ReplyCode,
    separator: Separator,
    text: TextString,
}

impl SmtpLine {
    /// Parses a single SMTP reply line, validating format and allowed characters
    /// according to RFC 5321.
    fn parse(line: &str) -> Result<Self> {
        if !line.ends_with(CRLF) {
            return Err(anyhow!(
                "SMTP reply line must be terminated with CRLF: '{}'",
                line
            ));
        }
        // Remove the CRLF for parsing
        let unterminated_line = &line[..line.len() - 2];

        if unterminated_line.len() < SMTP_REPLY_CODE_LEN {
            return Err(anyhow!(
                "SMTP reply line too short: '{}'",
                unterminated_line
            ));
        }

        let reply_code = &unterminated_line[..SMTP_REPLY_CODE_LEN];
        let code = match reply_code.parse::<ReplyCode>() {
            Ok(code) => code,
            Err(_) => {
                return Err(anyhow!(
                    "Unsupported SMTP reply code. Got: '{}'",
                    reply_code
                ));
            }
        };

        let textstring_start = SMTP_REPLY_CODE_LEN + 1;
        let separator_char = unterminated_line.chars().nth(SMTP_REPLY_CODE_LEN);
        let (separator, textstring) = match separator_char {
            Some(CHAR_SPACE) => (
                Separator::Space,
                unterminated_line.get(textstring_start..).unwrap_or(""),
            ),
            Some(CHAR_HYPHEN) => (
                Separator::Hyphen,
                unterminated_line.get(textstring_start..).unwrap_or(""),
            ),
            None => (Separator::Space, ""), // Only code, no separator or text
            Some(_) => {
                return Err(anyhow!(
                    "Invalid SMTP reply-line format: '{}'",
                    unterminated_line
                ))
            }
        };
        let text = TextString::parse(textstring)?;

        Ok(SmtpLine {
            code,
            separator,
            text,
        })
    }
}

impl std::fmt::Display for SmtpLine {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}{}{}\r\n", self.code, self.separator, self.text)
    }
}

/// SMTP reply codes according to RFC 5321
#[repr(u16)]
#[derive(PartialEq, Eq, Clone, Copy, Debug)]
enum ReplyCode {
    // Add more reply codes when needed, remember to update FromStr impl
    Ready = 220,
    Ok = 250,
    TlsNotAvailableTemporary = 454,
    SyntaxError = 501,
}

impl std::str::FromStr for ReplyCode {
    type Err = ();
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.parse::<u16>() {
            Ok(220) => Ok(ReplyCode::Ready),
            Ok(250) => Ok(ReplyCode::Ok),
            Ok(454) => Ok(ReplyCode::TlsNotAvailableTemporary),
            Ok(501) => Ok(ReplyCode::SyntaxError),
            _ => Err(()),
        }
    }
}

impl std::fmt::Display for ReplyCode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", *self as u16)
    }
}

#[derive(Debug, PartialEq, Eq)]
enum Separator {
    Hyphen,
    Space,
}

impl std::fmt::Display for Separator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Separator::Hyphen => write!(f, "{}", CHAR_HYPHEN),
            Separator::Space => write!(f, "{}", CHAR_SPACE),
        }
    }
}

/// Represents a validated SMTP textstring according to RFC 5321
#[derive(Debug, Clone, PartialEq, Eq)]
struct TextString(String);

impl TextString {
    fn parse(s: &str) -> Result<Self> {
        if s.is_empty() {
            return Ok(TextString(String::new()));
        }
        if let Some((i, byte)) = s
            .as_bytes()
            .iter()
            .enumerate()
            .find(|&(_, &b)| !Self::is_textstring_char(b))
        {
            return Err(anyhow!(
                "Invalid non-printable character in SMTP response textstring at position {}: 0x{:02x}",
                i,
                byte
            ));
        }
        Ok(TextString(s.to_string()))
    }

    /// Checks if a byte is allowed in SMTP textstring according to RFC 5321:
    /// textstring = 1*(%d09 / %d32-126) ; HT, SP, Printable US-ASCII
    fn is_textstring_char(byte: u8) -> bool {
        byte == b'\t' || (32..=126).contains(&byte)
    }
}

impl std::fmt::Display for TextString {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_smtp_line_equality() {
        let line1 = SmtpLine {
            code: ReplyCode::Ok,
            separator: Separator::Hyphen,
            text: TextString::parse("STARTTLS").unwrap(),
        };
        let line2 = SmtpLine {
            code: ReplyCode::Ok,
            separator: Separator::Hyphen,
            text: TextString::parse("STARTTLS").unwrap(),
        };
        let line3 = SmtpLine {
            code: ReplyCode::Ok,
            separator: Separator::Hyphen,
            text: TextString::parse("XSTARTTLS").unwrap(),
        };
        assert_eq!(line1, line2);
        assert_ne!(line1, line3);
    }

    #[test]
    fn test_smtp_line_parse_valid() {
        let line = "220 Ready to start TLS\r\n";
        let parsed = SmtpLine::parse(line).unwrap();
        assert_eq!(parsed.code, ReplyCode::Ready);
        assert_eq!(parsed.separator, Separator::Space);
        assert_eq!(parsed.text.0, "Ready to start TLS");
    }

    #[test]
    fn test_smtp_line_parse_invalid_code() {
        let line = "123 Ready\r\n";
        let result = SmtpLine::parse(line);
        assert!(result.is_err());
    }

    #[test]
    fn test_smtp_line_parse_invalid_format() {
        let line = "220*Ready\r\n";
        let result = SmtpLine::parse(line);
        assert!(result.is_err());
    }

    #[test]
    fn test_smtp_line_parse_missing_crlf() {
        let line = "220 Ready to start TLS";
        let result = SmtpLine::parse(line);
        assert!(result.is_err());
    }

    #[test]
    fn test_smtp_line_empty() {
        let line = "\r\n";
        let result = SmtpLine::parse(line);
        assert!(result.is_err());
    }

    #[test]
    fn test_smtp_line_missing_textstring() {
        let line = "250 \r\n";
        let parsed = SmtpLine::parse(line).unwrap();
        assert_eq!(parsed.code, ReplyCode::Ok);
        assert_eq!(parsed.separator, Separator::Space);
        assert_eq!(parsed.text.0, "");
    }

    #[test]
    fn test_smtp_line_missing_separator_and_textstring() {
        let line = "250\r\n";
        let parsed = SmtpLine::parse(line).unwrap();
        assert_eq!(parsed.code, ReplyCode::Ok);
        assert_eq!(parsed.separator, Separator::Space);
        assert_eq!(parsed.text.0, "");
    }

    #[test]
    fn test_smtp_response_parse_multiline() {
        let response = b"250-STARTTLS\r\n250 OK\r\n";
        let mut cursor = std::io::Cursor::new(response);
        let parsed = read_response(&mut cursor).unwrap();
        assert_eq!(parsed.code, ReplyCode::Ok);
        assert_eq!(parsed.lines.len(), 2);
        assert_eq!(parsed.lines[0].separator, Separator::Hyphen);
        assert_eq!(parsed.lines[1].separator, Separator::Space);
        assert_eq!(parsed.lines[0].text.0, "STARTTLS");
        assert_eq!(parsed.lines[1].text.0, "OK");
    }

    #[test]
    fn test_smtp_response_parse_invalid_last_line() {
        let response = b"250-STARTTLS\r\n250-OK\r\n";
        let mut cursor = std::io::Cursor::new(response);
        let result = read_response(&mut cursor);
        assert!(result.is_err());
    }

    #[test]
    fn test_textstring_parse_valid() {
        let s = "Hello World!";
        let ts = TextString::parse(s).unwrap();
        assert_eq!(ts.0, s);
    }

    #[test]
    fn test_textstring_parse_invalid() {
        let s = "Hello\x01World!";
        let result = TextString::parse(s);
        assert!(result.is_err());
    }

    #[test]
    fn test_reply_codes_from_str() {
        assert_eq!("220".parse::<ReplyCode>(), Ok(ReplyCode::Ready));
        assert_eq!("250".parse::<ReplyCode>(), Ok(ReplyCode::Ok));
        assert!("150".parse::<ReplyCode>().is_err());
        assert!("22".parse::<ReplyCode>().is_err());
        assert!("abc".parse::<ReplyCode>().is_err());
    }
}
