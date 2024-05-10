// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{ComputerName, InstanceName};

use super::sqls::find_known_query;
use super::{client::Client, sqls};
use std::borrow::Borrow;

use anyhow::Result;
use std::time::Instant;

use tiberius::{ColumnData, Query, Row};

pub type Answer = Vec<Row>;

pub trait Column<'a> {
    fn get_bigint_by_idx(&self, idx: usize) -> i64;
    fn get_bigint_by_name(&self, idx: &str) -> i64;
    fn get_value_by_idx(&self, idx: usize) -> String;
    fn get_optional_value_by_idx(&self, idx: usize) -> Option<String>;
    fn get_value_by_name(&self, idx: &str) -> String;
    fn get_optional_value_by_name(&self, idx: &str) -> Option<String>;
    fn get_all(self, sep: char) -> String;
}

impl<'a> Column<'a> for Row {
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
    client: &mut Client,
    id: T,
) -> Result<Vec<Answer>> {
    let start = Instant::now();
    let result = _run_known_query(client, id.borrow()).await;
    log_query(start, &result, format!("{:?}", id.borrow()).as_str());
    result
}

/// Runs any query
/// return Vec\<Vec\<Row\>\> as a Results Vec: one Vec\<Row\> per one statement in query.
pub async fn run_custom_query<T: AsRef<str>>(client: &mut Client, query: T) -> Result<Vec<Answer>> {
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

fn log_query(start: Instant, result: &Result<Vec<Answer>>, query_body: &str) {
    let total = (Instant::now() - start).as_millis();
    match result {
        Ok(_) => log::info!("Query [SUCCESS], took {total} ms, `{query_body}`"),
        Err(err) => {
            log::info!("Query [ERROR], took {total} ms, error: `{err}`, query: `{query_body}`",)
        }
    }
}

async fn _run_known_query<T: Borrow<sqls::Id>>(client: &mut Client, id: T) -> Result<Vec<Answer>> {
    log::debug!("Query name: `{:?}`", id.borrow());
    let query = find_known_query(id)?;
    exec_sql(client, query).await
}

async fn exec_sql(client: &mut Client, query: &str) -> Result<Vec<Answer>> {
    log::debug!("Query to run short: `{}`", make_short_query(query));
    log::trace!("Query to run: `{}`", query);
    let stream = Query::new(query).query(client).await?;
    let rows: Vec<Answer> = stream.into_results().await?;
    Ok(rows)
}

fn make_short_query(query: &str) -> &str {
    query
        .get(0..std::cmp::min(16, query.len() - 1))
        .unwrap_or_default()
}

pub async fn obtain_computer_name(client: &mut Client) -> Result<Option<ComputerName>> {
    let rows = run_known_query(client, sqls::Id::ComputerName).await?;
    if rows.is_empty() || rows[0].is_empty() {
        log::warn!("Computer name not found with query computer_name");
        return Ok(None);
    }
    let row = &rows[0];
    Ok(row[0]
        .try_get::<&str, usize>(0)
        .ok()
        .flatten()
        .map(str::to_string)
        .map(|s| s.into()))
}

pub async fn obtain_instance_name(client: &mut Client) -> Result<Option<InstanceName>> {
    let rows = run_custom_query(client, "select @@ServiceName").await?;
    if rows.is_empty() || rows[0].is_empty() {
        log::warn!("Instance name not found with query");
        return Ok(None);
    }
    let row = &rows[0];
    Ok(row[0]
        .try_get::<&str, usize>(0)
        .ok()
        .flatten()
        .map(str::to_string)
        .map(|s| s.into()))
}

pub async fn obtain_system_user(client: &mut Client) -> Result<Option<String>> {
    let rows = run_custom_query(client, "select System_User").await?;
    if rows.is_empty() || rows[0].is_empty() {
        log::warn!("Can't obtain system user with query `select SystemUser`");
        return Ok(None);
    }
    let row = &rows[0];
    Ok(row[0]
        .try_get::<&str, usize>(0)
        .ok()
        .flatten()
        .map(str::to_string))
}
