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

use crate::config::ora_sql::CustomService;
use crate::config::{
    authentication::{AuthType, Authentication, Role},
    connection::EngineTag,
    ora_sql::Endpoint,
};
use crate::ora_sql::types::Target;
use crate::types::{Credentials, InstanceName, SqlQuery};
use anyhow::{Context, Result};
use oracle::sql_type::{FromSql, ToSql};
use oracle::{Connection, Connector, Privilege};
use std::marker::PhantomData;

#[derive(Debug)]
pub struct StdEngine {
    connection: Option<Connection>,
}

impl Clone for StdEngine {
    fn clone(&self) -> Self {
        StdEngine { connection: None }
    }
}

pub trait OraDbEngine: Send {
    fn connect(&mut self, target: &Target, instance: Option<&InstanceName>) -> Result<()>;

    fn close(&mut self) -> Result<()>;

    fn query_table(&self, query: &SqlQuery) -> QueryResult;

    fn clone_box(&self) -> Box<dyn OraDbEngine + Send + Sync>;
}

impl OraDbEngine for StdEngine {
    fn connect(&mut self, target: &Target, instance_name: Option<&InstanceName>) -> Result<()> {
        if self.connection.is_some() {
            log::warn!("Connection already established, closing the previous connection.");
            return Ok(());
        }

        let connection_string = target.make_connection_string(instance_name);
        log::info!("Connection string: {}", connection_string);
        log::info!("Auth type: {:?}", target.auth.auth_type());

        let mut connector = match target.auth.auth_type() {
            AuthType::Standard => {
                // Standard authentication with username and password
                let username = target.auth.username();
                let password = target.auth.password().unwrap_or("");
                log::info!("Using standard authentication with user: {}", username);
                Connector::new(username, password, &connection_string)
            }
            AuthType::Os | AuthType::Wallet => {
                // OS/Wallet authentication - use external auth with empty credentials
                log::info!("Using Wallet/OS authentication (external auth)");
                let mut conn = Connector::new("", "", &connection_string);
                conn.external_auth(true);
                conn
            }
        };

        if let Some(role) = target.auth.role() {
            log::info!("Using role: {}", role);
            connector.privilege(_to_privilege(role));
        }

        self.connection = Some(connector.connect()?);

        Ok(())
    }

    fn close(&mut self) -> Result<()> {
        if let Some(conn) = self.connection.take() {
            conn.close()?;
        }
        Ok(())
    }

    fn query_table(&self, query: &SqlQuery) -> QueryResult {
        fn _query_table(
            connection: Option<&Connection>,
            query: &SqlQuery,
        ) -> Result<Vec<Vec<String>>> {
            let conn = connection.ok_or_else(|| anyhow::anyhow!("No connection established"))?;
            let x = query
                .params()
                .iter()
                .map(|(k, v)| {
                    let z: &dyn ToSql = v;
                    (k.as_str(), z)
                })
                .collect::<Vec<(&str, &dyn ToSql)>>();

            Ok(conn
                .query_named(query.as_str(), x.as_slice())?
                .map(|row| row_to_vector(&row))
                .collect::<Vec<Vec<String>>>())
        }

        let result = _query_table(self.connection.as_ref(), query);

        QueryResult(result)
    }

    fn clone_box(&self) -> Box<dyn OraDbEngine + Send + Sync> {
        Box::new(self.clone())
    }
}

impl Clone for Box<dyn OraDbEngine + Send + Sync> {
    fn clone(&self) -> Box<dyn OraDbEngine + Send + Sync> {
        self.clone_box()
    }
}

fn row_to_vector(row: &oracle::Result<oracle::Row>) -> Vec<String> {
    if let Ok(r) = row {
        r.sql_values()
            .iter()
            .map(|val| {
                if val.is_null().unwrap_or(false) {
                    "".to_string()
                } else {
                    String::from_sql(val).unwrap_or_else(|e| format!("Error: {}", e))
                }
            })
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

#[derive(Debug, Clone)]
pub struct SqlPlusEngine {}

impl OraDbEngine for SqlPlusEngine {
    fn connect(&mut self, _target: &Target, _service_name: Option<&InstanceName>) -> Result<()> {
        anyhow::bail!("Sql*Plus engine is not implemented yet")
    }

    fn close(&mut self) -> Result<()> {
        Ok(()) // No operation needed for Sql*Plus
    }

    fn query_table(&self, _query: &SqlQuery) -> QueryResult {
        let result = Err(anyhow::anyhow!("Sql*Plus engine is not implemented yet"));
        QueryResult(result)
    }
    fn clone_box(&self) -> Box<dyn OraDbEngine + Send + Sync> {
        Box::new(self.clone())
    }
}

#[derive(Debug, Clone)]
pub struct JdbcEngine {}
impl OraDbEngine for JdbcEngine {
    fn connect(&mut self, _target: &Target, _service_name: Option<&InstanceName>) -> Result<()> {
        anyhow::bail!("Jdbc engine is not implemented yet")
    }
    fn close(&mut self) -> Result<()> {
        Ok(()) // No operation needed for Sql*Plus
    }

    fn query_table(&self, _query: &SqlQuery) -> QueryResult {
        let result = Err(anyhow::anyhow!("Sql*Plus engine is not implemented yet"));
        QueryResult(result)
    }
    fn clone_box(&self) -> Box<dyn OraDbEngine + Send + Sync> {
        Box::new(self.clone())
    }
}
#[derive(Debug)]
enum EngineType {
    Std,
    SqlPlus,
    Jdbc,
}

impl EngineType {
    fn create_engine(&self) -> Box<dyn OraDbEngine + Send + Sync> {
        match self {
            EngineType::Std => Box::new(StdEngine { connection: None }),
            EngineType::SqlPlus => Box::new(SqlPlusEngine {}),
            EngineType::Jdbc => Box::new(JdbcEngine {}),
        }
    }
}

#[derive(Default)]
pub struct SpotBuilder {
    target: Option<Target>,
    engine_type: Option<EngineType>,
    custom_engine: Option<Box<dyn OraDbEngine>>,
    database: Option<String>,
}

pub struct Closed;
pub struct Opened;

pub type OpenedSpot = Spot<Opened>;
pub type ClosedSpot = Spot<Closed>;

pub struct Spot<State: Send> {
    pub target: Target,
    engine: Box<dyn OraDbEngine + Send + Sync>,
    _database: Option<String>,
    _state: PhantomData<State>,
}

impl Clone for Spot<Closed> {
    fn clone(&self) -> Self {
        Spot {
            target: self.target.clone(),
            engine: self.engine.clone(),
            _database: self._database.clone(),
            _state: PhantomData::<Closed>,
        }
    }
}

impl Spot<Closed> {
    pub fn connect(mut self, use_instance: Option<&InstanceName>) -> Result<Spot<Opened>> {
        log::info!(
            "{} {:?} -> {}",
            "Connecting to",
            self.target,
            self.target.make_connection_string(use_instance)
        );
        self.engine.connect(&self.target, use_instance)?;
        Ok(Spot {
            target: self.target,
            engine: self.engine,
            _database: self._database,
            _state: PhantomData::<Opened>,
        })
    }
    pub fn target(&self) -> &Target {
        &self.target
    }

    pub fn database(&self) -> Option<&String> {
        self._database.as_ref()
    }
}

pub struct QueryResult(pub Result<Vec<Vec<String>>>);

impl QueryResult {
    pub fn format(self, sep: &str) -> Result<Vec<String>> {
        let result: Vec<String> = self
            .0?
            .into_iter()
            .map(|row| row.join(sep))
            .collect::<Vec<String>>();

        Ok(result)
    }
}

impl Spot<Opened> {
    pub fn close(mut self) -> Spot<Closed> {
        if let Err(e) = self.engine.close() {
            log::error!("Failed to close the engine: {}", e);
        };

        Spot {
            target: self.target,
            engine: self.engine,
            _database: self._database,
            _state: PhantomData::<Closed>,
        }
    }

    pub fn query_table(&self, query: &SqlQuery) -> QueryResult {
        self.engine.query_table(query)
    }

    pub fn target(&self) -> &Target {
        &self.target
    }

    pub fn database(&self) -> Option<&String> {
        self._database.as_ref()
    }
}

impl SpotBuilder {
    pub fn new() -> SpotBuilder {
        SpotBuilder::default()
    }

    pub fn database<S: Into<String>>(mut self, database: Option<S>) -> Self {
        self.database = database.map(|d| d.into());
        self
    }

    pub fn endpoint_target(mut self, endpoint: &Endpoint) -> Self {
        self.target = Some(Target {
            host: endpoint.hostname().clone(),
            service_name: endpoint.conn().service_name().map(|n| n.to_owned()),
            service_type: endpoint.conn().service_type().map(|t| t.to_owned()),
            instance_name: endpoint.conn().instance_name().map(|i| i.to_owned()),
            alias: None,
            port: endpoint.conn().port().clone(),
            auth: endpoint.auth().clone(),
        });
        self
    }

    pub fn custom_instance_target(mut self, instance: &CustomService) -> Self {
        let ep = &instance.endpoint();
        self.target = Some(Target {
            host: ep.hostname().clone(),
            service_name: Some(instance.service_name().clone()),
            service_type: ep.conn().service_type().map(|t| t.to_owned()),
            instance_name: ep.conn().instance_name().map(|t| t.to_owned()),
            alias: instance.alias().clone(),
            port: ep.conn().port().clone(),
            auth: ep.auth().clone(),
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

    pub fn custom_engine(mut self, engine: Box<dyn OraDbEngine>) -> Self {
        self.custom_engine = Some(engine);
        self
    }

    pub fn build(self) -> Result<ClosedSpot> {
        Ok(Spot {
            engine: self
                .engine_type
                .map(|e| e.create_engine())
                .or(self.custom_engine.map(|v| v.clone_box()))
                .context("Engine is not defined")?,
            target: self
                .target
                .ok_or_else(|| anyhow::anyhow!("Target is absent"))?,
            _database: self.database,
            _state: PhantomData::<Closed>,
        })
    }
}

pub fn make_spot(endpoint: &Endpoint) -> Result<ClosedSpot> {
    SpotBuilder::new()
        .endpoint_target(endpoint)
        .engine_type(endpoint.conn().engine_tag())
        .build()
}

pub fn make_custom_spot(instance: &CustomService) -> Result<ClosedSpot> {
    SpotBuilder::new()
        .custom_instance_target(instance)
        .engine_type(instance.endpoint().conn().engine_tag())
        .build()
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
       service_name: XE
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
        assert!(make_spot(&config.endpoint()).is_ok());
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
