// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef DictColumn_h
#define DictColumn_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>

#include "Column.h"
#include "Filter.h"
#include "Row.h"
#include "opids.h"
enum class AttributeKind;
class Aggregator;
class RowRenderer;

#ifdef CMC
#include "contact_fwd.h"
#else
// TODO(sp) Why on earth is "contact_fwd.h" not enough???
#include "nagios.h"
#endif

struct DictColumn : Column {
    using value_type = std::unordered_map<std::string, std::string>;
    // The next two classes may be implemented later for consistency.
    // However, they are not currently necessary.
    // class Constant;
    // class Reference;
    template <class T>
    class Callback;
    using Column::Column;
    virtual ~DictColumn() override = default;

    [[nodiscard]] ColumnType type() const override { return ColumnType::dict; }

    void output(Row row, RowRenderer &r, const contact *auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override = 0;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    virtual value_type getValue(Row row) const = 0;
};

template <class T>
class DictColumn::Callback : public DictColumn {
public:
    using function_type = std::function<value_type(const T &)>;
    Callback(const std::string &name, const std::string &description,
             const ColumnOffsets &offsets, const function_type &f)
        : DictColumn{name, description, offsets}, f_{f} {}
    ~Callback() override = default;

    value_type getValue(Row row) const override {
        const T *data = columnData<T>(row);
        return data == nullptr ? Default : f_(*data);
    }

private:
    value_type Default{};
    function_type f_;
};

#endif
