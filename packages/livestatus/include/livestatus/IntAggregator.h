// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef IntAggregator_h
#define IntAggregator_h

#include <chrono>
#include <functional>
#include <utility>
#include <variant>

#include "livestatus/Aggregator.h"
#include "livestatus/Column.h"
#include "livestatus/User.h"
class Row;
class RowRenderer;
class User;

class IntAggregator : public Aggregator {
    using f0_t = std::function<int(Row)>;
    using f1_t = std::function<int(Row, const User &)>;
    using function_type = std::variant<f0_t, f1_t>;

public:
    IntAggregator(const AggregationFactory &factory, function_type f)
        : _aggregation{factory()}, f_{std::move(f)} {}

    void consume(Row row, const User &user,
                 std::chrono::seconds /*timezone_offset*/) override {
        if (std::holds_alternative<f0_t>(f_)) {
            _aggregation->update(std::get<f0_t>(f_)(row));
        } else if (std::holds_alternative<f1_t>(f_)) {
            _aggregation->update(std::get<f1_t>(f_)(row, user));
        } else {
            throw std::runtime_error("unreachable");
        }
    }

    void output(RowRenderer &r) const override {
        r.output(_aggregation->value());
    }

private:
    std::unique_ptr<Aggregation> _aggregation;
    const function_type f_;
};

#endif  // IntAggregator_h
