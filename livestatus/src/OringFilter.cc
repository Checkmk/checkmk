// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OringFilter.h"

#include <algorithm>
#include <iterator>
#include <ostream>
#include <type_traits>
#include <vector>

#include "AndingFilter.h"
#include "Row.h"

// static
std::unique_ptr<Filter> OringFilter::make(Kind kind,
                                          const Filters &subfilters) {
    Filters filters;
    for (const auto &filter : subfilters) {
        if (filter->is_tautology()) {
            return AndingFilter::make(kind, {});
        }
        auto disjuncts = filter->disjuncts();
        filters.insert(filters.end(),
                       std::make_move_iterator(disjuncts.begin()),
                       std::make_move_iterator(disjuncts.end()));
    }
    return filters.size() == 1 ? std::move(filters[0])
                               : std::make_unique<OringFilter>(
                                     kind, std::move(filters), Secret());
}

bool OringFilter::accepts(Row row, const User &user,
                          std::chrono::seconds timezone_offset) const {
    return std::any_of(_subfilters.cbegin(), _subfilters.cend(),
                       [&](const auto &filter) {
                           return filter->accepts(row, user, timezone_offset);
                       });
}

std::unique_ptr<Filter> OringFilter::partialFilter(
    columnNamePredicate predicate) const {
    Filters filters;
    std::transform(
        _subfilters.cbegin(), _subfilters.cend(), std::back_inserter(filters),
        [&](const auto &filter) { return filter->partialFilter(predicate); });
    return make(kind(), filters);
}

std::optional<std::string> OringFilter::stringValueRestrictionFor(
    const std::string &column_name) const {
    std::optional<std::string> restriction;
    for (const auto &filter : _subfilters) {
        if (auto current = filter->stringValueRestrictionFor(column_name)) {
            if (!restriction) {
                restriction = current;  // First restriction? Take it.
            } else if (restriction != current) {
                return {};  // Different restrictions? Give up.
            }
        } else {
            return {};  // No restriction for subfilter? Give up.
        }
    }
    return restriction;
}

std::optional<int32_t> OringFilter::greatestLowerBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    std::optional<int32_t> result;
    for (const auto &filter : _subfilters) {
        if (auto glb =
                filter->greatestLowerBoundFor(column_name, timezone_offset)) {
            result = result ? std::min(*result, *glb) : glb;
        }
    }
    return result;
}

std::optional<int32_t> OringFilter::leastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    std::optional<int32_t> result;
    for (const auto &filter : _subfilters) {
        if (auto lub =
                filter->leastUpperBoundFor(column_name, timezone_offset)) {
            result = result ? std::max(*result, *lub) : lub;
        }
    }
    return result;
}

std::optional<std::bitset<32>> OringFilter::valueSetLeastUpperBoundFor(
    const std::string &column_name,
    std::chrono::seconds timezone_offset) const {
    std::optional<std::bitset<32>> result;
    for (const auto &filter : _subfilters) {
        if (auto lub = filter->valueSetLeastUpperBoundFor(column_name,
                                                          timezone_offset)) {
            result = result ? (*result | *lub) : lub;
        }
    }
    return result;
}

std::unique_ptr<Filter> OringFilter::copy() const {
    return make(kind(), disjuncts());
}

std::unique_ptr<Filter> OringFilter::negate() const {
    Filters filters;
    std::transform(_subfilters.cbegin(), _subfilters.cend(),
                   std::back_inserter(filters),
                   [](const auto &filter) { return filter->negate(); });
    return AndingFilter::make(kind(), filters);
}

bool OringFilter::is_tautology() const { return false; }

bool OringFilter::is_contradiction() const { return _subfilters.empty(); }

Filters OringFilter::disjuncts() const {
    Filters filters;
    std::transform(_subfilters.cbegin(), _subfilters.cend(),
                   std::back_inserter(filters),
                   [](const auto &filter) { return filter->copy(); });
    return filters;
}

Filters OringFilter::conjuncts() const {
    Filters filters;
    filters.push_back(copy());
    return filters;
}

std::ostream &OringFilter::print(std::ostream &os) const {
    for (const auto &filter : _subfilters) {
        os << *filter << "\\n";
    }
    switch (kind()) {
        case Kind::row:
            os << "Or";
            break;
        case Kind::stats:
            os << "StatsOr";
            break;
        case Kind::wait_condition:
            os << "WaitConditionOr";
            break;
    }
    return os << ": " << _subfilters.size();
}
