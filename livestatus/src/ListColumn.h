// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef ListColumn_h
#define ListColumn_h

// We use `std::transform` but IWYU does not want the header.
#include <algorithm>  // IWYU pragma: keep
#include <chrono>
#include <functional>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <variant>
#include <vector>

#include "Column.h"
#include "Filter.h"
#include "ListFilter.h"
#include "Renderer.h"
#include "Row.h"
#include "auth.h"
#include "contact_fwd.h"
#include "opids.h"
class Aggregator;

namespace column::detail {
// Specialize this function in the classes deriving ListColumn.
template <class U>
std::string serialize(const U &);

template <>
inline std::string serialize(const std::string &s) {
    return s;
}
}  // namespace column::detail

template <class U>
struct ListColumnRenderer {
    using value_type = U;
    virtual ~ListColumnRenderer() = default;
    virtual void output(ListRenderer &l, const U &value) const = 0;
};

template <class U>
struct SimpleListColumnRenderer : ListColumnRenderer<U> {
    void output(ListRenderer &l, const U &value) const override {
        l.output(column::detail::serialize<U>(value));
    }
};

// TODO(sp): Is there a way to have a default value in the template parameters?
// Currently it is hardwired to the empty vector.
template <class T, class U = std::string>
class ListColumn : public Column {
public:
    using f0_t = std::function<std::vector<U>(const T &)>;
    using f1_t = std::function<std::vector<U>(const T &, const Column &)>;
    using f2_t = std::function<std::vector<U>(const T &, const contact *)>;
    using f3_t = std::function<std::vector<U>(const T &, std::chrono::seconds)>;
    using function_type = std::variant<f0_t, f1_t, f2_t, f3_t>;
    using value_type = std::vector<std::string>;

    ListColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets,
               std::unique_ptr<ListColumnRenderer<U>> renderer, function_type f)
        : Column{name, description, offsets}
        , renderer_{std::move(renderer)}
        , f_{std::move(f)} {}
    ListColumn(const std::string &name, const std::string &description,
               const ColumnOffsets &offsets, function_type f)
        : ListColumn{name, description, offsets,
                     std::make_unique<SimpleListColumnRenderer<U>>(),
                     std::move(f)} {}

    [[nodiscard]] ColumnType type() const override { return ColumnType::list; }

    void output(Row row, RowRenderer &r, const User &user,
                std::chrono::seconds timezone_offset) const override {
        ListRenderer l{r};
        for (const auto &val :
             getRawValue(row, user.authUser(), timezone_offset)) {
            renderer_->output(l, val);
        }
    }

    [[nodiscard]] std::unique_ptr<Filter> createFilter(
        Filter::Kind kind, RelationalOperator relOp,
        const std::string &value) const override {
        return std::make_unique<ListFilter>(
            kind, name(),
            [this](Row row, const User &user,
                   std::chrono::seconds timezone_offset) {
                return getValue(row, user.authUser(), timezone_offset);
            },
            relOp, value, logger());
    }

    [[nodiscard]] std::unique_ptr<Aggregator> createAggregator(
        AggregationFactory /*factory*/) const override {
        throw std::runtime_error("aggregating on list column '" + name() +
                                 "' not supported");
    }

    // TODO(sp) What we actually want here is a stream of strings, not a
    // concrete container.
    virtual value_type getValue(Row row, const contact *auth_user,
                                std::chrono::seconds timezone_offset) const {
        auto raw_value = getRawValue(row, auth_user, timezone_offset);
        std::vector<std::string> values;
        std::transform(raw_value.begin(), raw_value.end(),
                       std::back_inserter(values),
                       column::detail::serialize<U>);
        return values;
    }

private:
    [[nodiscard]] std::vector<U> getRawValue(
        Row row, const contact *auth_user,
        std::chrono::seconds timezone_offset) const {
        const T *data = ListColumn<T, U>::template columnData<T>(row);
        if (data == nullptr) {
            return {};
        }
        if (std::holds_alternative<f0_t>(f_)) {
            return std::get<f0_t>(f_)(*data);
        }
        if (std::holds_alternative<f1_t>(f_)) {
            return std::get<f1_t>(f_)(*data, *this);
        }
        if (std::holds_alternative<f2_t>(f_)) {
            return std::get<f2_t>(f_)(*data, auth_user);
        }
        if (std::holds_alternative<f3_t>(f_)) {
            return std::get<f3_t>(f_)(*data, timezone_offset);
        }
        throw std::runtime_error("unreachable");
    }

    std::unique_ptr<ListColumnRenderer<U>> renderer_;
    function_type f_;
};

#endif
