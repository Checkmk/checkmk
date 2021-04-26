// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListLambdaColumn_h
#define ListLambdaColumn_h

#include <chrono>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <variant>
#include <vector>

#include "Column.h"
#include "Filter.h"
#include "Row.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;
class RowRenderer;

struct ListColumn : Column {
    using value_type = std::vector<std::string>;
    class Constant;
    class Reference;
    template <class T>
    class Callback;
    using Column::Column;
    ~ListColumn() override = default;

    [[nodiscard]] ColumnType type() const override { return ColumnType::list; }

    void output(Row row, RowRenderer& r, const contact* auth_user,
                std::chrono::seconds timezone_offset) const override;

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string& value) const override;

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory factory) const override;

    // TODO(sp) What we actually want here is a stream of strings, not a
    // concrete container.
    virtual value_type getValue(Row row, const contact* auth_user,
                                std::chrono::seconds timezone_offset) const = 0;
};

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty vector.
template <class T>
class ListColumn::Callback : public ListColumn {
    using f0_t = std::function<value_type(const T&)>;
    using f1_t = std::function<value_type(const T&, const contact*)>;
    using function_type = std::variant<f0_t, f1_t>;

public:
    Callback(const std::string& name, const std::string& description,
             const ColumnOffsets& offsets, function_type f)
        : ListColumn{name, description, offsets}, f_{std::move(f)} {}
    ~Callback() override = default;

    value_type getValue(
        Row row, const contact* auth_user,
        std::chrono::seconds /*timezone_offset*/) const override {
        const T* data = columnData<T>(row);
        if (std::holds_alternative<f0_t>(f_)) {
            return data == nullptr ? Default : std::get<f0_t>(f_)(*data);
        }
        if (std::holds_alternative<f1_t>(f_)) {
            return data == nullptr ? Default
                                   : std::get<f1_t>(f_)(*data, auth_user);
        }
        throw std::runtime_error("unreachable");
    }

private:
    const value_type Default{};
    function_type f_;
};

class ListColumn::Constant : public ListColumn {
public:
    // NOTE: clangd-11 and cppcheck disagree, shut up cppcheck >:-)
    Constant(const std::string& name, const std::string& description,
             // cppcheck-suppress passedByValue
             value_type x)
        : ListColumn{name, description, {}}, x_{std::move(x)} {}
    ~Constant() override = default;
    value_type getValue(Row /*row*/, const contact* /*auth_user*/,
                        std::chrono::seconds /*timezone_offset*/
    ) const override {
        return x_;
    }

private:
    const value_type x_;
};

class ListColumn::Reference : public ListColumn {
public:
    Reference(const std::string& name, const std::string& description,
              const value_type& x)
        : ListColumn{name, description, {}}, x_{x} {}
    ~Reference() override = default;
    value_type getValue(Row /*row*/, const contact* /*auth_user*/,
                        std::chrono::seconds /*timezone_offset*/
    ) const override {
        return x_;
    }

private:
    const value_type& x_;
};

#endif
