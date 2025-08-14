// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::PiggybackHostName;

const PREFIX: &str = "oracle";

pub fn header(name: &str, separator: char) -> String {
    let sep = separator as u8;
    format!("<<<{PREFIX}_{name}:sep({sep:0>2})>>>")
}

pub fn signaling_header(name: &str) -> String {
    format!("<<<{PREFIX}_{name}>>>")
}

pub fn piggyback_header(piggyback_host_name: &PiggybackHostName) -> String {
    format!("<<<<{piggyback_host_name}>>>>")
}

pub fn piggyback_footer() -> String {
    piggyback_header(&"".to_string().into())
}
