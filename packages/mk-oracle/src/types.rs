// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::defines::defaults::DEFAULT_SEP;
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

#[derive(PartialEq, Debug, Display, Clone, Default, Into, Hash, Eq)]
pub struct InstanceName(String);

impl From<&str> for InstanceName {
    fn from(s: &str) -> Self {
        Self(s.to_string().to_uppercase())
    }
}

impl InstanceName {
    fn is_asm(&self) -> bool {
        self.0.starts_with("+")
    }

    pub fn is_suitable_affinity(&self, affinity: &SectionAffinity) -> bool {
        match affinity {
            SectionAffinity::All => true,
            SectionAffinity::Db => !self.is_asm(),
            SectionAffinity::Asm => self.is_asm(),
        }
    }
}
impl From<&String> for InstanceName {
    fn from(s: &String) -> Self {
        Self(s.clone().to_uppercase())
    }
}

#[derive(PartialEq, Debug, Clone)]
pub enum SectionAffinity {
    All,
    Db,
    Asm,
}

#[derive(PartialEq, From, Debug, Display, Clone, Default, Into, Hash, Eq)]
pub struct ServiceName(String);

impl From<&str> for ServiceName {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

#[derive(PartialEq, From, Clone, Debug, Display)]
pub struct ServiceType(String);
impl From<&str> for ServiceType {
    fn from(s: &str) -> Self {
        Self(s.to_string())
    }
}

#[derive(PartialEq, From, Clone, Debug, Display, Default)]
pub struct InstanceId(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct InstanceEdition(String);

#[derive(PartialEq, From, Clone, Debug, Display, Default, Into)]
pub struct InstanceVersion(String);

#[derive(PartialEq, From, Clone, Copy, Debug, Display, Default, Into, PartialOrd)]
pub struct InstanceNumVersion(u32);

#[derive(PartialEq, Eq, Debug, Copy, Clone)]
pub enum Tenant {
    All,
    Cdb,
    NoCdb,
}

#[derive(PartialEq, Eq, Debug, Copy, Clone)]
pub enum AsmInstance {
    Yes,
    No,
}

impl Tenant {
    pub fn new(tenant: &str) -> Self {
        match tenant.to_lowercase().as_str() {
            "all" => Tenant::All,
            "cdb" | "yes" => Tenant::Cdb,
            "nocdb" | "no" => Tenant::NoCdb,
            _ => panic!("Unknown tenant type: {}", tenant),
        }
    }
}

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

#[derive(PartialEq, From, Clone, Debug, Display, Hash, Eq, Into)]
pub struct SectionName(String);

impl SectionName {
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug)]
pub struct Credentials {
    pub user: String,
    pub password: String,
}

#[derive(Debug, Clone, PartialEq, Eq, From)]
pub enum Separator {
    No,
    Comma,
    Decorated(char),
}

impl Default for Separator {
    fn default() -> Self {
        Separator::Decorated(DEFAULT_SEP)
    }
}

pub type SqlBindParam = (String, u8);

#[derive(Debug, Clone, PartialEq, Eq, From)]
pub struct SqlQuery {
    text: String,
    separator: Separator,
    params: Vec<SqlBindParam>,
}

impl SqlQuery {
    pub fn new<T: AsRef<str> + Sized>(s: T, separator: Separator, params: &[SqlBindParam]) -> Self {
        let p: Vec<SqlBindParam> = params
            .iter()
            .filter_map(|(k, v)| {
                if s.as_ref().contains((":".to_string() + k).as_str()) {
                    Some((k.clone(), *v))
                } else {
                    None
                }
            })
            .collect();
        match separator {
            Separator::No => Self {
                text: s.as_ref().to_owned(),
                separator: crate::types::Separator::No,
                params: p,
            },
            Separator::Comma => Self {
                text: use_sep(s.as_ref(), ","),
                separator: Separator::Comma,
                params: p,
            },
            Separator::Decorated(c) => Self {
                text: use_sep(s, format!("|| '{}' ||", c).as_str()),
                separator: Separator::Decorated(c),
                params: p,
            },
        }
    }
    pub fn params(&self) -> &Vec<SqlBindParam> {
        &self.params
    }

    pub fn as_str(&self) -> &str {
        &self.text
    }

    pub fn sep(&self) -> Option<char> {
        match &self.separator {
            Separator::No => None,
            Separator::Comma => None,
            Separator::Decorated(c) => Some(*c),
        }
    }
}
fn use_sep<T: AsRef<str>>(s: T, sep: &str) -> String {
    s.as_ref().replace("{sep}", sep)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_instance_name() {
        assert_eq!(&InstanceName::from("teST").to_string(), "TEST");
    }

    #[test]
    fn test_sql_query() {
        assert_eq!(
            SqlQuery::new("a {sep} b", Separator::No, &[]).as_str(),
            "a {sep} b"
        );
        assert_eq!(
            SqlQuery::new("a {sep} b", Separator::Comma, &[]).as_str(),
            "a , b"
        );
        assert_eq!(
            SqlQuery::new("a {sep} b", Separator::default(), &[]).as_str(),
            "a || '|' || b"
        );
        assert_eq!(
            SqlQuery::new("a {sep} b", Separator::Decorated('x'), &[]).as_str(),
            "a || 'x' || b"
        );
    }
    #[test]
    fn test_sql_query_params() {
        let params = vec![("AAA".to_string(), 1), ("BBB".to_string(), 2)];
        assert_eq!(
            SqlQuery::new("a {sep} b", Separator::No, &params).params(),
            &Vec::new()
        );
        assert_eq!(
            SqlQuery::new("AAA {sep} b", Separator::No, &params).params(),
            &Vec::new()
        );
        assert_eq!(
            SqlQuery::new(":AAA {sep} b", Separator::No, &params).params(),
            &vec![("AAA".to_string(), 1)]
        );
        assert_eq!(
            SqlQuery::new(":AAA {sep} b :BBB", Separator::No, &params).params(),
            &params
        );
    }

    #[test]
    fn test_make_query() {
        const QUERY: &str = "a{sep}b{sep}c";
        assert_eq!(use_sep(QUERY, ","), "a,b,c");
    }

    #[test]
    fn test_tenant() {
        assert_eq!(Tenant::new("all"), Tenant::All);
        assert_eq!(Tenant::new("cdb"), Tenant::Cdb);
        assert_eq!(Tenant::new("nocdb"), Tenant::NoCdb);
        assert_eq!(Tenant::new("yEs"), Tenant::Cdb);
        assert_eq!(Tenant::new("no"), Tenant::NoCdb);
        // panic on unknown tenant
        let result = std::panic::catch_unwind(|| Tenant::new("unknown"));
        assert!(result.is_err());
    }

    #[test]
    fn test_affinity() {
        assert!(InstanceName::from("+X").is_asm());
        assert!(!InstanceName::from("X").is_asm());
    }

    #[test]
    fn test_instance_affinity() {
        assert!(!InstanceName::from("+X").is_suitable_affinity(&SectionAffinity::Db));
        assert!(InstanceName::from("+X").is_suitable_affinity(&SectionAffinity::All));
        assert!(InstanceName::from("+X").is_suitable_affinity(&SectionAffinity::Asm));
        assert!(InstanceName::from("X").is_suitable_affinity(&SectionAffinity::Db));
        assert!(InstanceName::from("X").is_suitable_affinity(&SectionAffinity::All));
        assert!(!InstanceName::from("X").is_suitable_affinity(&SectionAffinity::Asm));
    }
}
