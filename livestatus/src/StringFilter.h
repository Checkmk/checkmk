// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringFilter_h
#define StringFilter_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <memory>
#include <optional>
#include <string>
#include "ColumnFilter.h"
#include "Filter.h"
#include "contact_fwd.h"
#include "opids.h"
class RegExp;
class Row;
class StringColumn;

class StringFilter : public ColumnFilter {
public:
    StringFilter(Kind kind, const StringColumn &column,
                 RelationalOperator relOp, const std::string &value);
    bool accepts(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;

private:
    const StringColumn &_column;
    std::shared_ptr<RegExp> _regExp;
};

#endif  // StringFilter_h
