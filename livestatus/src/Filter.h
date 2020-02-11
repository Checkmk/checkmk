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

#ifndef Filter_h
#define Filter_h

#include "config.h"  // IWYU pragma: keep
#include <bitset>
#include <chrono>
#include <cstdint>
#include <functional>
#include <iosfwd>
#include <memory>
#include <optional>
#include <string>
#include <vector>
#include "contact_fwd.h"
class Column;
class Filter;
class Row;

using Filters = std::vector<std::unique_ptr<Filter>>;

/// A propositional formula over column value relations, kept in negation normal
/// form.
class Filter {
public:
    enum Kind { row, stats, wait_condition };

    explicit Filter(Kind kind) : _kind(kind) {}
    virtual ~Filter();
    [[nodiscard]] Kind kind() const { return _kind; }
    virtual bool accepts(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) const = 0;
    virtual std::unique_ptr<Filter> partialFilter(
        std::function<bool(const Column &)> predicate) const = 0;

    // TODO(sp) We might be able to unify all the methods below if we make the
    // underlying lattice structure explicit, i.e. provide a set type and
    // corresponding meet/join operations. Perhaps we can even get rid of the
    // std::optional by making the lattice bounded, i.e. by providing bottom/top
    // values.
    [[nodiscard]] virtual std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const;
    [[nodiscard]] virtual std::optional<int32_t> greatestLowerBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const;
    [[nodiscard]] virtual std::optional<int32_t> leastUpperBoundFor(
        const std::string &column_name,
        std::chrono::seconds timezone_offset) const;
    [[nodiscard]] virtual std::optional<std::bitset<32>>
    valueSetLeastUpperBoundFor(const std::string &column_name,
                               std::chrono::seconds timezone_offset) const;

    [[nodiscard]] virtual std::unique_ptr<Filter> copy() const = 0;
    [[nodiscard]] virtual std::unique_ptr<Filter> negate() const = 0;

    /// Checks for a *syntactic* tautology.
    [[nodiscard]] virtual bool is_tautology() const = 0;

    /// Checks for a *syntactic* contradiction.
    [[nodiscard]] virtual bool is_contradiction() const = 0;

    /// Combining the returned filters with *or* yields a filter equivalent to
    /// the current one.
    [[nodiscard]] virtual Filters disjuncts() const = 0;

    /// Combining the returned filters with *and* yields a filter equivalent to
    /// the current one.
    [[nodiscard]] virtual Filters conjuncts() const = 0;

    friend std::ostream &operator<<(std::ostream &os, const Filter &filter) {
        return filter.print(os);
    }

private:
    const Kind _kind;
    virtual std::ostream &print(std::ostream &os) const = 0;
};

#endif  // Filter_h
