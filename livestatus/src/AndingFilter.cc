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

#include "AndingFilter.h"
#include <algorithm>
#include <iterator>
#include <memory>
#include <ostream>
#include <type_traits>
#include <vector>
#include "Filter.h"
#include "OringFilter.h"
#include "Row.h"

// static
std::unique_ptr<Filter> AndingFilter::make(Kind kind,
                                           const Filters &subfilters) {
    Filters filters;
    for (const auto &filter : subfilters) {
        if (filter->is_contradiction()) {
            return OringFilter::make(kind, {});
        }
        auto conjuncts = filter->conjuncts();
        filters.insert(filters.end(),
                       std::make_move_iterator(conjuncts.begin()),
                       std::make_move_iterator(conjuncts.end()));
    }
    return filters.size() == 1 ? std::move(filters[0])
                               : std::make_unique<AndingFilter>(
                                     kind, std::move(filters), Secret());
}

bool AndingFilter::accepts(Row row, const contact *auth_user,
                           std::chrono::seconds timezone_offset) const {
    return std::all_of(
        _subfilters.cbegin(), _subfilters.cend(), [&](const auto &filter) {
            return filter->accepts(row, auth_user, timezone_offset);
        });
}

std::unique_ptr<Filter> AndingFilter::partialFilter(
    std::function<bool(const Column &)> predicate) const {
    Filters filters;
    std::transform(
        _subfilters.cbegin(), _subfilters.cend(), std::back_inserter(filters),
        [&](const auto &filter) { return filter->partialFilter(predicate); });
    return make(kind(), filters);
}

std::optional<std::string> AndingFilter::stringValueRestrictionFor(
    const std::string &column_name) const {
    for (const auto &filter : _subfilters) {
        if (auto value = filter->stringValueRestrictionFor(column_name)) {
            return {value};
        }
    }
    return {};
}

std::optional<int32_t> AndingFilter::greatestLowerBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    std::optional<int32_t> result;
    for (const auto &filter : _subfilters) {
        if (auto glb =
                filter->greatestLowerBoundFor(column_name, timezone_offset)) {
            result = result ? std::max(*result, *glb) : glb;
        }
    }
    return result;
}

std::optional<int32_t> AndingFilter::leastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    std::optional<int32_t> result;
    for (const auto &filter : _subfilters) {
        if (auto lub =
                filter->leastUpperBoundFor(column_name, timezone_offset)) {
            result = result ? std::min(*result, *lub) : lub;
        }
    }
    return result;
}

std::optional<std::bitset<32>> AndingFilter::valueSetLeastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    std::optional<std::bitset<32>> result;
    for (const auto &filter : _subfilters) {
        if (auto lub = filter->valueSetLeastUpperBoundFor(column_name,
                                                          timezone_offset)) {
            result = result ? (*result & *lub) : lub;
        }
    }
    return result;
}

std::unique_ptr<Filter> AndingFilter::copy() const {
    return make(kind(), conjuncts());
}

std::unique_ptr<Filter> AndingFilter::negate() const {
    Filters filters;
    std::transform(_subfilters.cbegin(), _subfilters.cend(),
                   std::back_inserter(filters),
                   [](const auto &filter) { return filter->negate(); });
    return OringFilter::make(kind(), filters);
}

bool AndingFilter::is_tautology() const { return _subfilters.empty(); }

bool AndingFilter::is_contradiction() const { return false; }

Filters AndingFilter::disjuncts() const {
    Filters filters;
    filters.push_back(copy());
    return filters;
}

Filters AndingFilter::conjuncts() const {
    Filters filters;
    std::transform(_subfilters.cbegin(), _subfilters.cend(),
                   std::back_inserter(filters),
                   [](const auto &filter) { return filter->copy(); });
    return filters;
}

std::ostream &AndingFilter::print(std::ostream &os) const {
    for (const auto &filter : _subfilters) {
        os << *filter << "\\n";
    }
    switch (kind()) {
        case Kind::row:
            os << "And";
            break;
        case Kind::stats:
            os << "StatsAnd";
            break;
        case Kind::wait_condition:
            os << "WaitConditionAnd";
            break;
    }
    return os << ": " << _subfilters.size();
}
