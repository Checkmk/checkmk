// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use derive_more::{From, Into};

#[derive(PartialEq, Debug, Clone)]
pub struct Port(pub u16);

impl Port {
    pub fn value(&self) -> u16 {
        self.0
    }
}

impl std::fmt::Display for Port {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

#[derive(PartialEq, From, Into, Debug, Clone)]
pub struct MaxConnections(pub u32);

#[derive(PartialEq, From, Debug, Clone)]
pub struct MaxQueries(pub u32);
