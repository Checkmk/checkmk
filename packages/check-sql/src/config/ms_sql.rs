// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

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
            auth: Authentication {},
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
pub struct Authentication {}

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

    #[test]
    fn test_config_default() {
        assert_eq!(
            Config::default(),
            Config {
                auth: Authentication {},
                conn: None,
                sqls: None,
                instance_filter: None,
                mode: Mode::Port,
                instances: vec![],
            }
        );
    }
}
