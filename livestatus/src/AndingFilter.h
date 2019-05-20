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

#ifndef AndingFilter_h
#define AndingFilter_h

#include "config.h"  // IWYU pragma: keep
#include <bitset>
#include <chrono>
#include <cstdint>
#include <functional>
#include <iosfwd>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include "Filter.h"
#include "contact_fwd.h"
class Column;
class Row;

class AndingFilter : public Filter {
    struct Secret {};

public:
    static std::unique_ptr<Filter> make(Kind kind, const Filters &subfilters);
    bool accepts(Row row, const contact *auth_user,
                 std::chrono::seconds timezone_offset) const override;
    std::unique_ptr<Filter> partialFilter(
        std::function<bool(const Column &)> predicate) const override;
    std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const override;
    std::optional<int32_t> greatestLowerBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const override;
    std::optional<int32_t> leastUpperBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const override;
    std::optional<std::bitset<32>> valueSetLeastUpperBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const override;
    std::unique_ptr<Filter> copy() const override;
    std::unique_ptr<Filter> negate() const override;
    bool is_tautology() const override;
    bool is_contradiction() const override;
    Filters disjuncts() const override;
    Filters conjuncts() const override;

    // NOTE: This is effectively private, but it can't be declared like this
    // because of std::make_unique.
    AndingFilter(Kind kind, Filters subfilters, Secret /*unused*/)
        : Filter(kind), _subfilters(std::move(subfilters)) {}

private:
    Filters _subfilters;

    std::ostream &print(std::ostream &os) const override;
};

#endif  // AndingFilter_h
