// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef NebTimeperiod_h
#define NebTimeperiod_h

#include "livestatus/Interface.h"
#include "neb/TimeperiodsCache.h"
#include "neb/nagios.h"

class NebTimeperiod : public ITimeperiod {
public:
    explicit NebTimeperiod(const ::timeperiod &timeperiod)
        : timeperiod_{timeperiod} {}
    [[nodiscard]] std::string name() const override { return timeperiod_.name; }
    [[nodiscard]] std::string alias() const override {
        return timeperiod_.alias;
    }
    [[nodiscard]] bool isActive() const override {
        return g_timeperiods_cache->inTimeperiod(&timeperiod_);
    }
    [[nodiscard]] std::vector<std::chrono::system_clock::time_point>
    transitions(std::chrono::seconds /* timezone_offset */) const override {
        return {};
    }

    [[nodiscard]] int32_t numTransitions() const override { return 2; }

    [[nodiscard]] int32_t nextTransitionId() const override { return 1; }

    [[nodiscard]] std::chrono::system_clock::time_point nextTransitionTime()
        const override {
        return std::chrono::system_clock::from_time_t(0);
    }

private:
    const ::timeperiod &timeperiod_;
};

#endif  // NebTimeperiod_h
