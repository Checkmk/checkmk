// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use super::defines::{defaults, keys, values};
use super::yaml::{Get, Yaml};
use anyhow::{anyhow, Result};
use std::fmt;

#[derive(PartialEq, Debug, Clone)]
pub enum Role {
    SysDba,
    SysOper,
    SysBackup,
    SysDG,
    SysKM,
    SysASM,
}

impl Role {
    pub fn from_yaml(auth: &Yaml) -> Option<Self> {
        auth.get_string(keys::ROLE)
            .and_then(|role| Role::new(role.as_str()))
    }
    pub fn new(value: &str) -> Option<Self> {
        match str::to_ascii_lowercase(value).as_ref() {
            values::SYS_DBA => Some(Self::SysDba),
            values::SYS_OPER => Some(Self::SysOper),
            values::SYS_BACKUP => Some(Self::SysBackup),
            values::SYS_DG => Some(Self::SysDG),
            values::SYS_KM => Some(Self::SysKM),
            values::SYS_ASM => Some(Self::SysASM),
            "" => {
                log::info!("No role specified");
                None
            }
            _ => {
                log::error!("Invalid role {value}");
                None
            }
        }
    }
}
impl fmt::Display for Role {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::SysDba => write!(f, "{}", values::SYS_DBA),
            Self::SysOper => write!(f, "{}", values::SYS_OPER),
            Self::SysBackup => write!(f, "{}", values::SYS_BACKUP),
            Self::SysDG => write!(f, "{}", values::SYS_DG),
            Self::SysKM => write!(f, "{}", values::SYS_KM),
            Self::SysASM => write!(f, "{}", values::SYS_ASM),
        }
    }
}
#[derive(PartialEq, Debug, Clone)]
pub struct Authentication {
    username: String,
    password: Option<String>,
    auth_type: AuthType,
    role: Option<Role>,
}

impl Default for Authentication {
    fn default() -> Self {
        Self {
            username: "".to_owned(),
            password: None,
            auth_type: AuthType::default(),
            role: None,
        }
    }
}
impl Authentication {
    pub fn from_yaml(yaml: &Yaml) -> Result<Self> {
        let auth = yaml.get(keys::AUTHENTICATION);
        if auth.is_badvalue() {
            anyhow::bail!("authentication is missing");
        }

        let auth_type = AuthType::try_from(
            auth.get_string(keys::TYPE)
                .as_deref()
                .unwrap_or(defaults::AUTH_TYPE),
        )?;
        let role = Role::from_yaml(auth);
        if auth_type == AuthType::Os {
            Ok(Self {
                username: String::new(),
                password: None,
                auth_type,
                role,
            })
        } else {
            Ok(Self {
                username: auth.get_string(keys::USERNAME).unwrap_or_default(),
                password: auth.get_string(keys::PASSWORD),
                auth_type,
                role,
            })
        }
    }
    pub fn username(&self) -> &str {
        &self.username
    }
    pub fn password(&self) -> Option<&String> {
        self.password.as_ref()
    }
    pub fn auth_type(&self) -> &AuthType {
        &self.auth_type
    }

    pub fn role(&self) -> Option<&Role> {
        self.role.as_ref()
    }
}

#[derive(PartialEq, Debug, Clone)]
pub enum AuthType {
    Standard,
    Os,
    Wallet,
}

impl Default for AuthType {
    fn default() -> Self {
        Self::Standard
    }
}

impl TryFrom<&str> for AuthType {
    type Error = anyhow::Error;

    fn try_from(val: &str) -> Result<Self> {
        match str::to_ascii_lowercase(val).as_ref() {
            values::STANDARD => Ok(AuthType::Standard),
            values::OS => Ok(AuthType::Os),
            values::WALLET => Ok(AuthType::Wallet),
            _ => Err(anyhow!("unsupported auth type `{val}`")),
        }
    }
}

impl fmt::Display for AuthType {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            AuthType::Standard => write!(f, "{}", values::STANDARD),
            AuthType::Os => write!(f, "{}", values::OS),
            AuthType::Wallet => write!(f, "{}", values::WALLET),
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::yaml::test_tools::create_yaml;
    mod data {
        pub const AUTHENTICATION_FULL: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "standard"
  role: sysdba
"#;
        pub const AUTHENTICATION_OS: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "os"
"#;
        pub const AUTHENTICATION_MINI: &str = r#"
authentication:
  username: "foo"
  _password: "bar"
  _type: "system"
"#;
    }

    #[test]
    fn test_authentication_from_yaml() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_FULL)).unwrap();
        assert_eq!(a.username(), "foo");
        assert_eq!(a.password(), Some(&"bar".to_owned()));
        assert_eq!(a.auth_type(), &AuthType::Standard);
        assert_eq!(a.role(), Some(&Role::SysDba));
    }
    #[test]
    fn test_authentication_role() {
        pub const AUTHENTICATION_FIRST: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "standard"
  role: "#;
        let test_set: Vec<(&str, Option<&Role>)> = vec![
            ("", None),
            ("aaa", None),
            ("SYSdba", Some(&Role::SysDba)),
            ("sysoper", Some(&Role::SysOper)),
            ("sysbackup", Some(&Role::SysBackup)),
            ("sysdg", Some(&Role::SysDG)),
            ("syskm", Some(&Role::SysKM)),
            ("sysasm", Some(&Role::SysASM)),
        ];
        for (role, expected) in test_set {
            let a =
                Authentication::from_yaml(&create_yaml(AUTHENTICATION_FIRST.to_string() + role))
                    .unwrap();
            assert_eq!(a.role(), expected);
        }
    }

    #[test]
    fn test_authentication_from_yaml_empty() {
        assert!(Authentication::from_yaml(&create_yaml(r"authentication:")).is_ok());
    }

    #[test]
    fn test_authentication_from_yaml_no_username() {
        assert!(Authentication::from_yaml(&create_yaml(
            r#"
authentication:
  _username: 'aa'
"#
        ))
        .is_ok());
    }

    #[test]
    fn test_authentication_from_yaml_mini() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_MINI)).unwrap();
        assert_eq!(a.username(), "");
        assert_eq!(a.password(), None);
        assert_eq!(a.auth_type(), &AuthType::Os);
    }

    #[test]
    fn test_authentication_from_yaml_integrated() {
        let a = Authentication::from_yaml(&create_yaml(data::AUTHENTICATION_OS)).unwrap();
        assert_eq!(a.username(), "");
        assert_eq!(a.password(), None);
        assert_eq!(a.auth_type(), &AuthType::Os);
    }
}
