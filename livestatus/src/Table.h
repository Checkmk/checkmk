// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Table_h
#define Table_h

#include "config.h"  // IWYU pragma: keep

#include <map>
#include <memory>
#include <string>
#include <utility>

#include "Row.h"
class Column;
class DynamicColumn;
class Logger;
class MonitoringCore;
class Query;
class User;

/// A table-like view for some underlying data, exposed via LQL.
///
/// table               | primary key
/// ------------------- | ---------------------------------------
/// columns             | table;name
/// commands            | name
/// comments            | id
/// contactgroups       | name
/// contacts            | name
/// crashreports        | id
/// downtimes           | id
/// eventconsoleevents  | event_id
/// eventconsolehistory | _none, problem: history_line unusable_
/// eventconsolerules   | rule_id
/// eventconsolestatus  | _none, but just a single-row table_
/// hostgroups          | name
/// hosts               | name
/// hostsbygroup        | hostgroup_name;name
/// log                 | time;lineno
/// servicegroups       | name
/// services            | host_name;description
/// servicesbygroup     | servicegroup_name;host_name;description
/// servicesbyhostgroup | hostgroup_name;host_name;description
/// statehist           | _none, totally unclear_
/// status              | _none, but just a single-row table_
/// timeperiods         | name
class Table {
public:
    explicit Table(MonitoringCore *mc);
    virtual ~Table();

    void addColumn(std::unique_ptr<Column> col);
    void addDynamicColumn(std::unique_ptr<DynamicColumn> dyncol);

    template <typename Predicate>
    bool any_column(Predicate pred) const {
        for (const auto &c : _columns) {
            if (pred(c.second)) {
                return true;
            }
        }
        return false;
    }

    /// The name of the table, as used in the GET command.
    [[nodiscard]] virtual std::string name() const = 0;

    /// \brief An optional prefix for column names.
    ///
    /// \todo Due to the way multisite works, column names are sometimes
    /// prefixed by a variation of the table name (e.g. "hosts" => "host_"), but
    /// the logic for this really shouldn't live on the cmc side. Furthermore,
    /// multisite sometimes even seems to use a *sequence* of prefixes, which is
    /// yet another a bug. Instead of fixing it there, it is currently papered
    /// over on the cmc side. :-/
    [[nodiscard]] virtual std::string namePrefix() const = 0;

    /// \brief Retrieve a column with a give name.
    ///
    /// If the name contains a ':' then we have a dynamic column with column
    /// arguments: The part before the colon is the column name of the dynamic
    /// column and the part after it is the name of the fresh, dynamically
    /// created column (up to the 2nd ':') and further arguments. This whole
    /// mechanism is e.g. used to access RRD metrics data.
    ///
    /// \todo This member function is virtual just because TableStateHistory and
    /// TableLog override it for some dubious reason: They first try the normal
    /// lookup, and if that didn't find a column, the lookup is retried with a
    /// "current_" prefix. This logic should probably not live in cmc at all.
    [[nodiscard]] virtual std::shared_ptr<Column> column(
        std::string colname) const;

    // NOTE: We can't make the query argument 'const' right now, because we call
    // the non-const Query::processDataset() member function on it. This is a
    // bit ugly, but only a minor issue: Each Query instance is only accessed in
    // the thread which created it. Splitting up the Query class into a const
    // and a non-const part can probably fix that wart.
    //
    // A much bigger problem is that we can't make answerQuery() itself 'const',
    // because its impementations in TableStateHistory and TableCachedStatehist
    // are non-const. Tables are shared between threads and the locking in the
    // problematic answerQuery() implementations is a "bit" chaotic, so this can
    // be a real correctness problem! This has to be fixed...
    virtual void answerQuery(Query &query, const User &user) = 0;

    [[nodiscard]] virtual Row get(const std::string &primary_key) const;

    // We have funny single-row tables without a primary key!
    [[nodiscard]] virtual Row getDefault() const;

    template <typename T>
    [[nodiscard]] const T *rowData(Row row) const {
        return row.rawData<T>();
    }

    [[nodiscard]] MonitoringCore *core() const { return _mc; }
    [[nodiscard]] Logger *logger() const;

private:
    MonitoringCore *_mc;

    [[nodiscard]] std::unique_ptr<Column> dynamicColumn(
        const std::string &colname, const std::string &rest) const;

    std::map<std::string, std::shared_ptr<Column>> _columns;
    std::map<std::string, std::unique_ptr<DynamicColumn>> _dynamic_columns;
};

#endif  // Table_h
