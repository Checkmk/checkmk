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

#ifndef Column_h
#define Column_h

#include "config.h"  // IWYU pragma: keep
#include <chrono>
#include <cstddef>
#include <functional>
#include <memory>
#include <string>
#include <vector>
#include "Filter.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregation;
class Aggregator;
class Logger;
class RowRenderer;

template <typename T>
const T *offset_cast(const void *ptr, size_t offset) {
    // cppcheck is too dumb to see that this is just pointer arithmetic... :-/
    // cppcheck-suppress invalidPointerCast
    return reinterpret_cast<const T *>(reinterpret_cast<const char *>(ptr) +
                                       offset);
}

enum class ColumnType { int_, double_, string, list, time, dict, blob, null };

using AggregationFactory = std::function<std::unique_ptr<Aggregation>()>;

class Column {
public:
    using Offsets = std::vector<int>;
    Column(std::string name, std::string description, Offsets);
    virtual ~Column() = default;

    [[nodiscard]] std::string name() const { return _name; }
    [[nodiscard]] std::string description() const { return _description; }

    template <typename T>
    [[nodiscard]] const T *columnData(Row row) const {
        return static_cast<const T *>(shiftPointer(row));
    }

    [[nodiscard]] virtual ColumnType type() const = 0;

    virtual void output(Row row, RowRenderer &r, const contact *auth_user,
                        std::chrono::seconds timezone_offset) const = 0;

    [[nodiscard]] virtual std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const = 0;

    [[nodiscard]] virtual std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const = 0;

    [[nodiscard]] Logger *logger() const { return _logger; }

private:
    Logger *const _logger;
    std::string _name;
    std::string _description;
    Offsets _offsets;

    [[nodiscard]] const void *shiftPointer(Row row) const;
};

#endif  // Column_h
