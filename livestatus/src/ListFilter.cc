// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "ListFilter.h"

#include "Logger.h"
#include "RegExp.h"

namespace {
RelationalOperator relOpForElement(RelationalOperator relOp) {
    switch (relOp) {
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
            return relOp;
        case RelationalOperator::less:
        case RelationalOperator::greater_or_equal:
            return RelationalOperator::equal;
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            return RelationalOperator::equal_icase;
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
            // optimization: do not create a RegExp later
            return RelationalOperator::less;
    };
    return relOp;  // make the compiler happy...
}
}  // namespace

ListFilter::ListFilter(Kind kind, const ListColumn &column,
                       RelationalOperator relOp, const std::string &value)
    : ColumnFilter(kind, column.name(), relOp, value)
    , _column(column)
    , _regExp(makeRegExpFor(relOpForElement(relOp), value)) {}

bool ListFilter::accepts(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) const {
    switch (oper()) {
        case RelationalOperator::equal:
            if (!value().empty()) {
                Informational(_column.logger())
                    << "Sorry, equality for lists implemented only for emptiness";
                return false;
            }
            return !any(row, auth_user, timezone_offset,
                        [](const std::string & /*unused*/) { return true; });
        case RelationalOperator::not_equal:
            if (!value().empty()) {
                Informational(_column.logger())
                    << "Sorry, inequality for lists implemented only for emptiness";
                return false;
            }
            return any(row, auth_user, timezone_offset,
                       [](const std::string & /*unused*/) { return true; });
        case RelationalOperator::matches:
        case RelationalOperator::matches_icase:
            return any(
                row, auth_user, timezone_offset,
                [&](const std::string &elem) { return _regExp->search(elem); });
        case RelationalOperator::doesnt_match:
        case RelationalOperator::doesnt_match_icase:
            return !any(
                row, auth_user, timezone_offset,
                [&](const std::string &elem) { return _regExp->search(elem); });
        case RelationalOperator::greater_or_equal:
        case RelationalOperator::less_or_equal:
            return any(
                row, auth_user, timezone_offset,
                [&](const std::string &elem) { return _regExp->match(elem); });
        case RelationalOperator::less:
        case RelationalOperator::greater:
            return !any(
                row, auth_user, timezone_offset,
                [&](const std::string &elem) { return _regExp->match(elem); });
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
            Informational(_column.logger())
                << "Sorry. Operator " << oper()
                << " for list columns not implemented.";
            return false;
    }
    return false;  // unreachable
}

std::optional<std::string> ListFilter::stringValueRestrictionFor(
    const std::string &column_name) const {
    if (column_name != columnName()) {
        return {};  // wrong column
    }
    switch (oper()) {
        case RelationalOperator::greater_or_equal:
            return {value()};
        case RelationalOperator::equal:
        case RelationalOperator::not_equal:
        case RelationalOperator::matches:
        case RelationalOperator::doesnt_match:
        case RelationalOperator::equal_icase:
        case RelationalOperator::not_equal_icase:
        case RelationalOperator::matches_icase:
        case RelationalOperator::doesnt_match_icase:
        case RelationalOperator::less:
        case RelationalOperator::greater:
        case RelationalOperator::less_or_equal:
            return {};
    }
    return {};  // unreachable
}

std::unique_ptr<Filter> ListFilter::copy() const {
    return std::make_unique<ListFilter>(*this);
}

std::unique_ptr<Filter> ListFilter::negate() const {
    return std::make_unique<ListFilter>(
        kind(), _column, negateRelationalOperator(oper()), value());
}
