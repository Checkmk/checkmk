// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "DictFilter.h"

#include <algorithm>
#include <cstddef>
#include <tuple>
#include <unordered_map>
#include <utility>

#include "RegExp.h"
#include "Row.h"

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

DictFilter::DictFilter(Kind kind, std::string columnName, function_type f,
                       RelationalOperator relOp, const std::string &value)
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

bool DictFilter::accepts(Row row, const contact * /* auth_user */,
                         std::chrono::seconds /* timezone_offset */) const {
    auto cvm = f_(row);
    auto it = cvm.find(ref_varname_);
    auto act_string = it == cvm.end() ? "" : it->second;
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::equal_icase:
            return regExp_->match(act_string);
        case RelationalOperator::not_equal:
        case RelationalOperator::not_equal_icase:
            return !regExp_->match(act_string);
        case RelationalOperator::matches:
        case RelationalOperator::matches_icase:
            return regExp_->search(act_string);
        case RelationalOperator::doesnt_match:
        case RelationalOperator::doesnt_match_icase:
            return !regExp_->search(act_string);
            // FIXME: The cases below are nonsense for UTF-8...
        case RelationalOperator::less:
            return act_string < ref_string_;
        case RelationalOperator::greater_or_equal:
            return act_string >= ref_string_;
        case RelationalOperator::greater:
            return act_string > ref_string_;
        case RelationalOperator::less_or_equal:
            return act_string <= ref_string_;
    }
    return false;  // unreachable
}

std::unique_ptr<Filter> DictFilter::copy() const {
    return std::make_unique<DictFilter>(*this);
}

std::unique_ptr<Filter> DictFilter::negate() const {
    return std::make_unique<DictFilter>(
        kind(), columnName(), f_, negateRelationalOperator(oper()), value());
}
