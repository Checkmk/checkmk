// Copyright (C) 2019 Checkmk GmbH - License: Check_MK Enterprise License
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef TrialManager_h
#define TrialManager_h

#include <chrono>
#include <cstddef>
#include <filesystem>
#include <string>

class TrialManager {
    const std::chrono::system_clock::time_point state_file_created_;
    const bool is_licensed_;

public:
    TrialManager(std::chrono::system_clock::time_point state_file_created,
                 bool is_licensed)
        : state_file_created_{state_file_created}, is_licensed_{is_licensed} {}

    constexpr static auto trialPeriod() { return std::chrono::days{30}; }

    constexpr static size_t maxServicesInTrialPeriod() { return 750; }

    void validateServiceCount(std::chrono::system_clock::time_point now,
                              size_t num_services) const;

    [[nodiscard]] bool isTrialExpired(
        std::chrono::system_clock::time_point now) const;

    [[nodiscard]] std::string state(
        std::chrono::system_clock::time_point now) const;
};

// TODO(sp) Find a better place for this.
namespace mk {
std::chrono::system_clock::time_point state_file_created(
    const std::filesystem::path &state_file_created_file,
    std::chrono::system_clock::time_point default_creation_time);

bool is_licensed(const std::filesystem::path &licensed_state_file);

TrialManager validate_license(
    std::chrono::system_clock::time_point state_file_created, bool is_licensed,
    std::chrono::system_clock::time_point now, size_t num_services);
}  // namespace mk

#endif  // TrialManager_h
