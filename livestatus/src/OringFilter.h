// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef OringFilter_h
#define OringFilter_h

#include "config.h"  // IWYU pragma: keep

#include <bitset>
#include <chrono>
#include <cstdint>
#include <iosfwd>
#include <memory>
#include <optional>
#include <string>
#include <utility>

#include "Filter.h"
class Row;
class User;

class OringFilter : public Filter {
    struct Secret {};

public:
    static std::unique_ptr<Filter> make(Kind kind, const Filters &subfilters);
    [[nodiscard]] bool accepts(
        Row row, const User &user,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::unique_ptr<Filter> partialFilter(
        columnNamePredicate predicate) const override;
    [[nodiscard]] std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const override;
    [[nodiscard]] std::optional<int32_t> greatestLowerBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::optional<int32_t> leastUpperBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::optional<std::bitset<32>> valueSetLeastUpperBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const override;
    [[nodiscard]] std::unique_ptr<Filter> copy() const override;
    [[nodiscard]] std::unique_ptr<Filter> negate() const override;
    [[nodiscard]] bool is_tautology() const override;
    [[nodiscard]] bool is_contradiction() const override;
    [[nodiscard]] Filters disjuncts() const override;
    [[nodiscard]] Filters conjuncts() const override;

    // NOTE: This is effectively private, but it can't be declared like this
    // because of std::make_unique.
    OringFilter(Kind kind, Filters subfilters, Secret /*unused*/)
        : Filter(kind), _subfilters(std::move(subfilters)) {}

private:
    Filters _subfilters;

    std::ostream &print(std::ostream &os) const override;
};

#endif  // OringFilter_h
