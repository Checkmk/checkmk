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

#include "CustomVarsDictFilter.h"
#include <algorithm>
#include <cstddef>
#include <tuple>
#include <unordered_map>
#include <utility>
#include "CustomVarsDictColumn.h"
#include "Filter.h"
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

CustomVarsDictFilter::CustomVarsDictFilter(Kind kind,
                                           const CustomVarsDictColumn &column,
                                           RelationalOperator relOp,
                                           const std::string &value)
    : ColumnFilter(kind, column, relOp, value), _column(column) {
    std::string rest;
    auto [starts_with_quote1, pos1] = skip_whitespace(value);
    std::tie(_ref_varname, rest) = starts_with_quote1
                                       ? parse_quoted(value, pos1 + 1)
                                       : parse_unquoted(value, pos1);
    auto [starts_with_quote2, pos2] = skip_whitespace(rest);
    _ref_string = starts_with_quote2 ? parse_quoted(rest, pos2 + 1).first
                                     : rest.substr(pos2);
    _regExp = makeRegExpFor(oper(), _ref_string);
}

bool CustomVarsDictFilter::accepts(
    Row row, const contact * /* auth_user */,
    std::chrono::seconds /* timezone_offset */) const {
    auto cvm = _column.getValue(row);
    auto it = cvm.find(_ref_varname);
    auto act_string = it == cvm.end() ? "" : it->second;
    switch (oper()) {
        case RelationalOperator::equal:
        case RelationalOperator::equal_icase:
            return _regExp->match(act_string);
        case RelationalOperator::not_equal:
        case RelationalOperator::not_equal_icase:
            return !_regExp->match(act_string);
        case RelationalOperator::matches:
        case RelationalOperator::matches_icase:
            return _regExp->search(act_string);
        case RelationalOperator::doesnt_match:
        case RelationalOperator::doesnt_match_icase:
            return !_regExp->search(act_string);
            // FIXME: The cases below are nonsense for UTF-8...
        case RelationalOperator::less:
            return act_string < _ref_string;
        case RelationalOperator::greater_or_equal:
            return act_string >= _ref_string;
        case RelationalOperator::greater:
            return act_string > _ref_string;
        case RelationalOperator::less_or_equal:
            return act_string <= _ref_string;
    }
    return false;  // unreachable
}

std::unique_ptr<Filter> CustomVarsDictFilter::copy() const {
    return std::make_unique<CustomVarsDictFilter>(*this);
}

std::unique_ptr<Filter> CustomVarsDictFilter::negate() const {
    return std::make_unique<CustomVarsDictFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
