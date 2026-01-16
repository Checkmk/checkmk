// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "livestatus/global_counters.h"

#include <chrono>
#include <compare>
#include <mutex>
#include <optional>
#include <ratio>
#include <vector>

#include "livestatus/ChronoUtils.h"

using namespace std::chrono_literals;

namespace {
constexpr int num_counters = 21;

struct CounterInfo {
    std::mutex mutex;
    double value{};
    double last_value{};
    double rate{};
};

// NOLINTNEXTLINE(cert-err58-cpp,cppcoreguidelines-avoid-non-const-global-variables)
std::vector<CounterInfo> counters(num_counters);

CounterInfo &counter(Counter which) {
    return counters[static_cast<int>(which)];
}

// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
std::optional<std::chrono::system_clock::time_point> last_statistics_update;
constexpr auto statistics_interval = 5s;
constexpr double rating_weight = 0.25;

double lerp(double a, double b, double t) { return ((1 - t) * a) + (t * b); }
}  // namespace

void counterReset(Counter which) {
    auto &c = counter(which);
    const std::scoped_lock sl{c.mutex};
    c.value = 0.0;
    c.last_value = 0.0;
    c.rate = 0.0;
}

void counterSet(Counter which, double value) {
    auto &c = counter(which);
    const std::scoped_lock sl{c.mutex};
    c.value = value;
}

void counterIncrement(Counter which) {
    auto &c = counter(which);
    const std::scoped_lock sl{c.mutex};
    c.value++;
}

void counterIncrementBy(Counter which, std::size_t value) {
    auto &c = counter(which);
    const std::scoped_lock sl{c.mutex};
    c.value += double(value);
}

double counterValue(Counter which) {
    auto &c = counter(which);
    const std::scoped_lock sl{c.mutex};
    return c.value;
}

double counterRate(Counter which) {
    auto &c = counter(which);
    const std::scoped_lock sl{c.mutex};
    return c.rate;
}

void do_statistics() {
    auto now = std::chrono::system_clock::now();
    if (!last_statistics_update) {
        last_statistics_update = now;
        return;
    }
    auto age = now - *last_statistics_update;
    if (age < statistics_interval) {
        return;
    }
    last_statistics_update = now;
    for (auto &c : counters) {
        const std::scoped_lock sl{c.mutex};
        auto age_secs = mk::ticks<std::chrono::seconds>(age);
        const double old_rate = c.rate;
        const double new_rate = (c.value - c.last_value) / double(age_secs);
        c.rate = lerp(old_rate, new_rate, old_rate == 0 ? 1 : rating_weight);
        c.last_value = c.value;
    }
}
