// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/RRDConsolidate.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <iterator>
#include <limits>

namespace {
constexpr double NaN = std::numeric_limits<double>::quiet_NaN();
}

std::ostream &operator<<(std::ostream &os, const CF &cf) {
    return os << cf.string();
}

double MaxCF::init() {
    const double out = counter_;
    counter_ = NaN;
    return out;
}

void MaxCF::handle(double value) {
    if (std::isnan(value)) {
        return;
    }
    counter_ = std::isnan(counter_) ? value : std::max(counter_, value);
}

double MinCF::init() {
    const double out = counter_;
    counter_ = NaN;
    return out;
}

void MinCF::handle(double value) {
    if (std::isnan(value)) {
        return;
    }
    counter_ = std::isnan(counter_) ? value : std::min(counter_, value);
}

double AvgCF::init() {
    const double out =
        nelem == 0 ? counter_ : counter_ / static_cast<double>(nelem);
    counter_ = NaN;
    nelem = 0;
    return out;
}

void AvgCF::handle(double value) {
    if (std::isnan(value)) {
        return;
    }
    counter_ = std::isnan(counter_) ? value : counter_ + value;
    nelem += 1;
}

double LastCF::init() {
    const double out = counter_;
    counter_ = NaN;
    return out;
}

void LastCF::handle(double value) { counter_ = value; }

std::vector<double> rrd_consolidate(const std::unique_ptr<CF> &cf,
                                    const std::vector<double> &input,
                                    std::size_t act_step, std::size_t target) {
    if (act_step >= target) {
        return input;
    }
    const std::size_t factor = target / act_step;
    auto out = std::vector<double>{};
    for (auto iter = input.begin(); iter != input.end(); iter++) {
        cf->handle(*iter);
        if (std::distance(input.begin(), iter) % factor == factor - 1) {
            out.emplace_back(cf->init());
        }
    }
    return out;
}
