// Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

//! Windows side of the agent info: reading `checkmk.dat`.
//!
//! The bakery writes the hash of the installed agent package into
//! `checkmk.dat` as `key: value` lines behind a comment header, where Unix gets
//! a JSON `agent_info.json`. This module holds the parser for that format; the
//! whole module is Windows-only.

use std::collections::HashMap;

/// Parse the `key: value` lines the bakery writes into `checkmk.dat`.
///
/// A `#` starts a comment that runs to the end of the line, trailing whitespace
/// is dropped - which also covers the CRLF line endings of the file - and empty
/// lines are skipped. What is left is split at the first `:`; a line without
/// one is no pair and is ignored. The key is trimmed, the value is passed
/// through [`parse_value`]. A repeated key keeps its last value.
pub fn parse_key_value(content: &str) -> HashMap<String, String> {
    content
        .lines()
        .filter_map(|line| {
            let line = line
                .split_once('#')
                .map_or(line, |(before_comment, _)| before_comment)
                .trim_end();
            if line.is_empty() {
                return None;
            }
            let (key, value) = line.split_once(':')?;
            Some((key.trim().to_owned(), parse_value(value)))
        })
        .collect()
}

/// Trim a value, drop every comma and strip one layer of quotes.
///
/// A value starting with `'` loses a leading and a trailing `'`, otherwise one
/// starting with `"` loses a leading and a trailing `"`. The trailing quote is
/// optional, so an unbalanced value is still usable.
fn parse_value(value: &str) -> String {
    let value = value.trim().replace(',', "");
    for quote in ['\'', '"'] {
        if let Some(unquoted) = value.strip_prefix(quote) {
            return unquoted.strip_suffix(quote).unwrap_or(unquoted).to_owned();
        }
    }
    value
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `checkmk.dat` as the bakery writes it: the agent file header, then the
    /// hash, with CRLF line endings throughout.
    const CHECKMK_DAT: &str = concat!(
        "# Created by Check_MK Agent Bakery.\r\n",
        "# This file is managed via WATO, do not edit manually or you\r\n",
        "# lose your changes next time when you update the agent.\r\n",
        "\r\n",
        "hash: 0123456789abcdef\r\n",
    );

    #[test]
    fn test_parse_key_value() {
        assert_eq!(
            parse_key_value(CHECKMK_DAT),
            HashMap::from([(String::from("hash"), String::from("0123456789abcdef"))])
        );
    }

    #[test]
    fn test_parse_key_value_skips_what_is_no_pair() {
        assert_eq!(
            parse_key_value("\r\n   \r\n# key: commented out\r\nno colon here\r\n"),
            HashMap::new()
        );
    }

    #[test]
    fn test_parse_key_value_splits_at_the_first_colon() {
        assert_eq!(
            parse_key_value("a: b: c"),
            HashMap::from([(String::from("a"), String::from("b: c"))])
        );
    }

    #[test]
    fn test_parse_key_value_keeps_the_last_of_repeated_keys() {
        assert_eq!(
            parse_key_value("hash: first\r\nhash: second\r\n"),
            HashMap::from([(String::from("hash"), String::from("second"))])
        );
    }

    #[test]
    fn test_parse_key_value_strips_a_trailing_comment() {
        assert_eq!(
            parse_key_value("hash: abc # and the rest is a comment\r\n"),
            HashMap::from([(String::from("hash"), String::from("abc"))])
        );
    }

    #[test]
    fn test_parse_value() {
        assert_eq!(parse_value("  abc  "), "abc");
        assert_eq!(parse_value("a,b,c"), "abc");
        assert_eq!(parse_value("'abc'"), "abc");
        assert_eq!(parse_value("\"abc\""), "abc");
        // A missing closing quote must not cost the value its last character.
        assert_eq!(parse_value("'abc"), "abc");
        assert_eq!(parse_value("\"abc"), "abc");
        // The outer quotes decide, the inner ones are part of the value.
        assert_eq!(parse_value("'\"abc\"'"), "\"abc\"");
        assert_eq!(parse_value(""), "");
        assert_eq!(parse_value("'"), "");
    }
}
