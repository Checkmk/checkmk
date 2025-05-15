// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

#[cfg(windows)]
use crate::constants::ODBC_CONNECTION_TIMEOUT;
use crate::platform::Block;

#[cfg(windows)]
use crate::platform::odbc;

use crate::types::{ComputerName, Edition, InstanceName};

use super::client::ManageEdition;
use super::sqls::find_known_query;
use super::{client::UniClient, sqls};
use std::borrow::Borrow;

use anyhow::Result;
use std::time::Instant;

use tiberius::{ColumnData, Query, Row};

pub type SqlRows = Vec<Row>;
pub enum UniAnswer {
    Rows(SqlRows),
    Block(Block),
}

impl UniAnswer {
    pub fn is_empty(&self) -> bool {
        match self {
            UniAnswer::Rows(rows) => rows.is_empty(),
            UniAnswer::Block(block) => block.is_empty(),
        }
    }

    pub fn get_node_names(&self) -> String {
        match self {
            UniAnswer::Rows(rows) => rows
                .iter()
                .map(|r| r.get_value_by_name("nodename"))
                .collect::<Vec<String>>(),
            UniAnswer::Block(block) => block
                .rows
                .iter()
                .map(|r| block.get_value_by_name(r, "nodename"))
                .collect::<Vec<String>>(),
        }
        .join(",")
    }
    pub fn get_active_node(&self) -> String {
        match self {
            UniAnswer::Rows(rows) => rows.last().map(|r| r.get_value_by_name("active_node")),
            UniAnswer::Block(b) => b.last().map(|r| b.get_value_by_name(r, "active_node")),
        }
        .unwrap_or_default()
    }

    pub fn get_is_clustered(&self) -> bool {
        match self {
            UniAnswer::Rows(rows) => rows.first().map(|r| r.get_value_by_name("is_clustered")),
            UniAnswer::Block(b) => b.first().map(|r| b.get_value_by_name(r, "is_clustered")),
        }
        .unwrap_or("0".to_owned())
            != "0"
    }
}

pub trait Column<'a> {
    fn get_bigint_by_idx(&self, idx: usize) -> i64;
    fn get_bigint_by_name(&self, idx: &str) -> i64;
    fn get_value_by_idx(&self, idx: usize) -> String;
    fn get_optional_value_by_idx(&self, idx: usize) -> Option<String>;
    fn get_value_by_name(&self, idx: &str) -> String;
    fn get_optional_value_by_name(&self, idx: &str) -> Option<String>;
    fn get_all(self, sep: char) -> String;
}

impl Column<'_> for Row {
    fn get_bigint_by_idx(&self, idx: usize) -> i64 {
        self.try_get::<i64, usize>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
    }

    fn get_bigint_by_name(&self, idx: &str) -> i64 {
        self.try_get::<i64, &str>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
    }

    fn get_value_by_idx(&self, idx: usize) -> String {
        self.try_get::<&str, usize>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
            .to_string()
    }

    fn get_optional_value_by_idx(&self, idx: usize) -> Option<String> {
        self.try_get::<&str, usize>(idx)
            .unwrap_or_default()
            .map(str::to_string)
    }

    fn get_value_by_name(&self, idx: &str) -> String {
        self.try_get::<&str, &str>(idx)
            .unwrap_or_default()
            .unwrap_or_default()
            .to_string()
    }

    fn get_optional_value_by_name(&self, idx: &str) -> Option<String> {
        self.try_get::<&str, &str>(idx)
            .unwrap_or_default()
            .map(str::to_string)
    }

    /// more or less correct method to extract all data from the tiberius.Row
    /// unfortunately tiberius::Row implements only into_iter -> we are using `self``, not `&self``
    fn get_all(self, sep: char) -> String {
        self.into_iter()
            .map(|c| match c {
                ColumnData::Guid(v) => v
                    .map(|v| format!("{{{}}}", v.to_string().to_uppercase()))
                    .unwrap_or_default(),
                ColumnData::I16(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::I32(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::F32(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::F64(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::Bit(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::U8(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::String(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                ColumnData::Numeric(v) => v.map(|v| v.to_string()).unwrap_or_default(),
                _ => format!("Unsupported '{:?}'", c),
            })
            .collect::<Vec<String>>()
            .join(&sep.to_string())
    }
}

/// Runs predefined query
/// return Vec\<Vec\<Row\>\> as a Results Vec: one Vec\<Row\> per one statement in query.
pub async fn run_known_query<T: Borrow<sqls::Id>>(
    client: &mut UniClient,
    id: T,
) -> Result<Vec<UniAnswer>> {
    let start = Instant::now();
    let result = _run_known_query(client, id.borrow()).await;
    log_query(start, &result, format!("{:?}", id.borrow()).as_str());
    result
}

/// Runs any query
/// return Vec\<Vec\<Row\>\> as a Results Vec: one Vec\<Row\> per one statement in query.
pub async fn run_custom_query<T: AsRef<str>>(
    client: &mut UniClient,
    query: T,
) -> Result<Vec<UniAnswer>> {
    let query = query.as_ref();
    if query.is_empty() {
        anyhow::bail!("Empty custom query");
    }
    let start = Instant::now();
    let result = exec_sql(client, query).await;
    log_query(start, &result, make_short_query(query));
    log::trace!("Full query: `{}`", query);
    result
}

fn log_query(start: Instant, result: &Result<Vec<UniAnswer>>, query_body: &str) {
    let total = (Instant::now() - start).as_millis();
    match result {
        Ok(_) => log::info!("Query [SUCCESS], took {total} ms, `{query_body}`"),
        Err(err) => {
            log::info!("Query [ERROR], took {total} ms, error: `{err}`, query: `{query_body}`",)
        }
    }
}

async fn _run_known_query<T: Borrow<sqls::Id>>(
    client: &mut UniClient,
    id: T,
) -> Result<Vec<UniAnswer>> {
    log::debug!("Query name: `{:?}`", id.borrow());
    let query = find_known_query(id, &client.get_edition())?;
    exec_sql(client, query).await
}

async fn exec_sql(client: &mut UniClient, query: &str) -> Result<Vec<UniAnswer>> {
    log::debug!("Query to run short: `{}`", make_short_query(query));
    log::trace!("Query to run: `{}`", query);
    match client {
        UniClient::Std(client) => {
            let stream = Query::new(query).query(client.client()).await?;
            let tiberius_rows: Vec<Vec<Row>> = stream.into_results().await?;
            let answers: Vec<UniAnswer> = tiberius_rows.into_iter().map(UniAnswer::Rows).collect();
            Ok(answers)
        }
        UniClient::Odbc(client) => {
            #[cfg(windows)]
            {
                let blocks =
                    odbc::execute(client.conn_string(), query, Some(ODBC_CONNECTION_TIMEOUT))?;
                let answers: Vec<UniAnswer> = blocks.into_iter().map(UniAnswer::Block).collect();
                Ok(answers)
            }
            #[cfg(unix)]
            anyhow::bail!("ODBC is not supported for now `{}`", client.conn_string());
        }
    }
}

fn make_short_query(query: &str) -> &str {
    query
        .get(0..std::cmp::min(16, query.len() - 1))
        .unwrap_or_default()
}

pub async fn obtain_computer_name(client: &mut UniClient) -> Result<Option<ComputerName>> {
    let answers = run_known_query(client, sqls::Id::ComputerName).await?;
    let result = match answers.first() {
        Some(UniAnswer::Rows(rows)) => get_first_row_column(rows, 0),
        Some(UniAnswer::Block(block)) => block.get_first_row_column(0),
        None => None,
    };
    if result.is_none() {
        log::warn!("Computer name not found with query computer_name");
    };
    Ok(result.map(ComputerName::from))
}

fn get_first_row(answers: &[UniAnswer]) -> Option<String> {
    match answers.first() {
        Some(UniAnswer::Rows(rows)) => get_first_row_column(rows, 0),
        Some(UniAnswer::Block(block)) => block.get_first_row_column(0),
        None => None,
    }
}

pub async fn obtain_server_edition(client: &mut UniClient) -> Result<Edition> {
    let answers =
        run_custom_query(client, "SELECT CAST(SERVERPROPERTY('Edition') AS NVARCHAR)").await?;
    let result = get_first_row(&answers);
    if &result.unwrap_or_default() == "SQL Azure" {
        log::info!("Azure detected");
        Ok(Edition::Azure)
    } else {
        Ok(Edition::Normal)
    }
}

pub async fn obtain_instance_name(client: &mut UniClient) -> Result<InstanceName> {
    let answers = match client.get_edition() {
        Edition::Azure => run_custom_query(client,
        "SELECT CAST(ISNULL(ISNULL(SERVERPROPERTY('InstanceName'), SERVERPROPERTY('FilestreamShareName')), SERVERPROPERTY('ServerName')) AS NVARCHAR)"
        ).await?,
        Edition::Normal => run_custom_query(client, "select @@ServiceName").await?,
        Edition::Undefined => { anyhow::bail!("Edition is not defined") }
    };

    let name = get_first_row(&answers).unwrap_or("???".to_string());
    if &name == "???" {
        log::error!("Instance name is unknown");
    }

    Ok(InstanceName::from(name))
}

pub async fn obtain_system_user(client: &mut UniClient) -> Result<Option<String>> {
    let answers = run_custom_query(client, "select System_User").await?;
    let result = match answers.first() {
        Some(UniAnswer::Rows(rows)) => get_first_row_column(rows, 0),
        Some(UniAnswer::Block(block)) => block.get_first_row_column(0),
        None => None,
    };
    if result.is_none() {
        log::warn!("Can't obtain system user with query `select SystemUser`");
    };
    Ok(result)
}

pub fn get_first_row_column(rows: &[Row], column: usize) -> Option<String> {
    rows.first().and_then(|r| {
        r.try_get::<&str, usize>(column)
            .ok()
            .flatten()
            .map(str::to_string)
    })
}
