// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Column_h
#define Column_h

#include <chrono>
#include <cstddef>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "livestatus/Filter.h"
#include "livestatus/Logger.h"
#include "livestatus/Row.h"

class Aggregation;
class Aggregator;
class Sorter;
enum class RelationalOperator;
class RowRenderer;
class User;

template <typename T>
const T *offset_cast(const void *ptr, size_t offset) {
    // This is our ugly "pointer shifting technology", so we need those casts.
    // NOLINTNEXTLINE(cppcoreguidelines-pro-bounds-pointer-arithmetic,cppcoreguidelines-pro-type-reinterpret-cast)
    return reinterpret_cast<const T *>(reinterpret_cast<const char *>(ptr) +
                                       offset);
}

enum class ColumnType {
    int_,
    double_,
    string,
    list,
    time,
    dictdouble,
    dictstr,
    blob,
    null
};

using AggregationFactory = std::function<std::unique_ptr<Aggregation>()>;

class ColumnOffsets {
public:
    using shifter = std::function<const void *(Row)>;
    [[nodiscard]] ColumnOffsets add(const shifter &shifter) const;
    [[nodiscard]] const void *shiftPointer(Row row) const;

private:
    std::vector<shifter> shifters_;
};

class Column {
public:
    Column(std::string name, std::string description, ColumnOffsets offsets);
    virtual ~Column() = default;

    [[nodiscard]] std::string name() const { return _name; }
    [[nodiscard]] std::string description() const { return _description; }
    [[nodiscard]] ColumnOffsets offsets() const { return _offsets; }

    template <typename T>
    [[nodiscard]] const T *columnData(Row row) const {
        return static_cast<const T *>(shiftPointer(row));
    }

    [[nodiscard]] virtual ColumnType type() const = 0;

    virtual void output(Row row, RowRenderer &r, const User &user,
                        std::chrono::seconds timezone_offset) const = 0;

    [[nodiscard]] virtual std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const = 0;

    [[nodiscard]] virtual std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const = 0;

    [[nodiscard]] virtual std::unique_ptr<Sorter> createSorter() const = 0;

    [[nodiscard]] Logger *logger() const { return &_logger; }

private:
    mutable ThreadNameLogger _logger;
    std::string _name;
    std::string _description;
    ColumnOffsets _offsets;

    [[nodiscard]] const void *shiftPointer(Row row) const;
};

#endif  // Column_h
