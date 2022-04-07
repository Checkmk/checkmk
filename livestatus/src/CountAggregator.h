// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CountAggregator_h
#define CountAggregator_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstdint>

#include "Aggregator.h"
class Filter;
class Row;
class RowRenderer;
class User;

class CountAggregator : public Aggregator {
public:
    explicit CountAggregator(const Filter *filter)
        : _filter(filter), _count(0) {}
    void consume(Row row, const User &user,
                 std::chrono::seconds timezone_offset) override;
    void output(RowRenderer &r) const override;

private:
    const Filter *const _filter;
    std::uint32_t _count;
};

#endif  // CountAggregator_h
