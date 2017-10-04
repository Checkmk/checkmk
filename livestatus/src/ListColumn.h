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

#ifndef ListColumn_h
#define ListColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include <string>
#include "Column.h"
#include "opids.h"
class Filter;
class Row;

class ListColumn : public Column {
public:
    /// Given a row, does a given list-valued column contain a given element?
    class Contains {
    public:
        virtual ~Contains();
        virtual bool operator()(Row row) = 0;
    };

    ListColumn(const std::string &name, const std::string &description,
               int indirect_offset, int extra_offset, int extra_extra_offset,
               int offset)
        : Column(name, description, indirect_offset, extra_offset,
                 extra_extra_offset, offset) {}
    ColumnType type() const override { return ColumnType::list; }
    virtual std::unique_ptr<Contains> makeContains(
        const std::string &name) const = 0;
    virtual bool isEmpty(Row row) const = 0;
    std::unique_ptr<Filter> createFilter(
        RelationalOperator relOp, const std::string &value) const override;
};

#endif  // ListColumn_h
