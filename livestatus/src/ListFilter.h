// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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
