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

#include "opids.h"
#include <algorithm>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include "RegExp.h"

namespace {
std::unordered_map<std::string, RelationalOperator> fl_from_string = {
    {"=", RelationalOperator::equal},
    {"!=", RelationalOperator::not_equal},
    {"~", RelationalOperator::matches},
    {"!~", RelationalOperator::doesnt_match},
    {"=~", RelationalOperator::equal_icase},
    {"!=~", RelationalOperator::not_equal_icase},
    {"~~", RelationalOperator::matches_icase},
    {"!~~", RelationalOperator::doesnt_match_icase},
    {"<", RelationalOperator::less},
    {"!<", RelationalOperator::greater_or_equal},
    {">=", RelationalOperator::greater_or_equal},
    {"!>=", RelationalOperator::less},
    {">", RelationalOperator::greater},
    {"!>", RelationalOperator::less_or_equal},
    {"<=", RelationalOperator::less_or_equal},
    {"!<=", RelationalOperator::greater}};
}  // namespace

std::ostream &operator<<(std::ostream &os, const RelationalOperator &relOp) {
    // Slightly inefficient, but this doesn't matter for our purposes. We could
    // use Boost.Bimap or use 2 maps if really necessary.
    auto it =
        std::find_if(fl_from_string.cbegin(), fl_from_string.cend(),
                     [&](auto &strAndOp) { return strAndOp.second == relOp; });
    return it == fl_from_string.cend() ? os : (os << it->first);
}

RelationalOperator relationalOperatorForName(const std::string &name) {
    auto it = fl_from_string.find(name);
    if (it == fl_from_string.end()) {
        throw std::runtime_error("invalid operator '" + name + "'");
    }
    return it->second;
}

RelationalOperator negateRelationalOperator(RelationalOperator relOp) {
    switch (relOp) {
        case RelationalOperator::equal:
            return RelationalOperator::not_equal;
        case RelationalOperator::not_equal:
            return RelationalOperator::equal;
        case RelationalOperator::matches:
            return RelationalOperator::doesnt_match;
        case RelationalOperator::doesnt_match:
            return RelationalOperator::matches;
        case RelationalOperator::equal_icase:
            return RelationalOperator::not_equal_icase;
        case RelationalOperator::not_equal_icase:
            return RelationalOperator::equal_icase;
        case RelationalOperator::matches_icase:
            return RelationalOperator::doesnt_match_icase;
        case RelationalOperator::doesnt_match_icase:
            return RelationalOperator::matches_icase;
        case RelationalOperator::less:
            return RelationalOperator::greater_or_equal;
        case RelationalOperator::greater_or_equal:
            return RelationalOperator::less;
        case RelationalOperator::greater:
            return RelationalOperator::less_or_equal;
        case RelationalOperator::less_or_equal:
            return RelationalOperator::greater;
    }
    return RelationalOperator::equal;  // unreachable
}

std::unique_ptr<RegExp> makeRegExpFor(RelationalOperator relOp,
                                      const std::string &value) {
    switch (relOp) {
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            return std::make_unique<RegExp>(
                value,
                (relOp == RelationalOperator::matches_icase ||
                 relOp == RelationalOperator::doesnt_match_icase)
                    ? RegExp::Case::ignore
                    : RegExp::Case::respect,
                RegExp::Syntax::pattern);
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
            return std::make_unique<RegExp>(
                value,
                (relOp == RelationalOperator::equal_icase ||
                 relOp == RelationalOperator::not_equal_icase)
                    ? RegExp::Case::ignore
                    : RegExp::Case::respect,
                RegExp::Syntax::literal);
        case RelationalOperator::less:
        case RelationalOperator::greater_or_equal:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            return nullptr;
    }
    return nullptr;  // make the compiler happy...
}
