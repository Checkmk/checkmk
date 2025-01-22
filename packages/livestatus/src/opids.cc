// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/opids.h"

#include <functional>
#include <ostream>
#include <ranges>
#include <stdexcept>
#include <unordered_map>
#include <utility>

#include "livestatus/RegExp.h"

using namespace std::string_view_literals;

namespace {
// NOLINTNEXTLINE(cert-err58-cpp)
const std::unordered_map<std::string_view, RelationalOperator> fl_from_string =
    {{"="sv, RelationalOperator::equal},
     {"!="sv, RelationalOperator::not_equal},
     {"~"sv, RelationalOperator::matches},
     {"!~"sv, RelationalOperator::doesnt_match},
     {"=~"sv, RelationalOperator::equal_icase},
     {"!=~"sv, RelationalOperator::not_equal_icase},
     {"~~"sv, RelationalOperator::matches_icase},
     {"!~~"sv, RelationalOperator::doesnt_match_icase},
     {"<"sv, RelationalOperator::less},
     {"!<"sv, RelationalOperator::greater_or_equal},
     {">="sv, RelationalOperator::greater_or_equal},
     {"!>="sv, RelationalOperator::less},
     {">"sv, RelationalOperator::greater},
     {"!>"sv, RelationalOperator::less_or_equal},
     {"<="sv, RelationalOperator::less_or_equal},
     {"!<="sv, RelationalOperator::greater}};
}  // namespace

std::ostream &operator<<(std::ostream &os, const RelationalOperator &relOp) {
    // Slightly inefficient, but this doesn't matter for our purposes. We could
    // use Boost.Bimap or use 2 maps if really necessary.
    auto it = std::ranges::find_if(fl_from_string, [&](const auto &strAndOp) {
        return strAndOp.second == relOp;
    });
    return it == fl_from_string.cend() ? os : (os << it->first);
}

RelationalOperator relationalOperatorForName(std::string_view name) {
    auto it = fl_from_string.find(name);
    if (it == fl_from_string.end()) {
        throw std::runtime_error("invalid operator '" + std::string{name} +
                                 "'");
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
