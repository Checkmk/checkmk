// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListFilter_h
#define ListFilter_h

// NOTE: IWYU oscillates regarding <algorithm>.
#include <algorithm>  // IWYU pragma: keep
#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "livestatus/ColumnFilter.h"
#include "livestatus/Row.h"

class ICore;
class Logger;
class RegExp;
class User;
enum class RelationalOperator;

class ListFilter : public ColumnFilter {
    using function_type = std::function<std::vector<std::string>(
        Row, const User &, std::chrono::seconds, const ICore &)>;

public:
    ListFilter(Kind kind, std::string columnName, function_type,
               RelationalOperator relOp, const std::string &value, Logger *);
    [[nodiscard]] bool accepts(Row row, const User &user,
                               std::chrono::seconds timezone_offset,
                               const ICore &core) const override;
    [[nodiscard]] std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;
    [[nodiscard]] Logger *logger() const;

private:
    const function_type f_;
    Logger *const _logger;
    std::shared_ptr<RegExp> _regExp;

    template <typename UnaryPredicate>
    bool any(Row row, const User &user, std::chrono::seconds timezone_offset,
             const ICore &core, UnaryPredicate pred) const {
        auto val = f_(row, user, timezone_offset, core);
        return std::any_of(val.begin(), val.end(), pred);
    }
};

#endif  // ListFilter_h
