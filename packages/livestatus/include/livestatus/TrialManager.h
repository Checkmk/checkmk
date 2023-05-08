// Copyright (C) 2019 Checkmk GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TrialManager_h
#define TrialManager_h

#include <chrono>
#include <stdexcept>
#include <string>

#include "livestatus/ChronoUtils.h"

class TrialManager {
    const std::chrono::system_clock::time_point installed_;
    const bool is_licensed_;

public:
    TrialManager(std::chrono::system_clock::time_point installed,
                 bool is_licensed)
        : installed_(installed), is_licensed_{is_licensed} {}

    constexpr static auto trialPeriod() { return mk::days{30}; }
    constexpr static size_t maxServicesInTrialPeriod() { return 750; }

    void validateServiceCount(std::chrono::system_clock::time_point now,
                              size_t num_services) const {
        if (is_licensed_ || !isTrialExpired(now)) {
            return;
        }

        if (num_services > maxServicesInTrialPeriod()) {
            auto days = mk::ticks<mk::days>(trialPeriod());
            throw std::runtime_error(
                "The " + std::to_string(days) +
                "-day trial is over and you are exceeding the limits of your Checkmk installation. Only max. " +
                std::to_string(maxServicesInTrialPeriod()) +
                " services with max. 1 site are possible, not " +
                std::to_string(num_services) +
                " services. Please apply a valid license or adjust your configuration to be able to monitor again. Exiting...");
        }
    }

    [[nodiscard]] bool isTrialExpired(
        std::chrono::system_clock::time_point now) const {
        return now > installed_ + trialPeriod();
    }

    [[nodiscard]] std::string state(
        std::chrono::system_clock::time_point now) const {
        return is_licensed_          ? "licensed"
               : isTrialExpired(now) ? "expired trial"
                                     : "active trial";
    }
};

#endif  // TrialManager_h
