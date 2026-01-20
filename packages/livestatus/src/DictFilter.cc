// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/DictFilter.h"

#include <algorithm>
#include <cstddef>
#include <memory>
#include <type_traits>
#include <utility>

#include "livestatus/DoubleFilter.h"
#include "livestatus/Row.h"
#include "livestatus/StringFilter.h"
#include "livestatus/opids.h"

namespace {
constexpr const char *whitespace = " \t\n\v\f\r";
constexpr char quote = '\'';

bool is_quote_at(const std::string &str, size_t pos) {
    return pos < str.size() && str[pos] == quote;
}

std::pair<bool, size_t> skip_whitespace(const std::string &str) {
    auto pos = std::min(str.find_first_not_of(whitespace), str.size());
    return {is_quote_at(str, pos), pos};
}

// the parsed entity plus the rest of the string following it
using parse_result = std::pair<std::string, std::string>;

parse_result parse_quoted(const std::string &str, size_t start) {
    std::string result;
    result.reserve(str.size() - start);
    while (true) {
        auto pos = str.find(quote, start);
        if (pos == std::string::npos) {
            // missing terminating quote: just take the rest
            return {result + str.substr(start), ""};
        }
        if (!is_quote_at(str, pos + 1)) {
            // a quote without another quote directly following it: stop
            return {result + str.substr(start, pos - start),
                    str.substr(pos + 1)};
        }
        // two consecutive quotes mean a single quote
        result += str.substr(start, pos + 1 - start);
        start = pos + 2;
    }
    return {{}, {}};  // unreachable
}

parse_result parse_unquoted(const std::string &str, size_t start) {
    auto pos = std::min(str.find_first_of(whitespace, start), str.size());
    return {str.substr(start, pos - start), str.substr(pos)};
}
}  // namespace

DictStrValueFilter::DictStrValueFilter(Kind kind, std::string columnName,
                                       function_type f,
                                       RelationalOperator relOp,
                                       const std::string &value)
    : ColumnFilter{kind, columnName, relOp, value}
    , f_{std::move(f)}
    , filter_{[this, kind, columnName = std::move(columnName), relOp, &value] {
        auto [starts_with_quote1, pos1] = skip_whitespace(value);
        auto [ref_varname, rest] = starts_with_quote1
                                       ? parse_quoted(value, pos1 + 1)
                                       : parse_unquoted(value, pos1);
        auto [starts_with_quote2, pos2] = skip_whitespace(rest);
        const auto ref_string = starts_with_quote2
                                    ? parse_quoted(rest, pos2 + 1).first
                                    : rest.substr(pos2);
        return StringFilter{
            kind,
            columnName,
            [get_col = f_, ref_varname = std::move(ref_varname)](Row row) {
                auto cvm = get_col(row);
                auto it = cvm.find(ref_varname);
                return it == cvm.end() ? "" : it->second;
            },
            relOp,
            ref_string,
        };
    }()} {}

bool DictStrValueFilter::accepts(Row row, const User &user,
                                 std::chrono::seconds timezone_offset,
                                 const ICore &core) const {
    return filter_.accepts(row, user, timezone_offset, core);
}

std::unique_ptr<Filter> DictStrValueFilter::copy() const {
    return std::make_unique<DictStrValueFilter>(*this);
}

std::unique_ptr<Filter> DictStrValueFilter::negate() const {
    return std::make_unique<DictStrValueFilter>(
        kind(), columnName(), f_, negateRelationalOperator(oper()), value());
}

DictDoubleValueFilter::DictDoubleValueFilter(Kind kind, std::string columnName,
                                             function_type f,
                                             RelationalOperator relOp,
                                             const std::string &value,
                                             Logger *logger)
    : ColumnFilter{kind, columnName, relOp, value}
    , f_{std::move(f)}
    , filter_{[this, kind, columnName = std::move(columnName), &value, logger] {
        auto [starts_with_quote1, pos1] = skip_whitespace(value);
        auto [ref_varname, rest] = starts_with_quote1
                                       ? parse_quoted(value, pos1 + 1)
                                       : parse_unquoted(value, pos1);
        auto [starts_with_quote2, pos2] = skip_whitespace(rest);
        const auto ref_value = starts_with_quote2
                                   ? parse_quoted(rest, pos2 + 1).first
                                   : rest.substr(pos2);
        return DoubleFilter{
            kind,
            columnName,
            [get_col = f_, ref_varname = std::move(ref_varname)](Row row) {
                auto cvm = get_col(row);
                auto it = cvm.find(ref_varname);
                return it == cvm.end() ? 0.0 : it->second;
            },
            oper(),
            ref_value,
            logger};
    }()}
    , logger_(logger) {}

bool DictDoubleValueFilter::accepts(Row row, const User &user,
                                    std::chrono::seconds timezone_offset,
                                    const ICore &core) const {
    return filter_.accepts(row, user, timezone_offset, core);
}

std::unique_ptr<Filter> DictDoubleValueFilter::copy() const {
    return std::make_unique<DictDoubleValueFilter>(*this);
}

std::unique_ptr<Filter> DictDoubleValueFilter::negate() const {
    return std::make_unique<DictDoubleValueFilter>(
        kind(), columnName(), f_, negateRelationalOperator(oper()), value(),
        logger());
}
