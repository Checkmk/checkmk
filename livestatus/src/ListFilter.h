// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListFilter_h
#define ListFilter_h

#include "config.h"  // IWYU pragma: keep

#include <algorithm>
#include <chrono>
#include <functional>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

#include "ColumnFilter.h"
#include "Filter.h"
#include "Row.h"
#include "opids.h"
class RegExp;
class Logger;
class User;

class ListFilter : public ColumnFilter {
    using value_type = std::vector<std::string>;
    using f0_t = std::function<value_type(Row)>;
    using f1_t = std::function<value_type(Row, const User &)>;
    using f2_t = std::function<value_type(Row, std::chrono::seconds)>;
    using f3_t =
        std::function<value_type(Row, const User &, std::chrono::seconds)>;
    using function_type = std::variant<f0_t, f1_t, f2_t, f3_t>;

public:
    ListFilter(Kind kind, std::string columnName, function_type,
               RelationalOperator relOp, const std::string &value, Logger *);
    [[nodiscard]] bool accepts(
        Row row, const User &user,
        std::chrono::seconds timezone_offset) const override;
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
             UnaryPredicate pred) const {
        auto val = value_type{};
        if (std::holds_alternative<f0_t>(f_)) {
            val = std::get<f0_t>(f_)(row);
        } else if (std::holds_alternative<f1_t>(f_)) {
            val = std::get<f1_t>(f_)(row, user);
        } else if (std::holds_alternative<f2_t>(f_)) {
            val = std::get<f2_t>(f_)(row, timezone_offset);
        } else if (std::holds_alternative<f3_t>(f_)) {
            val = std::get<f3_t>(f_)(row, user, timezone_offset);
        } else {
            throw std::runtime_error("unreachable");
        }
        return std::any_of(val.begin(), val.end(), pred);
    }
};

#endif  // ListFilter_h
