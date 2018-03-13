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
#include <chrono>
#include <cstdint>
#include <functional>
#include <iosfwd>
#include <memory>
#include <optional>
#include <string>
#include "contact_fwd.h"
class Column;
class Row;

enum class LogicalOperator {
    and_,
    or_,
    stats_and,
    stats_or,
    wait_condition_and,
    wait_condition_or
};

LogicalOperator dual(LogicalOperator op);

std::ostream &operator<<(std::ostream &os, const LogicalOperator &op);

class Filter {
public:
    virtual ~Filter();
    virtual bool accepts(Row row, const contact *auth_user,
                         std::chrono::seconds timezone_offset) const = 0;
    virtual std::unique_ptr<Filter> partialFilter(
        std::function<bool(const Column &)> predicate) const = 0;
    virtual std::optional<std::string> stringValueRestrictionFor(
        const std::string &column_name) const;
    virtual void findIntLimits(const std::string &column_name, int *lower,
                               int *upper,
                               std::chrono::seconds timezone_offset) const;
    virtual bool optimizeBitmask(const std::string &column_name, uint32_t *mask,
                                 std::chrono::seconds timezone_offset) const;
    virtual std::unique_ptr<Filter> copy() const = 0;
    virtual std::unique_ptr<Filter> negate() const = 0;

    friend std::ostream &operator<<(std::ostream &os, const Filter &filter) {
        return filter.print(os);
    }

private:
    virtual std::ostream &print(std::ostream &os) const = 0;
};

#endif  // Filter_h
