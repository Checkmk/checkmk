// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "global_counters.h"

#include <ctime>
#include <mutex>
#include <vector>

namespace {
constexpr int num_counters = 10;

struct CounterInfo {
    std::mutex mutex;
    double value;
    double last_value;
    double rate;
};

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
std::vector<CounterInfo> counters(num_counters);

CounterInfo &counter(Counter which) {
    return counters[static_cast<int>(which)];
}

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
time_t last_statistics_update = 0;
constexpr time_t statistics_interval = 5;
constexpr double rating_weight = 0.25;

double lerp(double a, double b, double t) { return (1 - t) * a + t * b; }
}  // namespace

void counterReset(Counter which) {
    auto &c = counter(which);
    std::lock_guard<std::mutex> lg(c.mutex);
    c.value = 0.0;
    c.last_value = 0.0;
    c.rate = 0.0;
}

void counterIncrement(Counter which) {
    auto &c = counter(which);
    std::lock_guard<std::mutex> lg(c.mutex);
    c.value++;
}

double counterValue(Counter which) {
    auto &c = counter(which);
    std::lock_guard<std::mutex> lg(c.mutex);
    return c.value;
}

double counterRate(Counter which) {
    auto &c = counter(which);
    std::lock_guard<std::mutex> lg(c.mutex);
    return c.rate;
}

void do_statistics() {
    time_t now = time(nullptr);
    if (last_statistics_update == 0) {
        last_statistics_update = now;
        return;
    }
    time_t delta_time = now - last_statistics_update;
    if (delta_time < statistics_interval) {
        return;
    }
    last_statistics_update = now;
    for (auto &c : counters) {
        std::lock_guard<std::mutex> lg(c.mutex);
        double old_rate = c.rate;
        double new_rate = (c.value - c.last_value) / delta_time;
        c.rate = lerp(old_rate, new_rate, old_rate == 0 ? 1 : rating_weight);
        c.last_value = c.value;
    }
}
