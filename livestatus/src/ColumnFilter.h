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

#ifndef ColumnFilter_h
#define ColumnFilter_h

#include "config.h"  // IWYU pragma: keep
#include <functional>
#include <memory>
#include <ostream>
#include <string>
#include <utility>
#include "Column.h"
#include "Filter.h"
#include "opids.h"

class ColumnFilter : public Filter {
public:
    ColumnFilter(Kind kind, const Column &column, RelationalOperator relOp,
                 std::string value)
        : Filter(kind)
        , _column(column)
        , _relOp(relOp)
        , _value(std::move(value)) {}
    [[nodiscard]] std::string columnName() const { return _column.name(); }
    [[nodiscard]] RelationalOperator oper() const { return _relOp; }
    [[nodiscard]] std::string value() const { return _value; }
    std::unique_ptr<Filter> partialFilter(
        std::function<bool(const Column &)> predicate) const override;
    [[nodiscard]] bool is_tautology() const override;
    [[nodiscard]] bool is_contradiction() const override;
    [[nodiscard]] Filters disjuncts() const override;
    [[nodiscard]] Filters conjuncts() const override;

private:
    const Column &_column;
    const RelationalOperator _relOp;
    const std::string _value;

    std::ostream &print(std::ostream &os) const override;
};

#endif  // ColumnFilter_h
