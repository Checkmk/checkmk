// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/DictFilter.h"

#include <algorithm>
#include <cstddef>
#include <tuple>
#include <utility>

#include "livestatus/DoubleFilter.h"
#include "livestatus/RegExp.h"
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
    : ColumnFilter{kind, std::move(columnName), relOp, value}
    , f_{std::move(f)} {
    std::string rest;
    auto [starts_with_quote1, pos1] = skip_whitespace(value);
    std::tie(ref_varname_, rest) = starts_with_quote1
                                       ? parse_quoted(value, pos1 + 1)
                                       : parse_unquoted(value, pos1);
    auto [starts_with_quote2, pos2] = skip_whitespace(rest);
    ref_string_ = starts_with_quote2 ? parse_quoted(rest, pos2 + 1).first
                                     : rest.substr(pos2);
    regExp_ = makeRegExpFor(oper(), ref_string_);
}

bool DictStrValueFilter::accepts(Row row, const User &user,
                                 std::chrono::seconds timezone_offset) const {
    auto filter = StringFilter{
        kind(),
        columnName(),
        [this](Row row) {
            auto cvm = f_(row);
            auto it = cvm.find(ref_varname_);
            return it == cvm.end() ? "" : it->second;
        },
        oper(),
        ref_string_,
    };
    return filter.accepts(row, user, timezone_offset);
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
    : ColumnFilter{kind, std::move(columnName), relOp, value}
    , f_{std::move(f)}
    , logger_{logger} {
    std::string rest;
    auto [starts_with_quote1, pos1] = skip_whitespace(value);
    std::tie(ref_varname_, rest) = starts_with_quote1
                                       ? parse_quoted(value, pos1 + 1)
                                       : parse_unquoted(value, pos1);
    auto [starts_with_quote2, pos2] = skip_whitespace(rest);
    ref_value_ = starts_with_quote2 ? parse_quoted(rest, pos2 + 1).first
                                    : rest.substr(pos2);
}

bool DictDoubleValueFilter::accepts(
    Row row, const User &user, std::chrono::seconds timezone_offset) const {
    auto filter = DoubleFilter{kind(),
                               columnName(),
                               [this](Row row) {
                                   auto cvm = f_(row);
                                   auto it = cvm.find(ref_varname_);
                                   return it == cvm.end() ? 0.0 : it->second;
                               },
                               oper(),
                               ref_value_,
                               logger()};
    return filter.accepts(row, user, timezone_offset);
}

std::unique_ptr<Filter> DictDoubleValueFilter::copy() const {
    return std::make_unique<DictDoubleValueFilter>(*this);
}

std::unique_ptr<Filter> DictDoubleValueFilter::negate() const {
    return std::make_unique<DictDoubleValueFilter>(
        kind(), columnName(), f_, negateRelationalOperator(oper()), value(),
        logger());
}
