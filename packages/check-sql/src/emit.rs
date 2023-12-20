// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

const PREFIX: &str = "mssql";

pub fn header(name: &str, separator: Option<char>) -> String {
    match separator {
        Some(s) => {
            let sep = s as u8;
            format!("<<<{PREFIX}_{name}:sep({sep:0>2})>>>\n")
        }
        None => format!("<<<{PREFIX}_{name}>>>\n"),
    }
}

pub fn piggyback_header(name: &str) -> String {
    format!("<<<<{name}>>>>\n")
}

pub fn piggyback_footer() -> String {
    piggyback_header("")
}

#[cfg(test)]
mod test {
    use super::*;
    #[test]
    fn test_header() {
        assert_eq!(header("name", Some('\n')), "<<<mssql_name:sep(10)>>>\n");
        assert_eq!(header("name", Some('\t')), "<<<mssql_name:sep(09)>>>\n");
        assert_eq!(header("name", Some('|')), "<<<mssql_name:sep(124)>>>\n");
        assert_eq!(header("name", None), "<<<mssql_name>>>\n");
    }

    #[test]
    fn test_piggyback() {
        assert_eq!(piggyback_header("name"), "<<<<name>>>>\n");
        assert_eq!(piggyback_footer(), "<<<<>>>>\n");
    }
}
