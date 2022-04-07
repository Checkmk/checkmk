// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef StringFilter_h
#define StringFilter_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <optional>
#include <string>

#include "ColumnFilter.h"
#include "Filter.h"
#include "opids.h"
class RegExp;
class Row;
class User;

class StringFilter : public ColumnFilter {
public:
    StringFilter(Kind kind, std::string columnName,
                 std::function<std::string(Row)>, RelationalOperator relOp,
                 const std::string &value);
    [[nodiscard]] bool accepts(
        Row row, const User &user,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;

private:
    const std::function<std::string(Row)> _getValue;
    std::shared_ptr<RegExp> _regExp;
};

#endif  // StringFilter_h
