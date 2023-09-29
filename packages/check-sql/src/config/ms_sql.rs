// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use yaml_rust::Yaml;

mod keys {
    pub const AUTHENTICATION: &str = "authentication";
    pub const USERNAME: &str = "username";
    pub const PASSWORD: &str = "password";
    pub const TYPE: &str = "type";
    pub const ACCESS_TOKEN: &str = "access_token";
    pub const SYSTEM: &str = "system";
    pub const WINDOWS: &str = "windows";
}

#[derive(PartialEq, Debug)]
pub struct Config {
    auth: Authentication,
    conn: Option<Connection>,
    sqls: Option<Sqls>,
    instance_filter: Option<InstanceFilter>,
    mode: Mode,
    instances: Vec<Instance>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            auth: Authentication::default(),
            conn: None,
            sqls: None,
            instance_filter: None,
            mode: Mode::Port,
            instances: vec![],
        }
    }
}

impl Config {
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }
    pub fn conn(&self) -> Option<&Connection> {
        self.conn.as_ref()
    }
    pub fn sqls(&self) -> Option<&Sqls> {
        self.sqls.as_ref()
    }
    pub fn instance_filter(&self) -> Option<&InstanceFilter> {
        self.instance_filter.as_ref()
    }
    pub fn mode(&self) -> &Mode {
        &self.mode
    }
    pub fn instances(&self) -> &Vec<Instance> {
        &self.instances
    }
}

#[derive(PartialEq, Debug)]
pub struct Authentication {
    username: String,
    password: Option<String>,
    auth_type: AuthType,
    access_token: Option<String>,
}

impl Default for Authentication {
    fn default() -> Self {
        Self {
            username: "".to_owned(),
            password: None,
            auth_type: AuthType::System,
            access_token: None,
        }
    }
}
impl Authentication {
    pub fn from_yaml(yaml: &[Yaml]) -> Result<Self, String> {
        let auth = &yaml[0][keys::AUTHENTICATION];
        Ok(Self {
            username: auth[keys::USERNAME]
                .as_str()
                .ok_or("bad/absent username")?
                .to_owned(),
            password: auth[keys::PASSWORD].as_str().map(str::to_string),
            auth_type: match auth[keys::TYPE].as_str().unwrap_or(keys::SYSTEM) {
                keys::SYSTEM => AuthType::System,
                keys::WINDOWS => AuthType::Windows,
                _ => return Err("unknown auth type".to_owned()),
            },
            access_token: auth[keys::ACCESS_TOKEN].as_str().map(str::to_string),
        })
    }
}

#[derive(PartialEq, Debug)]
pub enum AuthType {
    System,
    Windows,
}

#[derive(PartialEq, Debug)]
pub struct Connection {}

#[derive(PartialEq, Debug)]
pub struct Sqls {}

#[derive(PartialEq, Debug)]
pub struct InstanceFilter {}

#[derive(PartialEq, Debug)]
pub enum Mode {
    Port,
    Socket,
    Special,
}

#[derive(PartialEq, Debug)]
pub struct Instance {
    name: String,
    auth: Authentication,
    conn: Option<Connection>,
    alias: String,
    piggyback: Option<Piggyback>,
}

impl Instance {
    pub fn name(&self) -> &String {
        &self.name
    }
    pub fn auth(&self) -> &Authentication {
        &self.auth
    }
    pub fn conn(&self) -> Option<&Connection> {
        self.conn.as_ref()
    }
    pub fn alias(&self) -> &String {
        &self.alias
    }
    pub fn piggyback(&self) -> Option<&Piggyback> {
        self.piggyback.as_ref()
    }
}

#[derive(PartialEq, Debug)]
pub struct Piggyback {
    hostname: String,
    sqls: Option<Sqls>,
}

impl Piggyback {
    pub fn hostname(&self) -> &String {
        &self.hostname
    }

    pub fn sqls(&self) -> Option<&Sqls> {
        self.sqls.as_ref()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use yaml_rust::YamlLoader;

    #[test]
    fn test_config_default() {
        assert_eq!(
            Config::default(),
            Config {
                auth: Authentication::default(),
                conn: None,
                sqls: None,
                instance_filter: None,
                mode: Mode::Port,
                instances: vec![],
            }
        );
    }

    #[test]
    fn test_authentication_from_yaml() {
        assert_eq!(
            Authentication::from_yaml(&create_authentication_yaml_full()).unwrap(),
            Authentication {
                username: "foo".to_owned(),
                password: Some("bar".to_owned()),
                auth_type: AuthType::Windows,
                access_token: Some("baz".to_owned())
            }
        );
    }

    fn create_yaml(source: &str) -> Vec<Yaml> {
        YamlLoader::load_from_str(source).expect("fix test string!")
    }

    fn create_authentication_yaml_full() -> Vec<Yaml> {
        const SOURCE: &str = r#"
authentication:
  username: "foo"
  password: "bar"
  type: "windows"
  access_token: "baz"
"#;
        create_yaml(SOURCE)
    }

    fn create_authentication_yaml_mini() -> Vec<Yaml> {
        const SOURCE: &str = r#"
authentication:
  username: "foo"
  _password: "bar"
  _type: "system"
  _access_token: "baz"
"#;
        create_yaml(SOURCE)
    }

    #[test]
    fn test_authentication_from_yaml_mini() {
        assert_eq!(
            Authentication::from_yaml(&create_authentication_yaml_mini()).unwrap(),
            Authentication {
                username: "foo".to_owned(),
                password: None,
                auth_type: AuthType::System,
                access_token: None
            }
        );
    }
}
