// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef BlobColumn_h
#define BlobColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "Column.h"
#include "Filter.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class RowRenderer;

namespace detail {
class BlobColumn : public Column {
public:
    class Constant;
    class Reference;
    using Column::Column;

    [[nodiscard]] ColumnType type() const override { return ColumnType::blob; }

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    [[nodiscard]] virtual std::unique_ptr<std::vector<char>> getValue(
        Row row) const = 0;
};
}  // namespace detail

struct BlobColumn : ::detail::BlobColumn {
    // This is for the legacy code and will go away once
    // the callers are ported to BlobLambdaColumn.
    using ::detail::BlobColumn::BlobColumn;
};

template <class T>
class BlobLambdaColumn : public ::detail::BlobColumn {
public:
    using ::detail::BlobColumn::Constant;
    using ::detail::BlobColumn::Reference;
    BlobLambdaColumn(std::string name, std::string description,
                     ColumnOffsets offsets,
                     std::function<std::vector<char>(const T &)> f)
        : BlobColumn(std::move(name), std::move(description),
                     std::move(offsets))
        , get_value_{std::move(f)} {}
    ~BlobLambdaColumn() override = default;
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row row) const override {
        const T *data = columnData<T>(row);
        return std::make_unique<std::vector<char>>(
            data == nullptr ? std::vector<char>{} : get_value_(*data));
    }

private:
    const std::function<std::vector<char>(const T &)> get_value_;
};

class detail::BlobColumn::Constant : public ::detail::BlobColumn {
public:
    Constant(std::string name, std::string description, std::vector<char> v)
        : detail::BlobColumn(std::move(name), std::move(description), {})
        , v{std::move(v)} {};
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row /*row*/) const override {
        return std::make_unique<std::vector<char>>(v);
    }

private:
    const std::vector<char> v;
};

class detail::BlobColumn::Reference : public ::detail::BlobColumn {
public:
    Reference(std::string name, std::string description,
              const std::vector<char> &v)
        : BlobColumn(std::move(name), std::move(description), {}), v{v} {};
    [[nodiscard]] std::unique_ptr<std::vector<char>> getValue(
        Row /*row*/) const override {
        return std::make_unique<std::vector<char>>(v);
    }

private:
    const std::vector<char> &v;
};

#endif  // BlobColumn_h
