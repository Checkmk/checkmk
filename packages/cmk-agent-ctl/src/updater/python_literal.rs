// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! The Python literals that the Python agent updater writes with `repr()` and
//! reads back with `ast.literal_eval`.
//!
//! Only what `repr()` produces for its state is understood: dicts, lists,
//! tuples, strings, bytes, integers, floats, `True`, `False` and `None`. Bytes
//! become strings, as the updater's own `fix_bytes` decodes them.
//!
//! The parsed text holds the `host_secret`, so an error names a byte offset
//! and never quotes the text.

use anyhow::{anyhow, Error, Result as AnyhowResult};
use serde_json::{Map, Number, Value};

pub fn parse(text: &str) -> AnyhowResult<Value> {
    let mut parser = Parser { text, pos: 0 };
    let value = parser.value()?;
    parser.skip_whitespace();
    if parser.pos < text.len() {
        return Err(parser.error("unexpected text after the literal"));
    }
    Ok(value)
}

struct Parser<'a> {
    text: &'a str,
    pos: usize,
}

impl Parser<'_> {
    fn value(&mut self) -> AnyhowResult<Value> {
        self.skip_whitespace();
        match self.peek() {
            Some('{') => self.dict(),
            Some('[') => self.sequence('[', ']'),
            Some('(') => self.sequence('(', ')'),
            Some('\'' | '"') => Ok(Value::String(self.string(false)?)),
            Some('-' | '0'..='9') => self.number(),
            Some(c) if c.is_ascii_alphabetic() => self.name(),
            _ => Err(self.error("expected a value")),
        }
    }

    fn dict(&mut self) -> AnyhowResult<Value> {
        let mut map = Map::new();
        self.expect('{')?;
        while self.another_item('}', map.is_empty())? {
            let Value::String(key) = self.value()? else {
                return Err(self.error("expected a string as key"));
            };
            self.skip_whitespace();
            self.expect(':')?;
            map.insert(key, self.value()?);
        }
        Ok(Value::Object(map))
    }

    fn sequence(&mut self, open: char, close: char) -> AnyhowResult<Value> {
        let mut items = Vec::new();
        self.expect(open)?;
        while self.another_item(close, items.is_empty())? {
            items.push(self.value()?);
        }
        Ok(Value::Array(items))
    }

    /// Python accepts a comma after the last item, and needs one in a tuple of
    /// one item.
    fn another_item(&mut self, close: char, first: bool) -> AnyhowResult<bool> {
        self.skip_whitespace();
        if self.consume(close) {
            return Ok(false);
        }
        if !first {
            self.expect(',')?;
            self.skip_whitespace();
            if self.consume(close) {
                return Ok(false);
            }
        }
        Ok(true)
    }

    fn name(&mut self) -> AnyhowResult<Value> {
        let start = self.pos;
        let end = self.text[start..]
            .find(|c: char| !c.is_ascii_alphanumeric() && c != '_')
            .map_or(self.text.len(), |length| start + length);
        let value = match &self.text[start..end] {
            "None" => Value::Null,
            "True" => Value::Bool(true),
            "False" => Value::Bool(false),
            "u" | "U" if self.text[end..].starts_with(['\'', '"']) => {
                self.pos = end;
                return Ok(Value::String(self.string(false)?));
            }
            "b" | "B" if self.text[end..].starts_with(['\'', '"']) => {
                self.pos = end;
                return Ok(Value::String(self.string(true)?));
            }
            _ => return Err(self.error("expected True, False, None or a string")),
        };
        self.pos = end;
        Ok(value)
    }

    fn number(&mut self) -> AnyhowResult<Value> {
        let start = self.pos;
        let end = self.text[start..]
            .find(|c: char| !c.is_ascii_digit() && !matches!(c, '-' | '+' | '.' | 'e' | 'E'))
            .map_or(self.text.len(), |length| start + length);
        let literal = &self.text[start..end];
        let number = if let Ok(integer) = literal.parse::<i64>() {
            Number::from(integer)
        } else {
            literal
                .parse::<f64>()
                .ok()
                .and_then(Number::from_f64)
                .ok_or_else(|| self.error("expected a number"))?
        };
        self.pos = end;
        Ok(Value::Number(number))
    }

    /// A string at the opening quote. In a bytes literal, `\x` escapes a byte
    /// rather than a character, and the bytes must decode as UTF-8.
    fn string(&mut self, bytes: bool) -> AnyhowResult<String> {
        let start = self.pos;
        let Some(quote) = self.next_char() else {
            return Err(self.error("expected a string"));
        };
        let mut decoded = Vec::new();
        loop {
            match self.next_char() {
                None => return Err(self.error_at(start, "unterminated string")),
                Some(c) if c == quote => break,
                Some('\\') => self.escape(bytes, &mut decoded)?,
                Some(c) => decoded.extend_from_slice(c.encode_utf8(&mut [0; 4]).as_bytes()),
            }
        }
        String::from_utf8(decoded).map_err(|_| self.error_at(start, "the bytes are not UTF-8"))
    }

    fn escape(&mut self, bytes: bool, decoded: &mut Vec<u8>) -> AnyhowResult<()> {
        let escaped = match self.next_char() {
            Some('\\') => '\\',
            Some('\'') => '\'',
            Some('"') => '"',
            Some('n') => '\n',
            Some('r') => '\r',
            Some('t') => '\t',
            Some('x') if bytes => {
                decoded.push(u8::try_from(self.hex_digits(2)?)?);
                return Ok(());
            }
            Some('x') => self.character(2)?,
            Some('u') if !bytes => self.character(4)?,
            Some('U') if !bytes => self.character(8)?,
            _ => return Err(self.error("invalid escape")),
        };
        decoded.extend_from_slice(escaped.encode_utf8(&mut [0; 4]).as_bytes());
        Ok(())
    }

    fn character(&mut self, digits: usize) -> AnyhowResult<char> {
        let code = self.hex_digits(digits)?;
        char::from_u32(code).ok_or_else(|| self.error("invalid escape"))
    }

    fn hex_digits(&mut self, digits: usize) -> AnyhowResult<u32> {
        let hex = self
            .text
            .get(self.pos..self.pos + digits)
            .filter(|hex| hex.chars().all(|c| c.is_ascii_hexdigit()))
            .ok_or_else(|| self.error("invalid escape"))?;
        let code = u32::from_str_radix(hex, 16).map_err(|_| self.error("invalid escape"))?;
        self.pos += digits;
        Ok(code)
    }

    fn skip_whitespace(&mut self) {
        let rest = &self.text[self.pos..];
        self.pos += rest.len() - rest.trim_start().len();
    }

    fn peek(&self) -> Option<char> {
        self.text[self.pos..].chars().next()
    }

    fn next_char(&mut self) -> Option<char> {
        let c = self.peek()?;
        self.pos += c.len_utf8();
        Some(c)
    }

    fn consume(&mut self, expected: char) -> bool {
        if self.peek() == Some(expected) {
            self.pos += expected.len_utf8();
            return true;
        }
        false
    }

    fn expect(&mut self, expected: char) -> AnyhowResult<()> {
        if !self.consume(expected) {
            return Err(self.error(&format!("expected '{expected}'")));
        }
        Ok(())
    }

    fn error(&self, what: &str) -> Error {
        self.error_at(self.pos, what)
    }

    fn error_at(&self, pos: usize, what: &str) -> Error {
        anyhow!("Not a Python literal at byte {pos}: {what}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_parse_the_state_of_a_python_updater() {
        assert_eq!(
            parse(
                "{'protocol': 'http', 'installed_aghash': 'a71dfa65aacb1b52', 'last_error': None, \
                 'site': 'stable', 'last_check': 1563801836.6, 'host_name': 'windows', \
                 'server': '10.3.2.41', 'last_update': 1563801842, 'host_secret': 'zlsgotaddy', \
                 'user': 'cmkadmin'}\n"
            )
            .unwrap(),
            json!({
                "protocol": "http",
                "installed_aghash": "a71dfa65aacb1b52",
                "last_error": null,
                "site": "stable",
                "last_check": 1563801836.6,
                "host_name": "windows",
                "server": "10.3.2.41",
                "last_update": 1563801842,
                "host_secret": "zlsgotaddy",
                "user": "cmkadmin",
            })
        );
    }

    /// Written by Python's `repr()`.
    #[test]
    fn test_parse_certificates_and_an_error_with_quotes() {
        assert_eq!(
            parse(
                r#"{'last_error': 'Couldn\'t reach "checkmk.example.com"', 'local_certificates': ['-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n'], 'pending_hash': None}"#
            )
            .unwrap(),
            json!({
                "last_error": "Couldn't reach \"checkmk.example.com\"",
                "local_certificates": ["-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"],
                "pending_hash": null,
            })
        );
    }

    #[test]
    fn test_parse_nested_values() {
        assert_eq!(
            parse("{'a': [1, -2, 3.5e-05], 'b': (True,), 'c': {'d': False}, 'e': (), 'f': [],}")
                .unwrap(),
            json!({"a": [1, -2, 3.5e-05], "b": [true], "c": {"d": false}, "e": [], "f": []})
        );
    }

    #[test]
    fn test_parse_escapes_in_both_quotes() {
        assert_eq!(
            parse(r#"["it's", 'say "hi"', 'a\'b\\c', "\n\t\x41é\U0001F600", 'ü']"#).unwrap(),
            json!(["it's", "say \"hi\"", "a'b\\c", "\n\tAé😀", "ü"])
        );
    }

    #[test]
    fn test_parse_bytes_and_unicode_strings() {
        assert_eq!(
            parse(r"{b'key': b'\xc3\xbc', u'other': u'\xfc'}").unwrap(),
            json!({"key": "ü", "other": "ü"})
        );
    }

    #[test]
    fn test_parse_rejects_what_repr_does_not_write() {
        for text in [
            "",
            "{'a': 1",
            "{'a' 1}",
            "{1: 'a'}",
            "{'a': 1} {}",
            "['a' 'b']",
            "[,]",
            "nan",
            "'unterminated",
            r"'\q'",
            r"b'\xff'",
            "{'a': os.system('x')}",
        ] {
            assert!(parse(text).is_err(), "{text:?} was accepted");
        }
    }

    /// CMK-39502: an error about the state file never shows its text, which
    /// holds the secret.
    #[test]
    fn test_parse_error_does_not_quote_the_text() {
        let error = parse("{'host_secret': 'zlsgotaddy', 'site' 'stable'}").unwrap_err();

        let error = format!("{error:#}");
        assert!(!error.contains("zlsgotaddy"));
        assert!(error.contains("byte 37"));
    }
}
