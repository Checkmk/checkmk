// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef Table_h
#define Table_h

#include "config.h"  // IWYU pragma: keep
#include <map>
#include <memory>
#include <string>
#include <utility>
#include "Row.h"
#include "contact_fwd.h"
class Column;
class DynamicColumn;
class Logger;
class MonitoringCore;
class Query;

// NOTE: This macro leads to undefined behaviour for non-POD/non-standard-layout
// classes, e.g. Entity, Host, etc., nevertheless we have to use it below. :-/
#define DANGEROUS_OFFSETOF(typename, member) \
    (reinterpret_cast<size_t>(&(reinterpret_cast<typename *>(32))->member) - 32)

/// A table-like view for some underlying data, exposed via LQL.
class Table {
public:
    explicit Table(MonitoringCore *mc);
    virtual ~Table();

    void addColumn(std::unique_ptr<Column> col);
    void addDynamicColumn(std::unique_ptr<DynamicColumn> dyncol);

    template <typename Predicate>
    bool any_column(Predicate pred) const {
        for (auto &c : _columns) {
            if (pred(c.second)) {
                return true;
            }
        }
        return false;
    }

    /// The name of the table, as used in the GET command.
    virtual std::string name() const = 0;

    /// \brief An optional prefix for column names.
    ///
    /// \todo Due to the way multisite works, column names are sometimes
    /// prefixed by a variation of the table name (e.g. "hosts" => "host_"), but
    /// the logic for this really shouldn't live on the cmc side. Furthermore,
    /// multisite sometimes even seems to use a *sequence* of prefixes, which is
    /// yet another a bug. Instead of fixing it there, it is currently papered
    /// over on the cmc side. :-/
    virtual std::string namePrefix() const = 0;

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
    virtual std::shared_ptr<Column> column(std::string colname) const;

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
    virtual void answerQuery(Query *query) = 0;
    virtual bool isAuthorized(Row row, const contact *ctc) const;
    virtual Row findObject(const std::string &objectspec) const;

    template <typename T>
    const T *rowData(Row row) const {
        return row.rawData<T>();
    }

    MonitoringCore *core() const { return _mc; }
    Logger *logger() const;

private:
    MonitoringCore *_mc;

    std::unique_ptr<Column> dynamicColumn(const std::string &name,
                                          const std::string &rest) const;

    std::map<std::string, std::shared_ptr<Column>> _columns;
    std::map<std::string, std::unique_ptr<DynamicColumn>> _dynamic_columns;
};

#endif  // Table_h
