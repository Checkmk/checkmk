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

#ifndef ListFilter_h
#define ListFilter_h

#include "config.h"  // IWYU pragma: keep
#include <algorithm>
#include <chrono>
#include <memory>
#include <optional>
#include <string>
#include <vector>
#include "ColumnFilter.h"
#include "Filter.h"
#include "ListColumn.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class RegExp;

class ListFilter : public ColumnFilter {
public:
    ListFilter(Kind kind, const ListColumn &column, RelationalOperator relOp,
               const std::string &value);
    bool accepts(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;

private:
    const ListColumn &_column;
    std::shared_ptr<RegExp> _regExp;

    template <typename UnaryPredicate>
    bool any(Row row, const contact *auth_user,
             std::chrono::seconds timezone_offset, UnaryPredicate pred) const {
        auto val = _column.getValue(row, auth_user, timezone_offset);
        return std::any_of(val.begin(), val.end(), pred);
    }
};

#endif  // ListFilter_h
