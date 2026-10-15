// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/opids.h"

#include <array>
#include <iterator>
#include <ostream>
#include <stdexcept>
#include <utility>

#include "livestatus/RegExp.h"

using namespace std::string_view_literals;

namespace {
using OperatorName = std::pair<std::string_view, RelationalOperator>;

// Each operator's canonical name comes before its aliases, and we output only
// the canonical names: The EC doesn't know the aliases.
constexpr auto operator_names = std::to_array<OperatorName>({
    {"="sv, RelationalOperator::equal},
    {"!="sv, RelationalOperator::not_equal},
    {"~"sv, RelationalOperator::matches},
    {"!~"sv, RelationalOperator::doesnt_match},
    {"=~"sv, RelationalOperator::equal_icase},
    {"!=~"sv, RelationalOperator::not_equal_icase},
    {"~~"sv, RelationalOperator::matches_icase},
    {"!~~"sv, RelationalOperator::doesnt_match_icase},
    {"<"sv, RelationalOperator::less},
    {">="sv, RelationalOperator::greater_or_equal},
    {">"sv, RelationalOperator::greater},
    {"<="sv, RelationalOperator::less_or_equal},
    // aliases
    {"!<"sv, RelationalOperator::greater_or_equal},
    {"!>="sv, RelationalOperator::less},
    {"!>"sv, RelationalOperator::less_or_equal},
    {"!<="sv, RelationalOperator::greater},
});
}  // namespace

std::ostream &operator<<(std::ostream &os, const RelationalOperator &relOp) {
    for (const auto &[op_name, op] : operator_names) {
        if (op == relOp) {
            return os << op_name;
        }
    }
    return os;
}

RelationalOperator relationalOperatorForName(std::string_view name) {
    for (const auto &[op_name, op] : operator_names) {
        if (op_name == name) {
            return op;
        }
    }
    throw std::runtime_error("invalid operator '" + std::string{name} + "'");
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
