// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use anyhow::Result;
use std::borrow::Borrow;
use std::collections::HashMap;

pub const UTC_DATE_FIELD: &str = "utc_date";

#[derive(Hash, PartialEq, Eq, Debug, Copy, Clone)]
pub enum Id {
    IoStats,
}

pub mod query {
    pub const IO_STATS: &str = r"WITH iostat_file AS (
                SELECT con_id,
                    filetype_name,
                    SUM(large_read_reqs) large_read_reqs,
                    SUM(large_read_servicetime) large_read_servicetime,
                    SUM(large_write_reqs) large_write_reqs,
                    SUM(large_write_servicetime) large_write_servicetime,
                    SUM(small_read_reqs) small_read_reqs,
                    SUM(small_read_servicetime) small_read_servicetime,
                    SUM(small_sync_read_reqs) small_sync_read_reqs,
                    SUM(small_write_reqs) small_write_reqs,
                    SUM(small_write_servicetime) small_write_servicetime,
                    SUM(small_read_megabytes * 1024 * 1024) small_read_bytes,
                    SUM(large_read_megabytes * 1024 * 1024) large_read_bytes,
                    SUM(small_write_megabytes * 1024 * 1024) small_write_bytes,
                    SUM(large_write_megabytes * 1024 * 1024) large_write_bytes
                FROM v$iostat_file
                GROUP BY con_id,
                    filetype_name
            )
            SELECT upper(
                    DECODE(
                        d.cdb,
                        'NO',
                        i.instance_name,
                        i.instance_name || '.' || vd.name
                    )
                )
                {sep} 'iostat_file'
                {sep} filetype_name
                {sep} small_read_reqs
                {sep} large_read_reqs
                {sep} small_write_reqs
                {sep} large_write_reqs
                {sep} small_read_servicetime
                {sep} large_read_servicetime
                {sep} small_write_servicetime
                {sep} large_write_servicetime
                {sep} small_read_bytes
                {sep} large_read_bytes
                {sep} small_write_bytes
                {sep} large_write_bytes
            FROM iostat_file io
                JOIN v$containers vd ON io.con_id = vd.con_id
                JOIN v$instance i ON 1 = 1
                JOIN v$database d ON 1 = 1
            ORDER BY vd.con_id,
                io.filetype_name";
}

lazy_static::lazy_static! {
    static ref QUERY_MAP: HashMap<Id, &'static str > = HashMap::from([
        (Id::IoStats, query::IO_STATS),
    ]);
}

pub fn find_known_query<T: Borrow<Id>>(query_id: T) -> Result<&'static str> {
    QUERY_MAP
        .get(query_id.borrow())
        .copied()
        .ok_or(anyhow::anyhow!(
            "Query for {:?} not found",
            query_id.borrow()
        ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Separator, SqlQuery};

    #[test]
    fn test_find_query() {
        let q = SqlQuery::new(find_known_query(Id::IoStats).unwrap(), Separator::default());
        assert!(!q.as_str().is_empty());
    }
}
