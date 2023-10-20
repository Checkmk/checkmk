// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

pub fn header(name: &str, separator: Option<char>) -> String {
    match separator {
        Some(s) => {
            let sep = s as u8;
            format!("<<<{name}:sep({sep:0>2})>>>\n")
        }
        None => format!("<<<{name}>>>\n"),
    }
}

#[cfg(test)]
mod test {
    use super::*;
    #[test]
    fn test_header() {
        assert_eq!(header("name", Some('\n')), "<<<name:sep(10)>>>\n");
        assert_eq!(header("name", Some('\t')), "<<<name:sep(09)>>>\n");
        assert_eq!(header("name", Some('|')), "<<<name:sep(124)>>>\n");
        assert_eq!(header("name", None), "<<<name>>>\n");
    }
}
