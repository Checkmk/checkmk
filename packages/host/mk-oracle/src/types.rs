// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use derive_more::{Display, From, Into};

#[derive(PartialEq, PartialOrd, Debug, Clone, From, Into)]
pub struct Port(pub u16);

impl Port {
    pub fn value(&self) -> u16 {
        self.0
    }
}

impl std::fmt::Display for Port {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.value())
    }
}

#[derive(PartialEq, From, Into, Debug, Clone)]
pub struct MaxConnections(pub u32);

#[derive(PartialEq, From, Debug, Clone)]
pub struct MaxQueries(pub u32);

#[derive(PartialEq, From, Debug, Display, Clone, Default, Into, Hash, Eq)]
pub struct InstanceName(String);

impl From<&str> for InstanceName {
    fn from(s: &str) -> Self {
        InstanceName(s.to_string())
    }
}

#[derive(PartialEq, From, Clone, Debug, Display, Default)]
pub struct InstanceId(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct InstanceEdition(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct InstanceVersion(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct InstanceCluster(String);

// used once, may be removed in the future
impl<'a> From<&'a InstanceCluster> for &'a str {
    fn from(instance_cluster: &'a InstanceCluster) -> &'a str {
        instance_cluster.0.as_str()
    }
}

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct ComputerName(String);

// used once, may be removed in the future
impl<'a> From<&'a ComputerName> for &'a str {
    fn from(computer_name: &'a ComputerName) -> &'a str {
        computer_name.0.as_str()
    }
}

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct ConfigHash(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into, Hash, Eq)]
pub struct PiggybackHostName(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct InstanceAlias(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct HostName(String);

/// this is a string as defined by Tiberius API
#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct CertPath(String);

#[derive(PartialEq, Debug, Clone)]
pub enum Edition {
    Azure,
    Normal,
    Undefined,
}
