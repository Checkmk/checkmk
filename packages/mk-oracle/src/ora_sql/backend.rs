// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::{
    authentication::{AuthType, Authentication, Role},
    connection::EngineTag,
    ora_sql::Endpoint,
};
use crate::ora_sql::types::Target;
use crate::types::{Credentials, InstanceName, SqlQuery};
use anyhow::Context;
use anyhow::Result;
use oracle::sql_type::FromSql;
use oracle::{Connection, Connector, Privilege};

#[derive(Debug)]
pub struct StdEngine {
    connection: Option<Connection>,
}

trait OraDbEngine {
    fn connect(&mut self, target: &Target) -> Result<()>;

    #[allow(dead_code)]
    fn query(&self, query: &SqlQuery, sep: &str) -> Result<Vec<String>>;

    #[allow(dead_code)]
    fn query_table(&self, query: &SqlQuery) -> Result<Vec<Vec<String>>>;
}

impl OraDbEngine for StdEngine {
    fn connect(&mut self, target: &Target) -> Result<()> {
        if self.connection.is_some() {
            return Ok(());
        }
        // Here we would normally establish a connection to the database.
        // For now, we just simulate a successful connection.
        if let Some(role) = target.auth.role() {
            let mut connector = Connector::new(
                target.auth.username(),
                target.auth.password().unwrap_or(""),
                target.make_connection_string(),
            );
            connector.privilege(_to_privilege(role));
            self.connection = Some(connector.connect()?);
        } else {
            self.connection = Some(Connection::connect(
                target.auth.username(),
                target.auth.password().unwrap_or(""),
                target.make_connection_string(),
            )?);
        }

        Ok(())
    }
    fn query(&self, query: &SqlQuery, sep: &str) -> Result<Vec<String>> {
        let conn = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("No connection established"))?;
        let rows = conn.query(query.as_str(), &[])?;
        // Process rows if needed
        let result: Vec<String> = rows
            .map(|row| row_to_string(&row, sep))
            .collect::<Vec<String>>();

        Ok(result)
    }
    fn query_table(&self, query: &SqlQuery) -> Result<Vec<Vec<String>>> {
        let conn = self
            .connection
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("No connection established"))?;
        let rows = conn.query(query.as_str(), &[])?;
        // Process rows if needed
        let result = rows
            .map(|row| row_to_vector(&row))
            .collect::<Vec<Vec<String>>>();

        Ok(result)
    }
}

fn row_to_string(row: &oracle::Result<oracle::Row>, sep: &str) -> String {
    row_to_vector(row).join(sep)
}

fn row_to_vector(row: &oracle::Result<oracle::Row>) -> Vec<String> {
    if let Ok(r) = row {
        r.sql_values()
            .iter()
            .map(|s| String::from_sql(s))
            .map(|s| s.unwrap_or_else(|e| format!("Error: {}", e)))
            .collect::<Vec<String>>()
    } else {
        vec![format!("Error: {}", row.as_ref().err().unwrap())]
    }
}

fn _to_privilege(role: &Role) -> Privilege {
    match role {
        Role::SysDba => Privilege::Sysdba,
        Role::SysOper => Privilege::Sysoper,
        Role::SysASM => Privilege::Sysasm,
        Role::SysBackup => Privilege::Sysbackup,
        Role::SysKM => Privilege::Syskm,
        Role::SysDG => Privilege::Sysdg,
    }
}

#[derive(Debug)]
pub struct SqlPlusEngine {}

impl OraDbEngine for SqlPlusEngine {
    fn connect(&mut self, _target: &Target) -> Result<()> {
        anyhow::bail!("Sql*Plus engine is not implemented yet")
    }
    fn query(&self, _query: &SqlQuery, _sep: &str) -> Result<Vec<String>> {
        anyhow::bail!("Sql*Plus engine is not implemented yet")
    }
    fn query_table(&self, _query: &SqlQuery) -> Result<Vec<Vec<String>>> {
        anyhow::bail!("Sql*Plus engine is not implemented yet")
    }
}

#[derive(Debug)]
pub struct JdbcEngine {}
impl OraDbEngine for JdbcEngine {
    fn connect(&mut self, _target: &Target) -> Result<()> {
        anyhow::bail!("Jdbc engine is not implemented yet")
    }
    fn query(&self, _query: &SqlQuery, _sep: &str) -> Result<Vec<String>> {
        anyhow::bail!("Jdbc engine is not implemented yet")
    }

    fn query_table(&self, _query: &SqlQuery) -> Result<Vec<Vec<String>>> {
        anyhow::bail!("Sql*Plus engine is not implemented yet")
    }
}
#[derive(Debug)]
enum EngineType {
    Std,
    SqlPlus,
    Jdbc,
}

impl EngineType {
    fn create_engine(&self) -> Box<dyn OraDbEngine> {
        match self {
            EngineType::Std => Box::new(StdEngine { connection: None }),
            EngineType::SqlPlus => Box::new(SqlPlusEngine {}),
            EngineType::Jdbc => Box::new(JdbcEngine {}),
        }
    }
}

#[derive(Debug, Default)]
pub struct TaskBuilder {
    target: Option<Target>,
    engine_type: Option<EngineType>,
    database: Option<String>,
}

pub struct Task {
    target: Target,
    engine: Box<dyn OraDbEngine>,
    _database: Option<String>,
}

impl Task {
    pub fn connect(&mut self) -> Result<()> {
        self.engine.connect(&self.target)?;
        Ok(())
    }

    pub fn query(&self, query: &SqlQuery, sep: &str) -> Result<Vec<String>> {
        self.engine.query(query, sep)
    }

    pub fn query_table(&self, query: &SqlQuery) -> Result<Vec<Vec<String>>> {
        self.engine.query_table(query)
    }

    pub fn target(&self) -> &Target {
        &self.target
    }

    pub fn database(&self) -> Option<&String> {
        self._database.as_ref()
    }
}

impl TaskBuilder {
    pub fn new() -> TaskBuilder {
        TaskBuilder::default()
    }

    pub fn database<S: Into<String>>(mut self, database: Option<S>) -> Self {
        self.database = database.map(|d| d.into());
        self
    }

    pub fn target(mut self, endpoint: &Endpoint) -> Self {
        self.target = Some(Target {
            host: endpoint.hostname().clone(),
            instance: endpoint.conn().instance().map(|i| i.to_owned()),
            service_name: endpoint.conn().service_name().map(|n| n.to_owned()),
            service_type: endpoint.conn().service_type().map(|t| t.to_owned()),
            port: endpoint.conn().port().clone(),
            auth: endpoint.auth().clone(),
        });
        self
    }

    pub fn engine_type(mut self, engine_tag: &EngineTag) -> Self {
        self.engine_type = Some(match engine_tag {
            EngineTag::Std | EngineTag::Auto => EngineType::Std,
            EngineTag::SqlPlus => EngineType::SqlPlus,
            EngineTag::Jdbc => EngineType::Jdbc,
        });
        self
    }

    pub fn build(self) -> Result<Task> {
        Ok(Task {
            engine: self
                .engine_type
                .map(|e| e.create_engine())
                .context("Engine is not defined")?,
            target: self
                .target
                .ok_or_else(|| anyhow::anyhow!("Target is absent"))?,
            _database: self.database,
        })
    }
}

pub fn make_task(endpoint: &Endpoint) -> Result<Task> {
    TaskBuilder::new()
        .target(endpoint)
        .engine_type(endpoint.conn().engine_tag())
        .build()
}

pub fn make_custom_task(endpoint: &Endpoint, instance: &InstanceName) -> Result<Task> {
    make_task(endpoint).map(|mut t| {
        t.target.instance = Some(instance.to_owned());
        t
    })
}

pub fn obtain_config_credentials(auth: &Authentication) -> Option<Credentials> {
    match auth.auth_type() {
        AuthType::Standard | AuthType::Wallet => Some(Credentials {
            user: auth.username().to_string(),
            password: auth.password().unwrap_or("").to_string(),
        }),
        AuthType::Os => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ora_sql::Config;

    fn make_config_with_auth_type(auth_type: &str) -> Result<Config> {
        const BASE: &str = r#"
---
oracle:
  main:
    authentication:
       username: "bad_user"
       password: "bad_password"
       type: type_tag
    connection:
       hostname: "localhost" # we use real host to avoid long timeout
       port: 65345 # we use weird port to avoid connection
       instance: XE
       timeout: 1
"#;
        let s = Config::from_string(BASE.replace("type_tag", auth_type))?.unwrap();
        Ok(s)
    }

    #[test]
    fn test_create_client_from_config_for_error() {
        let c = make_config_with_auth_type("bad");
        assert!(c.is_err());
    }

    #[test]
    fn test_create_client_from_config_correct() {
        let config = make_config_with_auth_type("standard").unwrap();
        assert!(make_task(&config.endpoint()).is_ok());
    }

    #[test]
    fn test_obtain_credentials_from_config() {
        assert!(
            obtain_config_credentials(make_config_with_auth_type("os").unwrap().auth()).is_none()
        );
        assert!(make_config_with_auth_type("kerberos").is_err());
        assert!(
            obtain_config_credentials(make_config_with_auth_type("standard").unwrap().auth())
                .is_some()
        );
    }
}
