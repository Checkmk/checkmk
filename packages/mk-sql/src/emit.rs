// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::PiggybackHostName;

use super::config::defines::defaults;
const PREFIX: &str = "mssql";

pub fn header(name: &str, separator: char) -> String {
    if separator == defaults::DEFAULT_SEP {
        format!("<<<{PREFIX}_{name}>>>\n")
    } else {
        let sep = separator as u8;
        format!("<<<{PREFIX}_{name}:sep({sep:0>2})>>>\n")
    }
}

pub fn piggyback_header(piggyback_host_name: &PiggybackHostName) -> String {
    format!("<<<<{piggyback_host_name}>>>>\n")
}

pub fn piggyback_footer() -> String {
    piggyback_header(&"".to_string().into())
}

#[cfg(test)]
mod test {
    use super::*;
    #[test]
    fn test_header() {
        assert_eq!(header("name", '\n'), "<<<mssql_name:sep(10)>>>\n");
        assert_eq!(header("name", '\t'), "<<<mssql_name:sep(09)>>>\n");
        assert_eq!(header("name", '|'), "<<<mssql_name:sep(124)>>>\n");
        assert_eq!(header("name", ' '), "<<<mssql_name>>>\n");
    }

    #[test]
    fn test_piggyback() {
        assert_eq!(
            piggyback_header(&"name".to_string().into()),
            "<<<<name>>>>\n"
        );
        assert_eq!(piggyback_footer(), "<<<<>>>>\n");
    }
}
