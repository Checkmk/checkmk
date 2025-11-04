// Copyright (C) 2025 Checkmk GmbH
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

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
