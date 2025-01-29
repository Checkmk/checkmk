// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef CountAggregator_h
#define CountAggregator_h

#include <chrono>
#include <cstdint>

#include "livestatus/Aggregator.h"
class Filter;

class CountAggregator : public Aggregator {
public:
    explicit CountAggregator(const Filter *filter) : _filter{filter} {}
    void consume(Row row, const User &user,
                 std::chrono::seconds timezone_offset) override;
    void output(RowRenderer &r) const override;

private:
    const Filter *const _filter;
    std::uint32_t _count{0};
};

#endif  // CountAggregator_h
