// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/AndingFilter.h"

#include <algorithm>
#include <bitset>
#include <iterator>
#include <optional>
#include <ostream>
#include <vector>

#include "livestatus/OringFilter.h"
#include "livestatus/Row.h"

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

bool AndingFilter::accepts(Row row, const User &user,
                           std::chrono::seconds timezone_offset) const {
    return std::ranges::all_of(_subfilters, [&](const auto &filter) {
        return filter->accepts(row, user, timezone_offset);
    });
}

std::unique_ptr<Filter> AndingFilter::partialFilter(
    columnNamePredicate predicate) const {
    Filters filters;
    std::ranges::transform(
        _subfilters, std::back_inserter(filters),
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
    // NOLINTNEXTLINE(clang-analyzer-cplusplus.NewDeleteLeaks)
    return make(kind(), conjuncts());
}

std::unique_ptr<Filter> AndingFilter::negate() const {
    Filters filters;
    std::ranges::transform(_subfilters, std::back_inserter(filters),
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
    std::ranges::transform(_subfilters, std::back_inserter(filters),
                           [](const auto &filter) { return filter->copy(); });
    return filters;
}

const ColumnFilter *AndingFilter::as_column_filter() const { return nullptr; };

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
